# Copyright (c) 2026 github.com/kglavin
# SPDX-License-Identifier: MIT

"""Domain-glossary extraction from documentation (H.4.a).

Per locked tuning H.4: every project of acme-cp's scale has a
ubiquitous language already formed in its docs — README headings,
"Definitions" sections, recurring capitalized terms, glossary tables,
the project's own naming for the things it does. The current
boundary / process / architect agents have no access to this; they
invent generic English (`proc_query_api`) instead of the project's
own vocabulary (`proc_explore_archi`).

This module walks the doc corpus (from `docs_walker.py`) + harvests
candidate glossary terms deterministically. The output feeds an
optional LLM curation pass (`hp-ingest-glossary` skill) which
ranks + categorizes + drops generics; the curated glossary is what
downstream naming agents (boundary / processes / leaf / architect)
load before producing names.

Bounded cost: pure Python over markdown + RST text. ~1s on a
acme-cp-scale doc corpus (~600 doc files).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .docs_walker import DocCategory, DocCorpus, load_corpus


# Minimum cross-file occurrence count for a CamelCase or capitalized
# phrase to graduate from "noise" to "glossary candidate". Below this,
# the term is almost always a one-off (a section heading in a single
# file, an example function name, etc.).
_MIN_FREQUENCY_GENERIC = 3

# Phrases extracted from explicit definition-list contexts (bold/italic,
# `Term:` patterns, glossary headings) are kept regardless of frequency —
# those are deliberate definitions, not statistical artifacts.
_DEFINITION_MIN_FREQUENCY = 1

# Common English words that pass capitalization checks but are noise.
# Filtering this kills 90% of "Heartbeat" / "ProjectModel" / "RuleTable" mixing with
# "The" / "Note" / "Example".
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
    "this", "that", "these", "those", "it", "its", "they", "them",
    "we", "you", "he", "she", "his", "her", "their", "our", "your",
    "if", "then", "else", "for", "while", "do", "while", "of", "in",
    "on", "at", "by", "to", "from", "with", "without", "as", "be",
    "been", "being", "have", "has", "had", "having", "will", "would",
    "should", "could", "may", "might", "must", "can", "shall",
    "i", "me", "my", "mine", "myself", "yourself",
    "note", "tip", "warning", "info", "example", "examples", "see",
    "todo", "fixme", "xxx", "nb",
    "yes", "no", "true", "false", "none", "null",
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "january", "february", "march", "april", "june", "july",
    "august", "september", "october", "november", "december",
}


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class GlossaryTermCandidate(BaseModel):
    """One candidate term harvested from docs. The LLM curator (H.4.b)
    refines this — drops generics, merges variants, categorizes."""

    term: str                                   # canonical form
    aliases: list[str] = Field(default_factory=list)   # case variants found
    definition_excerpt: Optional[str] = None    # surrounding paragraph if extracted from a definition
    sources: list[str] = Field(default_factory=list)   # repo-relative doc paths
    frequency: int = 0                          # total occurrences across the corpus
    extraction_kind: str = "frequency"          # how this term was surfaced — bold/definition/heading/frequency


class GlossaryCandidates(BaseModel):
    """`intermediate/glossary-candidates.json` — input to the LLM curator."""

    terms: list[GlossaryTermCandidate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Extraction patterns
# ─────────────────────────────────────────────────────────────────────

# **Heartbeat** or *ProjectModel* — markdown bold/italic capitalized. Single-word
# variant; multi-word also matched separately.
_BOLD_TERM = re.compile(r"\*\*([A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3})\*\*")
_ITAL_TERM = re.compile(r"(?<![\*\w])\*([A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3})\*(?!\*)")

# **Term:** definition  OR  **Term** — definition  OR  `Term`: definition
# Line-anchored to avoid matching mid-sentence.
_DEFINITION_LINE = re.compile(
    r"^\s*(?:\*\*|`)([A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3})(?:\*\*|`)\s*[:—–-]\s+(.+)$",
    re.MULTILINE,
)
# Also: Term: definition (no markdown markers) — only fires after a heading
# like "## Glossary" / "## Terms" / "## Concepts"
_BARE_DEFINITION_LINE = re.compile(
    r"^([A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3})\s*[:—–-]\s+(.+)$",
    re.MULTILINE,
)

# Section heading that flags definition-list territory: `## Glossary`,
# `# Terms`, `### Terminology`, `## Concepts`, `## Vocabulary`
_GLOSSARY_HEADING = re.compile(
    r"^#{1,6}\s+(?:Glossary|Terms|Terminology|Concepts|Vocabulary|Definitions)\b.*$",
    re.MULTILINE | re.IGNORECASE,
)
_HEADING_LINE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)

# CamelCase tokens — multi-word recognition: `HeartbeatStream`, `OrderManagement`.
# Avoids ALL-CAPS abbreviations (those tend to be acronyms, kept separately).
_CAMEL_CASE_TOKEN = re.compile(
    r"\b([A-Z][a-z][a-z\d]*(?:[A-Z][a-z\d]+)+)\b"
)

# All-caps abbreviations of length 2–8 (`BFF`, `CSPEC`, `DFD`). These are
# kept regardless of source — usually project-specific acronyms.
_ACRONYM = re.compile(r"\b([A-Z]{2,8})\b")

# Capitalized multi-word phrases (`Order Management`, `Bite Detector`).
# Matches 2–4 consecutive capitalized words.
_CAPITALIZED_PHRASE = re.compile(
    r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){1,3})\b"
)

# Markdown definition-list HTML: <dt>Term</dt><dd>Def</dd>
_DT_DD = re.compile(
    r"<dt[^>]*>(.+?)</dt>\s*<dd[^>]*>(.+?)</dd>",
    re.IGNORECASE | re.DOTALL,
)


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def extract(corpus: DocCorpus, codebase_root: Path) -> GlossaryCandidates:
    """Walk every doc file in `corpus` + harvest candidate glossary terms.

    Returns a GlossaryCandidates with one entry per unique canonical term;
    each entry aggregates aliases + source files + frequency across the
    whole corpus."""
    root = codebase_root.resolve()
    # canonical_lower -> aggregated state
    accum: dict[str, _TermAccum] = {}

    for doc in corpus.files:
        if doc.category in (DocCategory.CHANGELOG, DocCategory.OTHER_DOC) and doc.size_lines > 1000:
            # Skip long fallback docs — too much noise, not enough signal
            continue
        try:
            text = (root / doc.path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        _extract_from_doc(text, doc.path, doc.category, accum)

    # Filter + sort
    out: list[GlossaryTermCandidate] = []
    for state in accum.values():
        # Definition-quality terms always kept; frequency-only need ≥ threshold
        if state.has_definition_evidence:
            min_freq = _DEFINITION_MIN_FREQUENCY
        else:
            min_freq = _MIN_FREQUENCY_GENERIC
        if state.frequency < min_freq:
            continue
        out.append(GlossaryTermCandidate(
            term=state.canonical,
            aliases=sorted(state.aliases - {state.canonical}),
            definition_excerpt=state.best_definition,
            sources=sorted(state.sources),
            frequency=state.frequency,
            extraction_kind=state.extraction_kind,
        ))

    # Sort by frequency desc, then term asc (deterministic tie-break)
    out.sort(key=lambda t: (-t.frequency, t.term.lower()))
    return GlossaryCandidates(terms=out)


def write_candidates(c: GlossaryCandidates, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c.model_dump_json(indent=2))


def load_candidates(path: Path) -> GlossaryCandidates:
    return GlossaryCandidates.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

class _TermAccum:
    __slots__ = ("canonical", "aliases", "sources", "frequency",
                 "best_definition", "has_definition_evidence", "extraction_kind")

    def __init__(self, canonical: str) -> None:
        self.canonical = canonical
        self.aliases: set[str] = {canonical}
        self.sources: set[str] = set()
        self.frequency = 0
        self.best_definition: Optional[str] = None
        self.has_definition_evidence = False
        self.extraction_kind = "frequency"


def _extract_from_doc(
    text: str,
    rel_path: str,
    category: DocCategory,
    accum: dict[str, _TermAccum],
) -> None:
    """Process one doc's content + update the cross-doc accumulator."""
    # Detect glossary-section regions so we can pull bare `Term: def` lines
    # only inside them (otherwise the pattern matches sentences like
    # "Note: this is important").
    glossary_regions = _glossary_section_regions(text)

    # 1. Markdown bold / italic terms (high precision — author chose to emphasize)
    for match in _BOLD_TERM.finditer(text):
        _record(accum, match.group(1), rel_path, kind="bold",
                definition=_excerpt_around(text, match.start()))
    for match in _ITAL_TERM.finditer(text):
        _record(accum, match.group(1), rel_path, kind="italic",
                definition=_excerpt_around(text, match.start()))

    # 2. Markdown-formatted definition lines (Term: def with markdown emphasis)
    for match in _DEFINITION_LINE.finditer(text):
        term, definition = match.group(1), match.group(2)
        _record(accum, term, rel_path, kind="definition",
                definition=f"{term}: {definition.strip()}")

    # 3. Bare definition lines only inside glossary sections
    for region in glossary_regions:
        sub = text[region[0]:region[1]]
        for match in _BARE_DEFINITION_LINE.finditer(sub):
            term, definition = match.group(1), match.group(2)
            _record(accum, term, rel_path, kind="definition",
                    definition=f"{term}: {definition.strip()}")

    # 4. HTML <dt><dd> definition lists
    for match in _DT_DD.finditer(text):
        term, definition = _strip_html(match.group(1)), _strip_html(match.group(2))
        _record(accum, term, rel_path, kind="definition",
                definition=f"{term}: {definition.strip()}")

    # 5. Headings — these usually name a major concept of the doc
    for match in _HEADING_LINE.finditer(text):
        heading = match.group(1).strip()
        # Single-word capitalized headings are concept names; multi-word
        # ones are often instructions ("How to ...") — only the former
        if len(heading.split()) <= 3 and heading[:1].isupper() and not heading.endswith("?"):
            _record(accum, heading, rel_path, kind="heading", definition=None)

    # 6. CamelCase tokens (low-precision; frequency filter handles noise)
    for match in _CAMEL_CASE_TOKEN.finditer(text):
        _record(accum, match.group(1), rel_path, kind="frequency", definition=None)

    # 7. Acronyms (2–8 uppercase letters)
    for match in _ACRONYM.finditer(text):
        token = match.group(1)
        if token.lower() in _STOPWORDS:
            continue
        _record(accum, token, rel_path, kind="frequency", definition=None)

    # 8. Multi-word capitalized phrases — frequency-filtered too
    for match in _CAPITALIZED_PHRASE.finditer(text):
        _record(accum, match.group(1), rel_path, kind="frequency", definition=None)


def _record(
    accum: dict[str, _TermAccum],
    raw_term: str,
    path: str,
    *,
    kind: str,
    definition: Optional[str],
) -> None:
    term = raw_term.strip()
    if not term:
        return
    canonical = _canonicalize(term)
    if not canonical:
        return
    key = canonical.lower()
    state = accum.get(key)
    if state is None:
        state = _TermAccum(canonical)
        accum[key] = state
    state.aliases.add(term)
    # Prefer the more common casing (canonical = most-frequent alias variant);
    # for now just keep whatever first won.
    state.sources.add(path)
    state.frequency += 1
    if kind in ("bold", "italic", "definition", "heading"):
        # First definition wins — these are explicit so quality is uniform
        if definition and state.best_definition is None:
            state.best_definition = definition.strip()
        state.has_definition_evidence = True
        # Definition kinds are more informative than `frequency`
        if state.extraction_kind == "frequency":
            state.extraction_kind = kind


def _canonicalize(term: str) -> Optional[str]:
    """Return the canonical form for a candidate term, or None to reject."""
    term = term.strip().strip(".,;:!?'\"")
    if not term:
        return None
    parts = term.split()
    if len(parts) > 4:
        return None
    # Single-word stopword rejection (case-insensitive)
    if len(parts) == 1 and term.lower() in _STOPWORDS:
        return None
    # Too short to be substantive
    if len(term) < 2:
        return None
    # Reject purely numeric
    if term.isdigit():
        return None
    return term


def _excerpt_around(text: str, position: int, *, window: int = 200) -> Optional[str]:
    """Return the sentence around `position` for definition context.

    Looks back to a sentence boundary (or `window` chars), forward to the
    next sentence boundary. Used to capture definition context for bold
    or italic terms (since those aren't necessarily on `Term: def` lines)."""
    start = max(0, position - window)
    end = min(len(text), position + window)
    # Find sentence boundaries within window
    snippet = text[start:end].replace("\n", " ").strip()
    if len(snippet) > 300:
        snippet = snippet[:300] + "…"
    return snippet or None


def _glossary_section_regions(text: str) -> list[tuple[int, int]]:
    """Return (start, end) byte-offsets of glossary-named sections.

    A region runs from a glossary heading to the next heading of equal
    or shallower depth (or EOF). Used to scope bare `Term: def` matching."""
    out: list[tuple[int, int]] = []
    for match in _GLOSSARY_HEADING.finditer(text):
        heading_start = match.start()
        depth = len(match.group(0)) - len(match.group(0).lstrip("#"))  # rough — count leading #
        depth = match.group(0).count("#", 0, depth) or 1
        # Find next heading of equal or shallower depth after this match
        cursor = match.end()
        next_heading = re.search(r"^(#{1," + str(depth) + r"})\s+", text[cursor:], re.MULTILINE)
        end = cursor + next_heading.start() if next_heading else len(text)
        out.append((heading_start, end))
    return out


_HTML_TAG = re.compile(r"<[^>]+>")


def _strip_html(s: str) -> str:
    return _HTML_TAG.sub("", s).strip()


# ─────────────────────────────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse

    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(
        description="Extract candidate glossary terms from the doc corpus.",
    )
    parser.add_argument("--corpus", required=True, help="Path to docs-corpus.json")
    parser.add_argument("--codebase", required=True, help="Codebase root")
    parser.add_argument("--output", "-o", required=True,
                        help="Where to write glossary-candidates.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="0-glossary", agent="glossary_extractor")

    corpus = load_corpus(Path(args.corpus))
    candidates = extract(corpus, Path(args.codebase))
    write_candidates(candidates, out_path)

    by_kind = Counter(t.extraction_kind for t in candidates.terms)
    log_done(intermediate_dir, stage="0-glossary", agent="glossary_extractor",
             terms=len(candidates.terms),
             definitions=by_kind.get("definition", 0) + by_kind.get("bold", 0) + by_kind.get("italic", 0))
    print(json.dumps({
        "terms": len(candidates.terms),
        "by_kind": dict(by_kind),
        "top_10": [t.term for t in candidates.terms[:10]],
    }, indent=2))


if __name__ == "__main__":
    _main()
