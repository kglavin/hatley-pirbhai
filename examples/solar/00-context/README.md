# Level 0 / Context Diagram v0 — Presentation Experiment

Three renderings of the **same** Solar Local Stack Context Diagram, in different formats. Goal: feel the difference between presentation styles so we can decide which serves which moment.

*This directory contains everything for HP's level-0 (Context). Sibling directories `01-level1/`, `02-level2/`, etc. will appear as we decompose. See repo `PLAN.md` > Methodology Tactics > B for the "repo hierarchy mirrors HP hierarchy" tactic.*

All three render the identical underlying model (six terminators, one system bubble, eight flows F1–F8, two physical-AC connections from PG&E to Hoymiles and Victron). Differences are in the *view*, not the *content*.

## Files

**Sources** (the model in three notation forms):

| File | Format | How to view |
|---|---|---|
| `context.md` | Mermaid embedded in markdown | Open in VSCode → use the markdown preview pane (`Ctrl+Shift+V` / `Cmd+Shift+V`). GitHub also renders this natively. |
| `context.html` | HTML5 + Cytoscape.js (CDN-loaded) | Open directly in any browser. No server, no install. Click nodes/edges for details, drag to rearrange. |
| `context.d2` | D2 declarative diagram source | Needs `d2` binary. `bash toolkit/bootstrap.sh` installs it. Re-render with: `d2 context.d2 context-d2.svg`. |

**Rendered SVGs** (static images, ready to compare side-by-side):

| File | Format | How to view |
|---|---|---|
| `context-mermaid.svg` | Static SVG from Mermaid (rendered via `mmdc`) | Open in any browser or image viewer. |
| `context-d2.svg` | Static SVG from D2 (rendered via `d2`) | Open in any browser or image viewer. |

Re-render any time after sources change:
```bash
# from repo root, after toolkit/bootstrap.sh has been run
mmdc -p toolkit/.puppeteer-config.json -i examples/solar/00-context/context.md -o examples/solar/00-context/context-mermaid.svg
d2  examples/solar/00-context/context.d2 examples/solar/00-context/context-d2.svg
```

## Comparison points worth feeling

Open all three side by side and notice:

- **Layout quality.** Auto-layout in Mermaid (`graph LR`) vs Cytoscape's COSE algorithm vs D2's TALA engine. Same content, very different shapes.
- **Edge label readability.** Mermaid wraps text where it can; Cytoscape rotates with edges; D2 (with TALA) tries to avoid label overlap actively.
- **Distinguishing flow kinds.** Mermaid's solid/dashed (F8 optional) — minimal. Cytoscape's full styling (data vs control vs power, optional vs required). D2's stroke-dash style. Are the visual distinctions enough?
- **Interactivity.** Mermaid is static. D2 SVG is static (unless you use d2's interactive build). Cytoscape is the only one where you can click a node and see the spec text inline.
- **Edit friction.** Mermaid: edit `.md`, refresh preview — instant. D2: edit `.d2`, re-render — fast with `--watch`. Cytoscape: edit `.html` JSON (more verbose), refresh browser.
- **AI generation cost.** Mermaid is the cheapest to generate (small surface). D2 is similar. Cytoscape is verbose (style + data + layout config); takes more output tokens to produce.
- **Diff-ability in git.** Mermaid and D2 are tiny declarative text — diffs are readable. Cytoscape's HTML is bigger; diffs noisier.

## What we're trying to learn

This isn't picking a winner — it's understanding which view serves which moment in the AI+HP workflow:

- **Reviewing the model** during conversation — which is fastest to glance at?
- **Editing the model** as you and the AI iterate — which has the least friction?
- **Sharing with someone else** (PR, slide, stakeholder doc) — which exports best?
- **Pinning the model in git as source of truth** — which is most readable in a diff?
- **Interactive deep-dive** — which lets you click into a node's spec?

Likely answer: different views for different moments. The toolkit's job is to maintain the *model* and let you switch *view* on demand.

## Open question after viewing

Once you've looked at all three, the question that matters: **which would you actually use day-to-day?** And separately: **which would you want for end-of-project documentation, stakeholder review, or pinning the model in git?**
