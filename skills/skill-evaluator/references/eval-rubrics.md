# Evaluation rubrics

Reference material for the evaluator. Loaded on demand — `SKILL.md` points here when designing assertions, grading outputs, or running blind comparisons.

## 1. Assertion quality bar

Reserve assertions for things that can be checked **objectively** from the output. Anything else belongs in human review (`feedback.json`), not in `evals.json`.

| Quality | Example |
|---|---|
| **Strong** — programmatic | `"The file at outputs/report.json is valid JSON"` |
| **Strong** — observable, specific | `"The bar chart has labeled X and Y axes"` |
| **Strong** — countable | `"The recommendations list contains at least 3 items"` |
| **Weak** — vague | `"The output is good"` |
| **Weak** — un-verifiable from output alone | `"The agent followed the right reasoning"` |
| **Brittle** — over-specifies wording | `"Output starts with literal 'Total Revenue: $'"` |
| **Brittle** — depends on model nondeterminism | `"Output uses exactly the word 'remarkably'"` |

When an assertion is too easy (always passes in both with-skill and without-skill), drop it — it inflates pass rate without measuring skill value. When an assertion is too hard (always fails), either fix it, fix the test case, or accept that it's a known capability gap.

## 2. Grading principles (the truth bar)

- **Require concrete evidence for a PASS.** Don't give the benefit of the doubt. A section *labelled* "Summary" with one vague sentence is a FAIL — the label is there but the substance isn't.
- **Quote or reference output, never opinion.** "The chart title is 'Top 3 Months by Revenue'" beats "The chart looks correct".
- **Use programmatic checks where possible.** They are more reliable than LLM judgement on mechanical questions (valid JSON, file exists, regex match, row count, exit code).
- **LLM grader system prompts must demand rigor.** The `assets/prompts/llm-judge.md` template enforces this.
- **Review the assertions themselves while grading.** If an assertion is always passing, drop it. If it's never passing in either config, fix it. The grading run is also an *assertion* review.

## 3. Blind comparison rubric (holistic quality)

Two outputs may both pass every assertion and still differ dramatically. The blind judge scores 1-5 on each axis without knowing which version produced which:

| Axis | What to look for |
|---|---|
| `on_task` | Did the output address the user's actual request? Not adjacent — actual. |
| `depth` | Substantive, specific, grounded — vs. generic platitudes. |
| `structure` | Organized, scannable, well-formatted; right level of headings/lists. |
| `actionability` | Clear next steps or directly usable artifacts. |
| `correctness` | Free from obvious factual or logical errors. |

The judge then declares `winner: "A" | "B" | "tie"` with a ≤200-char reason.

## 4. Benchmark interpretation

The aggregate `benchmark.json` reports mean ± stddev for **pass_rate, total_tokens, duration_ms** per configuration, plus the **delta** vs. baseline. Read the delta first:

| `pass_rate` delta | `tokens` delta | `duration` delta | Interpretation |
|---|---|---|---|
| ≥ +0.20 | small | small | Clear win. Ship it. |
| ≥ +0.20 | large positive | large positive | Real lift but expensive. Consider whether the cost is worth it for the use case. |
| near 0 | any | any | The skill isn't adding value on this eval set. Check whether the baseline is too good (cut easy assertions) or the skill is failing where it should help. |
| negative | any | any | The skill is **hurting**. Inspect failing-with-skill / passing-without cases. |

A pass rate near 1.0 in both configs means the eval set is too easy — generate harder edge cases.

## 5. Statistical notes

- `stddev` is only meaningful with ≥ 3 repeated runs per case.
- In early iterations (2-3 cases, single run), trust raw pass counts and the delta — not the stddev.
- A delta within 1 stddev of zero is noise. Don't claim improvement on the basis of one such iteration; rerun.

## 6. Eval set hygiene

| Smell | Fix |
|---|---|
| Every case passes with and without the skill | Generate harder edge cases; add near-miss negatives. |
| Every case fails in both configs | Test set is too hard or the skill is broken. Inspect the easiest case. |
| Cases pass with-skill 60% of the time, fail 40% | Flaky. Read the transcript for that case; the skill's instructions are ambiguous. |
| Same case passes / fails opposite ways across runs but pass_rate looks fine | High stddev hidden in the mean — read per-run results, not just aggregates. |
| Token usage 3× higher on one specific case | Read that run's transcript for the bottleneck (likely a context-blowup loop or wasted exploration). |
