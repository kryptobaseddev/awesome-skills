# Patterns for challenging skill-unique test cases

Use these patterns when reviewing or hand-writing `evals.json`. The auto-generator targets them; humans should too.

## Variety axes (mix all four)

| Axis | Variants | Why |
|---|---|---|
| **Phrasing** | Formal / casual / typos / abbreviations / multi-language code-switching | Real users phrase requests every way imaginable. |
| **Detail** | Terse one-liner / context-heavy paragraph with file paths and history | The skill must work for both. |
| **Explicitness** | Names the domain directly ("analyze this CSV") / buries it ("my boss wants a chart from this data file") | Description triggering should not require explicit keywords. |
| **Complexity** | Single-step / multi-step where the skill is one step among many | Tests whether the agent recognizes the relevant slice of work. |

## Edge-case taxonomy (at least 1-2 per eval set)

1. **Malformed input** — corrupted CSV with mixed quoting, JSON with trailing comma, PDF with a unicode BOM.
2. **Capability boundary** — request just outside the skill's documented scope (does it bail gracefully or hallucinate?).
3. **Ambiguous wording** — pronoun without referent ("clean it up"), multiple plausible interpretations.
4. **Combination** — a request that crosses two domains and forces the skill to interact with another (e.g., "analyze this CSV and post the summary as a GitHub PR comment").
5. **Adversarial format** — empty input, single-row input, all-null column, unicode-only text.
6. **Implicit assumptions** — request that depends on info not provided ("use the standard format" — what standard?).
7. **Scale boundary** — input 10× larger than the skill's documented examples.

## Near-miss negatives (1 per ~10 positives)

Each negative shares keywords or concepts with the skill but actually needs **different work**. Strong examples for a CSV-analysis skill:

- ❌ Strong: `"can you write a python script that reads a csv and uploads each row to our postgres database"` — involves CSV but the task is ETL, not analysis.
- ❌ Strong: `"I need to update the formulas in my Excel budget spreadsheet"` — same data domain, different work.
- ✅ Weak: `"what's the weather today?"` — no overlap; tests nothing.

## Realistic context cues

Real prompts contain:

- File paths: `~/Downloads/q4_results.xlsx`, `/tmp/incident-2026-05-12.log`
- Personal context: `"my manager asked me to..."`, `"we're trying to ship by Friday"`
- Specific details: column names, exact numbers, real-sounding company names
- Casual language: lowercase, abbreviations ("idk", "tbh"), occasional typos
- Mixed register: a formal sentence then a casual aside

## Anti-patterns to avoid

- ❌ Reusing the skill's own example prompts verbatim — overfits to what the skill author already considered.
- ❌ All positive cases — without near-misses you can't tell if the skill over-triggers.
- ❌ Same phrasing for every case — produces a description that only matches that phrasing.
- ❌ Vague "expected_output" like "a good summary" — leaves grading subjective.
- ❌ "Assertions" that are really just paraphrases of the prompt — they always pass trivially.

## Auto-generator review checklist

After running `generate_testcases.py`, scan `evals.json`:

- [ ] Mix of formal and casual phrasings
- [ ] At least one terse prompt and one context-heavy prompt
- [ ] At least one prompt that doesn't name the domain explicitly
- [ ] At least 1-2 edge cases per 6 prompts
- [ ] At least 1 near-miss negative per 5-10 positives
- [ ] No assertion is "the output is good" or equivalent
- [ ] Every assertion is observable from the output alone, without intermediate state
- [ ] Counts and limits use specific numbers, not "many" or "several"

Hand-edit liberally — auto-generation is a starting point.
