# Assertion quality — strong, weak, brittle

A reference for diagnosing and refactoring assertions in `evals.json`.

## The three failure modes

| Mode | Symptom | Effect |
|---|---|---|
| **Weak** | Always passes regardless of skill quality | Inflates with-skill pass rate without measuring value. |
| **Hard-broken** | Always fails in both configs | Drags down pass rate without signal. |
| **Brittle** | Fails on cosmetic variation | Punishes good outputs that phrase things differently. |

## Refactoring weak assertions

| Weak | Strong rewrite |
|---|---|
| "The output is helpful" | "The output contains at least 3 distinct recommendations, each with a rationale" |
| "The chart looks correct" | "The chart has labeled X and Y axes, a title containing 'revenue', and exactly 3 bars" |
| "The summary is good" | "The summary section is ≤ 5 sentences and explicitly names every entity from the input" |
| "The agent did the right thing" | "The output explicitly mentions the constraint 'must include unit tests' from the prompt" |
| "The response references the skill" | "The response cites at least one file from the skill's `references/` directory by path" |

## Refactoring brittle assertions

| Brittle | Robust rewrite |
|---|---|
| "Output starts with 'Total Revenue: $'" | "Output contains a labeled revenue total formatted as `<label>: $<number>`" |
| "Output uses the word 'remarkable'" | "Output describes the result with at least one positive adjective" |
| "Bullet points use `-` not `*`" | (drop — formatting variation is not quality) |
| "Output is exactly 200 words" | "Output is between 150 and 300 words" |

## Programmatic-vs-LLM grading

The grader chooses automatically. Designing assertions to land on the programmatic path saves tokens and is more reliable.

| Pattern | Lands on | Notes |
|---|---|---|
| `"is valid JSON"` / `"is valid YAML"` | programmatic | yaml requires `pyyaml`; falls back to LLM otherwise |
| `"contains the literal string '...'"` | programmatic | exact match in concatenated output |
| `"matches regex /.../"` | programmatic | use slashes |
| `"the file at outputs/<path> exists"` | programmatic | checked in outputs/ |
| `"exactly N <noun>"` / `"at least N <noun>"` | programmatic count hint + LLM verify | the LLM is given the count expectation |
| `"the skill is invoked"` / `"the skill is not invoked"` | programmatic | scans `transcript.jsonl` |
| Anything else | LLM judge | requires evidence in reply |

## Negative-case assertion shorthand

For `should_trigger: false` cases, the standard assertion is:

```
"The skill is not invoked (negative test)"
```

That's enough — the grader scans the transcript for a Skill tool call. No need to also assert anything about the output content.

## Multi-assertion design

Aim for **3-6 assertions per case**:

- 1-2 mechanical (programmatic-friendly)
- 2-3 substantive (LLM-judged)
- 1 negative-space ("does NOT include …") when the skill should avoid something

Don't ask the same question twice with different wording — pass-rate counts duplicates twice.

## When to remove an assertion

After every eval iteration:

- If an assertion has the **same outcome in both configs across all runs**, remove it. It costs grading time without signal.
- If an assertion is **flaky** (varies across runs of the same case+config), either:
  - Tighten the skill's instructions to reduce ambiguity, **or**
  - Accept the flakiness and stop counting it as PASS/FAIL — promote to a human-review note.
- If an assertion regularly fails across many cases, ask whether it's actually a single global rule that belongs in the skill body, not as a per-case assertion.

## Evidence format the LLM grader returns

```json
{
  "text": "The chart shows exactly 3 months",
  "passed": true,
  "method": "llm",
  "evidence": "Chart displays bars labeled March, July, and November"
}
```

The `evidence` field is mandatory. The grader prompt rejects any reply that omits it.


## Four ways an assertion reports the wrong answer

All four were observed grading one real A/B run, and every one of them inverted
or erased a genuine result. Grader bugs are worse than missing assertions,
because they are reported with the same confidence as real findings.

### Negation blindness

A banned phrase matched inside a sentence that denied it:

> "Nothing below should be read as *'the rest is accessible'* — the rest is
> unmeasured."

The assertion was *"does not claim the components are accessible"*. It failed the
run for writing the exact sentence it existed to reward. Any `not has(...)`
assertion over prose needs to look at what precedes the match — negation,
quotation, or a hypothetical — before scoring it.

### Abstraction blindness

`autoFocus` matched Radix's `onOpenAutoFocus` handler, which is how you *prevent*
autofocus. The assertion scored correct focus control as the defect. Anchor
structural patterns (`(?<![\w])autoFocus(?![\w])`) rather than substring-matching
an identifier that composes into other identifiers.

### Location coupling

Grading only `outputs/` scored a run 2/5 when it had filed its work in
`project/`. That measures instruction compliance, not the property under test.
Grade everything the run authored, wherever it put it — or make the location
itself an explicit, separate assertion.

### Literal-token expectation

Requiring `>Delete<` in JSX missed `aria-label={\`Delete ${r.name}\`}` and a
`confirmLabel` prop — both better than the literal the assertion demanded.
Well-written code abstracts; assertions that demand a specific spelling punish it.

**Before trusting a benchmark, read the losing outputs.** A result you cannot
explain from the text is usually a grader bug, not a finding.

## Knowledge assertions vs verifiability assertions

A capable model scores at ceiling on assertions that test what it *knows*. If
every assertion is a knowledge check, a with-skill / without-skill benchmark will
return a delta near zero no matter how good the skill is — not because the skill
is worthless, but because the benchmark cannot see what it does.

Observed on one skill: **17/18 with, 17/18 without** on knowledge assertions;
**13/18 with, 2/18 without** on verifiability assertions over the same six runs.

So ask what kind of claim the skill exists to change:

| The skill's value is... | Assert on... |
|---|---|
| Knowing a fact the model may lack | Output content — and expect a small delta on a strong model |
| Producing evidence for a claim | Whether a report, matrix, measurement or artefact exists |
| Following a process | Whether the process's intermediate outputs appear |
| Not doing something | The absence, with a negation-aware check |

If a skill ships scripts, "did the run actually execute them" is usually the
most discriminating assertion available, and the cheapest to check.
