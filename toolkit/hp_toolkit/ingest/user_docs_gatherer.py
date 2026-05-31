# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""User-facing documentation gatherer for Stage-1 boundary inference (H.6).

Per locked tuning H.6: the boundary agent currently sees only
protocol-shaped evidence — HTTP listeners, gRPC servers, CLI entries.
It misses the semantic *who-and-why* of each boundary, which lives
in user-facing docs (README "Usage" sections, `docs/tutorial/`,
`docs/howto/`, OpenAPI / GraphQL schemas).

This gatherer walks the doc corpus + harvests:

- **Usage excerpts** — markdown sections under "Usage" / "Getting Started" /
  "Quickstart" / "Examples" / "Tutorial" headings, preserved verbatim
- **Actor phrases** — noun phrases that name the external party
  ("the developer", "an SRE operator", "your application")
- **Intent phrases** — short verb phrases describing what the actor does
  ("query the catalog", "drill into a service")
- **API specs** — paths to OpenAPI / GraphQL / proto / schema files
  (typed boundary surface)

Output `intermediate/user-docs.json` is read by `hp-ingest-boundary` to:
- Name terminators by role rather than protocol
- Use the docs' own phrasing in terminator descriptions
- Identify boundary flows by intent, not just wire shape
- Surface optional / privileged terminator variants

Pure Python, no LLM. Cheap pass — text patterns over the docs corpus.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .docs_walker import DocCategory, DocCorpus, load_corpus


# Headings the gatherer treats as "usage territory". Matched
# case-insensitively. The section runs from the heading to the next
# heading of equal or shallower depth (or EOF).
_USAGE_HEADINGS = re.compile(
    r"^(#{1,6})\s+(usage|getting[-_ ]?started|quickstart|quick[-_ ]?start|"
    r"how[-_ ]?to(?:\s+use)?|tutorial|examples?|api(?:\s+reference)?|"
    r"using(?:\s+the\s+\w+)?)\b.*$",
    re.MULTILINE | re.IGNORECASE,
)

# Actor noun-phrase patterns. Captures the actor "role" rather than the
# protocol. These are heuristic — the boundary LLM refines them; the
# value here is surfacing what the docs treat as the external party.
_ACTOR_PHRASES = re.compile(
    r"\b(?:the|a|an|your)\s+("
    # Role-shaped nouns (matches "the developer", "an SRE", "the operator")
    r"developer|sre|operator|administrator|admin|user|customer|client|"
    r"caller|consumer|publisher|producer|subscriber|tenant|workspace|"
    r"team|squad|agent|application|service|monitor|dashboard|"
    r"telemetry[-_ ]?(?:producer|consumer|source|sink)|"
    r"\w+[-_ ]?engineer|\w+[-_ ]?owner|end[-_ ]?user"
    r")\b",
    re.IGNORECASE,
)

# Intent verb-phrase patterns — short verbal clauses describing what the
# actor does. Matched after an actor pattern.
_INTENT_PHRASES = re.compile(
    r"\b("
    r"query|querying|fetch|fetches|fetching|"
    r"create|creates|creating|delete|deletes|deleting|"
    r"submit|submits|submitting|publish|publishes|publishing|"
    r"subscribe|subscribes|subscribing|consume|consumes|consuming|"
    r"monitor|monitors|monitoring|inspect|inspects|inspecting|"
    r"observe|observes|observing|explore|explores|exploring|"
    r"manage|manages|managing|update|updates|updating|"
    r"trigger|triggers|triggering|drill|drills|drilling|"
    r"analyze|analyzes|analyzing|search|searches|searching"
    r")\s+(?:the\s+|their\s+|a\s+|an\s+|your\s+|some\s+)?(\w+(?:\s+\w+){0,2})\b",
    re.IGNORECASE,
)

# Code-block patterns — used to harvest examples
_FENCED_BLOCK = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)

# How many usage-section excerpts to keep per source file. Avoids blowing
# up token budget on doc-heavy projects.
_MAX_EXCERPTS_PER_FILE = 5

# Maximum bytes per usage excerpt. Longer sections truncated with
# `[…truncated…]`.
_MAX_EXCERPT_BYTES = 2_000


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class UsageExcerpt(BaseModel):
    """One markdown section flagged as usage territory."""

    source_file: str
    section_heading: str
    text: str                                # verbatim section content, possibly truncated


class CodeExample(BaseModel):
    """One fenced code block harvested from usage docs."""

    source_file: str
    language: Optional[str] = None
    body: str


class UserDocsHarvest(BaseModel):
    """`intermediate/user-docs.json` shape."""

    usage_excerpts: list[UsageExcerpt] = Field(default_factory=list)
    code_examples: list[CodeExample] = Field(default_factory=list)
    api_specs: list[str] = Field(default_factory=list)        # repo-relative paths

    # Cross-corpus aggregations — the boundary agent uses these to spot
    # the actors + intents the docs treat as canonical.
    actor_phrases: dict[str, int] = Field(default_factory=dict)    # phrase → frequency
    intent_phrases: dict[str, int] = Field(default_factory=dict)   # phrase → frequency


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def gather(corpus: DocCorpus, codebase_root: Path) -> UserDocsHarvest:
    """Walk the doc corpus + harvest user-facing-doc evidence for Stage 1."""
    root = codebase_root.resolve()
    out = UserDocsHarvest()
    actor_counter: Counter[str] = Counter()
    intent_counter: Counter[str] = Counter()

    for doc in corpus.files:
        # API specs surface as paths only — the boundary LLM reads them
        # directly when relevant (typed surfaces don't compress well)
        if doc.category == DocCategory.API_SPEC:
            out.api_specs.append(doc.path)
            continue

        # We only mine narrative docs for usage / actor / intent signal
        if doc.category not in (
            DocCategory.README,
            DocCategory.USAGE_DOC,
            DocCategory.OTHER_DOC,
        ):
            continue

        try:
            text = (root / doc.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # 1. Usage-section excerpts
        excerpts = _extract_usage_excerpts(text, doc.path)
        out.usage_excerpts.extend(excerpts)

        # 2. Code examples from those excerpts (high-precision territory)
        for excerpt in excerpts:
            for match in _FENCED_BLOCK.finditer(excerpt.text):
                lang, body = match.group(1) or None, match.group(2).strip()
                if not body:
                    continue
                # Cap example body length so noisy generated examples don't
                # blow the harvest size
                if len(body) > 500:
                    body = body[:500] + "\n# [...truncated...]"
                out.code_examples.append(CodeExample(
                    source_file=doc.path,
                    language=lang,
                    body=body,
                ))

        # 3. Actor + intent phrases across the whole doc (not just usage
        # sections — README intros frequently set the actor frame)
        for match in _ACTOR_PHRASES.finditer(text):
            actor_counter[match.group(1).lower().strip()] += 1
        for match in _INTENT_PHRASES.finditer(text):
            verb = match.group(1).lower()
            object_phrase = match.group(2).lower().strip()
            phrase = f"{verb} {object_phrase}"
            # Cap object-phrase to avoid catching noise like
            # "query the database schema with the migrations option"
            if len(object_phrase.split()) <= 3 and len(phrase) <= 50:
                intent_counter[phrase] += 1

    # Filter to phrases with ≥ 2 occurrences cross-corpus (1-offs are
    # usually documentation-internal references)
    out.actor_phrases = {p: c for p, c in actor_counter.most_common(50) if c >= 2}
    out.intent_phrases = {p: c for p, c in intent_counter.most_common(50) if c >= 2}

    # Deterministic sort: api_specs by path
    out.api_specs.sort()
    return out


def write_harvest(harvest: UserDocsHarvest, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(harvest.model_dump_json(indent=2))


def load_harvest(path: Path) -> UserDocsHarvest:
    return UserDocsHarvest.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

def _extract_usage_excerpts(text: str, source_path: str) -> list[UsageExcerpt]:
    """Find every usage-territory heading + return the section that
    follows (up to next equal-or-shallower heading or EOF)."""
    out: list[UsageExcerpt] = []
    matches = list(_USAGE_HEADINGS.finditer(text))
    if not matches:
        return []
    for i, m in enumerate(matches):
        if len(out) >= _MAX_EXCERPTS_PER_FILE:
            break
        heading = m.group(0).strip().lstrip("#").strip()
        depth = len(m.group(1))
        # Find next heading of equal or shallower depth
        start = m.end()
        end = len(text)
        for j in range(i + 1, len(matches)):
            jm = matches[j]
            if len(jm.group(1)) <= depth:
                end = jm.start()
                break
        # Also stop at any heading of equal-or-shallower depth that wasn't
        # itself a usage-heading match
        next_any_heading = re.search(
            r"^(#{1," + str(depth) + r"})\s+",
            text[start:end],
            re.MULTILINE,
        )
        if next_any_heading:
            end = start + next_any_heading.start()
        section = text[start:end].strip()
        if not section:
            continue
        if len(section) > _MAX_EXCERPT_BYTES:
            section = section[:_MAX_EXCERPT_BYTES] + "\n\n[…truncated by user_docs_gatherer…]"
        out.append(UsageExcerpt(
            source_file=source_path,
            section_heading=heading,
            text=section,
        ))
    return out


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse
    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(
        description="Gather user-facing documentation for Stage-1 boundary inference.",
    )
    parser.add_argument("--corpus", required=True, help="Path to docs-corpus.json")
    parser.add_argument("--codebase", required=True, help="Codebase root")
    parser.add_argument("--output", "-o", required=True, help="Where to write user-docs.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="0-user-docs", agent="user_docs_gatherer")

    corpus = load_corpus(Path(args.corpus))
    harvest = gather(corpus, Path(args.codebase))
    write_harvest(harvest, out_path)

    log_done(intermediate_dir, stage="0-user-docs", agent="user_docs_gatherer",
             excerpts=len(harvest.usage_excerpts),
             examples=len(harvest.code_examples),
             api_specs=len(harvest.api_specs),
             actor_phrases=len(harvest.actor_phrases),
             intent_phrases=len(harvest.intent_phrases))
    print(json.dumps({
        "excerpts": len(harvest.usage_excerpts),
        "examples": len(harvest.code_examples),
        "api_specs": len(harvest.api_specs),
        "actors_top_5": list(harvest.actor_phrases.keys())[:5],
        "intents_top_5": list(harvest.intent_phrases.keys())[:5],
    }, indent=2))


if __name__ == "__main__":
    _main()
