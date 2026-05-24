---
name: hp-ingest-scan
description: Stage 0 of brownfield ingest — walk a codebase, classify each file with an HP role hint (boundary / pure-logic / state-machine / data-store / infra / config), detect languages + frameworks, apply the significance filter, and emit `intermediate/scan.json`. Pure Python; no LLM cost beyond a one-paragraph project description.
---

# hp-ingest-scan

## When to use

The first step of `hp-ingest`. Invoked once per ingest run (or per `--incremental` re-run). Produces the substrate that every downstream ingest agent (boundary-finder, process-extractor, leaf-analyzer, architect, assembler-reviewer) reads.

Also useful standalone, before ingest design decisions are locked, to audit *what hp-ingest sees* in a codebase — which files are filtered out, which role hints fire, what language/framework distribution looks like.

## What it does

Walks the target codebase, classifies every file, emits `scan.json`. The classifier and significance filter are deterministic Python (`hp_toolkit/ingest/scan.py` + `role_classifier.py` + `significance.py`) — no LLM calls.

Output structure (`intermediate/scan.json`):

```jsonc
{
  "project": {
    "name": "cloudctlplane",
    "languages": ["rust", "python", "typescript", "go"],
    "frameworks": ["Axum", "Tonic", "FastAPI", "React", ...],
    "git_commit_hash": "<sha>",
    "analyzed_at": "2026-05-23T..."
  },
  "files": [
    {
      "path": "src/api/handlers.rs",
      "language": "rust",
      "size_lines": 142,
      "hp_role_hint": "boundary",
      "is_significant": true,
      "notes": null
    },
    {
      "path": "tests/integration_test.rs",
      "language": "rust",
      "size_lines": 0,
      "hp_role_hint": null,
      "is_significant": false,
      "notes": "filtered: skipped path (pre-walk filter)"
    },
    ...
  ],
  "import_map": {}                              // populated in a later commit
}
```

The optional LLM step is a one-paragraph project description fitting the `project.description` field. Skipped when run as `--scan-only` for fast iteration.

## Behavior

When invoked, conversationally:

1. **Locate the codebase.** Default: the directory passed via CLI. If `.git/` exists, use `git ls-files` for the file enumeration (respects `.gitignore`). Otherwise recursive walk with default skips.
2. **Per file:**
   - Pre-walk filter (`is_path_always_skipped`) — skip tests / build outputs / vendored / docs / lockfiles without reading content.
   - Read up to 16KB of head content (cheap; the patterns we match are top-of-file).
   - Skip if content marks itself AUTO-GENERATED / DO NOT EDIT.
   - Call `classify_file(path, content)` → one of the 6 HP role hints, or `None` if no match.
3. **Aggregate framework signals.** While reading content, accumulate framework-marker hits (FastAPI, Axum, React, etc.) into a counter; the top hits land in `project.frameworks`.
4. **Apply significance filter.** Mark each file `is_significant` based on role hint + size thresholds (`SignificanceConfig`). Filter does *not* delete files from scan.json — sets `is_significant=False` with a `notes` reason so the architect can audit.
5. **Emit `scan.json`.** Default location: `<project-dir>/intermediate/scan.json`.
6. **Optional:** if invoked without `--scan-only`, write the one-paragraph project description (LLM call, ~500 tokens out, based on top-of-tree README + framework list).

## Discipline

- **The classifier is deterministic Python.** Never asks the LLM to classify a file's role. The LLM is reserved for architectural judgment (Stage 1+), not file-level classification.
- **Aggressive filter, transparent filter.** Filtered-out files stay in scan.json with `is_significant=False` + a reason. The architect should be able to audit "why didn't hp-ingest see X?" via grep over scan.json.
- **Tunable thresholds.** `SignificanceConfig` exposes `min_pure_logic_lines`, `skip_config_when_size_under`, `keep_all_infra`. Defaults aim for ~50–100 significant entities at cloudctlplane scale; tighten for smaller, loosen for larger.
- **Cheap.** Scanner runs in seconds on cloudctlplane-scale repos. The downstream agents are where token cost happens, so cheap Stage 0 = more agility to iterate on filter tuning.

## Lived examples

- `/home/kevin/hatley-pirbhai/examples/fishing-rig/` — small self-test target. Expected output: ~10 files significant, dominated by `pure-logic` + a handful of `config` / `infra`.
- `/home/kevin/hatley-pirbhai/` (the toolkit itself, self-ingest) — ~50 files significant, polyglot Python + markdown.
- `/home/kevin/bluerock/cloudctlplane/` — real polyglot brownfield. First non-trivial test, IP-firewalled (no IP into toolkit artifacts).

## Implementation status

**Skill description: ✅ drafted.** Backing code: ✅ live in `hp_toolkit/ingest/scan.py` (Commit 1 of `kg/brownfield-ingest`). CLI: `uv run python scripts/hp_ingest.py <codebase> --output <project-dir> --scan-only`.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) — full pipeline design.
- Schema: [`hp_toolkit/ingest/schema.py`](../hp_toolkit/ingest/schema.py) — `HpRoleHint`, `ProjectScan`, `FileEntry`.
- Followers: [`hp-ingest-boundary`](hp-ingest-boundary.md) (Stage 1), [`hp-ingest-processes`](hp-ingest-processes.md) (Stage 2) — both consume `scan.json`. *(both drafted in Commit 2)*
