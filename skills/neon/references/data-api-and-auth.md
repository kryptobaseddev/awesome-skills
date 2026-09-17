# Data API & Managed Better Auth Reference

The two surfaces with configuration large enough to need their own page. Both are branch-scoped, both
resolve project/branch/database from the `.neon` context when the flags are omitted, auto-select when there
is only one candidate, and prompt otherwise.

Flags were read from `neon --help` at 4.18.1. Where a doc and the binary disagree, the binary wins — and on a CLI releasing this often, re-check `--help` before trusting either.

## Table of Contents

- [Data API](#data-api)
  - [Provisioning](#provisioning)
  - [PostgREST-style settings](#postgrest-style-settings)
  - [Auth wiring](#auth-wiring)
  - [Schema cache](#schema-cache)
- [Managed Better Auth (`neon-auth`)](#managed-better-auth-neon-auth)
  - [Lifecycle](#lifecycle)
  - [Email + password policy](#email--password-policy)
  - [Email delivery](#email-delivery)
  - [OAuth providers](#oauth-providers)
  - [Trusted domains](#trusted-domains)
  - [Organizations and webhooks](#organizations-and-webhooks)
  - [Users](#users)

---

## Data API

A REST interface over one database, PostgREST-shaped. Requires CLI 2.22.2+.

### Provisioning

```bash
neon data-api create [options]
neon data-api get
neon data-api update [options]      # merges with current settings by default
neon data-api delete
neon data-api refresh-schema
```

`create` accepts everything `update` does, plus the auth-wiring and bootstrap flags below.

| Flag | Meaning |
|---|---|
| `--add-default-grants` | Grant all permissions on `public` **tables** to authenticated users. Table-level, so columns added later are covered automatically. Convenient for a prototype and far too broad for anything real — prefer explicit grants |
| `--skip-auth-schema` | Skip creating the auth schema and RLS helper functions, for a database that already has them |
| `--branch`, `--project-id`, `--database` | Target selection |

### PostgREST-style settings

Accepted by both `create` and `update`:

| Flag | Meaning |
|---|---|
| `--db-schemas` | Comma-separated schemas exposed via the API. Everything not listed is invisible — the primary containment control |
| `--db-anon-role` | Role used for anonymous, unauthenticated requests. Its grants define what the public internet can read |
| `--db-max-rows` | Cap on rows returned by a single request — the cheapest guard against an unbounded table scan over HTTP |
| `--db-extra-search-path` | Extra schemas appended to the search path |
| `--db-aggregates-enabled` | Allow aggregate functions in queries; off means clients cannot make the database do expensive rollups on demand |
| `--openapi-mode` | `ignore-privileges` or `disabled` — controls how much of the schema the generated OpenAPI doc reveals |
| `--server-cors-allowed-origins` | CORS allowlist |
| `--server-timing-enabled` | Emit `Server-Timing` response headers (useful in dev, a mild information leak in production) |
| `--replace` (update only) | Keep **only** the flags provided; every omitted setting **reverts to its server default** (default false). Without it `update` merges, so an omitted flag is left unchanged |

`--replace` is worth reading twice, in both directions: the merge default means you cannot unset something
by leaving it out, and `--replace` means anything you leave out is silently reset to a server default
rather than preserved. Read the current config with `neon data-api get` before using it.

### Auth wiring

| Flag | Meaning |
|---|---|
| `--auth-provider` | `neon_auth` (use Managed Better Auth on this branch) or `external` |
| `--jwks-url` | Where to fetch the JWKS, with `external` |
| `--provider-name` | Name of the external provider (Clerk, Stytch, Auth0…) |
| `--jwt-audience` | Expected `aud` claim |
| `--jwt-role-claim-key` | JWT claim path the role is read from — this is what maps a token to a Postgres role, and therefore to RLS behavior |
| `--jwt-cache-max-lifetime` | Max JWT cache lifetime in seconds |

### Schema cache

```bash
neon data-api refresh-schema [--branch <id|name>] [--project-id <id>] [--database <db>]
```

The one to remember operationally: after a migration changes tables, the Data API keeps serving its cached
schema until refreshed. A "my new column 404s" report is almost always this.

**Confirm before acting.** The response body names the cause — PostgREST returns `PGRST204` with a message
like *"Could not find the 'x' column of 'orders' in the schema cache"*. That string distinguishes a stale
cache from a genuinely missing table or a permission error, so read it before chasing RLS.

Two things it is *not*, worth ruling out in this order:

- **Wrong branch.** Both surfaces are branch-scoped, and a migration run against a different branch than the
  one the API serves produces an identical 404. `neon data-api get` shows which branch is being served.
- **Grants.** A table-level grant covers columns added later, so a new column on an already-working table is
  not normally a grant problem. Column-level grants do *not* extend to new columns — if the project used
  those, that is the exception. RLS filters rows, never columns, so it cannot explain a missing column.

Chain the refresh onto whatever applies migrations, so this never surfaces in the first place:

```bash
drizzle-kit migrate && neon data-api refresh-schema --branch "$NEON_BRANCH"
```

---

## Managed Better Auth (`neon-auth`)

Neon's hosted Better Auth, enabled per branch. For the library itself — schema, plugins, client SDK — see
the `better-auth` skill; this command group only manages the hosted configuration.

### Lifecycle

```bash
neon neon-auth enable [--database-name <db>]
neon neon-auth status
neon neon-auth disable [--delete-data]
```

`--delete-data` on `disable` **permanently deletes all Neon Auth data and the auth schema from the
database** (default false). Without it, disabling is reversible; with it, it is not.

### Email + password policy

```bash
neon neon-auth config email-password get
neon neon-auth config email-password update [options]
```

| Flag | Meaning |
|---|---|
| `--enabled` | Turn email+password sign-in on or off |
| `--disable-sign-up` | Keep sign-in working while closing new registrations — the flag you want for an invite-only or internal app |
| `--require-email-verification` | Block unverified accounts |
| `--email-verification-method` | How verification is performed |
| `--send-verification-email-on-sign-up` / `--send-verification-email-on-sign-in` | When verification mail goes out |
| `--auto-sign-in-after-verification` | Sign the user in once they verify |

### Email delivery

```bash
neon neon-auth config email-provider get
neon neon-auth config email-provider update --type <type> --host <h> --port <p> \
    --username <u> --password <pw> --sender-email <from> --sender-name <name>
neon neon-auth config email-provider test --recipient-email <addr>
```

`test` sends through the saved SMTP settings and is the fastest way to prove delivery works before users
hit it. Verification email that silently fails is indistinguishable from a broken sign-up flow.

### OAuth providers

```bash
neon neon-auth oauth-provider list
neon neon-auth oauth-provider add --provider-id <id> --oauth-client-id <id> --oauth-client-secret <secret>
neon neon-auth oauth-provider update ...
neon neon-auth oauth-provider delete ...
```

### Trusted domains

```bash
neon neon-auth domain list
neon neon-auth domain add <domain>
neon neon-auth domain delete <domain>
neon neon-auth domain allow-localhost enable|disable|get
```

`allow-localhost enable` is for development. Leaving it on for a production branch means localhost origins
stay trusted, which is exactly the kind of thing that survives to launch unnoticed.

### Organizations and webhooks

```bash
neon neon-auth config organization get
neon neon-auth config organization update [--enabled ...] [--limit <n>] [--creator-role <role>]

neon neon-auth config webhook get
neon neon-auth config webhook update --enabled <true|false> [--url <url>] [--enabled-events <list>] [--timeout <seconds>]

neon neon-auth plugins list
neon neon-auth plugins get <plugin-name>
```

`--creator-role` sets the role assigned to whoever creates an organization; `--limit` caps organizations per
user.

For webhooks, `--enabled` is **required** on every `update` (there is no partial update that leaves it
alone), and `--timeout` is in **seconds, range 1–10** — passing milliseconds is out of range and rejected.
`--enabled-events` narrows which events are delivered, which beats receiving everything and filtering
downstream.

### Users

```bash
neon neon-auth user create --email <email> [--name <name>]
neon neon-auth user set-role <user-id> --roles <roles>
neon neon-auth user delete <user-id>
```

`set-role` takes the full role set, so it replaces rather than appends — read the current roles first if you
mean to add one.
