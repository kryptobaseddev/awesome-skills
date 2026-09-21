# Verify: the gauntlet, in order

```bash
python3 skills/skill-forge/scripts/forge_check.py skills/<name>
```

That is the whole stage. It runs the three existing tools and adds what they do
not cover. Everything below explains what it is doing and how to read a failure.

## What it delegates

| Check | Tool | Blocks? |
|---|---|---|
| Structure and frontmatter | `skill-validator/scripts/validate.py` | yes |
| Progressive disclosure | `skill-validator/scripts/check_depth.py` | yes |
| Sections, links, dupes, placeholders | `skill-validator/scripts/audit_body.py` | no |

## What it adds

**Category resolution.** Prints which section the skill lands in and *why* —
explicit slug, or the specific tag/keyword that matched. Catches the silent
failure where an unrecognised `metadata.category` falls through to rule matching
with no warning.

**Executable bits as git records them.** Parses the body for
`python3 scripts/x.py` / `bash scripts/x.sh` and checks each against
`git ls-files -s`. Under `core.fileMode=false` this is the only view that
matters. Found the bug in two shipped skills.

**Generated-file freshness.** `build_registry.py --check`. A hard CI gate, and
the most common reason a correct skill fails the pipeline.

**Description headroom and boundary.** Length against the configured cap, plus
whether there is a "Use when" clause and whether anything states what the skill
is *not* for.

**Evals presence.** `trigger_queries.json` with a real negative count —
negatives are what catch a skill poaching its neighbours — and `evals.json`.

**The skill's own selftest.** Runs `scripts/selftest.py` if present; warns if the
skill ships scripts and has none.

## Reading failures

| Symptom | Cause |
|---|---|
| `progressive disclosure exit 1` | Body <100 lines *and* fewer than 3 top-level `references/*.md`. Sub-directories do not count |
| `executable bits ... not +x in git` | Run the printed `git update-index --chmod=+x` |
| `generated files stale` | `python3 scripts/build_registry.py`, commit the result |
| `category ... matches no slug` | Typo'd slug; it is failing silently. Use one from `categories.yml` |
| `description ... over the limit` | Trim; the cap is a hard ERROR |

## Before you commit

Warnings do not block. They are still worth a pass — every one of them is
something that has bitten someone. In particular, a skill with no evals cannot be
measured by anything, ever, and that is a decision worth making deliberately
rather than by omission.
