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
- [Named credential profiles](#named-credential-profiles)
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
# every `vpc endpoint` subcommand REQUIRES --region-id
neon vpc endpoint list --region-id aws-us-east-2
neon vpc endpoint assign <endpoint-id> --region-id aws-us-east-2 [--label <label>]
neon vpc endpoint status <endpoint-id> --region-id aws-us-east-2
neon vpc endpoint remove <endpoint-id> --region-id aws-us-east-2

neon vpc project restrict <endpoint-id> [--label <label>]   # project only accepts connections via this VPC
neon vpc project list
neon vpc project remove <endpoint-id>
```

`--region-id` is **required on every `vpc endpoint` subcommand** — endpoints are per region, so there is no
account-wide listing. `vpc project` subcommands do not take it. `--org-id` is only needed when the account
belongs to more than one organization. Azure regions are not supported yet. Restricting a project to a VPC endpoint can cut off existing public connections — pair it with `projects update --block-public-connections` deliberately, not incidentally.

---

## Branch logs

**Beta.** Covers Neon Functions and Object Storage today (Postgres compute logs are not there yet), and only in `aws-us-east-2` and `aws-eu-central-1`.

```bash
neon logs query                                   # last hour, default branch, newest first
neon logs query --since 15m --severity-text ERROR        # exact, case-sensitive
neon logs query --source function --body-contains "timeout" --limit 100
neon logs fields                                  # what's filterable on this branch
neon logs field-values <field>                    # observed values for a field
```

`--source` takes **singular** values: `function`, `storage`, `pg_endpoint` (not `functions`). `pg_endpoint`
is accepted but returns nothing yet.

**`--minimum-severity` does not work.** Neon documents it as unsupported by the branch log backend — use
`--severity-text`, which matches the exact, case-sensitive value (`ERROR`, `INFO`, uppercase). Severities
vary by source, so an empty result can be legitimate: storage logs are S3 access records and are all `INFO`,
so `--source storage --severity-text ERROR` matches nothing by construction. Run
`neon logs field-values severity_text` to see what a branch actually reports before filtering.

Other filters: `--since`, `--start-time`/`--end-time`, `--service-name`, `--scope-name`, `--body-contains`,
`--trace-id`, `--logql`, `--limit`, `--cursor`, `--sort-order`. Running `fields` before building a filter
beats guessing at attribute names.

---

## Raw API passthrough

```bash
neon api <path> [options]
```

Sends an authenticated request to any Neon Platform API route. Method defaults to `GET`, or `POST` when a
body is supplied. This is the escape hatch when a route has no CLI command yet.

| Flag | Meaning |
|---|---|
| `-X`, `--method` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` |
| `-F`, `--field` | Body field `key=value`, repeatable. **Dot-notation nests** (`-F branch.name=dev`) and values are typed — numbers, booleans, null and JSON are parsed, not stringified |
| `-f`, `--raw-field` | Same, but the value stays a raw string — use it when a numeric-looking value must remain text |
| `-d`, `--data` | Raw body: a JSON string, `@file`, or `-` for stdin. Overrides `--field` |
| `-Q`, `--query` | Query parameter `key=value`, repeatable |
| `-H`, `--header` | Extra request header `key:value`, repeatable |
| `-i`, `--include` | Print response status and headers before the body |
| `--list` | List every available API route from the OpenAPI spec |
| `--describe` | Print the path, query and body fields for a route **without calling it**; body names come back dotted, ready to paste after `-F` |
| `--refresh` | Refresh the cached OpenAPI spec (used with `--list` / `--describe`) |

`--describe` is the feature that makes this usable without a browser: ask the CLI what a route accepts,
then build the call.

```bash
neon api --list                                   # every route
neon api /projects --describe                     # GET /projects query params
neon api /projects -X POST --describe             # create-project body fields
neon api /projects/{id}/branches -X POST -F branch.name=dev
```

It is a **raw** passthrough: it ignores the `.neon` context file and fills nothing in, so every route gets
exactly the parameters you pass. Some routes therefore need a parameter the equivalent CLI command would
have supplied for you — `neon api /projects` can come back with `org_id is required` depending on how the
session is authenticated, which `-Q org_id=<id>` (from `neon orgs list`) resolves. On a
browser-authenticated personal account it usually just works, so treat this as a thing to read from the
error rather than a rule.

---

## Named credential profiles

Separate accounts or scopes without juggling environment variables.

```bash
neon profile create <name> [--api-key <key> | --mint] [--org-id <id>] [--project-id <id>] [--keyring]
neon profile list                 # each profile, its account, and where its credentials live
neon profile rotate-key <name>    # mint a fresh key at the same scope and revoke the one it replaces
neon profile remove <name> [--yes]
```

A profile holds **either** a browser sign-in or an API key, never both. `--mint` has Neon issue the key for
you; `--org-id` / `--project-id` scope it down. `--keyring` stores the secret in the OS keyring instead of
a file, which is the difference between a credential at rest in plaintext and one that isn't.

Select a profile per command with `--profile <name>`, or set `NEON_PROFILE`. `rotate-key` is the clean
rotation path: the replacement is minted before the old key is revoked, so nothing is briefly unauthenticated.
