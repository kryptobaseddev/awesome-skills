# Security & Operations Reference

## Table of Contents
- [IP Allow](#ip-allow)
  - [list](#ip-allow-list)
  - [add](#ip-allow-add)
  - [remove](#ip-allow-remove)
  - [reset](#ip-allow-reset)
- [Operations](#operations)
  - [list](#operations-list)
- [Organizations](#organizations)
- [User Info](#user-info)

---

## IP Allow

Manage IP allowlists. Supports individual IPs, ranges, and CIDR notation.

All subcommands accept `--project-id` and `--context-file`.

### ip-allow list
```bash
neon ip-allow list [--project-id <id>]
neon ip-allow list --project-id <id> --output json
```

### ip-allow add
```bash
neon ip-allow add <ip> [<ip>...] [--project-id <id>] [--protected-only <true|false>]
```

- `--protected-only` applies restriction to protected branches only

```bash
neon ip-allow add 192.0.2.1 --project-id my-project
neon ip-allow add 10.0.0.0/24 192.168.1.0/24 --project-id my-project
neon ip-allow add 203.0.113.0/24 --protected-only true --project-id my-project
```

### ip-allow remove
```bash
neon ip-allow remove <ip> [<ip>...] [--project-id <id>]
```

```bash
neon ip-allow remove 192.0.2.1 --project-id my-project
```

### ip-allow reset
Replace the entire allowlist. Omit IPs to clear all entries.
```bash
neon ip-allow reset [<ip>...] [--project-id <id>]
```

```bash
# Replace with new IPs
neon ip-allow reset 10.0.0.1 10.0.0.2 --project-id my-project

# Clear all IPs (removes allowlist)
neon ip-allow reset --project-id my-project
```

---

## Operations

### operations list
List operations (actions performed on a project).
```bash
neon operations list [--project-id <id>]
```

Output includes: operation ID, action type (e.g. `apply_config`, `suspend_compute`), status, and timestamp.

---

## Organizations

```bash
neon orgs list
```

Lists organizations the authenticated user belongs to.

---

## User Info

```bash
neon me
neon me --output json
```

Display current authenticated user information.
