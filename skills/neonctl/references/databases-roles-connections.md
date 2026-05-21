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
