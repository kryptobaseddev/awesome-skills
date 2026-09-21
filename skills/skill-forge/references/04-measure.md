# Measure: two different questions

**Does it trigger?** and **does it change the output?** are separate, and
reporting one as the other is the commonest error in this area.

## Triggering

```bash
python3 skills/skill-evaluator/scripts/trigger_behavior_eval.py \
    --skill skills/<name> \
    --queries skills/<name>/evals/trigger_queries.json \
    --cwd <a real project containing what the queries name> --runs 3
```

Three ways to measure this; only one answers the question people are asking.
`skill-evaluator/references/trigger-measurement.md` has the detail. The short
version, all of it measured rather than reasoned:

- **Arbiter judgement** (ask a model whether the description *should* match) is
  cheap and tells you about wording. No agent runs. Do not report it as a rate.
- **First-tool-call detection** under-reports badly. Agents orient before
  consulting anything — median 6 calls in one measured run — so a detector that
  gives up when call #1 is `Bash` scored **0/11** on a skill that triggered
  **10/11**.
- **Whole-sequence behavioural measurement** is the real answer, and it needs a
  **real fixture**. Queries that name files and routes trigger nothing in an
  empty directory, because the agent correctly says there is nothing to look at.
  Three queries went 0/3 → 2–3/3 purely by adding the files they mentioned.

Rate is noisy: ±2 of 20 between identical runs. One run per query cannot support
a delta. Three to report, five or more to claim an improvement.

## Building the query set

20 queries, roughly 11 positive / 9 negative. Realistic prose — file paths, stack
names, lowercase, typos, a bit of backstory. The negatives matter more than the
positives: make them **near-misses** that share vocabulary with the skill but
need different work. An obviously-irrelevant negative tests nothing.

Then build the fixture *from* the queries. Whatever they mention must exist.

## Output quality

Run the task with and without the skill and grade both. `skill-evaluator` has the
A/B loop, the graders and the aggregation.

The trap worth knowing before you start: **a capable model scores at ceiling on
knowledge.** If every assertion tests what the model knows, the delta will be
near zero regardless of skill quality — not because the skill is worthless but
because the benchmark cannot see what it does.

Measured on one skill, same six runs:

| Assertion kind | with | without |
|---|---|---|
| Knowledge (does it know the right answer) | 17/18 | 17/18 |
| Verifiability (is the claim backed by evidence) | 13/18 | 2/18 |

So assert on the thing the skill actually changes. If it ships scripts, *"did the
run execute them"* is usually the most discriminating assertion available and the
cheapest to check.

## Grading the grader

Four assertion failure modes, all observed inverting a real result — negation
blindness, abstraction blindness, location coupling, literal-token expectation.
They are documented with examples in
`skill-evaluator/references/assertion-quality.md`.

**Read the losing outputs before believing a benchmark.** A result you cannot
explain from the text is usually a grader bug. In one run a banned-phrase check
failed a skill for writing *"nothing below should be read as 'the rest is
accessible'"* — the exact sentence the assertion existed to reward.

## When not to measure

A skill whose value is a boundary ("do not do X here") or a reference table may
have no meaningful output delta. Say so and skip the A/B rather than
manufacturing assertions that will pass either way. A non-discriminating
benchmark is worse than none: it produces a number people will quote.
