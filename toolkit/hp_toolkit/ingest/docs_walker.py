# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Shared documentation-corpus walker for the input-expansion extractors.

The Stage-0 scanner + significance filter intentionally drop documentation
(`README*`, `docs/`, `*.md`, etc.) so they don't pollute the production-code
candidate pool. But documentation is the highest-density source of
architectural prose, project vocabulary, user-intent narratives, and
external-actor descriptions — exactly what the input-expansion findings
(H.2 rationale, H.4 glossary, H.6 user docs, H.7 testbed scenarios) want.

`docs_walker.py` walks the repo once + emits a `DocCorpus` typed list of
doc-like files with category labels. Downstream extractors filter the
corpus by category + (optionally) by directory neighborhood to a target
candidate. This way the doc-walk cost is paid once for all four extractors
that follow in T6–T9.

The corpus is written to `intermediate/docs-corpus.json` so it's
inspectable, --resume-able, and shareable across the extractors that fire
in different stages.
"""

from __future__ import annotations

import json
import re
import subprocess
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────
# Doc categories
# ─────────────────────────────────────────────────────────────────────

class DocCategory(str, Enum):
    """How a doc file is most likely consumed by downstream extractors.

    Categories are exclusive — each file is assigned exactly one. The
    matching is heuristic + ordered (the first matching pattern wins),
    so more specific categories sit ahead of `OTHER_DOC` in the rules
    table below."""

    README = "readme"                        # README.md at any depth
    USAGE_DOC = "usage_doc"                  # docs/{tutorial,howto,quickstart,...}/*
    ARCHITECTURE_DOC = "architecture_doc"    # design / architecture notes
    PROPOSAL_DOC = "proposal_doc"            # proposals/ rfcs/
    ADR = "adr"                              # decisions/ adrs/ or *adr*.md
    GLOSSARY_DOC = "glossary_doc"            # GLOSSARY / TERMS / TERMINOLOGY
    API_SPEC = "api_spec"                    # openapi / graphql schema / .proto
    TESTBED_DOC = "testbed_doc"              # README inside a candidate testbed dir
    CHANGELOG = "changelog"                  # CHANGELOG / HISTORY — low-signal but capturable
    OTHER_DOC = "other_doc"                  # markdown that didn't match anything else


# Patterns are evaluated against the POSIX relative path. First match wins.
# Order matters: most-specific first. Categories with explicit directory
# patterns sit ahead of the generic `*.md → OTHER_DOC` fallback.
_CATEGORY_RULES: list[tuple[DocCategory, re.Pattern[str]]] = [
    # API specs — extension-driven, highest precision
    (DocCategory.API_SPEC, re.compile(r"\.(graphql|proto)$")),
    (DocCategory.API_SPEC, re.compile(r"(^|/)(openapi|swagger|schema)\.(ya?ml|json)$", re.IGNORECASE)),

    # Glossary first (it lives under docs/ but has a stronger signal)
    (DocCategory.GLOSSARY_DOC, re.compile(r"(^|/)(GLOSSARY|TERMS|TERMINOLOGY)\.(md|txt)$", re.IGNORECASE)),
    (DocCategory.GLOSSARY_DOC, re.compile(r"(^|/)docs?/glossary", re.IGNORECASE)),

    # ADR archives — many conventions
    (DocCategory.ADR, re.compile(r"(^|/)(decisions|adrs?)/", re.IGNORECASE)),
    (DocCategory.ADR, re.compile(r"(^|/)docs?/(decisions|adrs?)/", re.IGNORECASE)),
    (DocCategory.ADR, re.compile(r"adr[-_]?\d", re.IGNORECASE)),

    # Architecture / design notes
    (DocCategory.ARCHITECTURE_DOC, re.compile(r"(^|/)(architecture|design)/", re.IGNORECASE)),
    (DocCategory.ARCHITECTURE_DOC, re.compile(r"(^|/)docs?/(architecture|design)", re.IGNORECASE)),

    # Proposals / RFCs
    (DocCategory.PROPOSAL_DOC, re.compile(r"(^|/)(proposals?|rfcs?)/", re.IGNORECASE)),

    # Usage docs — tutorial / quickstart / howto / user-guide
    (DocCategory.USAGE_DOC, re.compile(
        r"(^|/)docs?/(user[-_]?guide|tutorial|howto|how[-_]to|usage|getting[-_]?started|quickstart|examples?)",
        re.IGNORECASE,
    )),
    (DocCategory.USAGE_DOC, re.compile(r"(^|/)examples?/.+\.md$", re.IGNORECASE)),

    # Changelog / history
    (DocCategory.CHANGELOG, re.compile(r"(^|/)(CHANGELOG|HISTORY|RELEASE[-_]?NOTES)", re.IGNORECASE)),

    # README at any depth (after the more-specific categories above so a
    # docs/architecture/README.md is classified ARCHITECTURE_DOC, not README)
    (DocCategory.README, re.compile(r"(^|/)README(\.md|\.rst|\.txt)?$", re.IGNORECASE)),

    # Generic markdown fallback
    (DocCategory.OTHER_DOC, re.compile(r"\.(md|rst|adoc|asciidoc)$", re.IGNORECASE)),
]


# Paths that even the doc walker should skip — vendored / node_modules /
# generated dirs sometimes carry their own READMEs we don't want to ingest
# as architecture signal.
_DOC_SKIP_PATTERNS = [
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"(^|/)\.tox/"),
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"(^|/)target/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"(^|/)\.next/"),
    re.compile(r"\.egg-info/"),
]


# ─────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────

class DocFile(BaseModel):
    """One doc-like file recorded by the walker."""

    path: str                            # repo-relative POSIX path
    category: DocCategory
    size_bytes: int
    size_lines: int
    title: Optional[str] = None          # first H1 / RST title if extractable
    notes: Optional[str] = None          # walker-side note (e.g. "skipped: binary")


class DocCorpus(BaseModel):
    """Output of one doc-walker pass — `intermediate/docs-corpus.json`."""

    root: str                            # absolute path of the codebase that was walked
    files: list[DocFile] = Field(default_factory=list)

    def by_category(self, category: DocCategory) -> list[DocFile]:
        return [f for f in self.files if f.category == category]

    def near(self, directory: str, *, categories: Iterable[DocCategory] | None = None) -> list[DocFile]:
        """Files whose path starts with `directory/` (repo-relative).

        If `categories` is given, also filter by category. Used by the
        rationale gatherer (T6) to find READMEs/docstrings inside a
        candidate module's `implemented_by[]` directory neighborhood."""
        prefix = directory.rstrip("/") + "/"
        cats = set(categories) if categories else None
        return [
            f for f in self.files
            if f.path.startswith(prefix) and (cats is None or f.category in cats)
        ]


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def walk_docs(root: Path) -> DocCorpus:
    """Enumerate doc-like files under `root` and classify each one.

    Uses `git ls-files` when available (so untracked / gitignored docs are
    excluded — matches the scanner's behavior); falls back to a recursive
    walk filtered by `_DOC_SKIP_PATTERNS`.

    Cheap pass — typically <1s on a 4000-file repo because doc files are a
    small fraction of the tree and we only read the first ~1KB per file to
    extract the title."""
    root = root.resolve()
    files: list[DocFile] = []
    for path in _enumerate_files(root):
        rel = path.relative_to(root).as_posix()
        if _should_skip(rel):
            continue
        category = _classify(rel)
        if category is None:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        size_bytes = stat.st_size
        size_lines = 0
        title: Optional[str] = None
        if size_bytes > 0 and category != DocCategory.API_SPEC:
            try:
                head = path.read_bytes()[:4096].decode("utf-8", errors="replace")
                size_lines = head.count("\n") + (1 if head and not head.endswith("\n") else 0)
                title = _extract_title(head)
            except OSError:
                pass
        files.append(DocFile(
            path=rel,
            category=category,
            size_bytes=size_bytes,
            size_lines=size_lines,
            title=title,
        ))
    files.sort(key=lambda f: (f.category.value, f.path))
    return DocCorpus(root=str(root), files=files)


def write_corpus(corpus: DocCorpus, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(corpus.model_dump_json(indent=2))


def load_corpus(path: Path) -> DocCorpus:
    return DocCorpus.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _enumerate_files(root: Path) -> list[Path]:
    if (root / ".git").is_dir():
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "ls-files"],
                capture_output=True, text=True, check=True,
            )
            return [root / line for line in result.stdout.splitlines() if line]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    out: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(root).parts):
            out.append(p)
    return out


def _should_skip(rel: str) -> bool:
    return any(p.search(rel) for p in _DOC_SKIP_PATTERNS)


def _classify(rel: str) -> Optional[DocCategory]:
    for cat, pattern in _CATEGORY_RULES:
        if pattern.search(rel):
            return cat
    return None


_H1_MD = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_TITLE_RST = re.compile(r"^(.+)\n[=]{3,}\s*$", re.MULTILINE)


def _extract_title(head: str) -> Optional[str]:
    m = _H1_MD.search(head)
    if m:
        return m.group(1).strip()
    m = _TITLE_RST.search(head)
    if m:
        return m.group(1).strip()
    return None


# ─────────────────────────────────────────────────────────────────────
# CLI entry — `python -m hp_toolkit.ingest.docs_walker <root> --output <path>`
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse

    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(description="Walk a repo for doc-like files + emit docs-corpus.json")
    parser.add_argument("root", help="Path to the codebase to walk")
    parser.add_argument("--output", "-o", required=True, help="Where to write docs-corpus.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="0-docs", agent="docs_walker", root=args.root)

    corpus = walk_docs(Path(args.root))
    write_corpus(corpus, out_path)

    counts = {cat.value: len(corpus.by_category(cat)) for cat in DocCategory}
    counts = {k: v for k, v in counts.items() if v}
    log_done(intermediate_dir, stage="0-docs", agent="docs_walker", docs=len(corpus.files), **counts)
    print(json.dumps({"docs": len(corpus.files), **counts}, indent=2))


if __name__ == "__main__":
    _main()
