# Test case generator prompt

This is the LLM system+user prompt used by `scripts/generate_testcases.py`. Stored as a separate asset so it can be reviewed, audited, or swapped without editing Python.

## System

```
You design rigorous evaluations for AI agent skills. You are creative, specific,
and never produce generic boilerplate. You always reply with the JSON block
requested — nothing else.
```

## User template

```
You are designing an evaluation set for an Agent Skill. The skill is below
inside <skill></skill>. Produce {count} challenging, REALISTIC test prompts
that probe whether the skill produces high-quality outputs.

Hard requirements for the set as a whole:
  - About {pos_count} prompts SHOULD activate the skill (should_trigger: true).
  - About {neg_count} prompts should NOT activate the skill (should_trigger: false)
    but must be NEAR-MISSES — share keywords or concepts with the skill yet
    actually need something different. No trivial negatives.
  - At least {edge_count} prompts must hit an edge case: malformed/missing
    inputs, ambiguous wording, a capability boundary, an unusual combination
    not shown in the skill's own examples, or a request that mixes the skill's
    domain with an unrelated one.
  - Vary phrasing (formal, casual, with typos/abbreviations), vary detail
    (terse vs. context-heavy multi-paragraph), vary explicitness (names the
    domain directly vs. buries it). Include realistic context (file paths,
    column names, personal context like "my manager asked me to…").
  - DO NOT just reuse the skill's own example prompts. Push beyond them.

For each test case provide:
  - "id": short kebab-case slug (unique)
  - "prompt": the exact user prompt
  - "should_trigger": bool
  - "expected_output": one-sentence human description of what success looks like
  - "assertions": 3-6 specific, observable, programmatically- or
    LLM-checkable assertions. NO vague "looks good" assertions. Prefer
    "the output contains X", "the file at Y has Z rows", "valid JSON",
    "labelled axes", "exactly N items".
  - "files" (optional): list of input file paths the test would supply

Reply ONLY with a JSON array of test cases inside a ```json fenced block.
Do not include commentary outside the fence.

<skill>
name: {name}
description: {description}

{body_excerpt}
</skill>
```
