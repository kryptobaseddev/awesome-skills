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

**v1.4.3 (shipped): 27/27. Every should-trigger query fired in 3 of 3 runs (100% recall), and no near-miss
fired in any run (0% false triggers). That's 81 runs on claude-opus-5-5, on a machine that also has the
competing `deuxui` UX plugin installed.**

Reproduce it with `evals/run_triggers.py`:
```bash
cd evals && python3 run_triggers.py --eval-set trigger_queries.json --skill ux-laws --fixtures files \
  --work /path/to/scratch --runs 3 --model claude-opus-5-5 --out results.json
```

How the runner keeps the measurement honest:
- **It scans the whole tool sequence.** skill-creator's `run_eval.py` only inspects the first tool call, and it registers a temp command beside the installed skill, so it under-reports skills that agents reach after orienting.
- **Every run gets a fresh git copy of its fixture, deleted afterwards.** Agents can write files through the shell even with Edit/Write disabled. Sharing one copy let earlier runs half-migrate the cards and install Storybook, which changed what later runs saw.
- **Queries name their fixture.** That's `brownfield-shop` (React), `vue-marketplace` or `sveltekit-dashboard`, so "a vue 3 codebase" or `src/routes/settings/+page.svelte` meets a matching project.
- **A query that names a repo under `~` gets a throwaway HOME.** The query sets `home_path` (for example `work/fleetops-web`), and the runner builds a HOME that holds the fixture at that path and links the real Claude config. Without that, the agent rightly refuses to audit a repo that isn't there.

The corpus has 27 queries: 18 should-trigger and 9 near-miss should-not. Of the 18, 9 are the original
phrasings and 9 point at files in the fixture.

| Description | Harness | Accuracy | Should-trigger recall | False triggers |
|---|---|---|---|---|
| v1.4.0 (audit-first wording) | shared copy, original 18 | 11/18 | 22% | 0% |
| v1.4.1 (user-intent first) | shared copy, 27 | 25/27 | 81% | 0% |
| v1.4.2 (+ component foundation for new apps) | shared copy, 27 | 26/27 | 92% | 0% |
| **v1.4.3 (+ "from a single page review to the whole codebase")** | **isolated per run, 27** | **27/27** | **100%** | **0%** |

What moved recall:
1. **User intent first.** Lead with the jobs users ask for: make it work on phones, one error pattern across every form, merge duplicate components, guardrails, a design contract or component foundation. Leading with the method lost those requests to `deuxui`.
2. **Claim the whole range of scope.** "From a single page review to the whole codebase" replaced "whole codebase rather than one screen", which had been steering single-page Laws of UX reviews away.
3. **Give every query a project that matches it.**

The shared-copy rows are indicative; only the v1.4.3 row was measured with per-run isolation.

The 9 near-misses all stayed off: backend work, TanStack API questions, palettes, a blog post on Jakob's Law,
scraping, flaky e2e, Storybook, an HTML email, a Next upgrade.
