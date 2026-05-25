---
name: hp-ingest-glossary
description: Stage 0c of brownfield ingest — given the deterministic glossary-candidates list (terms harvested from doc bold/italic/headings/frequency), curate the project's canonical ubiquitous-language list: drop generics, merge case + alias variants, categorize each term (concept/actor/event/artifact/process/state), keep the top 30–60. The curated glossary seeds every downstream naming agent (boundary/processes/leaf/architect) so process + flow + module names match the project's own vocabulary instead of generic English.
---

# hp-ingest-glossary

## When to use

Stage 0c of the `/hp-ingest` orchestration. Runs once after `hp-ingest-scan` + `docs_walker` + `glossary_extractor` have produced `intermediate/glossary-candidates.json`. Cheap LLM pass — a few thousand tokens in, ~2k tokens out.

Per locked tuning H.4: the deterministic extractor surfaces ~50–10000 candidate terms (depends on project doc volume); most are noise. The curator reduces this to ~30–60 canonical glossary entries the project actually uses. Those entries seed every subsequent agent so terminator / process / module / flow names use the team's own words rather than generic English.

## What it does

Given:

- `intermediate/glossary-candidates.json` — deterministic harvest from doc bold/italic/headings/frequency (from `glossary_extractor.py`)
- `intermediate/docs-corpus.json` — for looking up definition context when the candidate's `definition_excerpt` is missing or thin

Produce `intermediate/glossary.curated.json` — the canonical project glossary the agents will consume.

Output shape:

```json
{
  "terms": [
    {
      "term": "Pulse",
      "aliases": ["pulse", "pulses", "PulseStream"],
      "definition": "Real-time telemetry signal flowing into the system from external sensors; emitted at 100ms cadence; the primary event the platform observes.",
      "category": "event",
      "sources": ["docs/architecture/pulse-design.md", "hydra/services/pulse/README.md"]
    },
    {
      "term": "Archi",
      "aliases": ["archi"],
      "definition": "An architecture-model artifact — the platform's project-level vocabulary for what an external user is examining when they query the system.",
      "category": "artifact",
      "sources": ["docs/glossary.md"]
    }
  ]
}
```

Categories (locked, per H.4.a):

- **`concept`** — domain abstractions (`PulseStream`, `BoundedContext`)
- **`actor`** — external participants the system serves (`Developer`, `SRE`, `TelemetryProducer`)
- **`event`** — things that happen, often flowing across boundaries (`Pulse`, `RuleViolation`, `OrderPlaced`)
- **`artifact`** — produced / stored things (`Archi`, `RuleTable`, `IngestReport`)
- **`process`** — the project's own name for an internal capability (`ExploreGraph`, `EvaluateRules`)
- **`state`** — operational states (`Quiescent`, `Backpressured`, `RecoveryMode`)

## Behavior

**Progress log:** at entry, append a START line; after writing `glossary.curated.json`, append a DONE line. Per `hp-ingest.md` orchestrator convention:
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START    stage=0-glossary-curate agent=hp-ingest-glossary" >> <intermediate-dir>/progress.log`
- `Bash: echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) DONE     stage=0-glossary-curate agent=hp-ingest-glossary curated=$N dropped=$D" >> <intermediate-dir>/progress.log`

When invoked, conversationally:

1. **Read inputs.** Load `intermediate/glossary-candidates.json`. If `intermediate/docs-corpus.json` is available + the candidate list has thin `definition_excerpt` fields, you can use the corpus to look up surrounding context in the original doc file (read the file directly from the codebase root).
2. **Drop generics.** Any candidate that's a common English word, generic technical term, or framework-shipped name has no place in the project's domain glossary. Drop: `API`, `JSON`, `HTTP`, `POST`, `GET`, `URL`, `JWT`, `OAuth`, `Server`, `Client`, `Request`, `Response`, `Error`, `Success`, `Note`, `Tip`, `Example`, `TODO`, `Note`. Drop file-format names + RFC titles + framework class names. Keep terms only if they're *the project's own* vocabulary.
3. **Drop one-source noise.** Terms appearing in only one doc file with `extraction_kind: frequency` are usually section-heading noise or accidental capitalizations. Drop unless the frequency is unusually high (≥10 in one file = a legit term, just not cross-doc).
4. **Merge variants.** Group case-aliases (`pulse` / `Pulse` / `PULSE` → one entry, canonical=`Pulse`), plurals (`Pulse` / `Pulses` → one entry), and abbreviations (`Pulse Stream` / `PulseStream` / `PS` → one entry IF the abbreviation is unambiguous). Keep the canonical form as the entry's `term`; the rest go in `aliases`.
5. **Categorize each kept term.** Use the six categories above. If a term is ambiguous (could be `event` or `artifact`), pick the more concrete one. If you can't categorize, drop — uncategorizable terms aren't useful guidance for downstream agents.
6. **Write definitions** if not already present. Each curated term needs a 1–2 sentence definition pulled from its source files (you have the paths + excerpts). Definitions should be project-specific — "the system's term for X" rather than "X" the general concept.
7. **Cap at 30–60 entries.** Aim for the 30 most-load-bearing terms in a small project, up to 60 for cloudctlplane-scale. Beyond that, downstream agents lose focus — too many name candidates dilutes the "use these words" signal.
8. **Write `intermediate/glossary.curated.json`.**

## Discipline

- **The glossary is the project's voice, not a generic dictionary.** Every entry must be something the project's docs treat as a defined term. If you can't point at the doc paragraph that introduces the concept, the term doesn't belong here.
- **Categories aren't suggestions.** Each entry has exactly one category from the six listed. Inventing new categories breaks downstream consumers.
- **Aliases collapse aggressively.** When in doubt, merge — easier for the downstream agent to consult one entry than to disambiguate three.
- **Definitions stay short.** 1–2 sentences. Architects who consult the glossary mid-naming want the concept anchor, not the spec.
- **Don't include code identifiers as glossary terms.** A function name (`validate_order()`) is not a glossary entry; an architectural concept (`Order Validation`) is. The line: if the term appears only in code (never in prose), it's an implementation detail, not a domain term.

## How downstream agents consume the glossary

Each agent (`hp-ingest-boundary`, `hp-ingest-processes`, `hp-ingest-leaf`, `hp-ingest-architect`) is taught to load `intermediate/glossary.curated.json` at the top of its run. When naming a terminator / process / flow / state / module, the agent's discipline is:

> *Prefer terms from the project's glossary over generic English. If a glossary term matches the entity you're naming, use it — "Pulse Stream" not "event stream"; "Archi" not "architecture artifact". Flow labels likewise: use "pulse signals" if "pulse" is the project's word for what the system observes, not "telemetry events".*

This is enforced as discipline, not via mechanical substitution — the agent reads the glossary, internalizes the vocabulary, and produces names that honor it.

## Implementation status

**Skill description: ✅ drafted.** Backing scripts: ✅ `hp_toolkit/ingest/glossary_extractor.py` (Branch 2 Commit T7). Orchestrator dispatch via `/hp-ingest` skill.

## See also

- Design doc: [`toolkit/INGEST_DESIGN.md`](../INGEST_DESIGN.md) + [`toolkit/INGEST_TUNING_DESIGN.md`](../INGEST_TUNING_DESIGN.md) > H.4.
- Predecessor: [`hp-ingest-scan`](hp-ingest-scan.md) + the deterministic `docs_walker` + `glossary_extractor` (no skill — pure Python).
- Followers: [`hp-ingest-boundary`](hp-ingest-boundary.md), [`hp-ingest-processes`](hp-ingest-processes.md), [`hp-ingest-leaf`](hp-ingest-leaf.md), [`hp-ingest-architect`](hp-ingest-architect.md) — each reads `glossary.curated.json` before producing names.
- DDD ubiquitous-language reference: [`toolkit/BOUNDED_CONTEXTS_DESIGN.md`](../BOUNDED_CONTEXTS_DESIGN.md) — H.4 is the ingest-time counterpart of the post-ingest `hp-propose-bounded-contexts` skill.
