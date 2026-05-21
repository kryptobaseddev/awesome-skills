---
name: neonctl
description: "Comprehensive Neon CLI (neonctl) management for serverless Postgres. Use when managing Neon projects, branches, databases, roles, connection strings, IP allowlists, operations, or authentication via the neonctl command-line tool. Triggers on: 'neonctl', 'neon cli', 'neon projects', 'neon branches', 'neon databases', 'neon roles', 'neon connection-string', 'neon set-context', 'neon ip-allow', 'neon operations', 'neon auth', 'neon schema-diff', 'neon branch reset', 'neon branch restore', 'NEON_API_KEY', 'neon completion', 'neon init', 'manage neon', 'neon setup', 'neonctl install'."
---

# Neonctl CLI

Neon CLI for managing serverless Postgres projects, branches, databases, roles, and compute.

## Installation

```bash
# npm (requires Node.js 18+)
npm i -g neonctl

# Homebrew (macOS)
brew install neonctl

# bun
bun install -g neonctl

# Without installing
npx neonctl <command>
bunx neonctl <command>
```

Enable shell completions:

```bash
# bash
neon completion >> ~/.bashrc && source ~/.bashrc
# zsh
neon completion >> ~/.zshrc && source ~/.zshrc
```

## Authentication

Priority order:
1. `--api-key <key>` flag (highest)
2. `NEON_API_KEY` environment variable
3. `~/.config/neonctl/credentials.json` (created by `neon auth`)
4. Browser-based login (fallback)

```bash
# Interactive browser login
neon auth

# API key via env var (CI/CD preferred)
export NEON_API_KEY=your_api_key_here

# Per-command API key
neon projects list --api-key your_api_key_here
```

## Global Options

```
-o, --output [json|yaml|table]   Output format (default: table)
--api-key <key>                  API key override
--config-dir <path>              Config dir (default: ~/.config/neonctl)
--context-file <path>            Context file path
--color / --no-color             Color output (default: enabled)
--analytics / --no-analytics     Usage analytics (default: enabled)
-v, --version                    Show version
-h, --help                       Show help
```

**Tip:** `table` output truncates data. Use `--output json` for complete output.

## Context (Avoid Repeating Project ID)

```bash
# Set default project context (creates .neon file)
neon set-context --project-id <id>

# Set project + org context
neon set-context --project-id <id> --org-id <org-id>

# Set context during project creation
neon projects create --name myapp --set-context

# Custom context file
neon set-context --project-id <id> --context-file ./my-context
neon branches list --context-file ./my-context

# Clear context
neon set-context   # or: rm .neon
```

The CLI searches up the directory tree for `.neon`, `package.json`, or `.git` to find context.

## Command Quick Reference

| Command | Purpose |
|---------|---------|
| `projects` | Create, list, update, delete, recover, get projects |
| `branches` | Create, list, delete, rename, reset, restore, schema-diff, set-default, add-compute, get branches |
| `databases` | Create, list, delete databases |
| `roles` | Create, list, delete roles |
| `connection-string` | Get connection strings (pooled, Prisma, psql) |
| `ip-allow` | Manage IP allowlists (list, add, remove, reset) |
| `operations` | List project operations |
| `orgs` | List organizations |
| `me` | Show current user info |

## Detailed Command References

For full syntax, flags, and examples for each command group:

- **Projects & Branches**: See [references/projects-branches.md](references/projects-branches.md)
- **Databases, Roles & Connections**: See [references/databases-roles-connections.md](references/databases-roles-connections.md)
- **Security & Operations**: See [references/security-operations.md](references/security-operations.md)

## Common Workflows

### New project setup
```bash
neon projects create --name myapp --region-id aws-us-east-2 --set-context
neon connection-string --pooled
```

### Feature branch workflow
```bash
neon branches create --name feature/auth --parent main --cu 0.5-2
neon connection-string feature/auth --pooled --prisma
# ... develop ...
neon branches schema-diff main feature/auth --database mydb
neon branches delete feature/auth
```

### Reset dev branch to match parent
```bash
neon branches reset dev --parent
# Keep backup before reset
neon branches reset dev --parent --preserve-under-name dev-backup
```

### Point-in-time restore
```bash
neon branches restore main ^self@2024-06-01T12:00:00Z --preserve-under-name main-backup
```

### CI/CD ephemeral branches
```bash
export NEON_API_KEY=${{ secrets.NEON_API_KEY }}
BRANCH="ci-${GITHUB_SHA:0:8}"
neon branches create --name "$BRANCH" --project-id $PROJECT_ID
CONN=$(neon connection-string "$BRANCH" --project-id $PROJECT_ID --pooled -o json | jq -r '.connection_string')
# Run tests against $CONN
neon branches delete "$BRANCH" --project-id $PROJECT_ID
```

### Add read replica
```bash
neon branches add-compute production --type read_only --cu 0.5-3
```
