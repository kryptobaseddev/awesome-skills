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
- [API keys](#api-keys)
- [Scoped branch credentials](#scoped-branch-credentials)
- [Private networking (VPC)](#private-networking-vpc)
- [Branch logs](#branch-logs)
- [Raw API passthrough](#raw-api-passthrough)
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

---

## API keys

Account- or organization-scoped keys, used for `NEON_API_KEY` and `--api-key`.

```bash
neon api-keys create --name ci-deploy
neon api-keys list
neon api-keys revoke <id>
```

The key value is printed **once at creation and never again** — if it isn't captured into a secret store in that moment, the only remedy is revoke-and-recreate. Revoking takes effect immediately, so anything still using the key starts failing without a grace period; rotate by creating the replacement, deploying it, then revoking the old one.

---

## Scoped branch credentials

Branch-scoped credentials let an application or agent reach a branch's non-Postgres surfaces without handing over an account API key — a meaningfully smaller blast radius.

Scopes: `storage:read`, `storage:write` (Object Storage), `ai_gateway:invoke` (AI Gateway), `functions:invoke` (Functions).

```bash
neon credentials create --scope storage:read --branch main
neon credentials list
neon credentials reveal <tokenId>
neon credentials rotate <tokenId>     # new secrets, same token id
neon credentials revoke <tokenId>
```

Each credential carries an `api_token` and an `s3_secret_access_key`, returned only on create, rotate, or an explicit `reveal`. The `token_id` (`nak_live_<hex>`) is stable across rotation, so rotating a credential doesn't require updating references to it — only the secret values.

---

## Private networking (VPC)

Two levels: endpoints registered on the organization, and per-project restrictions that pin a project to them.

```bash
neon vpc endpoint list
neon vpc endpoint assign <endpoint-id>
neon vpc endpoint status <endpoint-id>
neon vpc endpoint remove <endpoint-id>

neon vpc project restrict <endpoint-id>    # project only accepts connections via this VPC
neon vpc project list
neon vpc project remove <endpoint-id>
```

`--org-id` is only needed when the account belongs to more than one organization. Azure regions are not supported yet. Restricting a project to a VPC endpoint can cut off existing public connections — pair it with `projects update --block-public-connections` deliberately, not incidentally.

---

## Branch logs

**Beta.** Covers Neon Functions and Object Storage today (Postgres compute logs are not there yet), and only in `aws-us-east-2` and `aws-eu-central-1`.

```bash
neon logs query                                   # last hour, default branch, newest first
neon logs query --since 15m --minimum-severity warn
neon logs query --source functions --body-contains "timeout" --limit 100
neon logs fields                                  # what's filterable on this branch
neon logs field-values <field>                    # observed values for a field
```

Useful filters: `--since`, `--start-time`/`--end-time`, `--source`, `--service-name`, `--scope-name`, `--severity-text`, `--minimum-severity`, `--body-contains`, `--trace-id`, `--logql`, `--limit`, `--cursor`, `--sort-order`. Running `fields` before building a filter beats guessing at attribute names.

---

## Raw API passthrough

```bash
neon api <path> [-X <method>] [-d <json|@file|->] [-Q key=value]
```

Sends an authenticated request to any Neon Platform API route. Method defaults to `GET`, or `POST` when a body is supplied. This is the escape hatch when a route has no CLI command yet.

It is a **raw** passthrough: it ignores the `.neon` context file and fills in nothing. `neon api /projects` fails with `org_id is required` unless you add `-Q org_id=<id>` or authenticate with an org-scoped key — get the ID from `neon orgs list`.
