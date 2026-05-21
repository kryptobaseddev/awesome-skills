---
name: skill-evaluator
description: Eval-driven quality evaluation, regression detection, and auto-improvement of Agent Skills. Auto-generates challenging test cases unique to the target skill from its SKILL.md, runs A/B benchmarks (with-skill vs without-skill or version-vs-version), grades outputs with programmatic + LLM-judge assertions, aggregates pass-rate/token/latency deltas, detects regressions across iterations, proposes generalized improvements grounded in failure transcripts, and optimizes the trigger `description` field via train/validation splits. Use whenever the user wants to evaluate, benchmark, A/B test, grade, score, regression-test, fine-tune, harden, optimize, improve, iterate on, or measure the quality of any skill — even if they only say "test this skill", "is this skill any good", "rate this skill", "tune the description", "did my edits make it worse", or "make this skill better".
license: MIT
allowed-tools: Bash(uv:*) Bash(python3:*) Bash(jq:*) Bash(ls:*) Read Write Edit Glob Grep
---

# Skill Evaluator

Eval-driven quality measurement, regression detection, and iterative improvement for Agent Skills. This skill complements `skill-creator` (which builds skills) and `ct-skill-validator` (which checks structure) by measuring **runtime output quality** and closing the improvement loop without regressing previously-validated behavior.

## When to invoke

Trigger this skill any time someone wants to know whether a skill *actually works well in practice* — not just whether it parses, but whether it produces better outputs than no skill at all, holds up under varied prompts, and improves rather than regresses across edits.

Common trigger phrases: "eval this skill", "benchmark this skill", "is this skill better than no skill", "did my changes regress it", "auto-improve this skill", "score the output quality", "tune the description", "test cases for this skill", "rate this skill against …".

## Mental model

Five questions the evaluator answers, in order:

1. **Does it trigger?** — Does the `description` field reliably activate on relevant prompts and stay quiet on near-misses? (description eval)
2. **Does it help?** — On realistic prompts, do the outputs with-skill beat without-skill on assertions, blind judging, time, and tokens? (output eval)
3. **What's broken?** — Which assertions fail, where do transcripts go off the rails, what edge cases got missed? (pattern analysis)
4. **How do we fix it without breaking what works?** — Propose lean, generalized changes; rerun the *full* eval set to catch regressions. (improvement loop)
5. **Is the improvement real?** — Compare benchmark deltas across iterations with statistical context, not vibes. (regression detection)

## End-to-end workflow (the standard loop)

> Run from any working directory. All scripts accept `--skill <path>` and write into a workspace mirror of the skill directory: `<skill-parent>/<skill-name>-workspace/iteration-<N>/`. The workspace is *not* checked into the skill — it is build output.

### 0. Plan the evaluation

Before generating anything, confirm with the user:

- Path to the skill being evaluated (e.g. `~/.claude/skills/foo`).
- Whether this is a *first eval* (baseline = no skill) or an *iteration eval* (baseline = previous skill snapshot).
- How many test cases to generate (default: 6 — 4 normal, 2 edge cases). More than 12 wastes tokens before the first signal.
- Number of repeated runs per case to estimate stddev (default: 3).

### 1. Auto-generate challenging test cases

```bash
uv run scripts/generate_testcases.py \
    --skill <skill-path> \
    --count 6 \
    --edge-fraction 0.35 \
    --out <skill-path>/evals/evals.json
```

`generate_testcases.py` reads the target SKILL.md, extracts trigger keywords, declared capabilities, examples, gotchas, and referenced scripts and bundled assets, then produces *unique* test cases tailored to that specific skill — not generic boilerplate. It deliberately mixes:

- **Phrasing variety** — formal, casual, with typos, abbreviations
- **Detail variety** — terse one-liners and context-heavy multi-paragraph prompts
- **Explicitness variety** — prompts that name the domain directly, prompts that bury it
- **Edge cases** — malformed inputs, ambiguous wording, capability boundaries, combinations not shown in the skill's own examples
- **Anti-overfit** — at least one prompt that *should not* trigger the skill (near-miss)

If an LLM endpoint isn't available, the script falls back to a deterministic template generator seeded by the SKILL.md fingerprint (still skill-unique, just less creative).

Review and edit `evals.json` before running — auto-generation is a starting point, not a substitute for human judgment. See `references/testcase-patterns.md` for the full quality bar.

### 2. Run the A/B eval

```bash
uv run scripts/run_eval.py \
    --skill <skill-path> \
    --evals <skill-path>/evals/evals.json \
    --runs 3 \
    --workspace <workspace-path> \
    --iteration 1
```

For each test case, `run_eval.py` spawns isolated agent runs — fresh context, no leftover state — in three configurations:

- **`with_skill/`** — the skill is loaded
- **`without_skill/`** — baseline, no skill (for first evals)
- **`old_skill/`** — previous snapshot, baseline for iteration evals (auto-snapshotted from git, or from `<workspace>/skill-snapshot/`)

It records `outputs/`, `transcript.jsonl`, `timing.json` per run. **Always capture `total_tokens` and `duration_ms` immediately** — they aren't persisted anywhere else.

### 3. Grade outputs

```bash
uv run scripts/grade_assertions.py \
    --workspace <workspace-path>/iteration-1 \
    --evals <skill-path>/evals/evals.json \
    --judge llm           # or 'script' for pure-programmatic, or 'hybrid' (default)
```

Hybrid grading uses Python checks where mechanical (file exists, valid JSON, row count, regex match, exit code) and an LLM judge for the rest — backed by **concrete evidence** for every PASS/FAIL, never opinions. See `references/assertion-quality.md` for the assertion bar and grading principles.

### 4. Blind comparison (version-vs-version)

For iteration evals, run a blind judge that sees both outputs without knowing which version produced which:

```bash
uv run scripts/blind_compare.py \
    --workspace <workspace-path>/iteration-1 \
    --pairs with_skill,old_skill
```

The blind judge scores holistic qualities (organization, polish, usability) that assertions miss. Two outputs can both pass every assertion and still differ dramatically in quality.

### 5. Aggregate the benchmark

```bash
uv run scripts/aggregate_benchmarks.py \
    --workspace <workspace-path>/iteration-1 \
    --out <workspace-path>/iteration-1/benchmark.json
```

Produces mean ± stddev for pass-rate, tokens, and time per configuration, plus the **delta** (what the skill costs vs. what it buys).

### 6. Analyze patterns — the truth filter

```bash
uv run scripts/analyze_patterns.py \
    --workspace <workspace-path>/iteration-1 \
    --benchmark <workspace-path>/iteration-1/benchmark.json
```

Surfaces the signals worth acting on, ignoring the noise:

- **Assertions that always pass** in both configs — *drop them*, they inflate scores without measuring skill value.
- **Assertions that always fail** in both configs — *fix the assertion or the test case*, not the skill.
- **Assertions that pass with-skill but fail without** — *this is where the skill is earning its keep*; understand why before changing it.
- **Flaky cases** (high stddev across repeated runs) — tighten the skill's instructions to reduce ambiguity, or accept that the case is genuinely model-bound.
- **Token/time outliers** — read the slow run's transcript to find the bottleneck.

### 7. Detect regression (mandatory before declaring improvement)

```bash
uv run scripts/detect_regression.py \
    --baseline <workspace-path>/iteration-<N-1>/benchmark.json \
    --current  <workspace-path>/iteration-<N>/benchmark.json \
    --eval-results <workspace-path>/iteration-<N>
```

Compares the new iteration to the previous one **per assertion and per test case**, not just the aggregate. A skill can lift overall pass rate by adding a new capability while silently breaking an old one. The regression detector flags:

- Any assertion that previously passed and now fails (hard regression)
- Any test case whose pass rate dropped more than 1 stddev
- Any test case whose token/time cost grew by >25% without matching quality gain
- Cases where blind comparison preferred the old version

**Never declare a skill improved if regression detection flags any hard regression.** Either fix the regression first or revert the change.

### 8. Propose improvements

```bash
uv run scripts/propose_improvements.py \
    --skill <skill-path> \
    --workspace <workspace-path>/iteration-<N> \
    --feedback <workspace-path>/iteration-<N>/feedback.json \
    --out <workspace-path>/iteration-<N>/proposal.md
```

Feeds the current SKILL.md, failed-assertion details, transcripts, and any human `feedback.json` notes to an LLM with the proposer prompt at `assets/prompts/improvement-proposer.md`. The prompt enforces the standard guardrails:

- Generalize from feedback (no per-case patches)
- Keep the skill lean (prefer cuts over additions)
- Explain *why* in instructions, not just *what*
- Bundle repeated work into `scripts/` if transcripts show reinvention
- **Never weaken instructions known to defeat regressions** — the proposer is given the regression report as a hard constraint

Review the proposal carefully before applying — *propose ≠ commit*.

### 9. Optimize the trigger description (separate loop)

```bash
uv run scripts/description_eval.py \
    --skill <skill-path> \
    --queries <skill-path>/evals/trigger_queries.json \
    --train-frac 0.6 \
    --runs 3
```

This is the **description-only** loop, separate from output quality. It:

- Generates ~20 queries (10 should-trigger, 10 should-not-trigger, mixed near-misses) tailored to the skill if `trigger_queries.json` is absent.
- Splits into train/validation (default 60/40), keeping the proportional should-trigger mix in both.
- Runs each query through an isolated agent context multiple times to estimate trigger rate.
- Reports per-query trigger rates plus train/validation pass rates.
- Iterates the `description` field, **only ever optimizing against the train split**.
- Selects the description with the best **validation** pass rate (often not the last one — later iterations overfit).
- Enforces the 1024-character limit and warns if the description grew during optimization.

See `references/iteration-loop.md` for the description-revision heuristics.

## Auto-improvement (full loop)

To run the whole loop end-to-end (generate → run → grade → analyze → check regression → propose → review → loop):

```bash
uv run scripts/run_eval.py --skill <skill-path> --auto-loop --max-iterations 5
```

The auto-loop stops when:

- All assertions pass on the train set *and* validation pass rate is stable across two iterations, **or**
- No iteration improves pass rate by more than 1 stddev for two iterations in a row (further work is noise), **or**
- The proposer suggests a change blocked by regression detection (revert + stop), **or**
- `--max-iterations` reached.

Each iteration writes `iteration-<N>/proposal.md`. Apply the proposal manually unless `--apply-proposals` is set (not recommended without review).

## Anatomy of the workspace

```
<skill-name>-workspace/
├── skill-snapshot/                   # auto-snapshot of the previous skill version
└── iteration-1/
    ├── eval-<slug>/
    │   ├── with_skill/{outputs, transcript.jsonl, timing.json, grading.json}
    │   ├── without_skill/{outputs, transcript.jsonl, timing.json, grading.json}
    │   └── old_skill/{...}           # only on iteration evals
    ├── benchmark.json                # aggregate stats with delta
    ├── patterns.json                 # output of analyze_patterns
    ├── regression_report.json        # output of detect_regression
    ├── blind_comparison.json         # output of blind_compare
    ├── feedback.json                 # human review notes
    └── proposal.md                   # LLM-proposed SKILL.md changes
```

Never edit files under `<skill-name>-workspace/` by hand — they are reproducible build artifacts. Edit `<skill-path>/evals/evals.json` and `<skill-path>/SKILL.md`.

## Quality bar: what makes a good eval

| Element | Good | Weak |
|---|---|---|
| Prompt | "I've got `~/Downloads/q4.xlsx` with revenue col C and expenses col D — add a margin column and highlight margins under 10%" | "process this data" |
| Assertion | "The output file is valid JSON and contains exactly 3 entries" | "the output is good" |
| Assertion | "The bar chart has labeled X and Y axes" | "the chart looks correct" |
| Assertion (too brittle) | — | "Output starts with the literal string 'Total Revenue: $'" |
| Edge case | malformed CSV with mixed quoting and a unicode BOM | "an empty file" (trivial) |
| Near-miss negative | "write a python script that uploads CSV rows to postgres" (CSV mentioned but task is ETL not analysis) | "what's the weather" (zero overlap) |

Full rubric: `references/eval-rubrics.md`.

## Bundled resources

### `scripts/`
- `generate_testcases.py` — auto-generate skill-unique challenging test cases from a SKILL.md
- `run_eval.py` — orchestrate with/without/old A/B runs (or `--auto-loop` the whole flow)
- `grade_assertions.py` — programmatic + LLM-judge assertion grading with evidence
- `blind_compare.py` — blind A/B holistic-quality judge
- `aggregate_benchmarks.py` — mean/stddev/delta benchmarks across runs
- `analyze_patterns.py` — extract actionable signal from graded results
- `detect_regression.py` — per-assertion / per-case regression detector across iterations
- `propose_improvements.py` — LLM-driven improvement proposer with regression guardrails
- `description_eval.py` — trigger-rate eval with train/validation split and optimizer

Run any script with `--help` to see its full interface.

### `references/`
- `eval-rubrics.md` — assertion-quality bar, grading principles, scoring rubrics, blind-judge rubric
- `testcase-patterns.md` — patterns for generating challenging skill-unique test cases (edge cases, near-misses, phrasing variety axes)
- `assertion-quality.md` — strong/weak/brittle assertion taxonomy and refactoring patterns
- `iteration-loop.md` — full playbook for the improvement loop, including description-revision heuristics
- `anti-regression.md` — regression patterns, how to detect them, and how to prevent reintroducing fixed bugs

### `assets/`
- `templates/evals.template.json` — starter eval set
- `templates/benchmark.template.json` — benchmark output shape
- `templates/grading.template.json` — grading output shape
- `prompts/testcase-generator.md` — LLM prompt to generate skill-unique test cases
- `prompts/llm-judge.md` — LLM judge prompt for assertion grading
- `prompts/blind-judge.md` — blind A/B comparator prompt
- `prompts/improvement-proposer.md` — improvement proposer prompt with regression guardrails

## Gotchas

- **Save tokens and duration the moment a run finishes.** Many agent runtimes drop them from later transcripts. The eval scripts capture them at exit; if you wrap them differently, do the same.
- **Always rerun the full eval set after a SKILL.md edit, not just the previously-failing cases.** A skill can gain a capability and silently regress another — that's the entire reason `detect_regression.py` exists. Skipping it is the most common way iteration "improvements" make a skill worse.
- **Workspace lives outside the skill directory.** Never write eval results into `<skill-path>/` other than `evals/evals.json` and `evals/files/*` — the rest is build output and pollutes distribution.
- **`evals/evals.json` is the only manually-authored eval file.** `grading.json`, `timing.json`, `benchmark.json`, `patterns.json`, `regression_report.json` are produced — never hand-edit them.
- **Description optimization and output optimization are separate loops.** Don't intermingle them — fixing the description shouldn't churn the output assertions, and vice versa.
- **The `delta` matters more than the absolute pass rate.** A skill that passes 95% of assertions is meaningless if the no-skill baseline also passes 95% — the skill isn't adding value.
- **Three runs per case is a *minimum* for stddev.** Single-run results are noise; trust them only for sanity checks during local iteration.
- **The proposer can hallucinate confident bad ideas.** Always read `proposal.md` before applying. The regression detector catches obvious damage, but subtle drift requires human judgment.
- **`uv run` is preferred** — every bundled script declares PEP-723 inline dependencies, so `uv run scripts/<name>.py` works without a separate install step. `pipx run scripts/<name>.py` works as a fallback.

## Validation loop (self-test)

To verify this skill itself works correctly on a known-good skill:

```bash
uv run scripts/run_eval.py \
    --skill ~/.claude/skills/skill-creator \
    --evals-auto \
    --runs 2 \
    --workspace /tmp/skill-evaluator-selftest
```

Expect a meaningful positive delta in pass rate (skill-creator should clearly beat no-skill on skill-creation prompts). If the delta is near zero, something in this evaluator is misconfigured — investigate before trusting it on other skills.
