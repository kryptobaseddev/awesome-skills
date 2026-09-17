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

Branch defaults to the project's default branch.

| Option | Type | Description |
|--------|------|-------------|
| `--project-id` | string | Project ID |
| `--role-name` | string | Database role (required if branch has multiple roles) |
| `--database-name` | string | Database name (required if branch has multiple databases) |
| `--pooled` | boolean | Enable connection pooling (adds `-pooler` to hostname) |
| `--prisma` | boolean | Prisma-compatible format (appends `connect_timeout=30`) |
| `--endpoint-type` | string | Compute type (default: `read_write`) |
| `--extended` | boolean | Show extended connection details |
| `--psql` | boolean | Launch psql directly. **Does not require psql to be installed** — if it isn't on `$PATH` the CLI falls back to a built-in TypeScript implementation |
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

# Scripting: the plain form is ALREADY a bare string — `-o json` does not wrap it
CONN=$(neon connection-string --pooled)

# The structured form, when you need the parts (host, role, password, database, options)
neon connection-string --pooled --extended -o json | jq -r '.connection_string'
```

---

## psql

```bash
neon psql [branch] [options]
```

Opens an interactive `psql` session against a branch, resolving the connection string for you. A local `psql`
is used when present; when it isn't, the CLI falls back to a built-in TypeScript implementation, so this
works on a bare machine. Arguments after `--` are passed through:

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
| `--env`, `-e` | **Selector, not an input:** pull only these named variables (`DATABASE_URL`, `NEON_BRANCH`, `NEON_AUTH_*`…). Overrides `neon.ts` and unions with `--service`. The *load-a-dotenv* meaning of `--env` belongs to `config apply`/`deploy`/`checkout`/`functions deploy` — same flag name, different job |

With a `neon.ts` it writes credentials for every declared service, plus `NEON_FUNCTION_<SLUG>_BASE_URL` for
declared functions — derived from the branch, so the URL exists before the function is deployed.

**Without** a `neon.ts`, and with no `--service`/`--env` narrowing, it does not write a minimal trio — it
writes **everything the branch has, plus the AI Gateway**, which mints the default AI Gateway credential.
That is a secret landing in your working tree that you may not have asked for, so scope it (`--service
postgres`) when all you wanted was a database URL.

Two properties make this safe to run against a real `.env`: only Neon-managed keys are rewritten, and unrelated lines are preserved. Unset function env values are skipped rather than failing the pull — but `neon deploy`, `neon dev`, and `neon-env run` do require every declared value, so a pull that looks clean can still be followed by a deploy that complains.

```bash
neon env pull                          # everything the branch exposes
neon env pull --service postgres       # just the database URLs
neon env pull --file .env.development  # explicit target
```
