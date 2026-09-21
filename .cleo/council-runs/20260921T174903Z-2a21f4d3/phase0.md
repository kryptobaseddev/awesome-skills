# The Council — Is deluxui a design director or only a UX auditor, and what is the minimum addition that would make it both?

## Restated question

Should deluxui acquire a generative design-craft capability (and the enforcement of its own 20 inert UX laws), or should it stay a pure verification engine and cede design composition to the model's own knowledge — and if the former, what is the smallest set of additions that survives its NOT_RUN evidence discipline?

## Evidence pack

1. `skills/deluxui/references/rules/detectors.yaml` + `references/rules/registry.yaml` — **The 20 UX laws are inert.** `LAW-*` appears 0 times in detectors.yaml, 0 times in ux_report.py, and only as scattered single mentions in prose. No rule cites a law as its `basis` (that field carries S00–S46 only). Section 04 of the owner's rulebook declares `law_contract_defaults: enforcement: Project policy for applicable interfaces`, and the original plan claimed "19 enforceable LAW- contracts". The design-reasoning layer is carried as data and consumed by nothing. Rationale: this is the single largest gap between what the constitution promises and what the skill does, and it sits exactly on the axis the owner cares about.

2. `skills/deluxui/references/workflows/create.md:28-31` — the build order is "**Semantics, then states, then looks.** Role, name and keyboard behaviour first; then make every state reachable; then style it." The file then gives seven specifics, all of them engineering (native elements, headless primitives, CLS reservation, empty states, pending states, undo). **There is no guidance of any kind on how to style it.** Rationale: the generative moment is exactly where the skill goes silent.

3. Grep across all of `skills/deluxui/references/**` returns **zero files** for `colour ramp`/`color ramp`, `focal point`/`visual weight`, `grid system`/`column grid`/`layout grammar`, and `elevation`/`depth system`. Rationale: falsifies any claim that design craft is merely thin — on four core craft axes it is absent.

4. `skills/deluxui/references/anti-slop.md` (67 lines, the largest design-side file in the skill) — five sections (Colour and surface, Shape and depth, Type, Copy, the second-order trap), **every entry phrased as a tell to avoid**. Rationale: the skill's entire design vocabulary is negative; it can reject a gradient but cannot propose a palette.

5. `~/.agents/skills/impeccable/reference/` — **6,576 prose lines across 28 files vs deluxui's 1,079 across 24**, with dedicated *generative* operations deluxui has no counterpart for: `colorize.md` (257), `typeset.md` (279), `layout.md` (161), `shape.md` (165), `craft.md`, `brand.md`, `animate.md`, `delight.md`, `bolder.md`, `quieter.md`, `distill.md`, `overdrive.md`, `polish.md` (241), `interaction-design.md` (189). It covers `grid` in 19 files, `elevation` in 8, `optical` in 8 — deluxui covers those in 0, 0, 0. Rationale: the comparison the owner actually asked about, quantified; impeccable's advantage is precisely and only on the generative axis.

6. `memory/deluxui-skill.md` (A/B record, 3 tasks with/without the skill) — **knowledge-shaped assertions 17/18 vs 17/18 (zero delta)**; **verifiability-shaped assertions 15/18 vs 1/18** — Rationale: the most important datum in this review. Opus 5 already knows accessibility, Radix and design vocabulary; the skill's measured value is entirely in making claims checkable. Any proposed addition must be tested against this, because design prose is knowledge-shaped by construction.

7. `skills/deluxui/references/rules/registry.yaml` class distribution — **PROJECT 123, STANDARD 48, HEURISTIC 16, PLATFORM 3**; severity P0 26, P1 144, P2 20; detector engines source 85, element 40, computed 15, runtime_state 4, visual 2, report 10, manual 10 = 166. Rationale: only 16 rules are HEURISTIC class, i.e. taste-adjacent; the architecture is overwhelmingly built to adjudicate things with a defensible external basis, which constrains how design craft could legitimately enter it.
