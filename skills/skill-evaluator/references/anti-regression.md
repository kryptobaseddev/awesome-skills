# Anti-regression playbook

A skill improvement that lifts the headline pass rate while silently breaking a previously-working capability is a regression. This document describes the patterns and how to prevent reintroducing fixed bugs.

## What `detect_regression.py` catches

| Category | Definition | Block? |
|---|---|---|
| **Hard regression** | Assertion that previously passed (≥ 0.66) and now fails (≤ 0.34) on with_skill | **Yes** |
| **Case regression** | Per-case `with_skill` pass rate dropped by more than max(prev_stddev, 0.10) | Warn |
| **Cost regression** | Per-case mean tokens or duration grew > 25% without ≥ +0.05 pass-rate gain | Warn |
| **Blind regression** | Blind comparator preferred old version more often than new | **Yes** |

"Block" means `detect_regression.py` exits with code 1 — useful as a CI gate. Warns exit 0 but mark the report.

## Patterns that silently regress a skill

### 1. Adding a sweeping rule

> "ALWAYS validate inputs before processing."

Sounds harmless. Often makes the skill burn tokens on validation for prompts that need no validation, and the skill stops being useful for quick exploratory tasks.

**Prevent**: write rules as "When X, do Y because Z" — not absolutes. Always include a *because* clause.

### 2. Replacing a script with prose

When a `scripts/foo.py` is replaced by SKILL.md instructions, the agent reinvents the script differently each run. Pass rate looks fine on a small eval set but variance explodes on a larger one.

**Prevent**: don't remove bundled scripts without a transcript-grounded reason. If the script wasn't being used, check whether SKILL.md referenced it.

### 3. Description over-specialization

Iterating the description against a small training set can chase specific phrasings — the description grows verbose and starts missing prompts that don't include the bolted-on keywords.

**Prevent**: enforce the 1024-char limit. Use train/validation splits. Select the description with the **best validation pass rate**, not the latest one.

### 4. Removing gotchas

The "Gotchas" section is where corrections to model defaults live. Trimming it because "the agent should know that" reintroduces the original mistake.

**Prevent**: gotchas are protected by the do-not-weaken constraint generator. Once an assertion was lifted by a specific gotcha, the gotcha is preserved across iterations.

### 5. Refactoring the workflow order

Skills often encode a fragile sequence (snapshot → migrate → verify). Reordering "for clarity" breaks the sequence. The eval may not catch this because the eval prompts request the *whole* workflow, not the sequence specifically.

**Prevent**: add at least one assertion per workflow that checks **order** (e.g., "The output mentions snapshot before migrate"). Or include a `plan-validate-execute` flow in the skill itself.

### 6. Broadening the description

Pushing the description to trigger on more contexts can also trigger on near-miss negatives — the description's discriminative power is gone. Trigger rate goes up; usefulness goes down.

**Prevent**: keep near-miss negatives in the trigger eval set. Track validation pass rate, not raw trigger count.

## Do-not-weaken constraints

`propose_improvements.py` automatically collects **do-not-weaken** constraints from all prior `regression_report.json` files in the workspace. Each entry is a `(case, assertion)` pair that was once lifted by the skill and protected against re-regression.

The proposer prompt includes the list explicitly and refuses to propose changes that would defeat any of them. This is the single most important guardrail in the loop.

If you must intentionally relax a constraint (e.g., scope reduction), do it in two steps:

1. Document the relaxation in `feedback.json` with a `_meta` note.
2. Delete the matching assertion from `evals.json` so the constraint stops being protected.

Don't ask the proposer to "remove the gotcha about X" — it will refuse, and rightly so.

## CI integration

If you want regression detection as a hard gate in CI:

```bash
uv run scripts/run_eval.py --skill ./my-skill --executor api --runs 3
uv run scripts/grade_assertions.py --workspace ./my-skill-workspace/iteration-1 --evals ./my-skill/evals/evals.json
uv run scripts/aggregate_benchmarks.py --workspace ./my-skill-workspace/iteration-1
if [ -d ./my-skill-workspace/iteration-0 ]; then
  uv run scripts/detect_regression.py \
    --baseline ./my-skill-workspace/iteration-0/benchmark.json \
    --current  ./my-skill-workspace/iteration-1/benchmark.json \
    --eval-results ./my-skill-workspace/iteration-1 \
    || exit 1   # block merge on regression
fi
```

The exit code is what to gate on. The JSON report is what to attach to the PR for review.

## Manual regression checks (no LLM required)

Even without LLM grading, you can spot regressions by reading `benchmark.json` deltas:

- If `with_skill.pass_rate.mean` dropped vs. previous iteration — **regression candidate**.
- If `with_skill.total_tokens.mean` grew > 25% with no pass-rate gain — **cost regression**.
- If `delta.pass_rate` (vs. baseline) shrank — the skill is less valuable than before.

`detect_regression.py` formalises these checks; do them by eye when you're iterating fast.
