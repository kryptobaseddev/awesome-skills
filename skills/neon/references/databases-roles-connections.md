# Databases, Roles & Connections Reference

## Table of Contents
- [Databases](#databases)
  - [create](#databases-create)
  - [list](#databases-list)
  - [delete](#databases-delete)
- [Roles](#roles)
  - [create](#roles-create)
  - [list](#roles-list)
  - [delete](#roles-delete)
- [Connection String](#connection-string)
- [psql](#psql)
- [Environment variables (`env pull`)](#environment-variables-env-pull)

---

## Databases

All database commands accept `--project-id` and `--branch` (defaults to project's default branch).

### databases create
```bash
neon databases create --name <db-name> [--owner-name <role>] [--branch <id|name>] [--project-id <id>]
```

`--name` is required. `--owner-name` defaults to current user.

```bash
neon databases create --name appdb --owner-name appadmin
neon databases create --name testdb --branch feature/auth
```

### databases list
```bash
neon databases list [--branch <id|name>] [--project-id <id>]
```

### databases delete
```bash
neon databases delete <db-name> [--branch <id|name>] [--project-id <id>]
```

---

## Roles

All role commands accept `--project-id` and `--branch` (defaults to project's default branch).

### roles create
```bash
neon roles create --name <role-name> [--no-login] [--branch <id|name>] [--project-id <id>]
```

- `--name` required (max 63 bytes)
- `--no-login` creates a passwordless, non-login role

```bash
neon roles create --name readonly_user --no-login
neon roles create --name app_service
```

### roles list
```bash
neon roles list [--branch <id|name>] [--project-id <id>]
```

### roles delete
```bash
neon roles delete <role-name> [--branch <id|name>] [--project-id <id>]
```

---

## Connection String

```bash
neon connection-string [branch[@timestamp|@LSN]] [options]
```

Branch defaults to the project's primary branch.

| Option | Type | Description |
|--------|------|-------------|
| `--project-id` | string | Project ID |
| `--role-name` | string | Database role (required if branch has multiple roles) |
| `--database-name` | string | Database name (required if branch has multiple databases) |
| `--pooled` | boolean | Enable connection pooling (adds `-pooler` to hostname) |
| `--prisma` | boolean | Prisma-compatible format (appends `connect_timeout=30`) |
| `--endpoint-type` | string | Compute type (default: `read_write`) |
| `--extended` | boolean | Show extended connection details |
| `--psql` | boolean | Launch psql directly (requires psql installed) |
| `--ssl` | string | SSL mode: `require`, `verify-ca`, `verify-full`, `omit` |

### Examples

```bash
# Basic
neon connection-string

# Pooled connection for production
neon connection-string main --pooled

# Prisma-compatible
neon connection-string --pooled --prisma

# Specific branch + role + database
neon connection-string feature/auth --role-name app --database-name mydb --pooled

# Time-travel connection
neon connection-string @2024-06-01T00:00:00Z

# Launch psql directly
neon connection-string --psql

# Run SQL file via psql
neon connection-string --psql -- -f schema.sql

# JSON output for scripting
neon connection-string --pooled -o json | jq -r '.connection_string'
```

---

## psql

```bash
neon psql [branch] [options]
```

Opens an interactive `psql` session against a branch, resolving the connection string for you. It needs `psql` on PATH. Arguments after `--` are passed through:

```bash
neon psql                                  # context branch
neon psql dev -- -c "SELECT version()"     # one-off query
neon psql -- -f migrations/001.sql          # run a file
```

`neon connection-string --psql` does the same thing from the other direction; use whichever reads better in context.

---

## Environment variables (`env pull`)

`neon env pull` writes a branch's Neon-managed variables into a local dotenv file. `neon link` and `neon checkout` run it automatically unless you pass `--no-env-pull`.

```bash
neon env pull [--file <path>] [--branch <id|name>] [--service <name>...] [--config <neon.ts>]
```

| Option | Description |
|---|---|
| `--file` | Target file. Defaults to an existing `.env`, otherwise `.env.local` |
| `--branch` | Branch to pull from (defaults to context branch) |
| `--service` | Limit to `postgres`, `auth`, `data-api`, `functions`, `object-storage`, `ai-gateway` — repeatable or comma-separated |
| `--config` | Path to a `neon.ts` policy (defaults to walking up from cwd) |

Without a `neon.ts` it writes `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, and `NEON_BRANCH`. With one, it also writes credentials for every declared service, plus `NEON_FUNCTION_<SLUG>_BASE_URL` for declared functions — derived from the branch, so the URL exists before the function is deployed.

Two properties make this safe to run against a real `.env`: only Neon-managed keys are rewritten, and unrelated lines are preserved. Unset function env values are skipped rather than failing the pull — but `neon deploy`, `neon dev`, and `neon-env run` do require every declared value, so a pull that looks clean can still be followed by a deploy that complains.

```bash
neon env pull                          # everything the branch exposes
neon env pull --service postgres       # just the database URLs
neon env pull --file .env.development  # explicit target
```
