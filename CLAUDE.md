# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A curated collection of **Agent Skills** (the [agentskills.io](https://agentskills.io/specification.md) open spec) authored by @kryptobaseddev, plus the Python tooling that validates them and keeps the index current. There is no application here — the "product" is `skills/*/SKILL.md`. Almost every task is either *authoring/editing a skill* or *working on the validator/registry pipeline*.

Skills are consumed by symlinking or copying `skills/<name>/` into a runtime's skills dir (`~/.claude/skills/`, `~/.agents/skills/`, `<project>/.claude/skills/`). A skill must therefore be **self-contained and path-independent** — nothing may reference this repo's layout from inside a `SKILL.md`.

Tooling requirements: `python3` + `pyyaml` (the only dependency). No package manager, no test suite, no build.

## Commands

```bash
# Validate one skill (exit 1 on ERROR; WARNs don't fail)
python3 skills/skill-validator/scripts/validate.py skills/<name>
python3 skills/skill-validator/scripts/validate.py skills/<name> --json
python3 skills/skill-validator/scripts/validate.py --print-config   # merged effective config

# Validate everything
for d in skills/*/; do echo "=== $d"; python3 skills/skill-validator/scripts/validate.py "$d"; done

# Deeper single-skill audits
python3 skills/skill-validator/scripts/audit_body.py skills/<name>     # sections, links, dupes, placeholders
python3 skills/skill-validator/scripts/check_depth.py skills/<name>    # progressive-disclosure rule
python3 skills/skill-validator/scripts/check_depth.py skills --all     # repo-wide sweep

# Registry + README (generated — see below)
python3 scripts/build_registry.py             # write
python3 scripts/build_registry.py --dry-run
python3 scripts/build_registry.py --check     # exit 1 if stale; CI runs this

# Runtime quality evals (spawns agent runs — expensive, opt in deliberately)
python3 skills/skill-validator/scripts/run_quality_eval.py skills/<name> --runs 3
python3 skills/skill-validator/scripts/run_quality_eval.py skills/<name> --trigger   # description-only
```

The `skill-evaluator` skill drives the full A/B / regression loop (`scripts/generate_testcases.py`, `run_eval.py`, `grade_assertions.py`, `blind_compare.py`, `detect_regression.py`, `propose_improvements.py`, `description_eval.py`). It writes into `<skill-parent>/<skill-name>-workspace/iteration-<N>/`, which is build output and gitignored (`*-workspace/`).

## Generated files — never hand-edit

`registry.json` and the region of `README.md` between `<!-- SKILLS-START -->` and `<!-- SKILLS-END -->` are both produced by `scripts/build_registry.py` from `skills/*/SKILL.md` frontmatter. Edit the frontmatter, then regenerate. Three things regenerate them:

| Trigger | Mechanism |
|---|---|
| `git commit` touching `skills/**` | `.githooks/pre-commit` (already wired via `core.hooksPath=.githooks`) validates each changed skill, then regenerates and re-stages `README.md` + `registry.json`. Bypass with `--no-verify`. |
| push to `main` | `.github/workflows/registry.yml` regenerates and auto-commits `chore(registry): ... [skip ci]`. |
| PR / push touching `skills/**` | `.github/workflows/validate.yml` validates changed skills and runs `build_registry.py --check`. |

A commit that changes a skill's `description` but leaves README/registry stale will fail CI's `--check`.

## Category resolution

Each skill lands in exactly one README section. Order of resolution, in `build_registry.py`:

1. `metadata.category: <slug>` in the skill's frontmatter (explicit override)
2. first matching rule in `skills/skill-validator/config/categories.yml` — matched by `tags` → `name_contains` → `keywords`, top-to-bottom
3. the `fallback` block ("Other" 📦)

**Rules are order-sensitive: list more specific categories first.** `Skill Development` must precede `AI Agents & LLMs` or `skill-validator`/`skill-evaluator` fall into the wrong bucket. Adding a category means editing `categories.yml` and rerunning the builder.

## Validator architecture

`skill-validator` is fully **config-driven** — rules are data, not code. `validate.py` merges YAML configs in this precedence order:

1. `--config <path>` (CLI)
2. `<skill-dir>/.skill-validator.yml` (skill-local)
3. `skill-validator.config.yml` (repo root) ← this repo's override
4. `skills/skill-validator/config/default.yml` (bundled spec defaults)

Overrides are partial — declare only the keys that differ. Any rule can be silenced with `severity: off`; whole groups with `enabled: false`. Tiers 1–3 (structure, frontmatter, body) always run; tiers 4–5 (manifest, provider map) activate only via `--manifest` / `--provider-map`.

The repo-root `skill-validator.config.yml` exists for one reason: it widens `frontmatter.allowed` to admit `inputs` and `references`, which are **local conventions, not spec fields**. A skill published outside this repo must drop them or fold them into `metadata`.

## Skill authoring conventions

Anatomy: `skills/<name>/SKILL.md` + optional `scripts/`, `references/`, `assets/`, `templates/`, `evals/`.

- **`name` must equal the directory name**; lowercase/digits/hyphens, ≤64 chars.
- **`description` is the only thing an agent reads at startup** — it is the trigger surface and the highest-leverage field in the repo. Single line (no YAML block scalar), ≤1024 chars, no angle brackets, and it must spell out concrete trigger phrases ("Use when …", "even if they only say '…'"). Study `quo` or `better-auth` for the house style.
- **Progressive disclosure**: body WARNs at 500 lines, ERRORs at 600. Long material belongs in `references/*.md` linked from the body, not inline. `check_depth.py` enforces the body-length-OR-`references/` rule.
- **`metadata.version` + `metadata.last_updated`** (`YYYY-MM-DD HH:MM:SS`) are bumped on every substantive edit; quote version strings (`version: "1.2.0"` — bare `1.0` WARNs as a float).
- **Bundled scripts** carry preflight/scaffolder/verifier duties (`*-preflight.sh`, `scaffold-*.mjs`, `verify-webhook.{js,py}`). This repo sets `core.fileMode=false`, so **`chmod +x` on disk does not reach git** — a script staged normally lands as `100644` no matter how it looks locally. Any script a `SKILL.md` tells the agent to run directly needs an explicit `git update-index --chmod=+x <path>` before committing. That is why 49 of the 65 committed scripts are non-executable and why a past commit had to fix one after the fact.
- **`evals/`** holds `evals.json` (output test cases) and/or `trigger_queries.json` (array of `{query, should_trigger}` — the description-eval corpus, deliberately including near-misses that must *not* fire).
- File references in the body must resolve relative to the skill dir, since the skill gets copied elsewhere.

## Conventions

- Commits: `feat(<skill-name>): summary (vX.Y.Z)` / `fix(<skill-name>): …`; pipeline commits use `chore(registry): …`.
- `.research/` is gitignored local scratch, not source.
- `*.skill`, `*.zip`, `dist/` are packaged artifacts and stay out of git.
