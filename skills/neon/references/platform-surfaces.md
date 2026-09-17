# Platform Surfaces Reference

Everything the 4.x CLI manages beyond Postgres itself. None of this existed in `neonctl` 2.x, so an
"unknown command" here usually means an old CLI rather than a wrong command — see
[migration-from-neonctl.md](migration-from-neonctl.md).

Flags below were read from `neon --help` at 4.18.1. **The installed binary's `--help` is the authority, not
this page and not the docs site** — Neon ships several releases a week (4.18.1 and 4.21.0 were days apart),
and several of these surfaces are in Beta (Functions, Triggers, Object Storage, branch Logs), so shapes move.
Check `--help` before concluding a documented flag is broken.

The Data API and Managed Better Auth have large configuration surfaces of their own and live in
[data-api-and-auth.md](data-api-and-auth.md).

## Table of Contents

- [Config as code (`neon.ts`)](#config-as-code-neonts)
- [Functions](#functions)
- [Local development (`neon dev`)](#local-development-neon-dev)
- [Triggers](#triggers)
- [Object storage buckets](#object-storage-buckets)
- [Postgres health inspection](#postgres-health-inspection)
- [Agent tooling](#agent-tooling)

---

## Config as code (`neon.ts`)

`neon.ts` declares what a branch should contain — databases, functions, auth, storage, Data API — and the
`config` commands reconcile the branch to it. The workflow mirrors Terraform: scaffold, inspect, preview,
apply.

```bash
neon config init      # scaffold neon.ts and install the config packages
neon config status    # what the branch actually looks like now   (alias: neon status)
neon config plan      # what apply would change — dry run
neon config apply     # reconcile the branch to the policy        (alias: neon deploy)
```

`neon deploy` and `neon status` are aliases, not separate implementations. Running `plan` before `apply` is
worth the extra command whenever the branch holds anything you would miss.

**`config init`**

| Flag | Meaning |
|---|---|
| `--install` / `--no-install` | Install `@neon/config` and `@neon/env` if missing (on by default; `--no-install` just prints the command) |
| `--from-branch` | Seed `neon.ts` from a branch's **live** state instead of prompting — the fast path for adopting config-as-code on an existing project |
| `--services` | Limit the scaffold to named services |
| `--branch`, `--project-id` | Target selection |

**`config apply` / `neon deploy`**

| Flag | Meaning |
|---|---|
| `--update-existing` | **Auto-confirms** overriding existing remote settings on the branch (default false). Without it `apply` stops and asks; with it, it overwrites silently — so it is the flag that makes a CI apply non-interactive, and the one that removes your last check against clobbering someone's manual change |
| `--allow-protected` | **Auto-confirms** applying to a branch marked protected (default false). Protection exists to force that pause; this skips it |
| `--env` | Load a `.env` before evaluating `neon.ts`, so Function env values resolve |
| `--env-pull` / `--no-env-pull` | Pull env vars after applying |

**`config status` / `neon status`**

| Flag | Meaning |
|---|---|
| `--config-json` | Emit the live state as JSON |
| `--current-branch` | **Prints only the linked branch name** from the local `.neon` file and makes no API call; exits non-zero when nothing is pinned. It is a context probe, not a status report — useful as a guard at the top of a script |

`neon env pull` reads `neon.ts` when present, which is what lets it emit per-service credentials rather
than just `DATABASE_URL`.

---

## Functions

**Beta.** Server-side functions deployed per branch.

```bash
neon functions deploy <slug> [options]
neon functions list
neon functions get <slug> [--list-env-variables]
neon functions delete <slug>
```

**`functions deploy`**

| Flag | Meaning |
|---|---|
| `--src` | Source: a directory containing `index.ts`/`index.js`/`index.mjs` (first match is the entry), or a path to the entry file |
| `--runtime` | Runtime — currently only `nodejs24` |
| `--env` | `KEY=VALUE`, repeatable |
| `--wait` / `--no-wait` | Wait for the build to finish (on by default) — `--no-wait` returns as soon as the deploy is queued, which is what you want in a fan-out script |
| `--bundle` / `--no-bundle` | Bundle `--src` with esbuild. `--no-bundle` zips a prebuilt directory (root must contain `index.mjs` or `index.js`) |
| `--branch`, `--project-id` | Target selection |

Custom domains:

```bash
neon functions domains list
neon functions domains register <domain> --slug <function-slug>
neon functions domains delete <domain>
```

Functions are branch-scoped, so a preview branch gets its own copy and its own invocation URL. `neon env
pull` writes that URL as `NEON_FUNCTION_<SLUG>_BASE_URL`, derived from the branch — the value exists before
the function is deployed, which makes it safe to wire into config ahead of the first deploy.

---

## Local development (`neon dev`)

```bash
neon dev [--source <path>] [--port <n>]
```

Watches for changes and hot-reloads. By default it serves **every** function declared in `neon.ts`, each on
its own dev server, using the per-function `dev.port` (auto-assigned when omitted). `--port` applies only in
**single-function mode**, i.e. together with `--source`, and fails if the port is taken.

Runs Neon Functions locally against a dev server. Unlike `env pull`, `dev` requires every env value the
declared functions read — a missing `process.env.*` that `env pull` quietly skipped will stop `dev` (and
`deploy`, and `neon-env run`).

---

## Triggers

**Beta.** Cron-scheduled invocation of a deployed function — a scheduler without a separate service.

```bash
neon triggers create --function-slug <slug> --name <name> --cron "<expr>" [options]
neon triggers list
neon triggers get <id>
neon triggers update <id> [--cron ... | --enabled ... | --function-slug ... | --function-path ...]
neon triggers disable <id>     # pause without losing the definition
neon triggers enable <id>
neon triggers delete <id>
```

**`triggers create`** — three flags are **required**: `--function-slug`, `--name`, `--cron`.

| Flag | Meaning |
|---|---|
| `--function-slug` | **Required.** Slug of the function to invoke |
| `--name` | **Required.** Trigger name, unique per branch |
| `--cron` | **Required.** Five-field **UTC** cron expression, e.g. `'*/15 * * * *'` |
| `--function-path` | Path the invocation is sent to (default `/`) — lets one function serve several triggers via routing |
| `--enabled` | Whether it runs (default true); create it disabled to stage a schedule before arming it |
| `--branch`, `--project-id` | Target selection |

The cron expression is interpreted in **UTC**, not the machine's local zone — the usual cause of a job that
fires at the wrong hour.

**Triggers cannot be declared in `neon.ts`** — it has no `triggers:` key, so cron is an imperative step that
`neon deploy` will not reproduce. Script the `triggers create` call next to the deploy if the schedule needs
to be reproducible.

Deploy the function first, then point a trigger at it. Triggers are **inherited by child branches**: one
created on a parent shows up on children with `Inherited: true` and `source_branch_id` pointing back to the
origin. That is convenient for propagating a nightly job, and a trap when branching a project whose parent
runs something with side effects — a preview branch inherits the schedule too. Check `triggers list` on a
new long-lived branch before assuming it's inert.

---

## Object storage buckets

**Beta.** S3-style buckets that belong to a branch.

```bash
neon buckets create <name> [--access-level private|public_read]
neon buckets list
neon buckets delete <name>

neon buckets object list <target> [--recursive] [--delimiter <d>] [--cursor <c>] [--limit <n>]
neon buckets object put <target> --file <local-path> [--content-type <type>]
neon buckets object get <target>
neon buckets object delete <target> [--recursive]
```

`--access-level` defaults to `private`; `public_read` makes every object in the bucket world-readable, so
it is a deliberate choice rather than a convenience. `object list` collapses folders like `aws s3 ls`
unless `--recursive` is passed, `--delimiter` changes what counts as a folder separator, and `--cursor` /
`--limit` page through a large bucket.

`object put` **requires `--file`** — the target is the remote key, the local path is a separate flag.

Deleting a prefix requires `--recursive` **and** a prefix ending in `/`; a trailing slash on its own does
nothing. That is a guard rail, not a hazard — but once `--recursive` is passed there is no undo, so confirm
the prefix with `object list` first.

Access from applications is best granted with scoped `storage:read` / `storage:write` credentials rather
than an account API key — see [security-operations.md](security-operations.md#scoped-branch-credentials).

**Using a bucket from application code.** Declaring `buckets` in `neon.ts` makes `neon env pull` write
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ENDPOINT_URL_S3` and `AWS_REGION`, so any S3 client
works — with one required setting: Neon Object Storage supports **path-style addressing only**. Set
`forcePathStyle: true` in the AWS SDK for JavaScript, or `endpoint_url` in boto3 / the `aws` CLI.
Virtual-hosted-style (`bucket.host/key`) requests fail, and the resulting error rarely names addressing as
the cause.

---

## Postgres health inspection

Read-only diagnostic queries. Nothing is modified, so these are safe against production branches.

```bash
neon inspect db <query> [--branch <id|name>] [--database-name <db>] [--role-name <role>] [--db-url <url>]
```

`--db-url` runs the query against an arbitrary connection string, which is how you inspect a database the
CLI has no project context for.

| Query | Answers |
|---|---|
| `table-sizes` / `index-sizes` | What is consuming storage |
| `bloat` | Estimated table/index bloat (statistical; no extension needed) |
| `unused-indexes` | Non-unique indexes with few scans — removal candidates |
| `seq-scans` | Sequential scans per table — missing-index signal |
| `outliers` | Queries with the most cumulative execution time (needs `pg_stat_statements`) |
| `calls` | Most frequently called queries (needs `pg_stat_statements`) |
| `long-running-queries` | Running > 5 minutes |
| `stalled-queries` | Active > 30s with waits and blockers, oldest first |
| `locks` | Locks held, with the acquiring query and its age |
| `vacuum-stats` | Autovacuum status, dead tuples, thresholds |
| `lfc-hit-rate` / `working-set` | Local File Cache effectiveness (needs the `neon` extension) |
| `replication-slots` / `subscriptions` | Logical replication state and lag |

A practical triage order for "the database feels slow": `stalled-queries` and `locks` for what's happening
right now, then `outliers` and `seq-scans` for what's chronically expensive, then `bloat` and
`vacuum-stats` for maintenance debt. The `pg_stat_statements` ones return nothing useful until the
extension is enabled, which reads as an empty result rather than an error.

---

## Agent tooling

Installers that wire Neon into coding agents.

```bash
neon init                 # full setup: agent tooling + linked project + optional neon.ts
neon mcp                  # just the hosted MCP server (https://mcp.neon.tech/mcp)
neon skills               # just Neon's agent skills
neon plugins              # skills + MCP as a plugin, where the agent supports marketplaces
neon bootstrap [dir]      # scaffold from a starter template, then install tooling and link
neon ask --prompt "<q>"   # ask the Neon assistant from the terminal
neon open                 # open the linked project in the Console
```

**`neon init`** — the umbrella. `--agent <name>` (repeatable) picks targets, `--template` / `--skip-template`
control scaffolding, `--link` / `--no-link` control project linking, `--config` / `--no-config` control
`neon.ts`, and `--project-id` / `--org-id` / `--project-name` / `--region-id` / `--branch` forward to `link`.

**`neon mcp`**

| Flag | Meaning |
|---|---|
| `--read-only` | Install the MCP server restricted to read-only tools — the right default when pointing an agent at anything production-adjacent |
| `--oauth` | Authenticate via OAuth instead of a minted API key |
| `--category` | Narrow which tool categories the agent sees, to keep the tool list small |
| `--project` | Write project-level config instead of global. **`mcp` has no `--global`** — that flag exists on `skills` and `plugins` only |
| `--agent`, `--project-id`, `--yes` | Target selection and non-interactive operation |

**`neon skills`** — `--skill <name>` (repeatable) limits it to named skills; `--agent`/`-a`, `--global` and `--yes` select targets. The `update` subcommand is narrower: **`neon skills update` accepts only `--yes` and `--global`** — passing `--agent` there errors, because agent selection lives on `neon skills` itself.

**`neon bootstrap`** — `--list-templates` shows what's available; `--template`, `--git`, `--install`,
`--agent-setup`, `--link`, `--default` control the scaffold.

All of these run interactively by default and non-interactively with flags. In a headless or scripted
environment, pass flags; without them these commands block on prompts.

```bash
neon init -y --agent cursor --project-id <id> --org-id <org-id>
neon skills update --yes            # note: no --agent on `update`
neon mcp --agent claude-code --read-only --yes    # --project for project-level config
```

`neon claim` is the outlier: it creates a temporary project **without an account**, then hands it to a human
to claim. Useful for demos, tutorials, and agent-created throwaway databases.

Both `--env-pull` (on `create`) and `--open` (on `accept`) **default to true**, so the flags you actually
reach for are `--no-env-pull` (don't write a dotenv) and `--no-open` (headless).

```bash
neon claim create [--no-env-pull]
neon claim status [project-id]
neon claim accept [project-id] [--no-open]   # URL where a human signs in and takes ownership
neon claim list
neon claim delete [project-id]
```
