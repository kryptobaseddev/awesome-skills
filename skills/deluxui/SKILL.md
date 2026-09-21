---
name: deluxui
description: "Engineer and verify interfaces against a 190-rule UX contract with runnable checks, not opinions. Use when building or changing any screen, flow, page, component, form, table, dashboard or layout - including small additions like a delete or submit control, which carry confirmation and undo duties. Also use when redesigning, polishing, simplifying or hardening existing UI, and when auditing accessibility, responsive reflow, empty/loading/error/offline states, destructive actions, focus order, contrast, hit areas, motion, microcopy or design-system drift. Ships 166 checks bound to cited rule IDs and a browser tier that measures contrast, focus rings and 320px reflow and forces the offline, empty and failed states nobody tests, behind a gate where NOT_RUN is never a pass. Knows React, Next.js, Svelte, Vue, Tailwind v3/v4, shadcn, Radix, Base UI, Three.js, Remotion. Not for bundle size, build config or backend work. Use even if the user only says 'make this look better' or 'the design feels off'."
license: MIT
compatibility: >-
  Python 3.9+ with pyyaml for the static tier and the report. The runtime tier
  needs the agent-browser CLI (npm i -g agent-browser) and a running app; without
  it every runtime rule reports NOT_RUN rather than passing. Framework-agnostic:
  understands React, Next.js, Remix, Svelte/SvelteKit, Vue/Nuxt, Astro, plain
  HTML/CSS, Tailwind v3 and v4, shadcn, Radix, Base UI, Three.js and Remotion.
metadata:
  author: github.com/kryptobaseddev
  version: "2.3.0"
  last_updated: "2026-09-21 11:04:31"
  category: frontend
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# deluxui — UX engineering with a verdict

Most interfaces an agent produces look right in the one state the agent looked at.
They fail in the states nobody opens: the empty list, the request that 500s, the
320px phone, the keyboard-only pass, the moment the network drops. And then the
agent reports success, because nothing told it otherwise.

This skill fixes the reporting problem first. It carries a 190-rule contract
derived from WCAG 2.2, platform guidance and named UX research, and it ships
scripts that actually test the testable parts. A rule that was checked says PASS.
A rule that was not says **NOT_RUN** — and NOT_RUN is never a pass, never rounds
up to one, and blocks a release audit when it sits on a safety rule.

Everything else here follows from that. Read `references/loop.md` for the full
execution loop; this page is the map.

## The loop

```
orient (.deluxui/ or init)  ->  classify the surface and the task
   ->  select applicable rules   ->  PRESERVE > MODIFY > COMPOSE > CREATE
   ->  implement                 ->  ux_check.py        (static)
   ->  ux_browser.sh             (runtime, forces the states nobody tests)
   ->  ux_report.py --merge      ->  fix                ->  re-run
   ->  report with the rule matrix, including what was not checked
```

The loop is not ceremony. Each step exists because skipping it is how a specific
class of defect ships. If you are making a one-line copy change, run the static
tier and say so. If you are touching a flow that takes someone's money, run all
three tiers and mean it.

## Facts that prevent broken work

Read this table first — each row is a failure that reaches real users.

| Fact | Consequence |
|---|---|
| **NOT_RUN is not PASS.** | The single most common dishonesty in agent UI work is reporting a check that never ran. If you did not test it, say NOT_RUN. |
| **The happy path is the smallest part of the work.** | Empty, loading, error, offline, stale, permission-denied and conflict are states a user will reach. `ux_browser.sh --api` forces them for you. |
| **Hover does not exist on touch or keyboard.** | Anything revealed only on hover is invisible to a large share of users. Mirror it on `focus-visible`. |
| **Tailwind v4 changed `outline-none`.** | In v4 it sets `outline-style:none`; the old forgiving behaviour is now `outline-hidden`. The default ring also dropped 3px to 1px. The checks branch on your installed major version. |
| **`100vh` is wrong on phones.** | It ignores retracting browser chrome, so your footer hides under the URL bar. Use `dvh`, or `svh` when you need the smallest stable height. |
| **`:invalid` fires before the user types.** | It paints an error on an untouched required field. Use `:user-invalid`. |
| **A clickable `div` or `Card` is not a button.** | No keyboard, no role, no name. If it already contains buttons, you also get two competing targets and a `stopPropagation` workaround. |
| **Contrast fails by tiny margins.** | Indigo-500 with white text is 4.47:1 — it fails 4.5:1 and no human eye will catch it. Only measurement will. |
| **Colour cannot be guessed from source.** | Tailwind v4 themes are OKLCH `--color-*` variables. The checks resolve colours from your project; unresolvable pairs report NOT_RUN instead of a made-up verdict. |
| **The static tier is heuristic.** | It scans source text and is wrong sometimes. Every finding carries a confidence. The runtime tier is what settles arguments. |
| **Creating is easier than reading.** | This is why agents turn mature apps into a collage of unrelated screens. The preserve ladder exists to make that cost visible. |
| **An exception may lower a PROJECT rule, never a STANDARD.** | You can document a deviation. You cannot relabel a failed WCAG criterion as passing. |
| **The 20 UX laws are reasoning, not verdicts.** | They carry `MUST`/`MUST_NOT`/`verify:` clauses and look like enforceable contracts, and nothing reads them. Roughly 14 of the 19 have a `verify:` clause an existing detector already covers — but the rule ID is what the gate adjudicates, so cite `NUM-004`, not `LAW-02`, when you mean a result. |
| **169 of the 190 rules have an automated detector; the other 21 are the manual tier.** | Every rule is accounted for and every P0 is automated. The 21 are judgement calls no checker can settle — is this the right amount of complexity to reveal, is this density right for this task — and they report NOT_RUN until a person records an answer. Coverage is not conformance. |
| **The report audits itself.** | `GOV-005/006/008`, the `QA-*` and several `MEASURE-*` rules are about the report, not the product — no scan of an app can tell you whether the agent describing it invented a result. `ux_report.py` checks that every PASS names a detector that ran, that unknowns are declared, and that project config has not been used to weaken a standard. |

## Orient

Before changing anything, find out what already exists.

```bash
python3 scripts/ux_check.py <project> --signals     # stack, theme vars, inventory
cat .deluxui/PRODUCT.md .deluxui/DESIGN.md          # if they exist
```

If `.deluxui/` is missing, follow `references/workflows/init.md`. It builds the
project memory by **inspecting** the repo — package manifest, theme variables,
component directories, routes — and asks only the two or three things it genuinely
cannot infer. Interrogating someone for twenty answers is the fastest way to make
a skill go unused.

Three layers, and they settle conflicts in this order: the **rules** in this skill
are universal; **PRODUCT.md** owns audience, jobs and risk; **DESIGN.md** owns the
visual system. When PRODUCT and DESIGN disagree, DESIGN wins on visual decisions
and PRODUCT wins on strategic ones. When either disagrees with a safety or
accessibility rule, the rule wins — see the priority order in `references/rules/00-governance.md`.

## Modes

Match the request to a mode, then read that workflow file. Do not read all of them.

| Mode | The user is asking for | Read | Tiers |
|---|---|---|---|
| `init` | Set this up / first time in this repo | `references/workflows/init.md` | — |
| `create` | A new screen, flow or component | `references/workflows/create.md` | static + runtime |
| `improve` | Make it better, polish, redesign, simplify | `references/workflows/improve.md` | static + runtime + baseline |
| `critique` | What is wrong with this? (no edits) | `references/workflows/critique.md` | static |
| `audit` | Is this ready? Full review, release check | `references/workflows/audit.md` | all three |
| `harden` | Accessibility, states, destructive actions | `references/workflows/harden.md` | all three |
| `responsive` | Mobile, layout, it breaks at some width | `references/workflows/responsive.md` | runtime |
| `optimize` | It feels slow, janky, shifts around | `references/workflows/optimize.md` | runtime |

When the request is ambiguous, `critique` is the safe default: it reads and
reports without touching anything.

## The preserve ladder

```
PRESERVE  ->  MODIFY  ->  COMPOSE  ->  CREATE
```

Before writing a new component, ask the inventory:

```bash
python3 scripts/ux_check.py <project> --inventory "dialog confirm"
```

Then record which existing primitive you reused, or why none fit. The default is
preserve, and the argument is about asymmetric cost: being wrong about preserving
costs a conservative-looking variant, which is recoverable in one message. Being
wrong about departing rewrites someone's product in a style they never asked for,
which is not. If you are unsure, you are in preserve mode.

Departure needs an explicit request, or a PRODUCT.md anti-reference aimed at *this
specific surface*. "Modern" and "clean" are not directions — see
`references/preserve.md` for how to lock an identity before you touch it.

If the project has Radix, Base UI, Headless UI, Ark or React Aria installed,
hand-writing a dialog, dropdown, tooltip or combobox is not a style choice. Those
libraries have already solved focus containment, escape handling, typeahead and
ARIA, and your version will not. Compose theirs.

## Run the checks

```bash
# Static tier -- source scanning, fast, heuristic
python3 scripts/ux_check.py <path>                       # human readable
python3 scripts/ux_check.py <path> --json > .deluxui/reports/static.json
python3 scripts/ux_check.py <path> --detector S-FOCUS-OUTLINE   # one check

# Runtime tier -- measures a running app, forces the states nobody tests
bash scripts/ux_browser.sh http://localhost:5173 \
     --routes /,/settings --api '**/api/**' --out .deluxui/reports/runtime

# The verdict
python3 scripts/ux_report.py --merge --feature forms --feature payments_or_legal \
     > .deluxui/reports/agent_report.yaml
python3 scripts/ux_report.py --merge --release      # unchecked P0 rules block
```

Exit codes compose: `0` clean, `2` findings, `3` runtime tier unavailable.

Prove the checks still work before you trust a report — `python3 scripts/selftest.py`
asserts every check fires on known-bad fixtures and stays silent on known-good ones.

## The verdict

Report the matrix, not an adjective. `ux_report.py --merge` emits the rule
results, the counts and one of four decisions:

- **BLOCKED** — a P0 or P1 rule is failing, or (in `--release`) a P0 rule was never checked.
- **CONDITIONAL** — nothing failing, but P0 rules are unverified. Fine mid-change; not enough to ship.
- **READY** — every applicable rule was checked and none are failing.
- Rules the product does not reach are **NOT_APPLICABLE**, declared through `features:`
  in `.deluxui/ux.config.yaml` or `--feature` (the flag adds to the file, it does not
  replace it).

When a **STANDARD**-class rule fails, cite its basis alongside the rule ID —
`NUM-001 (S03, WCAG SC 1.4.3)`. The registry carries a source for all 190 rules,
and a reader who can follow the claim to the criterion can check you; one who
cannot has to take your word for it, which is the thing this skill exists to stop.

Say what you did not check and why. "I ran the static tier; the runtime tier needs
the app running, so 84 rules are unverified" is a useful, honest report. "Looks
good" is not a report at all. `references/verification/evidence.md` has the format
and the exception process.

## Where to go next

Each reference is self-contained. Read the one you need.

| Task | Reference |
|---|---|
| The full execution loop, step by step | `references/loop.md` |
| Identity lock, preserve vs depart, variants | `references/preserve.md` |
| The AI-tell catalogue and why each one reads as generated | `references/anti-slop.md` |
| Everything in this skill, indexed | `references/index.md` |
| Governance, priority order, exceptions | `references/rules/00-governance.md` |
| Rule packs by domain (a11y, forms, state, layout, …) | `references/rules/` |
| The machine registry: 190 rules, severities, sources | `references/rules/registry.yaml` |
| The 20 UX laws, with limits and `verify:` clauses — **carried, not enforced**: no detector reads them, so cite one as reasoning, never as a result | `references/rules/registry.yaml` (`laws:`) |
| What each detector tests and with which engine | `references/rules/detectors.yaml` |
| Numeric thresholds, and which are overridable | `references/rules/thresholds.yaml` |
| React, Svelte, Vue, plain CSS, 3D, video specifics | `references/stacks/` |
| What the static tier can and cannot see | `references/verification/static-checks.md` |
| Driving the browser tier, probe by probe | `references/verification/browser-checks.md` |
| What no machine can check, and how to record it | `references/verification/manual-checks.md` |

## Scripts

| Script | Purpose |
|---|---|
| `scripts/ux_check.py` | **Static tier.** 125 source checks bound to rule IDs. Takes a file or a directory and reads exactly that. `--json`, `--signals`, `--inventory`, `--detector`, `--max`, `--config`, `--stdin` for editor hooks. |
| `scripts/ux_browser.sh` | **Runtime tier.** Drives agent-browser across your viewport matrix, measures contrast, targets, focus and vitals, and forces aborted, empty and offline states. |
| `scripts/ux_report.py` | **The verdict.** `--collect` interprets raw probes; `--merge` combines all tiers into the rule matrix and gate decision. |
| `scripts/uxconfig.py` | The only reader of `.deluxui/ux.config.yaml`. Merges overridable thresholds, refuses standards, and answers `--get app.dev_url` for the shell driver. |
| `scripts/selftest.py` | Asserts every check fires on bad fixtures and stays quiet on good ones, **and** that every config key changes something — each with a positive control. |
| `scripts/lint_rules.py` | Proves no prose cites an invented rule ID, no detector claims coverage nobody implemented, and no rule is orphaned onto a detector that can never run. |

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | Reporting PASS for a check that never ran | Report NOT_RUN. It is the honest status and it is the one the gate cares about. |
| 2 | Running only the static tier and calling it an audit | The static tier cannot see computed styles, real hit areas, focus order or any runtime state. Say which tiers ran. |
| 3 | Building a new Dialog next to the project's existing one | Run `--inventory` first. Compose the installed primitive. |
| 4 | Testing only the state you happened to build | Force the others: `ux_browser.sh --api '**/api/**'`. |
| 5 | Treating a screenshot as verification | A screenshot shows one state at one width. Read the rule matrix. |
| 6 | Redesigning everything when asked to fix one thing | Preserve is the default. Lock the identity first. |
| 7 | Using `outline-none` in Tailwind v4 without a replacement | It removes the indicator even in forced-colors mode. Use `outline-hidden` plus `focus-visible:ring-2`. |
| 8 | Adding a UI dependency for something the stack already does | Check the manifest. Three button components is how design systems die. |
| 9 | Silencing a check because it is noisy | If it is a false positive, fix the check and its fixture. If it is real, fix the code. |
| 10 | Claiming WCAG conformance from an automated scan | Automated checks cover a minority of the criteria. Conformance needs the manual tier and a stated scope. |

## Resources

- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/ARIA/apg/
- https://web.dev/articles/vitals
- https://tailwindcss.com/docs/upgrade-guide
- https://base-ui.com
- `docs/UX_UI_AGENT_RULES.md` — the source rulebook this skill implements
