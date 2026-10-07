# TanStack Intent

> Verified 2026-10-07 against `@tanstack/intent@0.5.5` (bin `intent`, Node >=20.12.0). Sources: its docs, `--help` for every subcommand, and live runs of `list`, `load` and `install --dry-run` in a scratch project (TanStack CLI 0.71.1). Pre-1.0: flags move between minors. Re-check with `npx -y @tanstack/intent@latest <cmd> --help`.

## Contents
When to use · Packages · Mental model · Core API (consumer) · Maintainer workflow · Patterns · Traps · Migration notes · Go deeper

## When to use / when not to

- **Working as an agent in a project that depends on TanStack (or other intent-enabled) packages:** run `intent list` before editing, then `intent load <pkg>#<skill>`. Those skills ship **inside `node_modules`** and match the **installed** version. Prefer them over this reference whenever one covers the task.
- **Setting up a repo so every agent session does that automatically:** `intent install` (guidance block) and optionally `intent hooks install` (edit gate).
- **Shipping skills with your own npm library:** the `maintainer` workflow.
- Intent is not a skill registry client and not a package manager. It never installs dependencies or publishes packages, and it never executes the code of the packages it scans.

## Packages

| Package | Role |
|---|---|
| `@tanstack/intent` | CLI (bin `intent`). Install as a **devDependency** so the lockfile pins it. |

```bash
npm i -D @tanstack/intent
```

Which packages ship skills (checked with `npm pack --dry-run` on 2026-10-07): `@tanstack/table-core` and `@tanstack/react-table` (v9 only), `@tanstack/router-core` (nested `router-core/*` skills), `@tanstack/react-start`, `@tanstack/ai`, `@tanstack/db`, `@tanstack/react-db`, `@tanstack/markdown`, `@tanstack/highlight`, `@tanstack/charts`, `@tanstack/devtools`. **Not** shipping skills at those versions: `@tanstack/react-query`/`query-core` 5.104, `@tanstack/react-router` (its skills live in `router-core`), `@tanstack/react-form`, `@tanstack/pacer`, `@tanstack/hotkeys`, `@tanstack/react-virtual`. Run `intent list` instead of assuming.

## Mental model

- **Skill** = `skills/<name>/SKILL.md` inside a published package, with frontmatter `metadata.library` and `metadata.library_version`, plus `requires:` (other skills) and `sources:` (doc paths it was written from).
- **Skill id** = `<package>#<skill>`, which may be nested: `@tanstack/router-core#router-core/auth-and-guards`. A bare package name is invalid for `load`.
- **Discovery** is static file reading over `node_modules`, workspace packages and Yarn PnP. Global packages are included only with `--global` or `--global-only`. A local copy beats a global one.
- **Trust** = `package.json#intent.skills` allowlist, then `intent.exclude`. If no allowlist is set, everything is surfaced with a deprecation notice. A future version will require the allowlist.
- **Guidance** = a managed `<!-- intent-skills:start -->…<!-- intent-skills:end -->` block in `AGENTS.md` (or an existing `CLAUDE.md`, `.cursorrules` or `.github/copilot-instructions.md`) telling agents to list, then load, then edit.
- **Hooks** = Claude Code and Codex `SessionStart` (skill catalog) + `PreToolUse` edit gate, which blocks edits until it sees `intent list` or `intent load`.
- Version match is automatic: updating the library updates its `skills/`, and `load` reads whatever version is installed.

## Core API (consumer)

```bash
# Agent workflow inside a project
npx -y @tanstack/intent@latest list                       # table of packages + skills with descriptions
npx -y @tanstack/intent@latest list --json                # [{use, packageName, packageVersion, skillName, description, type, framework}]
npx -y @tanstack/intent@latest load @tanstack/react-table#getting-started          # prints SKILL.md
npx -y @tanstack/intent@latest load @tanstack/react-table#getting-started --path   # node_modules/@tanstack/react-table/skills/getting-started/SKILL.md
```

If `@tanstack/intent` is a local devDependency, use the pinned binary (`npx intent …`, `pnpm exec intent …`, `node_modules/.bin/intent …`).

| Command | Key flags |
|---|---|
| `list` | `--json`, `--debug`, `--global`, `--global-only`, `--show-hidden` (sources hidden by the allowlist), `--no-notices` |
| `load <pkg>#<skill>` | `--path`, `--json` (`{package, skill, path, version, content, warnings}`), `--debug`, `--global`, `--global-only` |
| `install` | `--review`, `--map`, `--dry-run`, `--print-prompt`, `--maintainer`, `--global`, `--global-only`, `--no-notices` |
| `hooks install` | `--scope project\|user` (default project), `--agents copilot,claude,codex\|all` (default all) |
| `exclude [list\|add\|remove] [pattern]` | `--json` |
| `stale [dir]` | `--json`, `--github-review`: version drift / source-coverage signals |

The allowlist (`package.json`; the nearest non-null `intent.skills` wins, and `exclude` arrays accumulate from the root down):

```json
{
  "intent": {
    "skills": ["@tanstack/*", "@acme/ui#forms", "workspace:@acme/*"],
    "exclude": ["@tanstack/router-core#experimental-*"]
  }
}
```

Entries: `pkg`, `pkg#skill`, `@scope/*`, `workspace:pkg…`, `"*"` (everything, with a risk notice), `[]` (nothing). `git:` entries are reserved and rejected. One malformed entry fails the whole command. Set `INTENT_NO_NOTICES=1` to silence notices in CI.

## Maintainer workflow (library authors)

```bash
npx -y @tanstack/intent@latest maintainer setup [--distribution repo|none] [--skill <name>…]
#   writes skill_tree.yaml, domain_map.yaml, skill_spec.md (_artifacts/), an intent-maintainer block in AGENTS.md,
#   and .github/workflows/check-skills.yml if missing
npx -y @tanstack/intent@latest maintainer add retries --package packages/client --domain requests \
  --description "Use when configuring retries." --source src/retry.ts --task "Retry with bounded backoff"
npx -y @tanstack/intent@latest meta                    # list meta-skills: domain-discovery, generate-skill, tree-generator, skill-staleness-check
npx -y @tanstack/intent@latest meta generate-skill     # print the authoring procedure for your agent to follow
npx -y @tanstack/intent@latest validate [dir] [--fix|--check|--set-version <v>|--github-summary]
npx -y @tanstack/intent@latest maintainer sync         # align tree + package.json (adds `tanstack-intent` keyword, `files` entries)
npx -y @tanstack/intent@latest maintainer status [--json]
npx -y @tanstack/intent@latest maintainer review --json   # then: maintainer review --record .intent/report.json
npx -y @tanstack/intent@latest maintainer check        # CI gate: authoring gaps, stale generated files, pending reviews
```

Other commands: `maintainer remove <name>`, `repair [dir] [--write|--patch|--json]`, `review [dir]`, `setup` / `setup-github-actions` (copy CI templates only), `edit-package-json`. Skills live beside the owning package in `skills/<name>/SKILL.md`. Publishing happens through the library's normal release. The Intent registry indexes any npm package carrying the `tanstack-intent` keyword.

## Patterns

**Agent start-of-task routine (no setup required):**
```bash
npx -y @tanstack/intent@latest list --no-notices        # anything matching the task?
npx -y @tanstack/intent@latest load @tanstack/router-core#router-core/auth-and-guards
```
Follow `requires:` in the loaded frontmatter (for example `@tanstack/table-core#core`) and load those as well.

**One-time repo setup by a human** (first run is interactive: Enable all / choose packages or scopes / choose skills, then one confirmation):
```bash
npm i -D @tanstack/intent && npx intent install && npx intent hooks install
```

**Non-interactive setup (CI, agents):** write `intent.skills` into `package.json` first, then `intent install` only updates guidance and never prompts. `install --dry-run` prints the block without writing anything.

**`tanstack create --intent`** (and `tanstack add --intent`, whose help text reads the same: "set up TanStack Intent skill mappings for coding agents"; its post-step is unverified). After scaffolding, the TanStack CLI runs `npx -y @tanstack/intent install` and records `"intent": true` in `.cta.json`. It does **not** add `@tanstack/intent` to `devDependencies` or write `intent.skills`. In a non-interactive run (tested: `create app --blank --intent -y --no-install`) that step failed with `Command "npx -y @tanstack/intent install" did not run successfully. Please run this manually`, which is consistent with Trap 1. Run `intent install` yourself afterwards. `--blank` skips Intent by default; `--no-intent` skips it explicitly.

## Traps

1. **Running `install` without a TTY and no allowlist.** It fails with `Permissions: failed: intent.skills is not configured` and writes nothing (observed). Add `intent.skills` to `package.json` first (`cli/intent-install`).
2. **Copying the `Load:` hints from `list`.** They read `npm exec --no -- intent load …`, and `--no` forbids downloading. Without a local `@tanstack/intent` devDependency this fails with `could not determine executable to run` (observed). Use `npx -y @tanstack/intent@latest load …` or install it as a devDependency.
3. **`intent load @tanstack/react-table`.** Fails with `expected <package>#<skill>`. Always include `#skill`. Nested ids need the full path (`#router-core/auth-and-guards`); `load` suggests the right id on a near miss (`cli/intent-load`).
4. **Looking for skills in the framework package.** Router skills are in `@tanstack/router-core`, and most Table skills are in `@tanstack/table-core`, not only the `react-*` package. `list` shows the real owners.
5. **Assuming every TanStack library ships skills.** Query 5.x, Form, Pacer and Hotkeys shipped none on 2026-10-07. An empty result means falling back to `tanstack doc …`, not a broken setup.
6. **Treating `@latest` as the pinned CLI.** The docs' commands run `@tanstack/intent@latest`, which can differ from the lockfile version CI uses. Keep it in devDependencies and call the local binary in CI (`getting-started/quick-start-consumers`).
7. **Assuming the allowlist approves content.** Allowing a package covers its future skills too, and content changes when the dependency updates. No change notification exists yet (`concepts/trust-model`).
8. **Assuming hooks prove anything.** The edit gate only observes that a `list` or `load` command ran, not that it succeeded or that the agent followed it (`cli/intent-hooks`). Copilot CLI hooks are user scope only: `--scope user --agents copilot`.
9. **Global packages missing.** Global scanning is opt-in (`--global` / `--global-only`).
10. **Malformed ancestor `package.json`.** It stops discovery entirely because it might hold an inherited policy. Fix the file named in the error (`concepts/trust-model`).

## Migration notes

From the `@tanstack/intent` CHANGELOG:

| Old | Current (0.5.x) |
|---|---|
| `intent scaffold` (≤0.4) | Removed in 0.5.0. Use `maintainer setup / add / status / sync / review / check` + `meta generate-skill` |
| `intent maintainer adopt` (+ `--apply`, JSON plan) | Removed in 0.5.0. Use `maintainer setup`, which registers existing `skills/*/SKILL.md` |
| `intent resolve <pkg>#<skill>` (0.0.x) | Not in 0.5.5 `--help`. Use `load <pkg>#<skill> --path` |
| No allowlist (pre-0.1.0) | `intent.skills` added in 0.1.0, `*` patterns in 0.3.6. Without an allowlist you still get everything plus a deprecation notice |
| No hooks (pre-0.3.0) | `hooks install` added in 0.3.0. Session-start catalog in 0.3.2. Rerun `hooks install` after upgrading to get the faster local runner |
| Malformed ancestor `package.json` skipped | Fails closed since 0.4.0 |

## Go deeper

- `tanstack doc intent overview`: both workflows, command map
- `tanstack doc intent getting-started/quick-start-consumers`: consumer setup
- `tanstack doc intent getting-started/quick-start-maintainers`: authoring and publishing skills
- `tanstack doc intent concepts/configuration`: allowlist / exclude grammar
- `tanstack doc intent concepts/trust-model`: trust boundaries, lifecycle
- `tanstack doc intent cli/intent-install`: first-run flow, `--map` output
- `tanstack doc intent cli/intent-load`: resolution, errors, JSON shape
- `tanstack doc intent cli/intent-list`: discovery output
- `tanstack doc intent cli/intent-hooks`: per-agent hook locations
- `tanstack doc intent cli/intent-maintainer`: full maintainer reference
- `tanstack doc intent cli/intent-validate`: SKILL.md validation rules
- `tanstack doc intent registry`: get indexed via `tanstack-intent` keyword
