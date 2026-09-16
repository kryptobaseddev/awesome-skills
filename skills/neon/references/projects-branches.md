# Projects & Branches Reference

## Table of Contents
- [Projects](#projects)
  - [create](#projects-create)
  - [list](#projects-list)
  - [get](#projects-get)
  - [update](#projects-update)
  - [delete](#projects-delete)
  - [recover](#projects-recover)
- [Branches](#branches)
  - [create](#branches-create)
  - [list](#branches-list)
  - [get](#branches-get)
  - [delete](#branches-delete)
  - [rename](#branches-rename)
  - [reset](#branches-reset)
  - [restore](#branches-restore)
  - [schema-diff](#branches-schema-diff)
  - [set-default](#branches-set-default)
  - [set-expiration](#branches-set-expiration)
  - [add-compute](#branches-add-compute)
- [Schema diff shortcut](#schema-diff-shortcut)
- [Snapshots](#snapshots)
  - [create](#snapshots-create)
  - [list / get / update / delete](#snapshots-list--get--update--delete)
  - [restore](#snapshots-restore)
  - [schedule](#snapshots-schedule)

---

## Projects

### projects create
```bash
neon projects create [options]
```

| Option | Type | Description |
|--------|------|-------------|
| `--name` | string | Project name (uses project ID if omitted) |
| `--region-id` | string | Region (default: `aws-us-east-2`) |
| `--org-id` | string | Target organization |
| `--database` | string | Initial database name |
| `--role` | string | Initial role name |
| `--cu` | string | Compute size: fixed (`"2"`) or range (`"0.5-3"`) |
| `--psql` | boolean | Open psql after creation |
| `--set-context` | boolean | Set as active project context |
| `--hipaa` | boolean | Enable HIPAA compliance |
| `--block-public-connections` | boolean | Block internet access |
| `--block-vpc-connections` | boolean | Block VPC access |
| `--pg-version` | number | Major Postgres version (14–19) |
| `--secrets` / `--no-secrets` | boolean | Include connection credentials in output |

```bash
neon projects create --name myapp --region-id aws-us-west-2 --cu 0.5-3
neon projects create --name myapp --set-context --database appdb --role appadmin
```

Default Postgres version: 17. Pass `--pg-version` to pick another major (14–19); 19 has limited availability.

### projects list
```bash
neon projects list [options]
```

| Option | Type | Description |
|--------|------|-------------|
| `--org-id` | string | Filter by organization |
| `--recoverable-only` | boolean | Show only deleted projects within recovery window |

### projects get
```bash
neon projects get <project-id>
```

### projects update
```bash
neon projects update <project-id> [options]
```

| Option | Type | Description |
|--------|------|-------------|
| `--name` | string | New project name |
| `--cu` | string | Adjust compute resources |
| `--hipaa` | boolean | Toggle HIPAA mode |
| `--block-public-connections` | boolean | Toggle public access |
| `--block-vpc-connections` | boolean | Toggle VPC access |
| `--enable-logical-replication` | boolean | Enable logical replication on all endpoints — **suspends computes** and cannot be turned back off |
| `--yes` | boolean | Skip the logical-replication confirmation prompt |

```bash
neon projects update muddy-wood-859533 --name production-db
```

### projects delete
```bash
neon projects delete <project-id>
```

### projects recover
Restore a deleted project within its deletion grace period. This is the only undo for `projects delete` — branch and database deletions have no equivalent.
```bash
neon projects recover <project-id>
```

---

## Branches

### branches create
```bash
neon branches create [options]
```

| Option | Type | Description |
|--------|------|-------------|
| `--name` | string | Branch name |
| `--parent` | string | Source: branch ID, name, timestamp, or LSN (default: main) |
| `--project-id` | string | Project ID |
| `--compute` / `--no-compute` | boolean | Attach compute endpoint |
| `--type` | string | `read_write` (default) or `read_only` |
| `--cu` | string | Compute size: fixed or range |
| `--suspend-timeout` | number | Auto-suspend after N seconds of inactivity |
| `--schema-only` | boolean | Copy schema without data |
| `--expires-at` | string | RFC 3339 auto-deletion timestamp |
| `--psql` | boolean | Connect immediately |
| `--protected` | boolean | Mark as protected — blocks deletion and reset until unset |
| `--secrets` / `--no-secrets` | boolean | Include connection credentials in output |

```bash
neon branches create --name feature/auth --parent main --cu 0.5-2
neon branches create --name staging --schema-only
neon branches create --name ci-test --expires-at 2024-12-31T23:59:59Z
```

### branches list
```bash
neon branches list [--project-id <id>]
```

### branches get
```bash
neon branches get <id|name> [--project-id <id>]
```

### branches delete
```bash
neon branches delete <id|name> [--project-id <id>]
```

### branches rename
```bash
neon branches rename <id|name> <new-name> [--project-id <id>]
```
Max 256 characters, must be unique within project.

### branches reset
Sync a child branch with parent's latest state.
```bash
neon branches reset <id|name> --parent [--preserve-under-name <backup-name>]
```

```bash
neon branches reset dev --parent
neon branches reset dev --parent --preserve-under-name dev-backup-june
```

### branches restore
Rewind a branch to a specific point in time or another branch's state.
```bash
neon branches restore <target> <source>[@timestamp|@lsn] [--preserve-under-name <name>]
```

Source formats:
- `^self@<timestamp|lsn>` — Earlier state of same branch (**requires** `--preserve-under-name`)
- `^parent[@timestamp|lsn]` — Parent branch at head or specific point
- `<branch-id|name>[@timestamp|lsn]` — Another branch's state

```bash
# Restore main to earlier point (backup required)
neon branches restore main ^self@2024-06-01T12:00:00Z --preserve-under-name main-backup

# Restore from parent's current state
neon branches restore dev ^parent

# Restore from another branch at a specific time
neon branches restore staging production@2024-06-01T00:00:00Z
```

### branches schema-diff
Compare schemas between branches.
```bash
neon branches schema-diff [base-branch] [compare-source[@timestamp|@lsn]] [--database <name>]
```

Compare targets:
- `^self@<timestamp|lsn>` — Earlier schema of same branch
- `^parent[@timestamp|lsn]` — Parent branch schema
- `<branch-id|name>[@timestamp|lsn]` — Another branch's schema

```bash
neon branches schema-diff main feature/auth --database mydb
neon branches schema-diff main ^self@2024-05-01T00:00:00Z
```

### branches set-default
```bash
neon branches set-default <id|name> [--project-id <id>]
```

### branches set-expiration
```bash
# Set expiration
neon branches set-expiration <id|name> --expires-at <RFC3339-timestamp>

# Remove expiration (omit flag)
neon branches set-expiration <id|name>
```

### branches add-compute
Attach a compute endpoint to a branch.
```bash
neon branches add-compute <id|name> [--type read_write|read_only] [--cu <size|range>]
```

```bash
neon branches add-compute production --type read_only --cu 0.5-3
```

---

## Schema diff shortcut

`neon diff` is the git-style shortcut for the common case — "what did I change since branching?" — while `branches schema-diff` remains the tool for comparing against a timestamp or LSN.

```bash
neon diff [compare-branch] [--branch <reviewed>] [--database <name>]
```

The reviewed branch is the `+++` side and comes from `--branch`, else the `.neon` context, else the project default. Omitting `compare-branch` diffs against the parent. Output covers every database on the branch unless `--database` narrows it; `--output json` emits one entry per database.

```bash
neon diff                      # my branch vs its parent
neon diff main --database app  # my branch vs main, one database
```

---

## Snapshots

A snapshot captures a branch at a point in time for later restore. Compared with `branches restore`, snapshots are explicit artifacts with their own lifecycle and an optional automatic schedule — which is what makes them the right primitive for backups, where `restore` is the right primitive for an ad-hoc rewind.

If `--project-id` is omitted, the CLI resolves it from the context file, auto-selects when the account has exactly one project, and prompts otherwise.

### snapshots create

```bash
neon snapshots create [--branch <id|name>] [--name <name>] [--expires-at <rfc3339>] [--lsn <lsn> | --timestamp <rfc3339>]
```

Defaults to the head of the context branch (or the project's default branch). `--lsn` and `--timestamp` are mutually exclusive and must fall inside the branch's history window.

```bash
neon snapshots create --branch main --name pre-migration
neon snapshots create --branch main --timestamp 2026-01-01T00:00:00Z --expires-at 2026-12-31T23:59:59Z
```

Taking a named snapshot before a destructive migration is cheap insurance and makes the rollback story a single command instead of a point-in-time calculation.

### snapshots list / get / update / delete

```bash
neon snapshots list [--project-id <id>]
neon snapshots get <id|name>
neon snapshots update <id|name> [--name <new>] [--expires-at <rfc3339>] [--clear-expiration]
neon snapshots delete <id|name>
```

### snapshots restore

```bash
neon snapshots restore <id|name> [--target-branch <id|name>] [--name <name>] [--finalize]
```

Restoring produces a restored branch. Without `--finalize` the restore is a preview you can inspect before committing to it; `neon snapshots finalize <branch>` then swaps the restored branch in. Previewing first is the safer default when restoring over a branch an application is pointed at.

### snapshots schedule

```bash
neon snapshots schedule get [--branch <id|name>]
neon snapshots schedule set [--branch <id|name>] ...
```

Automatic snapshot schedules are per branch, so a project's default branch and its long-lived staging branch are configured independently.
