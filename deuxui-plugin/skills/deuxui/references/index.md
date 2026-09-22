# What is in this skill

Read `SKILL.md` first; it routes. This page is the full map for when you need
something specific.

## Start here

| File | What it is |
|---|---|
| `loop.md` | The execution loop, step by step, with the commands |
| `preserve.md` | Identity lock, the preserve ladder, preserve vs depart |
| `anti-slop.md` | The AI-tell catalogue and the second-order trap |

## Workflows — read exactly one per task

| File | Mode |
|---|---|
| `workflows/init.md` | Bootstrap `.deuxui/` from repo inspection |
| `workflows/create.md` | A new screen, flow or component |
| `workflows/improve.md` | Polish, redesign, simplify — preserve first |
| `workflows/critique.md` | Read-only review. The safe default |
| `workflows/audit.md` | Full matrix, evidence, release gate |
| `workflows/harden.md` | Accessibility, states, destructive actions |
| `workflows/responsive.md` | Layout, reflow, phone ergonomics |
| `workflows/optimize.md` | Perceived and measured performance |

## Operations — the thirty-five named moves

A workflow is the shape of a job; an operation is one move inside it. Each one
names the detectors that judge its output.

| File | What it is |
|---|---|
| `ops/index.md` | All thirty-five, grouped by what they are for |
| `ops/routing.md` | **Read this when the request does not name an operation.** Maps what people actually say onto a move, from measured signals |
| `ops/colorize.md`, `ops/typeset.md`, `ops/layout.md`, `ops/animate.md`, `ops/craft.md` | Making the system. The first two have generators behind them |
| `ops/bolder.md`, `ops/quieter.md`, `ops/distill.md`, `ops/clarify.md`, `ops/delight.md`, `ops/overdrive.md`, `ops/extract.md`, `ops/adapt.md`, `ops/polish.md` | Changing what exists. `polish` is where every other one hands off |
| `ops/shape.md`, `ops/new-work.md`, `ops/visualize.md`, `ops/decide.md`, `ops/prototype.md`, `ops/phase.md`, `ops/document.md`, `ops/generate.md` | Deciding and originating. `visualize` renders comps from the contract and measures generated ones back against it; `decide` serves the choice as a page; `phase` is the gate that refuses UI edits until somebody has chosen |
| `ops/ios.md`, `ops/android.md`, `ops/adapt-native.md`, `ops/audit-native.md` | The native platforms, detector by detector |
| `ops/ledger.md` | **The system of record.** `state` reads the contract, both prose briefs, the measured component system, the live approval per stage and what is open — four claims, never merged. `log` is the sequence. `show` resolves an approval against the contract as it stood, and says so plainly when those bytes were never archived |
| `ops/onboard.md`, `ops/live.md` (also the selection overlay: a person clicks what is wrong and it lands as a request naming an operation and an element), `ops/live-setup.md`, `ops/hooks.md`, `ops/doctor.md`, `ops/operate.md` | Working: setup, the iteration loop, the hook, diagnosis |

## Craft — thirteen files, one per domain

Each one ends by naming the detectors that adjudicate its claims, because craft
writing that terminates in an exhortation cannot be wrong, which means it cannot
be checked, which means it changes nothing.

| File | Read it when |
|---|---|
| `craft/index.md` | The map, and the three things true across all twelve domains |
| `craft/type.md` | Anything with words in it |
| `craft/color.md` | Choosing or auditing a palette; dark mode |
| `craft/space.md` | It feels cramped, arbitrary, or like unrelated boxes |
| `craft/depth.md` | Cards, modals, dropdowns, anything stacked |
| `craft/composition.md` | A new screen; "the layout feels off" |
| `craft/density.md` | Tables, dashboards, anything an expert uses daily |
| `craft/motion.md` | Transitions, loading, anything that moves |
| `craft/imagery.md` | Photographs, plates, video — and flat vs plate |
| `craft/iconography.md` | Icons and anything without a label |
| `craft/voice.md` | Every string in the product |
| `craft/states.md` | Empty, loading, error, offline — the majority of the work |
| `craft/detail.md` | The last five per cent, after everything else is right |

## The contract

| File | What it is |
|---|---|
| `brand.md` | DeuxUI's own identity — name, tagline, sub-line, pronunciation, voice, the mark — and the contract it holds itself to. `assets/brand/brand.contract.yaml` is the machine half, measured by `selftest.py` against this skill's own served pages |
| `design/visitor-modes.md` | What the person came to do — persuade, experience, operate, read, native. The layer where UX decides UI |
| `design/craft-floor.md` | Every craft number and the detector that decides it. Also defines "optical", which this skill used for a long time without saying what it meant |
| `workflows/design.md` | Greenfield: originate a world and a contract, then build |
| `workflows/uplift.md` | Brownfield: derive the contract from the code that is already there, then raise the floor |
| `parity/impeccable.yaml` | **The coverage claim as data.** Every impeccable command, CLI entry point, live subcommand and subagent, with this skill's answer and — where there is one — the gap, stated. `scripts/parity.py` resolves every piece of evidence and fails on a `partial` whose gap was quietly removed |
| `rules/registry.yaml` | **Source of truth.** 235 rules, 49 sources, severities, applicability, and the 20 UX laws. 19 are enforceable (LAW-17 is an alias): **14 have a live detector, 5 are manual-only, 0 unreachable** — `lint_rules.py` prints the split and errors on an unreachable law |
| `rules/detectors.yaml` | Which detector tests which rule, on which engine, with what confidence |
| `rules/thresholds.yaml` | Every number, and which ones a project may override |
| `rules/00-governance.md` … `14-android.md` | The same rules as readable tables, by domain. Generated — edit the registry |

Rule ID prefixes: `GOV` `CTX` governance · `UX` usability · `NUM` thresholds ·
`VIS` `LAY` visual and layout · `NAV` navigation · `FORM` forms · `COMP` components ·
`STATE` async and state · `A11Y` accessibility · `PERF` performance · `CONTENT`
content and i18n · `TRUST` `AI` trust and generated output · `MEASURE` `QA`
verification. `LAW-01`..`LAW-20` are the named UX laws, with their limits recorded.

## Stacks

| File | Covers |
|---|---|
| `stacks/react-tailwind.md` | React, Next.js, Tailwind v3 vs v4, shadcn, Radix, Base UI |
| `stacks/svelte.md` | Svelte 5 and SvelteKit |
| `stacks/vue-nuxt.md` | Vue 3 and Nuxt |
| `stacks/html-css.md` | Plain HTML and modern CSS, no framework |
| `stacks/three-3d.md` | Three.js and React Three Fiber |
| `stacks/remotion-video.md` | Remotion compositions — a surface with different rules |

## Verification

| File | What it is |
|---|---|
| `verification/static-checks.md` | What the source tier sees, and what it cannot |
| `verification/browser-checks.md` | Every runtime probe, and how to read it |
| `verification/manual-checks.md` | What no machine can check, and how to record it |
| `verification/evidence.md` | Report format, statuses, the gate, exceptions |

## Templates

`assets/templates/` holds `PRODUCT.md`, `DESIGN.md`, `ux.config.yaml`,
`component-contract.md`, `audit-report.md`, `exception.md` and `decision-record.md`.
`workflows/init.md` copies the first three into the target project.

## Provenance

`docs/UX_UI_AGENT_RULES.md` is the source rulebook — 190 rules with their acceptance
checks and a 47-entry source registry, kept so every rule ID in this skill can be
traced to the text it came from and the standard behind it.
