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

Measured on `trigger_queries.json` (9 should-trigger, 9 near-miss should-not) with a runner that scans the
whole tool sequence. skill-creator's `run_eval.py` only inspects the first tool call, and it registers a temp
command beside the installed skill, so it under-reports. Each query was run with `claude -p` (claude-opus-5-5)
inside a copy of the fixture project with file edits disabled, on a machine that also has the `deuxui` plugin
installed.

| Description | Accuracy | Should-trigger recall | False triggers | Winner on missed positives |
|---|---|---|---|---|
| v1 (shipped) | 11/18 | 22% | 0% | deuxui 9 of the misses, rest stop before choosing a skill |
| v2 (trigger phrases first) | 11/18 | 22% | 0% | deuxui 7 |
| v3 (explicit "choose this over deuxui" routing) | 2/9 positives | 22% | not run | deuxui 8 |

Reading the result:
- **No false triggers.** All 9 near-misses stayed off: backend work, TanStack API questions, palettes, a blog post about Jakob's Law, scraping, flaky e2e, Storybook, an HTML email, a Next upgrade.
- **Positives are lost to competition, not wording.** On this machine the `deuxui` plugin (whose description claims "any screen, flow, page, component…") wins most UX requests, so rewording ux-laws didn't move recall. On a machine without deuxui, ux-laws is the only UX skill these queries match.
- **The rest of the misses are a test artifact.** Several queries name repos that aren't in the test folder (`~/work/fleetops-web`), so the agent stops after looking around, before choosing any skill.
- The shipped description was kept, since no variant measured better.
- To route these requests to ux-laws on a machine that has both skills, narrow deuxui's description to building single screens against its contract. That's an owner decision about deuxui, not a ux-laws change.
