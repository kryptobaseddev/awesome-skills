# Platform Surfaces Reference

Everything the 4.x CLI manages beyond Postgres itself. None of this existed in `neonctl` 2.x, so an
"unknown command" here usually means an old CLI rather than a wrong command — see
[migration-from-neonctl.md](migration-from-neonctl.md).

Several of these surfaces are in Beta (Functions, Triggers, Object Storage, branch Logs). Beta here means
the shape can move between releases; when a flag doesn't behave as documented, `--help` on the installed
binary is the authority.

## Table of Contents

- [Config as code (`neon.ts`)](#config-as-code-neonts)
- [Functions](#functions)
- [Local development (`neon dev`)](#local-development-neon-dev)
- [Triggers](#triggers)
- [Object storage buckets](#object-storage-buckets)
- [Data API](#data-api)
- [Managed Better Auth (`neon-auth`)](#managed-better-auth-neon-auth)
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

`neon deploy` and `neon status` are aliases, not separate implementations, so documentation for either
applies to both. Running `plan` before `apply` is worth the extra command whenever the branch holds
anything you would miss.

`neon env pull` reads `neon.ts` when present, which is what lets it emit per-service credentials rather
than just `DATABASE_URL`.

---

## Functions

**Beta.** Server-side functions deployed per branch.

```bash
neon functions deploy <slug>     # deploy from a local directory
neon functions list
neon functions get <slug>
neon functions delete <slug>

neon functions domains list
neon functions domains register <domain>   # point a domain you own at a function
neon functions domains delete <domain>
```

Functions are branch-scoped, so a preview branch gets its own copy and its own invocation URL. `neon env
pull` writes that URL as `NEON_FUNCTION_<SLUG>_BASE_URL`, derived from the branch — the value exists
before the function is deployed, which makes it safe to wire into config ahead of the first deploy.

---

## Local development (`neon dev`)

```bash
neon dev
```

Runs Neon Functions locally against a dev server. Unlike `env pull`, `dev` requires every env value the
declared functions read — a missing `process.env.*` that `env pull` quietly skipped will stop `dev` (and
`deploy`, and `neon-env run`).

---

## Triggers

**Beta.** Cron-scheduled invocation of a deployed function — a scheduler without a separate service.

```bash
neon triggers create --function <slug> --schedule "<cron>"
neon triggers list
neon triggers get <id>
neon triggers update <id>
neon triggers disable <id>     # pause without losing the definition
neon triggers enable <id>
neon triggers delete <id>
```

Deploy the function first, then point a trigger at it. Triggers are **inherited by child branches**: one
created on a parent shows up on children with `Inherited: true` and `source_branch_id` pointing back to the
origin. That is convenient for propagating a nightly job, and a trap when branching a project whose parent
runs something with side effects — a preview branch inherits the schedule too. Check `triggers list` on a
new long-lived branch before assuming it's inert.

---

## Object storage buckets

**Beta.** S3-style buckets that belong to a branch.

```bash
neon buckets create <name>
neon buckets list
neon buckets delete <name>

neon buckets object list <target>        # folders collapsed, like `aws s3 ls`
neon buckets object list <target> --recursive
neon buckets object put <target>         # upload a local file
neon buckets object get <target>         # download to a local file
neon buckets object delete <target>      # one object, or everything under a prefix
```

`object delete` accepting a prefix is the sharp edge: a trailing-slash target removes every key beneath it,
with no undo. Confirm the prefix with `object list` first when the target isn't an exact key.

Access from applications is best granted with scoped `storage:read` / `storage:write` credentials rather
than an account API key — see [security-operations.md](security-operations.md#scoped-branch-credentials).

---

## Data API

A REST interface over a database. Requires CLI 2.22.2+.

```bash
neon data-api create
neon data-api get
neon data-api update            # merges with current settings by default
neon data-api refresh-schema    # re-read the schema cache after a migration
neon data-api delete
```

Project, branch, and database resolve from the context file, auto-select when there's only one, and prompt
otherwise. `refresh-schema` is the one to remember operationally: after a migration changes tables, the
Data API keeps serving the cached schema until it's refreshed.

---

## Managed Better Auth (`neon-auth`)

Neon's hosted Better Auth. Enabled per branch.

```bash
neon neon-auth enable
neon neon-auth status
neon neon-auth disable

neon neon-auth domain list
neon neon-auth domain add <domain>
neon neon-auth domain delete <domain>
neon neon-auth domain allow-localhost enable|disable|get

neon neon-auth oauth-provider list|add|update|delete
neon neon-auth config email-password get|update
neon neon-auth config email-provider get|update|test
neon neon-auth config organization get|update
neon neon-auth config webhook get|update
neon neon-auth plugins list
neon neon-auth plugins get <plugin-name>

neon neon-auth user create
neon neon-auth user set-role <user-id>
neon neon-auth user delete <user-id>
```

`domain allow-localhost enable` is for development; leaving it on for a production branch means localhost
origins stay trusted. `config email-provider test` sends through the saved SMTP settings and is the fastest
way to prove email delivery works before users hit it.

For the library itself (schema, plugins, client SDK) see the `better-auth` skill — this command group only
manages the hosted configuration.

---

## Postgres health inspection

Read-only diagnostic queries. Nothing is modified, so these are safe against production branches.

```bash
neon inspect db <query> [--branch <id|name>] [--database-name <db>] [--role-name <role>] [--db-url <url>]
```

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
neon ask "<question>"     # ask the Neon assistant from the terminal
neon open                 # open the linked project in the Console
```

All of them run interactively by default and non-interactively with flags — `--agent <name>` (repeatable),
`--yes`, `--global`, `--skill`. In a headless or scripted environment, pass flags; without them these
commands block on prompts.

```bash
neon init -y --agent cursor --project-id <id> --org-id <org-id>
neon skills update --agent claude-code --yes
```

`neon claim` is the outlier: it creates a temporary project **without an account**, then hands it to a human
to claim. Useful for demos, tutorials, and agent-created throwaway databases.

```bash
neon claim create
neon claim status [project-id]
neon claim accept [project-id]    # opens the URL where a human signs in and takes ownership
neon claim list
neon claim delete [project-id]
```
