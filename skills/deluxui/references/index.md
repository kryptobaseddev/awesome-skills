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
| `workflows/init.md` | Bootstrap `.deluxui/` from repo inspection |
| `workflows/create.md` | A new screen, flow or component |
| `workflows/improve.md` | Polish, redesign, simplify — preserve first |
| `workflows/critique.md` | Read-only review. The safe default |
| `workflows/audit.md` | Full matrix, evidence, release gate |
| `workflows/harden.md` | Accessibility, states, destructive actions |
| `workflows/responsive.md` | Layout, reflow, phone ergonomics |
| `workflows/optimize.md` | Perceived and measured performance |

## The contract

| File | What it is |
|---|---|
| `rules/registry.yaml` | **Source of truth.** 190 rules, 19 enforceable laws, 47 sources, severities, applicability |
| `rules/detectors.yaml` | Which detector tests which rule, on which engine, with what confidence |
| `rules/thresholds.yaml` | Every number, and which ones a project may override |
| `rules/00-governance.md` … `12-measurement-qa.md` | The same rules as readable tables, by domain. Generated — edit the registry |

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
