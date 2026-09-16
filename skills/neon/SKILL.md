---
name: neon
description: "Neon CLI (`neon`, formerly `neonctl`) for Lakebase Postgres — projects, branches, databases, roles, connection strings, snapshots, Functions, object-storage buckets, the Data API, Managed Better Auth, logs, and Postgres health inspection. Use when the user manages Neon from the terminal or CI: creating projects or ephemeral branches, getting a DATABASE_URL, resetting/restoring/schema-diffing branches, pulling env vars, deploying Functions, taking snapshots, setting IP allowlists or VPC restrictions, or wiring Neon into an AI coding agent. ALSO use for the neonctl-to-neon rename: migrating scripts and CI off `neonctl`, 'neonctl command not found', 'is neonctl deprecated', npm i -g neon, or `set-context` now being deprecated in favor of `neon link`. Triggers on: 'neon cli', 'neonctl', 'neon branches', 'neon connection-string', 'neon link', 'neon env pull', 'neon snapshots', 'neon functions', 'neon inspect', 'NEON_API_KEY', 'neon login', 'serverless postgres cli', 'ephemeral database branch in CI'."
license: MIT
compatibility: >-
  Requires Node.js 20.19.0+ for `npm i -g neon@latest` (the CLI keeps running on
  older Node, but upgrading on Node 18 fails). Homebrew, bun, and standalone
  binaries are also published. Authenticates via browser login or NEON_API_KEY.
  `psql` is needed only for `neon psql` and `--psql`; `neon inspect` runs its
  queries through the CLI itself.
metadata:
  author: kryptobaseddev
  version: "2.0.0"
  last_updated: "2026-09-16 12:05:00"
  category: databases
  tags: neon, postgres, cli, serverless, database-branching
  related: drizzle-orm
  docs: https://neon.com/docs/cli
---

# Neon CLI (`neon`)

One CLI for every Neon surface: Postgres branches, Functions, object storage, the Data API, and Managed Better Auth.

**The CLI was renamed from `neonctl` to `neon`.** If the user mentions `neonctl` at all — a broken script, a stale install, a CI job, "is it deprecated" — read [references/migration-from-neonctl.md](references/migration-from-neonctl.md) first. It covers the package split, the bin-symlink trap when uninstalling, and what changed at the command level.

## Orientation: check the install before anything else

Version drift is the single most common source of confusion here, because the old and new CLIs coexist happily and give no warning.

```bash
bash scripts/neon-preflight.sh     # version, auth, context, staleness — one shot
```

Or manually:

```bash
neon --version        # want 4.x — if this prints 2.x you are on the old CLI under a new name
neon me               # confirms authentication
```

If `neon` is missing or on 2.x, install the current CLI:

```bash
npm i -g neon@latest              # requires Node 20.19.0+
```

The command surface below assumes 4.x. On 2.x, roughly half of it (snapshots, functions, buckets, data-api, inspect, logs, env, link, checkout, profile) simply does not exist — which reads as "unknown command" rather than "please upgrade", so check the version before concluding a command is wrong.

## Authentication

Credentials resolve in this order, first match wins:

1. `--api-key <key>` on the command
2. `NEON_API_KEY` environment variable
3. `credentials.json` in the config directory, written by `neon login`
4. Interactive browser login (fallback)

```bash
neon login                                   # browser auth (alias: neon auth)
export NEON_API_KEY=<key>                    # preferred in CI — no browser available
neon projects list --api-key <key>           # one-off override
```

For several accounts or org-scoped keys, use named profiles instead of juggling env vars:

```bash
neon profile create work --api-key <key>     # or --mint to have Neon issue one
neon profile list
neon --profile work projects list            # or: export NEON_PROFILE=work
```

**Config directory gotcha:** `neon --help` advertises `~/.config/neon`, but the 4.x CLI actually reads and refreshes `~/.config/neonctl/credentials.json` — the legacy path. The practical consequence is good news: upgrading from `neonctl` keeps you logged in. Don't "fix" this by moving the directory; override it with `--config-dir` only if you have a real reason.

## Context: stop repeating `--project-id`

`neon link` binds the current directory to a project by writing a `.neon` file (`orgId`, `projectId`, and `branch` when pinned). Every command run from that directory or below picks it up.

```bash
neon link                                          # interactive: pick/create org + project
neon link --project-id <id> --org-id <org-id>      # non-interactive (CI, agents)
neon link --org-id <org> --project-name my-app --region-id aws-us-east-2   # create + link
neon checkout dev --create                         # pin a branch (creating it if absent)
neon link --clear                                  # unbind
```

Two behaviors worth knowing before they surprise someone: linking **pulls the branch's env vars into a local `.env`/`.env.local` by default** (`--no-env-pull` to skip), and after an interactive link the CLI **offers to scaffold a `neon.ts` config** (`--no-config` to skip). On first creation the CLI adds `.neon` to `.gitignore`; the file holds no secrets, so remove that entry if the team wants shared context.

`set-context` still works but is deprecated — prefer `link`, which validates the IDs and writes a complete context. In a repo where `neon link` would clobber a teammate's context, pin a separate file with the global `--context-file <path>`.

## Command map

Use this to pick a landing spot, then open the matching reference for flags and examples.

| Area | Commands | Reference |
|---|---|---|
| Projects, branches, schema diff | `projects`, `branches`, `diff`, `snapshots` | [projects-branches.md](references/projects-branches.md) |
| Databases, roles, connection strings, psql | `databases`, `roles`, `connection-string`, `psql`, `env` | [databases-roles-connections.md](references/databases-roles-connections.md) |
| IP allow, VPC, operations, logs, credentials, API keys | `ip-allow`, `vpc`, `operations`, `logs`, `credentials`, `api-keys`, `api` | [security-operations.md](references/security-operations.md) |
| Functions, triggers, buckets, Data API, Neon Auth, inspect, `neon.ts` | `functions`, `dev`, `triggers`, `buckets`, `data-api`, `neon-auth`, `inspect`, `config`/`deploy`/`status` | [platform-surfaces.md](references/platform-surfaces.md) |
| Setup, agent tooling | `login`, `profile`, `link`, `checkout`, `init`, `mcp`, `skills`, `plugins`, `bootstrap`, `claim`, `ask`, `open` | this file + [migration-from-neonctl.md](references/migration-from-neonctl.md) |

Aliases are pervasive and safe to use: `branch`, `db`, `cs`, `org`, `project`, `role`, `operation`, `snapshot`, `function`, `trigger`, `bucket`, `credential`, `auth` (= `login`).

## Output and scripting

`table` is the default and **it truncates** — long IDs, URIs, and timestamps get cut. Any time output is being parsed, captured, or shown as evidence, use JSON:

```bash
neon branches list --output json | jq -r '.branches[].name'
CONN=$(neon connection-string dev --pooled --output json | jq -r '.connection_string')
```

Global options that apply everywhere: `-o/--output json|yaml|table`, `--api-key`, `--profile`, `--config-dir`, `--context-file`, `--color/--no-color`, `--analytics/--no-analytics`, `-v/--version`, `-h/--help`. Help is available at every level — `neon branches create --help` is usually faster and more current than any doc.

Analytics are on by default and collect command/option names, not payloads or project IDs. `--no-analytics` opts out per command.

## Core workflows

### Start a project and get connected

```bash
neon projects create --name myapp --region-id aws-us-east-2 --set-context
neon connection-string --pooled
```

Use the pooled string for serverless and edge runtimes where connection count is the binding constraint; use the direct (unpooled) string for migrations and anything holding a session, since PgBouncer in transaction mode breaks session-scoped features.

### Feature branch, then throw it away

```bash
neon branches create --name feat/auth --parent main --cu 0.5-2
neon connection-string feat/auth --pooled --prisma
# ... develop ...
neon branches schema-diff main feat/auth --database mydb
neon branches delete feat/auth
```

`--schema-only` creates a branch with the schema but no data — the right choice when the parent holds production data that shouldn't be copied into a dev branch.

### Reset a stale dev branch

```bash
neon branches reset dev --parent
neon branches reset dev --parent --preserve-under-name dev-backup   # keep an escape hatch
```

`reset` discards the branch's data. `--preserve-under-name` keeps the pre-reset state as a separate branch, which costs storage but turns an irreversible action into a reversible one — worth defaulting to unless the user has said the data is disposable.

### Point-in-time restore

```bash
neon branches restore main ^self@2026-06-01T12:00:00Z --preserve-under-name main-backup
```

`<source>` is `^self`, `^parent`, or another branch, optionally `@timestamp` or `@lsn`. Restoring `main` in place is a production-affecting operation — confirm intent and keep the backup branch.

### Ephemeral database per CI job

```bash
export NEON_API_KEY=${{ secrets.NEON_API_KEY }}
BRANCH="ci-${GITHUB_SHA:0:8}"
neon branches create --name "$BRANCH" --project-id "$PROJECT_ID" --schema-only
CONN=$(neon connection-string "$BRANCH" --project-id "$PROJECT_ID" --pooled -o json | jq -r '.connection_string')
# run tests against $CONN
neon branches delete "$BRANCH" --project-id "$PROJECT_ID"
```

Delete in a step that runs even when tests fail (`if: always()`), or set `--expires-at` at creation so abandoned branches self-clean. Orphaned CI branches are the usual cause of a surprise Neon bill.

### Pull env vars into local development

```bash
neon env pull                      # writes .env (or .env.local), rewriting only Neon-managed keys
neon env pull --service postgres   # narrow to one surface
```

Without a `neon.ts`, this writes `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, and `NEON_BRANCH`. With one, it also writes credentials for each declared service. Non-Neon lines in the file are preserved, so it's safe to run against a `.env` that holds other secrets.

### Add a read replica

```bash
neon branches add-compute production --type read_only --cu 0.5-3
```

## Guidance when acting on someone's account

These commands operate on live infrastructure, and several are irreversible. `projects delete` has a grace period (`projects recover`), but `branches delete`, `branches reset`, `databases delete`, `roles delete`, `api-keys revoke`, `credentials revoke`, and `buckets object delete` do not.

Before a destructive command, confirm which project and branch is actually targeted — a `.neon` file two directories up may point somewhere unexpected. `neon projects list` and `neon branches list` cost nothing; a wrong `--project-id` is expensive. When a command is irreversible and the user hasn't clearly asked for that specific object, say what will be lost and let them confirm.
