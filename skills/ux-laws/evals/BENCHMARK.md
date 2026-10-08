# ux-laws benchmark

Each scenario in `evals.json` was run by an independent agent with the skill and without it (baseline),
then graded against the listed assertions by a separate grader agent that read the files on disk.
Run outputs live in the gitignored `ux-laws-workspace/` next to the skill; this file keeps the results.

## Iteration 2 (v1.3.0, 2026-10-08): 37 assertions across 3 scenarios

| Scenario | With skill | Baseline |
|---|---|---|
| 1. Brownfield full audit (13 assertions) | 13/13 | 9/13 |
| 2. Card consolidation (10) | 9/10 | 10/10 |
| 3. Checkout mobile fix (14) | 14/14 | 9/14 |
| **Mean pass rate** | **96.7%** | **77.8%** |
| Mean time / tokens per run | 483 s / 128k | 213 s / 83k |

What the skill added that baselines missed: law-cited findings with lawsofux.com URLs; security and broken
function ranked above UX (card data leaking into a GET URL); a real multi-step checkout that validates per
step and resumes after refresh without storing card data; screenshot-reviewed visual fixes; tokens before
primitives before screens.

Where baselines did better, and what changed in response:
- Scenario 2: the skill run hard-coded `alt=""` on card media. The card rule now requires alt through the data shape (component-systems.md).
- Scenario 1: one baseline re-measured the page with a viewport meta injected, showing the real mobile overflow is about 3x worse. That's now in browser-walkthrough.md §6.

The cost is real: about 2.3x the wall time and 1.5x the tokens, spent on captures, the scorecard,
the component map and flow maps.

## Iteration 1 (v1.0.0): 28 assertions, 100% vs 79.3%

The assertions were weaker. The grader found that baselines caught things the skill missed: a GET form leaking card data, a preview not
built from `src`, and source bugs found by reading code. v1.1 added "read the critical paths" and preview-drift checks,
v1.2 added the visual quality gate, and v1.3 added references-before-taste after the owner rejected an
"anti-slop" page that was still the newer AI template. Assertions were tightened for iteration 2.

## Trigger eval (2026-10-08)

Measured on `trigger_queries.json` with a runner that scans the whole tool sequence. skill-creator's
`run_eval.py` only inspects the first tool call, and it registers a temp command beside the installed skill,
so it under-reports. Each query ran through `claude -p` (claude-opus-5-5) inside a copy of the fixture project,
with file edits disabled, on a machine that also has the competing `deuxui` UX plugin installed.

The corpus has 27 queries: 18 should-trigger and 9 near-miss should-not. Of the 18, 9 are the original phrasings
and 9 point at files that exist in the fixture. The originals name repos that aren't in the test folder
(`~/work/fleetops-web`), and agents often stop to look for them before choosing any skill.

| Description | Corpus | Accuracy | Should-trigger recall | False triggers |
|---|---|---|---|---|
| v1.4.0 (audit-first wording) | original 18 | 11/18 | 22% | 0% |
| v1.4.0 | repo-grounded 18 | 14/18 | 50% | 0% |
| two rewordings of v1.4.0 | original 18 | 11/18 each | 22% | 0% |
| **v1.4.1 (shipped: user-intent first)** | **all 27** | **25/27** | **81%** | **0%** |

What moved recall: leading with the jobs users actually ask for, framed as whole-codebase work. That means
making an app work on phones, one error pattern across every form, merging duplicate components, and
guardrails and a design contract. Before, the description led with the method (inventories, probes,
scorecards). The `deuxui` plugin had been winning those intents.

The two remaining misses:
- "Vue card consolidation in a repo that isn't there": the agent goes looking for the repo, a test artifact.
- "Design contract for a brand-new SvelteKit dashboard": `deuxui` picks it up, which is a reasonable fit for a greenfield screen contract.

All 9 near-misses stayed off in every run: backend work, TanStack API questions, palettes, a blog post on
Jakob's Law, scraping, flaky e2e, Storybook, an HTML email, a Next upgrade.
