# Skill Validator — Configuration Guide

Every rule the validator applies is driven by YAML files in this folder. The validator code is a thin engine; the rules live here.

## Files in this folder

| File | Purpose |
|---|---|
| `default.yml` | The base ruleset, aligned with the [agentskills.io specification](https://agentskills.io/specification.md). Don't edit it — override it. |
| `categories.yml` | Category inference rules for the registry generator. Affects README, not validation. |
| `README.md` | This file. |

## Override precedence

When the validator runs, it loads config in this order. The first file found wins:

1. **CLI flag** — `validate.py --config /path/to/custom.yml`
2. **Skill-local** — `<skill-dir>/.skill-validator.yml`
3. **Project-level** — `<project-root>/skill-validator.config.yml`
4. **Bundled default** — this folder's `default.yml`

User configs only need to declare the keys they want to **change**; everything else inherits from `default.yml`.

## Tier groups

Every rule lives under a tier-group key. Each group has an `enabled` switch (most default `true`).

| Group | What it controls |
|---|---|
| `structure` | SKILL.md exists, frontmatter parses, body present (mandatory) |
| `frontmatter` | Which fields are allowed / required / forbidden at top level |
| `name` | Name pattern, length, directory match |
| `description` | Length, trigger words, character bans, YAML multiline check |
| `compatibility` | Spec-compliance for the `compatibility` field |
| `metadata` | `metadata` block rules incl. timestamps and per-key regexes |
| `booleans` | Validates `disable-model-invocation`, `user-invocable` |
| `allowed_tools` | Validates `allowed-tools` shape |
| `argument_hint` | Validates `argument-hint` length |
| `context` | Validates `context` value and pairing with `agent` |
| `body` | Line thresholds, placeholders, file-reference validation |
| `depth` | Progressive-disclosure depth rule + allowlist hygiene |
| `manifest` | (Optional) Tier 4 manifest.json alignment |
| `provider_compatibility` | (Optional) Tier 5 provider map alignment |

## Severity

Per-rule severity values:

| Value | Meaning |
|---|---|
| `error` | Fails the run (exit code 1) |
| `warn` | Notes the issue but doesn't fail |
| `off` | Disable the rule entirely |

Set severity on any rule that takes a `severity` key, e.g.:

```yaml
description:
  must_contain_trigger:
    severity: off    # tolerate descriptions without "when" / "use when"
```

## Common overrides

### Loosen body-length warning to 600

```yaml
body:
  warn_lines: 600
  error_lines: 800
```

### Add a custom required metadata key

```yaml
metadata:
  recommended_keys:
    keys: [author, version, last_updated, maintainer]
    severity: warn
```

### Forbid `version` at SKILL.md top level (force it into manifest-entry.json)

```yaml
frontmatter:
  forbidden:
    - version
    - tier
    - protocol
```

### Enforce SemVer on metadata.version

```yaml
metadata:
  patterns:
    version: '^\d+\.\d+\.\d+(?:[-+].+)?$'
```

### Change the timestamp format (e.g. accept date-only)

```yaml
metadata:
  timestamp_pattern: '^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$'
  timestamp_example: '2026-05-21 or 2026-05-21 14:00:18'
```

### Disable depth check entirely

```yaml
depth:
  enabled: false
```

### Add depth-allowlist entries with the cadence stamp

```yaml
depth:
  allowlist:
    my-stub-skill: "TICKET-123: deferred backfill | last_reviewed: 2026-05-21 14:00:18"
  allowlist_stale_days: 30
```

## Discovering effective config

To see exactly which rules apply after all merging:

```bash
python scripts/validate.py <skill-dir> --print-config
```

This prints the fully-merged config (default + project + skill-local) so you can confirm what's in effect.

## Category rules — `categories.yml`

The registry generator uses `categories.yml` to bucket skills under headings in the README. Each category has match rules; the first match wins. Override by:

- Adding **`metadata.category: <slug>`** to a skill's frontmatter (always wins)
- Editing this file to add new categories or adjust matches
- Reordering — earlier categories take priority

If you add a new category, give it:
- `name` — display name in the README
- `icon` — single emoji
- `slug` — short kebab-case identifier
- `match.keywords` — substrings to look for in name/description/tags
- `match.name_contains` — substrings the skill name must contain
- `match.tags` — exact-match tags (any of)

Run the registry generator after editing:

```bash
python <project-root>/scripts/build_registry.py
```

## Schema cheat sheet — common patterns

```yaml
# A simple severity-tagged rule
some_rule:
  severity: warn

# A rule with a value AND severity
some_rule:
  value: 500
  severity: warn

# A rule with a list AND severity (e.g. recommended keys)
some_rule:
  keys: [a, b, c]
  severity: warn

# A regex pattern map
some_rule:
  patterns:
    field_name: '<python-regex>'
```

## Adding a rule

The validator scripts look up keys by name in the loaded config. To add a new rule:

1. Decide its tier group and add the key under it in `default.yml`.
2. Document the key in this README under "Common overrides" if it's user-tunable.
3. Reference the key in the validator script that should enforce it.

The validator doesn't crash on unknown config keys — they're ignored. So you can stage rules incrementally.
