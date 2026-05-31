"""Purpose-built testbed detector + miner (H.7).

Per locked tuning H.7: production systems often ship with purpose-built
testbeds — top-level directories like `testbed/` on acme-cp that
exercise the system end-to-end with scenarios, fixtures, system spin-up
scripts, and assertions. These are **executable specifications** the
ingest currently treats as either noise (unit-test filter doesn't catch
them) or as spurious production architecture (their compose files become
candidate modules; their files inflate process clusters).

Two passes:

1. **Detect** (`detect_testbeds`) — heuristics-based walk of the codebase
   identifies directories scoring as testbeds. Per Q5: always-on with an
   `is_testbed_overrides` opt-out hook (callers can mark specific dirs as
   not-testbeds if a false positive). When ≥ 3 heuristics fire, flag as
   testbed.

2. **Mine** (`mine_testbed`) — per detected testbed, extract scenarios
   (function names + docstrings + assertion summaries), fixtures, setup
   data dirs, own compose / k8s topology, README excerpts.

Output: `intermediate/testbeds.json`. The boundary / processes / leaf /
architect agents read this as executable-spec evidence: scenario titles
inform operational use cases (Stage 1), scenario walk-throughs inform
process boundaries (Stage 2), assertions inform expected PSPEC outcomes
(Stage 4), testbed spin-up scripts are a separate deployment-config
class (Stage 5).

The `architecture_candidates.py` extractor will (in a follow-up commit)
read `intermediate/testbeds.json` + suppress testbed-dir compose/k8s
files from production-candidate inclusion. For now we just detect + mine
+ surface to the agents.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .scan import _enumerate_files  # reuse the scanner's git-aware enumerator


# Score threshold: a directory must accumulate at least this many
# heuristic hits to be flagged as a testbed.
_TESTBED_SCORE_THRESHOLD = 3

# Per-scenario file: how many functions to surface
_MAX_SCENARIOS_PER_FILE = 12

# Per-function docstring: cap length
_MAX_DOCSTRING_BYTES = 600


# Heuristic indicators of testbed-ness
_SCENARIO_FILENAME = re.compile(
    r"(^|/)(scenario|e2e|integration|acceptance|system|end[-_]?to[-_]?end|smoke)[-_]"
    r"|"
    r"(scenario|e2e|integration|acceptance|smoke)\.py$",
    re.IGNORECASE,
)

# Extensions that represent *executable* code (vs documentation). Per
# EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding G: only count
# scenario-shaped filenames toward "scenarios dominate" detection when
# the file is one of these. Markdown / RST / ADoc scenario-files are
# documentation, not executable specs.
_EXECUTABLE_SCENARIO_EXTENSIONS = {
    ".py", ".rs", ".go",
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp",
    ".js", ".ts", ".tsx", ".mjs",
    ".java", ".kt", ".scala",
    ".rb", ".sh", ".bash",
    ".feature",        # Gherkin/Cucumber acceptance specs
}


def _is_executable_scenario_file(rel_path: str) -> bool:
    ext = Path(rel_path).suffix.lower()
    return ext in _EXECUTABLE_SCENARIO_EXTENSIONS
_TESTBED_DIRNAME = re.compile(
    r"^(agent[-_]?gym|testbed|sim|simulator|harness|fixtures|integration|e2e|"
    r"acceptance|system[-_]?test|playground|sandbox|workbench)$",
    re.IGNORECASE,
)
_PYTEST_MARK = re.compile(
    r"@pytest\.mark\.(integration|e2e|slow|acceptance|system)",
)
_DEF_TEST = re.compile(
    r"^\s*(?:async\s+)?def\s+(test_\w+|scenario_\w+|e2e_\w+|smoke_\w+)\s*\([^)]*\)\s*(?:->[^:]*)?:",
    re.MULTILINE,
)
_DOCSTRING_AFTER_DEF = re.compile(
    r":\s*\n\s*(?:[\"']{3})(.+?)(?:[\"']{3})",
    re.DOTALL,
)
_ASSERT_LINE = re.compile(r"^\s*assert\s+(.+?)$", re.MULTILINE)


# ─────────────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────────────

class Scenario(BaseModel):
    """One scenario / e2e function within a testbed."""

    file: str
    function_name: str
    docstring: Optional[str] = None
    assertion_summary: Optional[str] = None     # first assertion as plain text


class Testbed(BaseModel):
    """One detected testbed + its mined contents."""

    name: str                                   # short slug
    directory: str                              # repo-relative dir path
    detection_score: int = 0
    detection_evidence: list[str] = Field(default_factory=list)

    # Mined content
    readme_files: list[str] = Field(default_factory=list)
    readme_excerpt: Optional[str] = None        # first ~1KB of the top README
    scenarios: list[Scenario] = Field(default_factory=list)
    fixture_files: list[str] = Field(default_factory=list)
    setup_data_dirs: list[str] = Field(default_factory=list)
    compose_files: list[str] = Field(default_factory=list)
    k8s_files: list[str] = Field(default_factory=list)
    dockerfiles: list[str] = Field(default_factory=list)


class TestbedHarvest(BaseModel):
    """`intermediate/testbeds.json` shape."""

    testbeds: list[Testbed] = Field(default_factory=list)

    @property
    def testbed_directories(self) -> set[str]:
        """Set of repo-relative directories that are inside a testbed.

        Used by downstream candidate extractors to suppress testbed files
        from production candidate pools."""
        return {tb.directory for tb in self.testbeds}


# ─────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────

def detect_and_mine(codebase_root: Path) -> TestbedHarvest:
    """Walk the codebase + detect testbeds + mine each.

    Single-pass entry point. The detection scoring is heuristic — see
    `_score_directory` for the rubric."""
    root = codebase_root.resolve()
    files = _enumerate_files(root)

    # Group files by their top-level directory under the repo root.
    # Testbeds are top-level (`testbed/`) or second-level
    # (`tests/integration/`) — we score every directory up to depth 2.
    by_dir: dict[str, list[Path]] = {}
    for f in files:
        try:
            rel = f.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        for depth in (1, 2):
            if len(parts) >= depth + 1:
                dir_path = "/".join(parts[:depth])
                by_dir.setdefault(dir_path, []).append(f)

    candidates: list[Testbed] = []
    seen_dirs: set[str] = set()

    # Score every directory; keep the highest-scoring root that contains
    # the others (prevents same testbed being detected at depth 1 + 2)
    for dir_path, dir_files in sorted(by_dir.items(), key=lambda kv: kv[0]):
        if any(dir_path.startswith(d + "/") for d in seen_dirs):
            continue
        score, evidence = _score_directory(dir_path, dir_files, root)
        if score >= _TESTBED_SCORE_THRESHOLD:
            tb = _mine_one(dir_path, dir_files, root, score, evidence)
            candidates.append(tb)
            seen_dirs.add(dir_path)

    return TestbedHarvest(testbeds=candidates)


def write_harvest(harvest: TestbedHarvest, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(harvest.model_dump_json(indent=2))


def load_harvest(path: Path) -> TestbedHarvest:
    return TestbedHarvest.model_validate_json(Path(path).read_text())


# ─────────────────────────────────────────────────────────────────────
# Internals — detection
# ─────────────────────────────────────────────────────────────────────

def _score_directory(dir_path: str, files: list[Path], root: Path) -> tuple[int, list[str]]:
    """Heuristic scoring of one directory. Returns (score, evidence-list).

    A directory must have *executable testbed signal* — a testbed-pattern
    name OR scenario-shaped Python files OR pytest @mark.integration
    markers. Compose / README / fixtures are supplementary; they exist
    on production service roots too, so they don't carry detection
    weight alone."""
    score = 0
    evidence: list[str] = []
    file_rels = [str(f.relative_to(root)) for f in files]

    # PRIMARY signals — without at least one of these, the dir isn't a testbed.
    has_testbed_name = bool(_TESTBED_DIRNAME.match(dir_path.split("/")[-1]))

    # Per EMBEDDED_FIRMWARE_TUNING_DESIGN.md finding G: scenario-shaped
    # filenames only count when the file is *executable* code, not
    # documentation. Without this, a docs/ dir full of `integration-guide.md`
    # / `system-test.md` files scores as a testbed (PX4 hit this).
    scenario_hits = sum(
        1 for p in file_rels
        if _SCENARIO_FILENAME.search(p) and _is_executable_scenario_file(p)
    )

    pytest_marker_hits = 0
    for p in file_rels[:50]:
        if not p.endswith(".py"):
            continue
        try:
            text = (root / p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _PYTEST_MARK.search(text):
            pytest_marker_hits += 1
            if pytest_marker_hits >= 3:
                break

    # A directory dominated by scenarios is a testbed; a production
    # codebase that happens to contain a few integration-test files is
    # not. The ratio matters more than the absolute count.
    py_total = sum(1 for p in file_rels if p.endswith(".py"))
    scenario_ratio = scenario_hits / py_total if py_total else 0.0
    scenarios_dominate = scenario_hits >= 2 and scenario_ratio >= 0.10

    has_primary_signal = (
        has_testbed_name
        or scenarios_dominate
        or pytest_marker_hits >= 2
    )
    if not has_primary_signal:
        return 0, [
            "no primary testbed signal (no testbed-pattern name, "
            "scenarios don't dominate the .py file pool, no pytest markers)"
        ]

    # Now score the primary signals (high weight)
    if has_testbed_name:
        score += 3
        evidence.append(f"dirname matches testbed pattern: '{dir_path.split('/')[-1]}'")
    if scenarios_dominate:
        score += 2
        evidence.append(
            f"scenarios dominate: {scenario_hits} scenario-shaped of {py_total} .py files "
            f"({scenario_ratio:.0%})"
        )
    elif scenario_hits == 1:
        score += 1
        evidence.append("contains 1 scenario-shaped file")
    if pytest_marker_hits >= 2:
        score += 2
        evidence.append(f"contains pytest @mark.integration/e2e/slow (≥{pytest_marker_hits} files)")

    # Supplementary signals (low weight, only count if primary already fired)
    if any(p.endswith(f"{dir_path}/README.md") for p in file_rels):
        score += 1
        evidence.append("has its own README.md")

    has_own_compose = any(
        re.search(r"(^|/)(compose|docker-compose)(\.[\w-]+)?\.ya?ml$", p)
        and p.startswith(dir_path + "/")
        for p in file_rels
    )
    has_own_dockerfile = any(
        Path(p).name.lower().startswith("dockerfile") and p.startswith(dir_path + "/")
        for p in file_rels
    )
    has_own_k8s = any(
        ("/k8s/" in p or "/kubernetes/" in p) and p.startswith(dir_path + "/")
        for p in file_rels
    )
    if has_own_compose or has_own_dockerfile or has_own_k8s:
        score += 1
        evidence.append("has own deployment artifacts (compose/Dockerfile/k8s)")

    if any(f"{dir_path}/fixtures/" in p or f"{dir_path}/data/" in p for p in file_rels):
        score += 1
        evidence.append("has fixtures/ or data/ subdir")

    return score, evidence


# ─────────────────────────────────────────────────────────────────────
# Internals — mining
# ─────────────────────────────────────────────────────────────────────

def _mine_one(
    dir_path: str,
    files: list[Path],
    root: Path,
    score: int,
    evidence: list[str],
) -> Testbed:
    # Use the full path-as-slug when nested so two testbeds at
    # `<repo>/X/test` and `<repo>/Y/test` don't collide on the slug
    # "test"; standalone top-level testbeds keep their single-segment
    # name (testbed, not just gym).
    name = _slug(dir_path.replace("/", "-"))
    file_rels = [str(f.relative_to(root)) for f in files]

    readme_files = [p for p in file_rels if Path(p).name.lower() == "readme.md"
                    and p.startswith(dir_path + "/")]
    readme_excerpt: Optional[str] = None
    if readme_files:
        try:
            readme_excerpt = (root / readme_files[0]).read_text(encoding="utf-8", errors="replace")
            if len(readme_excerpt) > 1200:
                readme_excerpt = readme_excerpt[:1200] + "\n\n[…truncated…]"
        except OSError:
            readme_excerpt = None

    compose_files = [p for p in file_rels
                     if re.search(r"(^|/)(compose|docker-compose)(\.[\w-]+)?\.ya?ml$", p)]
    k8s_files = [p for p in file_rels if "/k8s/" in p or "/kubernetes/" in p]
    dockerfiles = [p for p in file_rels if Path(p).name.lower().startswith("dockerfile")]

    fixture_files = [p for p in file_rels if "/fixtures/" in p]
    setup_data_dirs = sorted({
        "/".join(p.split("/")[:p.split("/").index("data") + 1])
        for p in file_rels if "/data/" in p.split("/data/")[0] + "/data/" and "/data/" in p
    }) if any("/data/" in p for p in file_rels) else []

    scenarios = _mine_scenarios(file_rels, root)

    return Testbed(
        name=name,
        directory=dir_path,
        detection_score=score,
        detection_evidence=evidence,
        readme_files=readme_files,
        readme_excerpt=readme_excerpt,
        scenarios=scenarios,
        fixture_files=fixture_files,
        setup_data_dirs=setup_data_dirs,
        compose_files=compose_files,
        k8s_files=k8s_files,
        dockerfiles=dockerfiles,
    )


def _mine_scenarios(file_rels: list[str], root: Path) -> list[Scenario]:
    """Walk each Python file in the testbed + extract function-level
    scenarios (def test_*, def scenario_*, def e2e_*).

    Per-function: name + docstring (cropped) + first assertion as plain
    text. Token-bounded so even a 200-scenario testbed produces a
    surveyable harvest."""
    out: list[Scenario] = []
    for p in file_rels:
        if not p.endswith(".py"):
            continue
        try:
            text = (root / p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not _DEF_TEST.search(text):
            continue
        per_file = 0
        for m in _DEF_TEST.finditer(text):
            if per_file >= _MAX_SCENARIOS_PER_FILE:
                break
            func_name = m.group(1)
            # Look at the body following the def to find docstring + first assert
            body_start = m.end()
            body_end = _next_def_position(text, body_start)
            body = text[body_start:body_end]
            doc_match = _DOCSTRING_AFTER_DEF.search(body)
            docstring: Optional[str] = None
            if doc_match:
                docstring = doc_match.group(1).strip()
                if len(docstring) > _MAX_DOCSTRING_BYTES:
                    docstring = docstring[:_MAX_DOCSTRING_BYTES] + "…"
            assert_match = _ASSERT_LINE.search(body)
            assertion_summary: Optional[str] = None
            if assert_match:
                assertion = assert_match.group(1).strip()
                if len(assertion) > 200:
                    assertion = assertion[:200] + "…"
                assertion_summary = assertion
            out.append(Scenario(
                file=p,
                function_name=func_name,
                docstring=docstring,
                assertion_summary=assertion_summary,
            ))
            per_file += 1
    return out


def _next_def_position(text: str, start: int) -> int:
    """Find the next `def ` at the same or shallower indent (rough — the
    docstring/assert extractor doesn't need perfect bounds)."""
    m = re.search(r"^\s*(?:async\s+)?def\s+\w+", text[start:], re.MULTILINE)
    if m:
        return start + m.start()
    return len(text)


_SLUG_REPLACE = re.compile(r"[^a-z0-9-]+")


def _slug(s: str) -> str:
    s = s.lower().replace("_", "-")
    s = _SLUG_REPLACE.sub("-", s).strip("-")
    return s or "testbed"


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def _main() -> None:
    import argparse
    from .progress_log import log_done, log_start

    parser = argparse.ArgumentParser(
        description="Detect + mine purpose-built testbeds (H.7).",
    )
    parser.add_argument("--codebase", required=True, help="Codebase root")
    parser.add_argument("--output", "-o", required=True, help="Where to write testbeds.json")
    args = parser.parse_args()

    out_path = Path(args.output)
    intermediate_dir = out_path.parent
    log_start(intermediate_dir, stage="0-testbeds", agent="testbed_miner")

    harvest = detect_and_mine(Path(args.codebase))
    write_harvest(harvest, out_path)

    log_done(intermediate_dir, stage="0-testbeds", agent="testbed_miner",
             testbeds=len(harvest.testbeds),
             scenarios=sum(len(tb.scenarios) for tb in harvest.testbeds))
    print(json.dumps({
        "testbeds": len(harvest.testbeds),
        "names": [tb.name for tb in harvest.testbeds],
        "scenarios": sum(len(tb.scenarios) for tb in harvest.testbeds),
    }, indent=2))


if __name__ == "__main__":
    _main()
