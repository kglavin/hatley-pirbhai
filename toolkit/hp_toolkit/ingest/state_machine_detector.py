"""Stage 3 candidate extractor — pulls state names + transition pairs out of
files classified as `state-machine` by the role classifier.

Pure Python, no LLM. Reads `intermediate/scan.json` for state-machine files,
re-reads each file's content, and extracts state enums + transition tables
via a small set of regexes. Emits `intermediate/state-machine-candidates.json`.

The LLM agent (`hp-ingest-leaf` in CSPEC mode) takes these candidates and
writes a full HP CSPEC (states + transitions + events + actions). The
detector's job is just to surface "here's what looks like state-machine
shape" so the LLM has a starting point, not an authoritative model.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .schema import HpRoleHint, ProjectScan


# Patterns that pull state-enum members. Each pattern's last group is the
# enum name; per-match content following the declaration is parsed for
# the variant names separately.
_STATE_ENUM_HEADERS = [
    # Python: class FooState(Enum): / class FooState(str, Enum):
    re.compile(r"class\s+(\w*(?:State|Mode|Phase|Status))\s*\([^)]*Enum[^)]*\)\s*:"),
    # Rust: #[derive(...)] enum FooState { ... }
    re.compile(r"(?:#\[[^\]]*\]\s*)*enum\s+(\w*(?:State|Mode|Phase|Status))\s*\{"),
    # TypeScript: type / enum FooState = ...
    re.compile(r"(?:enum|type)\s+(\w*(?:State|Mode|Phase|Status))\s*[={]"),
]


# Within an enum body, pull each variant identifier. Captures common syntaxes:
# Python: `INITIALIZING = "initializing"` / `INITIALIZING = auto()`
# Rust: `Initializing,` / `Initializing(...)` / `Initializing { ... }`
# TS: `Initializing = "initializing"` / `Initializing,`
_VARIANT_PATTERN = re.compile(r"^\s*(\w+)\s*[,=({]", re.MULTILINE)


# Transition extraction patterns. Heuristic — picks up the most common
# table-style declarations.
_TRANSITION_PATTERNS = [
    # match self { State::A => State::B, ... }
    re.compile(r"(?:State::)?(\w+)\s*(?:=>|->)\s*(?:State::)?(\w+)"),
    # transitions: [{from: "A", to: "B"}, ...]
    re.compile(r"from\s*[:=]\s*['\"](\w+)['\"]\s*,?\s*to\s*[:=]\s*['\"](\w+)['\"]"),
    # transitions[A] = B
    re.compile(r"transitions\[['\"]?(\w+)['\"]?\]\s*=\s*['\"]?(\w+)['\"]?"),
]


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class TransitionCandidate(BaseModel):
    """One detected transition. Source and target are *raw extracted strings*
    from the file — the LLM normalizes them to HP state names."""

    source_state: str
    target_state: str


class StateMachineCandidate(BaseModel):
    """One state-machine candidate, rooted at a single file."""

    owning_file: str
    enum_name: Optional[str] = None
    states_extracted: list[str] = Field(default_factory=list)
    transitions_extracted: list[TransitionCandidate] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class StateMachineCandidates(BaseModel):
    """`intermediate/state-machine-candidates.json` shape."""

    candidates: list[StateMachineCandidate] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────────────────────────────

def extract_candidates(scan: ProjectScan, codebase_root: Path) -> StateMachineCandidates:
    """Walk scan output, surface state-machine candidates per file."""
    out: list[StateMachineCandidate] = []
    for f in scan.files:
        if not f.is_significant or f.hp_role_hint != HpRoleHint.STATE_MACHINE:
            continue
        abs_path = codebase_root / f.path
        content = _read_head(abs_path)
        if content is None:
            continue
        enum_name, states = _extract_state_enum(content)
        transitions = _extract_transitions(content, set(states))
        evidence = _gather_evidence(content)
        out.append(StateMachineCandidate(
            owning_file=f.path,
            enum_name=enum_name,
            states_extracted=states,
            transitions_extracted=transitions,
            evidence=evidence,
        ))
    return StateMachineCandidates(candidates=out)


def write_candidates(c: StateMachineCandidates, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(c.model_dump_json(indent=2))


# ─────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────

_MAX_HEAD = 32 * 1024     # 32K for state-machine sniffing (transitions tend to live deeper)


def _read_head(path: Path) -> Optional[str]:
    try:
        with path.open("rb") as fh:
            head = fh.read(_MAX_HEAD)
        if b"\x00" in head:
            return None
        return head.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _extract_state_enum(content: str) -> tuple[Optional[str], list[str]]:
    """Find the first state enum + its variant identifiers. Returns (name, variants).

    If multiple state enums exist in the same file, only the first is
    extracted — the LLM gets the file content and can locate the others."""
    for header in _STATE_ENUM_HEADERS:
        m = header.search(content)
        if not m:
            continue
        enum_name = m.group(1)
        # Find the body of the enum. Simple bracket-matching from the end of header.
        body_start = m.end()
        body = _extract_block_body(content[body_start:body_start + 4000])
        variants = _extract_variants(body)
        return enum_name, variants
    return None, []


def _extract_block_body(text: str) -> str:
    """Best-effort extraction of an enum body. For brace-delimited languages,
    returns text up to the matching closing brace; for Python, returns text
    up to the next dedent (heuristic: blank line followed by non-indented
    text)."""
    if text.lstrip().startswith("{"):
        depth = 0
        for i, ch in enumerate(text):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[:i]
        return text
    # Python-style: dedent detection
    lines: list[str] = []
    started = False
    for line in text.splitlines():
        if not started:
            if line.strip():
                started = True
                lines.append(line)
            continue
        if line and not line[0].isspace() and not line.startswith("#"):
            break
        lines.append(line)
    return "\n".join(lines)


def _extract_variants(body: str) -> list[str]:
    """Pull plausible enum variant identifiers from the body."""
    raw = _VARIANT_PATTERN.findall(body)
    # Filter: variants conventionally start with uppercase or are SCREAMING_SNAKE.
    # Filter out keywords commonly captured by mistake.
    blacklist = {"class", "enum", "def", "fn", "let", "const", "var", "type",
                 "impl", "self", "match", "if", "else", "for", "in", "to", "from",
                 "pub", "use", "mod", "struct", "interface"}
    out: list[str] = []
    seen: set[str] = set()
    for ident in raw:
        if ident.lower() in blacklist:
            continue
        if ident in seen:
            continue
        # Prefer CamelCase or SCREAMING_SNAKE
        if not (ident[0].isupper() or ident.isupper()):
            continue
        out.append(ident)
        seen.add(ident)
        if len(out) >= 30:
            break
    return out


def _extract_transitions(content: str, known_states: set[str]) -> list[TransitionCandidate]:
    """Pull transition pairs from the file. If `known_states` is non-empty,
    restrict to pairs where both endpoints are known states (filters most noise)."""
    pairs: list[TransitionCandidate] = []
    seen: set[tuple[str, str]] = set()
    for pat in _TRANSITION_PATTERNS:
        for m in pat.finditer(content):
            src, tgt = m.group(1), m.group(2)
            if known_states and (src not in known_states or tgt not in known_states):
                continue
            key = (src, tgt)
            if key in seen or src == tgt:
                continue
            seen.add(key)
            pairs.append(TransitionCandidate(source_state=src, target_state=tgt))
            if len(pairs) >= 60:
                return pairs
    return pairs


def _gather_evidence(content: str) -> list[str]:
    matched: list[str] = []
    for header in _STATE_ENUM_HEADERS:
        for m in header.finditer(content):
            start = content.rfind("\n", 0, m.start()) + 1
            end = content.find("\n", m.end())
            if end < 0:
                end = len(content)
            line = content[start:end].strip()
            if line and line not in matched:
                matched.append(line)
            if len(matched) >= 3:
                return matched
    return matched


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main(argv: Optional[list[str]] = None) -> int:
    import argparse
    from .progress_log import log_done, log_start
    parser = argparse.ArgumentParser(
        prog="hp_state_machine_detector",
        description="Extract Stage-3 state-machine candidates from scan.json.",
    )
    parser.add_argument("--scan",   required=True, help="Path to intermediate/scan.json")
    parser.add_argument("--codebase", required=True, help="Codebase root (for re-reading file content)")
    parser.add_argument("--output", required=True, help="Output path for state-machine-candidates.json")
    args = parser.parse_args(argv)

    intermediate = Path(args.output).parent
    log_start(intermediate, stage="3-prep", agent="state_machine_detector")

    scan_data = json.loads(Path(args.scan).read_text())
    scan = ProjectScan.model_validate(scan_data)
    candidates = extract_candidates(scan, Path(args.codebase))
    write_candidates(candidates, Path(args.output))
    print(f"wrote {args.output} ({len(candidates.candidates)} state-machine candidates)")

    log_done(intermediate, stage="3-prep", agent="state_machine_detector",
             count=len(candidates.candidates))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main())
