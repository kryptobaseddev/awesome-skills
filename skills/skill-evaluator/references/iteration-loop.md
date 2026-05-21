# The iteration loop — full playbook

Read this when running the improvement loop manually rather than `--auto-loop`. Each pass through the loop produces one new `iteration-N/` directory.

## Loop diagram

```
   generate ──► run ──► grade ──► aggregate ──► analyze patterns
                                                       │
                                                       ▼
   apply  ◄── review ◄── propose ◄── detect regression ◄┘
     │
     ▼
   next iteration
```

## Step-by-step

### 1. Generate or refresh test cases

Skip this step on iterations 2+ unless you are deliberately expanding coverage. The eval set should be **stable across iterations** for the comparison to be valid.

If you add new cases mid-loop, they appear as `with_skill` passes / `without_skill` passes from iteration N onward — but there's no historical comparison. Document the change in `feedback.json`.

### 2. Run with stable parameters

Use the **same** `--runs` count and `--executor` across iterations. Changing them mid-loop invalidates regression detection because stddev shifts with sample size.

If you must change executor (e.g., switching from API to a real Claude Code session), treat the new iteration as a fresh baseline — don't compare it to prior iterations.

### 3. Grade with the same judge

`--judge hybrid` is the default. If you switch to `--judge llm` mid-loop, expect drift. The hybrid judge is more reproducible because programmatic checks are deterministic.

### 4. Aggregate and inspect the delta

Before reading `patterns.json`, look at `benchmark.json`:

- Is `delta.pass_rate` positive? If not, the skill is not adding value on this iteration.
- Is stddev small relative to the delta? A 5-point delta with 4-point stddev is noise.
- Did `tokens` or `duration` blow up? An "improvement" that triples token cost is suspect.

### 5. Patterns first, transcripts second

`analyze_patterns.py` shows you what to fix. The order to attack:

1. **Drop assertions in `always_pass_in_both`** — they were too easy.
2. **Fix or remove `always_fail_in_both`** — broken assertion or test case.
3. **Study `skill_dependent`** — note the largest-lift assertions; these are what the skill *should keep doing*. Add them to do-not-weaken when iterating.
4. **Investigate `flaky`** — open transcripts for those cases. If the skill's instructions are ambiguous in the relevant section, tighten them.
5. **Read `cost_outliers`** transcripts — usually a context-blowup loop or wasted exploration.

### 6. Detect regression *before* believing improvement

`detect_regression.py` is mandatory on iteration 2+. A non-empty `hard_regressions` list **blocks** declaring improvement. If you must accept a regression (e.g., a deliberate scope reduction), record it explicitly in `feedback.json` so the proposer treats it as intentional.

### 7. Read the proposal critically

The proposer is given the regression report and instructed not to weaken protected instructions. It still hallucinates confident bad ideas occasionally. Apply the heuristics below:

| Proposal smell | What to do |
|---|---|
| "Add a comprehensive section on …" | Push back. Comprehensive sections rarely help — concise wins. |
| "Add this 200-word rule to handle case X" | Ask whether case X is a real recurring need or a one-off. If one-off, drop it. |
| "Remove this paragraph" with rationale grounded in transcripts | Almost always good. Lean skills outperform exhaustive ones. |
| "Bundle this repeated logic into a script" | Verify the proposer's claim by reading 2-3 transcripts. If they really do reinvent the same logic, do it. |
| "Rewrite the description to add these keywords" | Suspect overfitting. Only accept if the keywords represent a general capability, not specific failed queries. |

### 8. Apply changes manually

Even with `--apply-proposals`, read every change. The proposal is markdown describing changes; copy them into `SKILL.md` yourself unless you have automation that diffs the file.

After applying, commit the diff (in your version control of choice) so the next iteration's snapshot captures the *previous* state. The evaluator's `skill-snapshot/` lives in the workspace and is auto-created on iteration ≥ 2, but it never overwrites — so an existing snapshot represents an earlier state.

### 9. Re-run the full eval set

A new iteration must rerun **all** cases, not just previously-failing ones. This is how `detect_regression.py` catches silent breakage.

## When to stop

| Signal | Action |
|---|---|
| Pass rate stable across two iterations within 1 stddev | Stop. Diminishing returns. |
| Pass rate dropping for two iterations | Revert. Either the proposer is wrong or the eval set drifted. |
| Hard regression you can't fix | Stop. Revert to the previous iteration. |
| Feedback consistently empty AND pass rate ≥ 90% | Ship it. |
| Pass rate ≥ 95% on a small eval set | Expand the eval set before declaring victory. |

## Description-loop interactions

The description optimization loop (`description_eval.py`) runs **separately** from the output-quality loop. Run it:

- Once when the skill is first created.
- Whenever you change the skill's scope or capabilities (description must follow scope, not lead it).
- If trigger rate seems low in observed real usage.

Do not interleave description tuning with output-quality tuning — they have different eval sets and different success metrics.

## Logging changes

Each iteration's `feedback.json` is the place for human notes that don't fit anywhere else:

```json
{
  "eval-top-months-chart": "Chart is missing axis labels and months are alphabetical.",
  "eval-clean-emails": "",
  "_meta": "Iteration 3: deliberately accepted regression on edge case 'binary csv' because the skill scope explicitly excludes binary inputs."
}
```

Empty string = "looked fine". The `_meta` field is for cross-cutting notes.
