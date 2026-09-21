# Measuring whether a skill triggers

Triggering is the highest-leverage property of a skill — a skill that never
loads has no other qualities — and it is the one most often measured wrong. Three
methods, in increasing order of what they actually tell you.

## 1. Arbiter judgement (`description_eval.py`)

Ask a model: *given this description and this query, should the skill activate?*

Cheap, deterministic enough, no agent runtime. It measures whether the
description **reads as relevant**. It cannot tell you whether an agent in a real
session would reach for it, because nothing in the loop is real: no project, no
competing skills, no tools, no cost of stopping to consult something.

Use it to iterate on wording quickly. Do not report it as a trigger rate.

## 2. First-tool-call detection

Run the agent, watch the stream, and decide from the first `tool_use` block: if
it is `Skill` or `Read`, wait for the name; otherwise conclude "did not trigger".

**This systematically under-reports, and the error is not small.** Agents
orient before they consult anything — `ls`, `find`, a couple of `Read`s to see
what they are dealing with — and invoke the skill several calls later. Skills
whose own instructions begin "first, inspect the project" are penalised hardest,
which is exactly backwards.

Measured on `deluxui`: **0/11 positives** by this method. Direct observation of
the same queries showed `Skill(deluxui)` firing at call 9 and the workflow
proceeding correctly. `trigger_behavior_eval.py` reports the median call depth
for this reason — if it is above 1, a first-call detector is lying to you.

## 3. Whole-sequence behavioural measurement (`trigger_behavior_eval.py`)

Run a real agent in a real project and scan every tool call for a `Skill`
invocation or a read of the skill's `SKILL.md`. This is the only one of the
three that measures the thing people mean by "does it trigger".

```bash
python3 scripts/trigger_behavior_eval.py \
  --skill skills/my-skill \
  --queries skills/my-skill/evals/trigger_queries.json \
  --cwd /path/to/a/real/project --runs 3
```

### The fixture has to be real

A good trigger query names files, routes, a stack, a dev server — that is what
makes it realistic. Run it in an empty directory and the agent correctly answers
*"there's nothing here to look at"* and triggers nothing at all.

Observed directly: three `deluxui` queries scored 0/3 in a fixture missing the
files they named. After adding a `DataTable.tsx` and a Three.js component to the
fixture, the same three queries scored 2/3, 2/3 and 3/3 with no change to the
skill. **Every one of those "misses" was a property of the fixture.**

Build the fixture from the queries: whatever they mention must exist.

### Trigger rate is noisy — budget runs accordingly

Identical 20-query sets, same description, differed by two on consecutive runs.
A single run cannot distinguish 17/20 from 18/20.

| Question | Runs per query |
|---|---|
| Rough signal while iterating on wording | 1 |
| Reporting a rate | 3 |
| Claiming a delta between two descriptions | 5+, and compare the same queries |

### Reading the two failure modes differently

A **MISS** (should trigger, did not) is usually one of: the description does not
name the user's vocabulary; the task reads as too small to be worth consulting a
skill; or the fixture does not contain what the query refers to. Check the third
before editing the description — it is the most common and the least suspected.

A **FALSE** (should not trigger, did) means the description claims territory the
skill does not serve. The fix is usually a boundary sentence, not a shorter
description. If the skill's own body already draws that line, say so in the
description too: they should agree.

### Do not overfit

Twenty queries is a small set. If a wording change fixes exactly one query and
changes nothing else, you have probably fitted the query rather than improved the
description. Prefer edits that name a capability the skill genuinely has, or a
boundary it genuinely keeps — both generalise; a keyword does not.
