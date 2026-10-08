---
name: ux-laws
description: "Make an existing web app work on phones and hold it to the Laws of UX, across the whole codebase rather than one screen: mobile-first responsive fixes (sideways scroll, tiny tap targets, grids and tables on phones), one consistent pattern for forms, validation and errors across every form, merging duplicate components (several card, modal, button or input versions) into reusable ones, a design contract before adding screens, and PR guardrails measured in a real browser at 320-1440px with a 38-check PASS/WARN/FAIL scorecard (lawsofux.com, WCAG 2.2, Core Web Vitals). Ships a component inventory with where-used blast radius, a browser probe and the scorecard. Use when the user says the UI is a mess or inconsistent, the app is broken or unusable on mobile, every form handles errors differently, one component exists several ways, wants guardrails or a design contract, or names a law such as Hick's or Fitts's. Not for backend work, one library's API, palettes or marketing copy."
license: MIT
compatibility: >-
  inventory.py and scorecard.py need only Python 3.9+ (stdlib). probe.js runs in any browser tool that can
  evaluate JavaScript (Playwright MCP, Claude in Chrome, agent-browser, DevTools). walk.mjs batches the walk
  with Node 18+, using playwright from the project or a private cache that `--install` sets up once. Framework-agnostic: React, Next.js, Remix,
  TanStack, Vue/Nuxt, Svelte/SvelteKit, Astro, plain HTML; Tailwind, CSS modules, CSS-in-JS.
metadata:
  author: github.com/kryptobaseddev
  version: "1.4.1"
  last_updated: "2026-10-08 07:30:00"
  category: frontend
  tags: ux, ui, laws-of-ux, design-system, mobile-first, responsive, accessibility, components, refactoring, audit
allowed-tools: Bash Read Write Edit Glob Grep
---

# UX Laws

Make product UI measurably better by holding it to two things at once: **the Laws of UX** (Jon
Yablonski's 30 psychology principles at [lawsofux.com](https://lawsofux.com/)) as the shared language for
*why* something fails, and **guardrails with numbers** (WCAG 2.2, Core Web Vitals, and law-anchored
thresholds) as the evidence that it does. The focus is brownfield: real apps where the same card exists
four times, forms bypass the input component, the mobile layout is a squeezed desktop, and nobody knows
what changing `Button` will break.

The thesis: **decompose before you redesign, measure before you claim, and fix at the component, not the
call site.** One fixed `Field` repairs forty forms; one fixed form repairs one.

## Pick the mode
| The user wants… | Mode | Phases |
|---|---|---|
| "Audit / improve the UX of this app", "our UI is a mess", a full restructure | **A. Full brownfield audit** | 0 → 7 |
| "We have cards/inputs/modals everywhere", "make components reusable", design-system cleanup | **B. Component consolidation** | 0, 1, 2, 5, 6, 7 (walk only the routes that consume the family) |
| "Make it work on mobile", "check the live site", responsive fixes | **C. Mobile-first walk** | 0, 3, 4, 5, 6 (inventory optional but makes fixes land at the component level) |
| "Review this screen/PR/flow against the laws", one form or page | **D. Focused critique** | Phase 5 on that screen, plus a probe at 390 and 1440 if it runs |
| A new app, or a redesign whose direction is undecided | **E. Greenfield contract** | design-contract.md → lock DESIGN.md → build primitives (component-architecture.md) → phases 3–4 on the first screens |

When unsure, start with A at phase 0 and narrow once you see the codebase.

## Phase 0 — Orient and scope
Find out, from the repo first and the user second:
- **Stack:** framework, router, styling system, UI kit (shadcn, MUI, Chakra, Radix, Headless UI…), token source, monorepo layout.
- **How to run it:** the dev command and URL, or a staging/preview URL. Seed data or a **test account** for authenticated routes. Never use credentials you weren't given for this.
- **Critical paths:** the 3–5 journeys the product exists for. If the user can't say, infer them from the nav and routes and confirm.
- **Constraints:** a brand or design system that must be kept, browser/device targets, deadlines, what's off-limits.
- **Output location:** create `ux-audit/` at the project root for every artifact (ask whether it should be committed or gitignored).
- **Is the thing you'll walk built from the code you'll read?** A preview, a staging build, or a static mock can drift from `src`. Compare a few landmarks (nav items, components, copy) between the running page and the source. If they differ, say so up front, tag every runtime finding with where it was observed, and don't attribute a preview measurement to a source component without checking the source too.

If a decision is genuinely the user's (keep the brand vs. redirect it, which conflicting rule to follow,
whether to touch a high-fan-in component), ask with concrete options instead of guessing.

## Phase 1 — Inventory (static decomposition)
```bash
python3 <skill>/scripts/inventory.py <project-root> --out ux-audit       # inventory.json + inventory.md
python3 <skill>/scripts/inventory.py <project-root> --where ProductCard  # every definition and usage, file:line
```
The output has component definitions with fan-in, UI families (card, button, field, overlay, toast,
table…), raw native elements used where a primitive exists, style literals vs `var(--token)`, routes, and
data-fetching files with or without loading/error/empty handling.

It's regex, not an AST, so **every row is a lead**. Verify before reporting: find-references for usages,
grep plus barrel and lazy-import checks before calling anything unused, and follow data up one level before
claiming a missing state. Read the token source and the UI kit's entry point by hand. Full procedure and
traps: [brownfield-decomposition.md](references/brownfield-decomposition.md).

## Phase 2 — Read the critical paths, then map components and flows
**Read the code of every critical path end to end before mapping anything.** The scripts measure
presentation; they can't see a form that submits nothing, so this reading is where the most serious findings
come from. Look for:
- **broken function:** handlers that do nothing, inputs without `name` (never submitted), props or data shapes that don't match between caller and component (blank cards), dead buttons, unhandled promise rejections;
- **security and privacy:** forms that `GET` sensitive fields into the URL (history, logs, referrers), card data or tokens in `localStorage`, secrets in client code, user enumeration in auth errors;
- **lost work:** state that vanishes on refresh, Back or a failed submit.
These outrank every UX finding in the report: a checkout that leaks card numbers is not a Fitts's Law problem.

Then:
- Put every component in a layer: **tokens → primitives → patterns → domain components → screens**. Record fan-in and an action (keep / merge into X / extract / delete-after-verify) in `ux-audit/component-map.md`.
- Map the 3–5 critical paths in `ux-audit/flows.md`: each screen's primary action, decisions, fields and reachable states; plus the path's cost (screens, taps, fields, decisions, waits, dead ends). These counts are the baseline later iterations must beat.

## Phase 3 — Walk the running app, mobile first
Narrowest first: **320 and 390 (touch-emulated), then 768, 1024, 1440.** For each critical-path route at
each width: navigate, run `scripts/probe.js`, save the JSON as `<route>@<width>.json`, screenshot, and
**look at the screenshot**. Then do the path for real: messy input, invalid submit, Back, refresh
mid-flow, and time the feedback.
```bash
node <skill>/scripts/walk.mjs --base http://localhost:5173 --routes / /checkout /account \
  --widths 320,390,768,1024,1440 --out ux-audit/captures      # add --install once if playwright is missing
```
With Playwright MCP, Claude in Chrome or agent-browser, do the same steps by hand: resize, navigate,
evaluate probe.js, screenshot. Then force the states nobody tests (slow network, failed request, offline,
empty account, success, no permission) and do a keyboard-only pass. Recipes per tool, state forcing, and
mobile and desktop checklists: [browser-walkthrough.md](references/browser-walkthrough.md).

No browser at all? Say so. Every runtime metric is then NOT_MEASURED, and the walk becomes the first item
in the plan.

## Phase 4 — Scorecard
```bash
python3 <skill>/scripts/scorecard.py --inventory ux-audit/inventory.json --probes ux-audit/captures \
  [--manual ux-audit/manual.json] [--baseline ux-audit/iteration-1/scorecard.json] --out ux-audit
```
This gives 38 guardrails, each PASS / WARN / FAIL / **NOT_MEASURED** with the law or standard it protects.
NOT_MEASURED is never a pass; a thin audit must look thin. Hand-measured values (INP, feedback time,
visible focus, keyboard completion, states verified) go in `manual.json`. Thresholds and their sources:
[metrics.md](references/metrics.md).

## Phase 5 — Law critique, one system at a time
Name which **systems** each screen contains (search, form, card entry, error, notification, toast,
settings, table, list, login, dashboard, icons, success, nav, modal), and apply only those systems' rules:
[component-systems.md](references/component-systems.md). Then run the six lenses from
[laws.md](references/laws.md) over the screen and the flow:
1. **Decisions:** one primary action; choices sequenced; vital few first (Hick's, Choice Overload, Pareto, Occam's, Parkinson's).
2. **Perception:** spacing encodes grouping; same function looks the same; one distinct thing per view (Gestalt laws, Von Restorff, Aesthetic-Usability).
3. **Memory:** persistent labels, chunked steps, resumable work (Miller's, Working Memory, Chunking, Serial Position, Zeigarnik).
4. **Motor and time:** big, near targets; feedback under 400ms or a designed wait (Fitts's, Doherty, Flow).
5. **Expectations:** conventions for commodity UX; domain words; forgiving input; complexity absorbed by the system (Jakob's, Mental Model, Paradox of the Active User, Postel's, Tesler's).
6. **Experience and ethics:** designed peaks and endings, honest progress, no dark patterns (Peak-End, Goal-Gradient, Cognitive Load, Selective Attention, Cognitive Bias).

Finish with the anti-generic pass, [anti-generic.md](references/anti-generic.md): unchosen defaults
(Inter-only, indigo gradients, centered hero with dual CTAs, three equal icon cards, uniform radius and
shadow, "Welcome back") each get a named replacement, not just a ban.

Then the **visual quality gate**, [visual-quality.md](references/visual-quality.md): review viewport slices
(`walk.mjs --slices`) at 390 and 1440 in light and dark, interact before judging (focus, invalid submit, menus),
and check imagery-to-content match, accent, shape, theme and type locks, alignment baselines, sticky UI
obscuring focus, and copy tells (em dashes, filler, fake-precise numbers, one label per intent). **A green
scorecard is not a good design**: the gate catches what no counter can.

Where two rules conflict (validation timing, radius scale, toast duration, 44 vs 48 targets, shadows),
write both sides and let the owner choose. Don't pick a winner silently.

## Phase 6 — Report and plan
Write `ux-audit/report.md` from [assets/report-template.md](assets/report-template.md) (if you can't write
files, return the report inline). Rank findings by **broken or unsafe first, then critical path, then fan-in,
then severity**. A FAIL in a primitive used on 30 screens outranks a
FAIL on an about page. Every finding uses this shape:

```
### 3. Checkout is one 11-field wall with placeholder-only labels: FAIL
- Law: Chunking https://lawsofux.com/chunking/ · Working Memory https://lawsofux.com/working-memory/ · WCAG 1.3.1
- Where: /checkout@390 · src/features/checkout/CheckoutForm.tsx:8 · raw <input> ×7 bypassing TextInput
- Evidence: probe fields.forms[0].fields = 11; fields.unlabeled = 11; below16px = 11 (iOS zooms on focus)
- Fix: 3 steps (contact → shipping → payment) on the shared Field; persistent labels; type/inputmode/autocomplete;
       16px inputs; validate in-step and block Next; save each step (Zeigarnik)
- Verify by: form_wall ≤ 7, unlabeled_fields = 0, input_zoom = 0 at 390
```

The plan is ordered work: **tokens → primitives → patterns → screens**, one concern per batch, each with
the metrics it must move. For restructures that touch high-fan-in components, or that change the visual
direction, get the owner's approval on the plan before editing. For a direct "fix it" request on a bounded
scope, proceed and report.

## Phase 7 — Implement in batches, then re-verify
- Build or repair the primitive first (all its states, the shared prop contract, tokens only), then move consumers in small batches with adapters and `@deprecated` markers. Strangler, not big bang: [brownfield-decomposition.md §8](references/brownfield-decomposition.md#8-migrate-safely).
- API conventions that make components interchangeable (`value`/`onChange`/`invalid`/`error`/`size`/`variant`, slots, compound parts, the four-state `AsyncView` pattern, container queries, centralized formatters and normalizers): [component-architecture.md](references/component-architecture.md).
- When you change visuals, **capture 3–6 real products in the same category first** and copy their structure (visual-quality.md §2). Swapping banned defaults for newer ones (Geist plus an emerald accent, split hero, bordered cards, icon-fact rows) is still a template. Then state the design read and dials, build from DESIGN.md tokens, and use real or verified imagery, never random placeholder photos.
- After each batch, re-run the project's tests, re-walk the affected routes, pass the visual gate again, and re-run the scorecard with `--baseline`. Keep each iteration in `ux-audit/iteration-N/`. Report the deltas: FAIL→PASS is a result; a new FAIL is a regression to fix before moving on.

## Rules of evidence
- **Cite the law by name and URL** for every finding. Quote definitions from lawsofux.com exactly and briefly. The site is CC BY-NC-ND, so link to it rather than reproducing its pages.
- **No invented numbers.** Never promise conversion lifts. Report measured before/after values, flow-cost counts, and standards thresholds. The only numbers the laws themselves state are Doherty <400ms, Miller 7±2 (which the site warns is not a hard UI limit) and Pareto 80/20.
- **NOT_MEASURED ≠ pass.** Say what wasn't covered (auth routes, field performance data, real devices) in the summary.
- **Leads aren't findings.** Script output is verified in source or in the browser before it goes in the report.
- **Lab ≠ field.** One local load's LCP/CLS is a lead; Core Web Vitals are judged on real-user p75.
- **Green is not good.** A clean scorecard plus an unreviewed screenshot is not done; report the visual gate's result next to the numbers.
- **The project's own written standard beats this skill's defaults.** Cite it, and record any tuned threshold with its reason.

## Guardrails at a glance
| Area | Bar | Law / standard |
|---|---|---|
| Reflow | no horizontal scroll at 320 | WCAG 1.4.10 |
| Targets | none < 24px; ≥ 44px on touch | WCAG 2.5.8 · Fitts's |
| Inputs | labeled; ≥ 16px on phones; correct type/inputmode/autocomplete | WCAG 1.3.1 · Working Memory · Postel's |
| Decisions | ≤ 1 filled CTA in the first viewport; forms ≤ ~7 visible fields per step | Hick's · Von Restorff · Chunking |
| Contrast | 4.5:1 text, 3:1 large text | WCAG 1.4.3 |
| Feedback | visible response < 400ms; INP ≤ 200ms | Doherty · Core Web Vitals |
| States | every data view: loading, empty, error, success | Doherty · Postel's · Peak-End |
| Loading | LCP ≤ 2.5s, CLS ≤ 0.1 (field p75) | Core Web Vitals |
| System | token adoption ≥ 0.8; ≤ 9 font sizes, ≤ 5 radii, ≤ 4 shadows rendered; no raw controls beside a primitive | Similarity · Common Region |
| Copy | no template filler; errors say what happened and what to do; success names the thing and the next step | Mental Model · Peak-End |

## Mobile-first, then scale up
Base styles are the phone. Primary actions sit in the thumb zone (sticky bottom on long forms); 3–5
bottom-tab destinations, not a 30-link hamburger; dialogs become sheets; tables become two-line cards at the
table's container width; nothing essential hides behind hover (`@media (hover: hover)`, never UA
sniffing); the viewport meta allows zoom. Scaling up adds columns, density and shortcuts. It doesn't
stretch a phone layout across 1440px. Container queries for components, media queries for page layout.

## Reference map
| Read | When |
|---|---|
| [references/laws.md](references/laws.md) | any critique: 30 laws in six lenses, each with a check, evidence key and AI tell, plus a law → component-system map |
| [references/component-systems.md](references/component-systems.md) | a screen contains search, forms, card entry, errors, toasts, settings, tables, lists, login, dashboards, icons or success; also the documented rule conflicts |
| [references/brownfield-decomposition.md](references/brownfield-decomposition.md) | phases 1, 2 and 7: verifying the inventory, layers, flow maps, consolidation specs, safe migration |
| [references/component-architecture.md](references/component-architecture.md) | designing or repairing primitives: token layers, prop contract, variants and slots, four-state pattern, utilities |
| [references/browser-walkthrough.md](references/browser-walkthrough.md) | phase 3: widths, recipes per tool, state forcing, keyboard pass, mobile and desktop checks |
| [references/metrics.md](references/metrics.md) | phase 4: every guardrail's threshold and source, manual metrics, flow-cost metrics, CI wiring |
| [references/visual-quality.md](references/visual-quality.md) | every changed screen: screenshot protocol, design read and dials, locks, imagery, copy and layout tells, the before/after worked example |
| [references/anti-generic.md](references/anti-generic.md) | the screen looks templated or AI-generated; pre-ship checklist |
| [references/design-contract.md](references/design-contract.md) | greenfield, redesign direction, extracting a brownfield contract, motion rules |
| [assets/DESIGN.template.md](assets/DESIGN.template.md) · [assets/report-template.md](assets/report-template.md) | the contract and report skeletons |

## Scripts
| Script | Does | Needs |
|---|---|---|
| `scripts/inventory.py <root> [--out DIR] [--where Name] [--json]` | component inventory, families, fan-in, bypass, token drift, routes, data-view states | Python 3.9+ |
| `scripts/probe.js` | in-page measurement at the current viewport: reflow, targets, fields, CTAs, headings, contrast, sprawl, fixed chrome, hover-only rules, copy tells, lab LCP/CLS | any browser tool that evaluates JS |
| `scripts/walk.mjs --base URL --routes … [--widths …] [--slices] [--install] [--out DIR]` | batch walk with touch emulation below 768; writes probe JSON, screenshots and (with `--slices`) viewport slices for visual review | Node 18+; playwright from the project or `--install` (private cache) |
| `scripts/scorecard.py --inventory … --probes … [--manual …] [--baseline …] [--gate]` | 38 guardrails → PASS/WARN/FAIL/NOT_MEASURED with deltas | Python 3.9+ |

`<skill>` means this skill's directory. Run the scripts from there; don't copy them into the user's app
unless they ask (for CI, copy them into the repo; see metrics.md).

## Anti-patterns
- Letting the scripts replace reading the code: a perfect scorecard on a form that submits nothing
- Redesigning screens before knowing where each component is used
- Fixing the same bug at 12 call sites instead of once in the primitive
- Reviewing only at desktop width, or "mobile" via a resized desktop window that never emulates touch
- Reporting a law violation with no evidence, or a lift percentage with no data
- Treating script counts as findings without verifying them
- Banning a default (Inter, purple) without naming the replacement, or replacing it with the next default (Geist, emerald, split hero) instead of the category's real conventions
- Resolving a rule conflict by picking whatever is easiest to build
- One big-bang refactor PR across tokens, primitives and every screen at once

## Done when
- Every critical path has been walked at 390 and 1440 (or the gap is stated), with screenshots and probe JSON
- The scorecard exists, NOT_MEASURED items are listed, and every FAIL has a finding or a stated exception
- Every finding names a law with its URL, evidence, a fix at the right layer, and the metric that verifies it
- The visual gate was run on screenshots someone looked at, and its findings are in the report
- The component map shows layers, fan-in and a decision for every multi-member family
- After changes: a re-run scorecard with `--baseline` shows the movement, and no new FAILs
