---
name: skill-validator
description: "Validate any Agent Skill against the agentskills.io specification plus project- or skill-local rule overrides. Use when auditing a skill folder for compliance, preparing a skill for distribution, checking PR-changed skills in CI, enforcing custom frontmatter rules, or verifying that a skill's `metadata`, `compatibility`, body length, and file references all meet the spec. Every rule is config-driven — point the validator at a YAML config to customize allowed/required/forbidden frontmatter fields, regex patterns for metadata values, timestamp formats, body thresholds, and placeholder bans. Triggers on: 'validate skill', 'check skill compliance', 'audit SKILL.md', 'lint skill folder', 'verify skill against agentskills.io', 'is this skill spec-compliant'."
license: MIT
allowed-tools: Bash(python *) Bash(python3 *)
metadata:
  author: kryptobaseddev
  version: "2.0.0"
  last_updated: "2026-05-21 14:00:18"
  spec: https://agentskills.io/specification.md
  related: skill-evaluator
---

# Skill Validator

Config-driven validator for [Agent Skills](https://agentskills.io). Runs a 5-tier compliance gauntlet (structure → frontmatter → body → optional manifest → optional provider map) and emits a precise PASS / WARN / FAIL report.

The validator's behavior is controlled entirely by `config/default.yml`. Projects can override any rule via a project-local or skill-local YAML — see [`config/README.md`](config/README.md) for the override precedence and rule catalogue.

## Quick start

```bash
# Validate one skill
python scripts/validate.py <path-to-skill-dir>

# JSON output for scripting / CI
python scripts/validate.py <path-to-skill-dir> --json

# Use a custom rule config
python scripts/validate.py <path-to-skill-dir> --config ./my-rules.yml

# Print the fully-merged effective config (debug overrides)
python scripts/validate.py --print-config

# Deep body quality audit (sections, links, duplicates, placeholders)
python scripts/audit_body.py <path-to-skill-dir>

# Progressive-disclosure depth check (body length OR references/ subdir)
python scripts/check_depth.py <path-to-skill-dir>

# Repo-wide depth sweep across every skill in a directory
python scripts/check_depth.py <project-root>/skills --all

# Allowlist hygiene audit (CI cron — exits 1 on findings)
python scripts/check_depth.py <skill-dir> --audit-allowlist
```

## Tiers

| Tier | What it checks |
|---|---|
| **1 — Structure** | SKILL.md exists, frontmatter parses, no forbidden fields |
| **2 — Frontmatter Quality** | Field types, lengths, patterns, recommended metadata keys, timestamp formats |
| **3 — Body Quality** | Line thresholds, placeholders, section headers, file-reference validation |
| **4 — Manifest Integration** *(optional)* | Skill is registered in a `manifest.json` with required entry fields |
| **5 — Provider Compatibility** *(optional)* | Skill is referenced in a provider-skills-map |

Tiers 1-3 always run. Tiers 4 and 5 activate only when you pass `--manifest` / `--provider-map` or enable them in config.

## Configuration

All rules are data. See [`config/README.md`](config/README.md) for the full guide. Highlights:

```yaml
# Common overrides — drop in <project>/skill-validator.config.yml

# Tighten body length cap
body:
  warn_lines: 400
  error_lines: 500

# Add a required metadata key
metadata:
  recommended_keys:
    keys: [author, version, last_updated, maintainer]

# Enforce SemVer on metadata.version
metadata:
  patterns:
    version: '^\d+\.\d+\.\d+(?:[-+].+)?$'

# Forbid project-specific fields at top-level
frontmatter:
  forbidden: [version, tier, protocol]   # must live in manifest-entry.json
```

Disable any rule by setting `severity: off`. Disable any whole tier group by setting `enabled: false`.

## Override precedence

1. **CLI flag**: `--config /path/to/rules.yml`
2. **Skill-local**: `<skill-dir>/.skill-validator.yml`
3. **Project-level**: `<project-root>/skill-validator.config.yml`
4. **Bundled default**: `config/default.yml`

User overrides only need to declare the keys they want to change; everything else inherits from `default.yml`.

## Spec alignment

The validator targets the [agentskills.io](https://agentskills.io/specification.md) specification exactly:

- Required top-level fields: `name`, `description`
- Optional top-level fields: `license`, `compatibility` (string, ≤500 chars), `metadata` (dict of string→string), `allowed-tools`
- `name` rules: lowercase + digits + hyphens, ≤64 chars, no consecutive/leading/trailing hyphens, must match directory
- `description` rules: ≤1024 chars, no angle brackets, single-line (no YAML multiline)
- Body: keep under 500 lines; hard cap at 600

The validator also recognises Claude Code harness extensions (`argument-hint`, `disable-model-invocation`, `user-invocable`, `model`, `context`, `agent`, `hooks`) as allowed but non-spec.

## `metadata` conventions enforced

| Sub-key | Convention | Default rule |
|---|---|---|
| `author` | recommended | WARN if `metadata` exists but no `author/version/last_updated` |
| `version` | recommended | (Optional) WARN if not SemVer when patterns are configured |
| `last_updated` | recommended timestamp | WARN if not `YYYY-MM-DD HH:MM:SS` |
| `last_reviewed` | optional timestamp | WARN if not `YYYY-MM-DD HH:MM:SS` |

Add or relax any of these via config. Numeric values like `version: 1.0` produce a WARN — quote them as `version: "1.0"` per spec.

## Body audit (deep checks)

`scripts/audit_body.py` runs a separate, deeper pass over the body content:

- Section-heading hierarchy (H1/H2/H3 order, no broken jumps)
- Code-block file references resolve on disk
- Internal markdown link validation
- Placeholder scan (`TODO`, `FIXME`, etc.)
- Duplicate-heading detection
- Statistics (lines, sections, code blocks, links)

Run with `--json` for CI integration. The defaults already match the agentskills.io spec recommendations.

## Progressive-disclosure depth (`check_depth.py`)

A skill PASSES depth when ANY of:

- SKILL.md body has ≥ `depth.min_body_lines` content lines (default 100)
- `references/` has ≥ `depth.min_reference_files` markdown files (default 3)
- Manifest `references[]` array is populated and all files exist on disk

The depth rule guards against "stub" skills with no meaningful guidance. Allowlist exempted skills via `config/default.yml` → `depth.allowlist` — each entry MUST have a `last_reviewed: YYYY-MM-DD HH:MM:SS` stamp. Stale entries (> 30 days by default) emit a WARN. Run `--audit-allowlist` for an explicit CI pass that exits 1 on any finding.

## Quality eval delegation

For runtime A/B benchmarking, regression detection, and auto-improvement of skill *output quality* (a complementary concern), the validator delegates to a dedicated skill resolved dynamically via `scripts/_skill_finder.py`. Run:

```bash
python scripts/run_quality_eval.py <skill-dir> --list       # see what would dispatch
python scripts/run_quality_eval.py <skill-dir> --runs 3 --executor api
```

`run_quality_eval.py` prefers `skill-evaluator` and falls back to `ct-skill-creator` if neither was installed alongside. The skill-finder searches in priority order:

1. `$SKILL_FINDER_PATH` (colon-separated override)
2. `~/.claude/skill-finder-paths.txt` (newline-separated roots)
3. Sibling skill directory
4. Walk-up ancestors and their project-shaped children
5. `~/.claude/skills/<name>/`

No hardcoded cross-skill paths anywhere — the dispatcher resolves the target every run.

## Bundled report generator

`scripts/generate_validation_report.py` aggregates `validate.py` + `audit_body.py` JSON output into a single HTML report and opens it in the browser. Useful for human review or sharing PR audit results.

```bash
python scripts/generate_validation_report.py <skill-dir>            # opens browser
python scripts/generate_validation_report.py <skill-dir> --no-open --output report.html
python scripts/generate_validation_report.py <skill-dir> --audit    # include audit_body
```

## Validation rule reference

See [`references/validation-rules.md`](references/validation-rules.md) for the complete table of rule IDs, severities, and fix guidance.

## Self-validation

```bash
python scripts/validate.py .       # validates this skill itself
```
