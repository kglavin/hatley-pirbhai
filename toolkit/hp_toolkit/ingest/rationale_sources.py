# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Per-module-candidate rationale evidence gatherer.

Per locked tuning H.2: the architect agent currently produces terse,
structural module descriptions because its inputs are too narrow — it
sees `hp-graph.json` + `architecture-candidates.json`, but not the
README files, compose comments, or file-header docstrings that
actually carry the *why* of each module.

This module walks the candidate set + harvests the rationale-rich
content associated with each candidate:

- READMEs in or near the candidate's source directory
- Top-of-file docstrings / header comments for each implementation file
- Infra-file comments (Dockerfile / compose / k8s — the `# ...` lines
  that often label what a service is for)

Output: `intermediate/rationale-sources.json` keyed by candidate_id. The
hp-ingest-architect skill (per H.2.c) reads this alongside the existing
inputs and uses it to write a substantive `design_rationale` /
`design_justification` / `required_constraints` per module.

Bounded cost: only top-of-file (first ~30 lines) per implementation
file, plus the full content of any nearby README and infra comments.
On acme-cp-scale repos this is a few hundred KB of rationale
prose — small relative to the architect agent's total token budget.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .architecture_candidates import ArchitectureCandidates, ModuleCandidate
from .docs_walker import DocCategory, DocCorpus, load_corpus


# Maximum lines of file-header to capture per implementation file. The
# module docstring / file-level "what is this" prose almost always sits
# in the top of the file — beyond ~30 lines we're reading code, not
# rationale.
_MAX_HEADER_LINES = 30

# Maximum bytes of README to inline per candidate. READMEs longer than
# this are truncated with an ellipsis marker; the architect agent can
# still ask to read the full file if needed.
_MAX_README_BYTES = 8_000


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class RationaleEvidence(BaseModel):
    """All rationale-rich content harvested for one module candidate."""

    candidate_id: str
    candidate_dir: Optional[str] = None              # repo-relative directory the candidate lives in
    nearby_readmes: dict[str, str] = Field(default_factory=dict)   # path → contents (truncated)
    file_headers: dict[str, str] = Field(default_factory=dict)     # path → top-N lines as raw text
    infra_comments: list[str] = Field(default_factory=list)        # block-quoted strings of '#' lines from infra
    notes: Optional[str] = None                                    # walker-side note (skipped/empty/etc.)


class RationaleSources(BaseModel):
    """`intermediate/rationale-sources.json` shape."""

    by_candidate: dict[str, RationaleEvidence] = Field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def gather(
    candidates: ArchitectureCandidates,
    corpus: DocCorpus,
    codebase_root: Path,
) -> RationaleSources:
    """Walk every module candidate + harvest its rationale evidence.

    `corpus` is the shared docs-walker output (typed list of doc-like
    files with category labels). The walker is invoked once for the
    whole repo; here we slice it per-candidate via `corpus.near()`."""
    root = codebase_root.resolve()
    out = RationaleSources()
    for cand in candidates.modules:
        out.by_candidate[cand.candidate_id] = _gather_one(cand, corpus, root)
    return out


def write_sources(sources: RationaleSources, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(sources.model_dump_json(indent=2))


def load_sources(path: Path) -> RationaleSources:
    return RationaleSources.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _gather_one(
    cand: ModuleCandidate,
    corpus: DocCorpus,
    root: Path,
) -> RationaleEvidence:
    candidate_dir = _candidate_directory(cand)
    ev = RationaleEvidence(candidate_id=cand.candidate_id, candidate_dir=candidate_dir)

    if candidate_dir:
        ev.nearby_readmes = _harvest_readmes(corpus, candidate_dir, root)

    # Source file + related files → file headers (skip infra; we extract
    # those as comments in a separate pass below).
    files_for_headers = [cand.source_file, *cand.related_files]
    for f in files_for_headers:
        if not f or _is_infra_filename(f):
            continue
        text = _read_head(root / f)
        if text:
            ev.file_headers[f] = text

    # Infra-file comments (Dockerfile / compose / k8s) — the `# ...` lines
    # often carry rationale we wouldn't get from `image:` / `FROM` alone.
    infra_files = [f for f in files_for_headers if f and _is_infra_filename(f)]
    for f in infra_files:
        comments = _harvest_infra_comments(root / f)
        if comments:
            ev.infra_comments.extend(comments)

    return ev


def _candidate_directory(cand: ModuleCandidate) -> Optional[str]:
    """Repo-relative directory associated with the candidate.

    For Dockerfile / compose / package-manifest candidates the source
    file's parent dir is the right answer. For k8s / terraform resources
    that may live in a shared infra dir, we still use the file's parent
    as a starting point — better to have the wrong README than no
    README; the architect agent can ignore irrelevant context."""
    if not cand.source_file:
        return None
    return Path(cand.source_file).parent.as_posix() or "."


def _harvest_readmes(corpus: DocCorpus, candidate_dir: str, root: Path) -> dict[str, str]:
    """Return README contents for every README at or below `candidate_dir`.

    Uses the docs corpus's `near()` filter to locate READMEs, then reads
    each one fresh from disk (the corpus tracks paths, not contents)."""
    out: dict[str, str] = {}
    readmes = corpus.near(candidate_dir, categories=[DocCategory.README])
    # Also pull architecture / usage docs from the same neighborhood —
    # those are first-class rationale sources for the architect.
    extras = corpus.near(candidate_dir, categories=[
        DocCategory.ARCHITECTURE_DOC,
        DocCategory.USAGE_DOC,
    ])
    for doc in readmes + extras:
        try:
            content = (root / doc.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(content) > _MAX_README_BYTES:
            content = content[:_MAX_README_BYTES] + "\n\n[…truncated by rationale_sources…]"
        out[doc.path] = content
    return out


_INFRA_FILENAME_PATTERNS = [
    re.compile(r"(^|/)Dockerfile([.-].+)?$", re.IGNORECASE),
    re.compile(r"(^|/)docker-?compose(\.[a-zA-Z0-9_-]+)?\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)compose(\.[a-zA-Z0-9_-]+)?\.ya?ml$", re.IGNORECASE),
    re.compile(r"(^|/)k8s/.+\.ya?ml$", re.IGNORECASE),
    re.compile(r"\.tf$"),
]


def _is_infra_filename(rel: str) -> bool:
    return any(p.search(rel) for p in _INFRA_FILENAME_PATTERNS)


def _read_head(path: Path) -> Optional[str]:
    """Read the first `_MAX_HEADER_LINES` lines of `path`.

    Returns None on read error or empty file. Does not attempt to
    extract / strip the docstring — passes raw text through so the
    architect agent can read it in context (the comment markers + the
    surrounding code give useful structure)."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            head = []
            for i, line in enumerate(fh):
                if i >= _MAX_HEADER_LINES:
                    break
                head.append(line.rstrip("\n"))
    except OSError:
        return None
    text = "\n".join(head).strip()
    return text or None


# Detect `# ...` comment blocks in YAML / Dockerfile infra. A block is
# 1+ contiguous comment lines; we surface each block as one string so
# the architect agent can match it to the candidate it labels.
_INFRA_COMMENT_LINE = re.compile(r"^\s*#(.*)$")


def _harvest_infra_comments(path: Path) -> list[str]:
    """Pull `# comment` blocks out of an infra file.

    Returns one entry per contiguous comment block. Strips the leading
    `#` + one space; preserves indentation otherwise so the structure
    is readable."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    blocks: list[list[str]] = []
    current: list[str] = []
    for raw_line in content.splitlines():
        m = _INFRA_COMMENT_LINE.match(raw_line)
        if m:
            text = m.group(1)
            # Strip exactly one leading space (so "# hello" → "hello") but
            # preserve further indentation
            if text.startswith(" "):
                text = text[1:]
            current.append(text)
        else:
            if current:
                blocks.append(current)
                current = []
    if current:
        blocks.append(current)
    # Skip blocks that are obviously noise: shebangs, license headers
    # (which start with "Copyright" / "All rights reserved" patterns),
    # or short 1-line blocks that aren't even a sentence.
    out: list[str] = []
    for block in blocks:
        joined = "\n".join(block).strip()
        if not joined:
            continue
        if joined.startswith("!"):                          # shebang `#!`
            continue
        if "All rights reserved" in joined or "SPDX-License" in joined:
            continue
        if len(joined) < 15 and " " not in joined:           # one-word marker
            continue
        out.append(joined)
    return out


# ─────────────────────────────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse

    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(
        description="Gather per-candidate rationale evidence for the architect agent.",
    )
    parser.add_argument("--candidates", required=True,
                        help="Path to architecture-candidates.json")
    parser.add_argument("--corpus", required=True,
                        help="Path to docs-corpus.json (from docs_walker)")
    parser.add_argument("--codebase", required=True,
                        help="Codebase root (for reading file contents)")
    parser.add_argument("--output", "-o", required=True,
                        help="Where to write rationale-sources.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="5-rationale", agent="rationale_sources")

    candidates = ArchitectureCandidates.model_validate_json(Path(args.candidates).read_text())
    corpus = load_corpus(Path(args.corpus))
    sources = gather(candidates, corpus, Path(args.codebase))
    write_sources(sources, out_path)

    total_readmes = sum(len(e.nearby_readmes) for e in sources.by_candidate.values())
    total_headers = sum(len(e.file_headers) for e in sources.by_candidate.values())
    total_infra_blocks = sum(len(e.infra_comments) for e in sources.by_candidate.values())
    log_done(intermediate_dir, stage="5-rationale", agent="rationale_sources",
             candidates=len(sources.by_candidate),
             readmes=total_readmes, headers=total_headers, infra_blocks=total_infra_blocks)
    print(json.dumps({
        "candidates": len(sources.by_candidate),
        "readmes": total_readmes,
        "headers": total_headers,
        "infra_blocks": total_infra_blocks,
    }, indent=2))


if __name__ == "__main__":
    _main()
