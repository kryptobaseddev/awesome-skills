# Constrain: the limits, before you author

All of these are enforced. Reading them first is cheaper than being rejected by
CI. The numbers live in `skills/skill-validator/config/default.yml`; the ones
below are the ones that actually bite.

## Hard errors

| Limit | Value | Notes |
|---|---|---|
| Body length | **ERROR at ≥600 lines**, WARN at ≥500 | Counted after frontmatter, blank lines included. Nothing in this repo exceeds 494 |
| `description` | **≤1024 chars**, single-line quoted scalar | Also: no `<` or `>` at all |
| `compatibility` | **≤500 chars** | Folded `>-` scalar |
| `name` | `^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`, ≤64 | No consecutive or edge hyphens |
| Frontmatter | `name` + `description` required | Must parse as a YAML dict |

## The allowed frontmatter set

`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`,
`argument-hint`, `disable-model-invocation`, `user-invocable`, `model`,
`context`, `agent`, `hooks`, plus this repo's two conventions: `inputs` and
`references`. Anything else WARNs.

`metadata` values must be strings — quote versions (`version: "1.0.0"`; bare
`1.0` is a float and WARNs). `last_updated` wants `YYYY-MM-DD HH:MM:SS`.

## Progressive disclosure

Passes if **any one** holds:

1. body ≥100 lines, **or**
2. `references/` contains ≥3 `.md` files — **non-recursive**, top level only, **or**
3. a manifest lists ≥3 resolvable references (not used in this repo).

Most skills pass on the body rule without noticing. If you are deliberately
keeping the body short, put at least three `.md` files at the *top* of
`references/` — files in `references/sub/` count as zero.

## Category resolution, and its traps

Order: explicit `metadata.category` → first matching rule → fallback `other`.
Rules are checked top to bottom, and within each rule: `tags`, then
`name_contains`, then `keywords`.

- **An unrecognised slug fails silently.** It matches nothing, falls through to
  rule matching, and warns nobody. `design` and `ux` are not slugs.
- **Earlier rules win.** A `mobile`, `ios`, `android` or `automation` tag pulls a
  frontend skill into another section.
- **`keywords` match name + description + tags**, on word boundaries. The literal
  token `react-native` anywhere routes to Mobile; "React Native" with a space
  does not.

Set `metadata.category` explicitly and none of this applies to you.

## File references

The body's file references are resolved only for paths starting `references/`,
`scripts/`, `config/` or `assets/`. Fenced and inline code is stripped first, so
examples are exempt. Paths under `docs/` or `templates/` are never checked —
they can rot silently.

## Generated files

`README.md` (between the markers) and `registry.json` are produced by
`scripts/build_registry.py` from frontmatter. CI runs `--check`. The pre-commit
hook regenerates and re-stages automatically; `--no-verify` skips it and CI will
catch you instead.

## Executable bits

**This repo sets `core.fileMode=false`.** A local `chmod +x` is invisible to git.
Any script the SKILL.md tells an agent to run needs:

```bash
git update-index --chmod=+x skills/<name>/scripts/<file>
```

`forge_check.py` reads `git ls-files -s` and fails on any directly-invoked script
that is not `100755`. It found this exact bug in two shipped skills.
