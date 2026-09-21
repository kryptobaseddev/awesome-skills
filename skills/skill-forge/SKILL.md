---
name: skill-forge
description: "End-to-end pipeline for building an Agent Skill in this repository, from deciding whether it should be a skill at all through to the commit. Use when creating a new skill, restructuring an existing one, deciding whether something needs scripts or just prose, choosing between a skill and a plugin, or working out why a skill fails CI, lands in the wrong README category, or never triggers. Ties together the pieces this repo already has - skill-validator for structure, skill-evaluator for measurement, plugin-creator for packaging - and adds the one gate that runs all of them at once plus the repo-specific traps none of them catch: git-recorded executable bits under core.fileMode=false, order-sensitive category matching, stale generated files, and descriptions that state a trigger but no boundary. Use even if the user only says 'make a skill for this', 'why is my skill failing CI', or 'should this be a plugin'."
license: MIT
compatibility: >-
  Python 3.9+ with pyyaml. Expects this repository's layout: skills/<name>/,
  a generated registry.json and README, and skill-validator present at
  skills/skill-validator. The measurement stage additionally needs the
  `claude` CLI for behavioural trigger evaluation. Nothing here is required to
  author a skill - it is required to know whether the one you authored is sound.
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-09-20 19:05:00"
  category: skill-development
allowed-tools: Bash Read Write Edit Glob Grep
---

# skill-forge — the pipeline from idea to commit

This repository already has the pieces: `skill-validator` checks structure,
`skill-evaluator` measures runtime quality, `plugin-creator` packages. What it did
not have is the thing that joins them — the order to do them in, the decisions
that come before any of them, and the handful of repo-specific traps that none of
them catch because they are not structural.

That gap is not theoretical. Running the gate across this repo found scripts in
two skills that their own SKILL.md tells an agent to execute, committed
non-executable, because `core.fileMode=false` means a local `chmod +x` never
reaches git.

## Three commands

```bash
# create -- emits a skill that passes the gate cold, constraints already applied
python3 skills/skill-forge/scripts/forge_new.py <name> \
    --purpose "one line" --category <slug> \
    --trigger "a situation" --boundary "what it is not for" \
    --casual "a casual phrasing" [--scripts]

# gate -- run before every commit that touches a skill
python3 skills/skill-forge/scripts/forge_check.py skills/<name>

# lifecycle -- gate, then measure triggering, then say what is next
python3 skills/skill-forge/scripts/forge_loop.py skills/<name> \
    --fixture <a real project containing what the queries name> [--runs 3]
```

`forge_new.py` exists because nothing else creates a skill from nothing —
`plugin-creator` scaffolds plugins, the other two check and measure, and the
globally-installed `skill-creator` writes files ad hoc. So every skill in this
repo was hand-authored and every author rediscovered the same constraints. The
scaffolder applies them: a validated name and a **real** category slug, a
description in the shape that triggers, three *top-level* reference files
because the depth rule is non-recursive, an eval set with more negatives than
positives, and the exact `git update-index --chmod=+x` line you will need.

Its output is a working skill, not a stub — the gate reports zero blocking rows
on it immediately, and the selftest asserts that round-trip.

Runs the validator, the progressive-disclosure rule and the body audit, then adds
what they do not cover: which README category the skill actually lands in and
which rule put it there, executable bits **as git records them**, generated-file
freshness, description headroom and boundary, eval presence, and the skill's own
selftest. Exit `0` clean, `1` problems.

Run it before every commit that touches a skill. `--json` for machine use.

## The pipeline

```
DECIDE     is this a skill? what shape? scripts or prose? skill or plugin?
   ↓
CONSTRAIN  read the limits BEFORE authoring, not after CI rejects you
   ↓
AUTHOR     description first, then body, then references, then scripts
   ↓
VERIFY     forge_check.py -- structure, category, exec bits, generated files
   ↓
MEASURE    does it trigger, and does it change the output
   ↓
SHIP       chmod in git, regenerate, commit, optionally package or wrap
```

Each stage has a reference. Read the one you are in.

| Stage | Read |
|---|---|
| Decide | `references/00-decide.md` |
| Constrain | `references/01-constraints.md` |
| Author | `references/02-author.md` — start with `forge_new.py` |
| Verify | `references/03-verify.md` |
| Measure | `references/04-measure.md` |
| Ship | `references/05-ship.md` |

## Facts that prevent broken work

| Fact | Consequence |
|---|---|
| **`core.fileMode=false` in this repo.** | `chmod +x` never reaches a commit. A script your SKILL.md says to run lands at `100644` and fails for every user. Needs `git update-index --chmod=+x`. Two shipped skills have this bug right now. |
| **Category matching is order-sensitive.** | A `mobile`, `ios`, `android` or `automation` tag hijacks a frontend skill into the wrong README section. So does the literal token `react-native` anywhere in name, description or tags. Set `metadata.category` explicitly and the whole question disappears. |
| **An unrecognised `metadata.category` fails silently.** | It matches no slug, falls through to rule matching, and nobody is warned. `design` and `ux` are not slugs; `frontend` is. |
| **The depth rule counts `references/*.md` non-recursively.** | Three files in `references/rules/` count as zero. Body ≥100 lines also satisfies it, which is why most skills pass without noticing. |
| **`README.md` and `registry.json` are generated and CI gates on them.** | A description change without regenerating fails `build_registry.py --check`. The pre-commit hook does it for you; `--no-verify` skips that. |
| **The body ERRORs at 600 lines, WARNs at 500.** | House norm is 200–300 with the weight in `references/`. Nothing in this repo exceeds 494. |
| **The description is the only thing an agent reads at startup.** | It is the entire trigger surface. A skill with a perfect body and a vague description never runs. |
| **A description with a trigger but no boundary poaches neighbours.** | Say what it is *not* for. Measured: adding one boundary clause removed a false trigger without costing a true one. |
| **Assertions grade text, not meaning.** | A banned-phrase check failed a skill for writing "nothing here should be read as 'the rest is accessible'" — the exact sentence it was meant to reward. |
| **A capable model scores at ceiling on knowledge.** | If every assertion tests what the model knows, a with/without benchmark returns ~0 delta no matter how good the skill is. Assert on evidence instead. |

## Decide before you build

Three questions, in order. `references/00-decide.md` has the full reasoning.

1. **Does this need to be a skill?** A skill earns its place when the task is
   multi-step, has non-obvious failure modes, or needs knowledge the model lacks
   or gets wrong. One-shot knowledge the model already has does not need one.
2. **Prose, or prose plus scripts?** Ship a script when the work is deterministic,
   repeated, and cheaper to run than to re-derive — and when its absence would
   have every invocation rewrite the same helper. Otherwise prose.
3. **Skill or plugin?** A skill is knowledge an agent loads. A plugin adds
   surfaces the harness owns: slash commands, subagents, hooks, MCP. If you want
   something to run *automatically* on a tool call, that is a hook, which means a
   plugin — see `plugin-creator`.

## Measure the two different things

Triggering and quality are separate questions with separate tools, and the
common mistake is reporting one as if it were the other.

```bash
# does an agent actually reach for it, in a real project
python3 skills/skill-evaluator/scripts/trigger_behavior_eval.py \
    --skill skills/<name> --queries skills/<name>/evals/trigger_queries.json \
    --cwd <a real project containing what the queries name> --runs 3

# does having it change the output
# (skill-evaluator's A/B loop, or skill-creator's if you have it installed)
```

`forge_loop.py` runs this for you and reports it as **not measured** rather than
guessing when you give it no fixture — because the two ways this goes wrong both
produce a confident zero. A detector that judges only the **first** tool call
reports ~0% (agents orient before consulting anything, median 6 calls in one
measured run), and realistic queries in an **empty** directory trigger nothing
(the agent correctly says there is nothing to look at). `references/04-measure.md`.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/forge_new.py` | **The scaffolder.** Creates a skill that passes the gate cold: validated name, real category slug, trigger-shaped description, three top-level references, an eval set, and the chmod line. `--list-categories` prints the real slugs. |
| `scripts/forge_check.py` | **The gate.** Validator + depth + body audit, plus category resolution, git-recorded exec bits, generated-file freshness, description headroom and boundary, evals, selftest. |
| `scripts/forge_loop.py` | **The lifecycle.** Runs the gate, then behavioural trigger measurement, then prints the next actions. Orchestrates — the measurement belongs to `skill-evaluator` and is not reimplemented here. |
| `scripts/selftest.py` | Asserts the gate fires on a broken fixture, stays silent on a sound one, and that a freshly scaffolded skill passes. |

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | `chmod +x` and committing | `git update-index --chmod=+x <path>`; `core.fileMode=false` hides the difference |
| 2 | Letting the category resolve by matching | Set `metadata.category` to a real slug |
| 3 | Using a slug that does not exist | It fails silently. Check against `categories.yml` |
| 4 | Editing a description without regenerating | CI gates on `build_registry.py --check` |
| 5 | Putting the weight in the body | 200–300 lines; depth belongs in `references/` |
| 6 | Counting `references/sub/*.md` toward the depth rule | The check is non-recursive |
| 7 | A description that triggers but never says what it is not for | Add a boundary; it costs ~40 characters |
| 8 | Reporting an arbiter judgement as a trigger rate | No agent was run. Use the behavioural evaluator |
| 9 | Writing assertions that match text literally | They invert results. See `skill-evaluator/references/assertion-quality.md` |
| 10 | Shipping scripts with no selftest | A check that cannot fail its own negative case is a comment |

## Resources

- https://agentskills.io/specification.md
- `skills/skill-validator/config/default.yml` — the thresholds, as data
- `skills/skill-validator/config/categories.yml` — the ordered category rules
- `skills/skill-evaluator/references/trigger-measurement.md`
- `skills/skill-evaluator/references/assertion-quality.md`
