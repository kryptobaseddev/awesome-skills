---
name: flarectl
description: "Cloudflare CLI management via the flarectl tool. Use when the user asks to manage Cloudflare zones, DNS records, firewall rules, cache purging, or zone exports using flarectl. Covers onboarding (installation, API Token vs Global API Key setup), zone CRUD, DNS record CRUD, firewall access rules, cache purging, zone file export, and permission verification. Also guides when to use Wrangler instead (Workers, Pages, R2, KV, D1). Triggers on: 'flarectl', 'cloudflare cli', 'cloudflare dns', 'cloudflare zone', 'CF_API_TOKEN', 'CF_API_KEY', 'manage cloudflare', 'cloudflare firewall', 'purge cloudflare cache', 'cloudflare setup', 'flarectl setup'."
---

# flarectl — Cloudflare CLI Skill

## Important: Scope Boundaries

flarectl manages **zones, DNS, firewall rules, cache, and zone exports**. It does NOT support Workers, Pages, R2, KV, D1, or Queues — use **Wrangler** (`npm i -g wrangler`) for those.

flarectl is legacy software (v0 branch of cloudflare-go). It works and is installable via Homebrew (v0.116.0+), but receives no new features.

## Onboarding Workflow

Guide users through setup in this order:

1. **Install** → verify with `flarectl --version`
2. **Authenticate** → choose API Token (recommended) or Global API Key
3. **Verify access** → run `flarectl zone list` or `flarectl user info`
4. **Verify token permissions** → run `scripts/cf-check-access.sh`

See [references/setup-guide.md](references/setup-guide.md) for detailed installation and authentication instructions.

## Authentication Quick Reference

| Method | Env Vars | Security |
|--------|----------|----------|
| **API Token** (recommended) | `CF_API_TOKEN` | Scoped permissions, limited blast radius |
| **Global API Key** (legacy) | `CF_API_KEY` + `CF_API_EMAIL` | Full account access, dangerous if leaked |

Precedence: `CF_API_TOKEN` wins if set. Otherwise both `CF_API_KEY` and `CF_API_EMAIL` required.

**Note:** flarectl uses `CF_` prefixed vars. Wrangler uses `CLOUDFLARE_` prefixed vars. They are NOT interchangeable.

## Verifying Access & Permissions

Run `scripts/cf-check-access.sh` to verify token validity and test common permissions. Or manually:

```bash
# Verify token is valid (API Token only)
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq .

# List token details and policies
curl -s "https://api.cloudflare.com/client/v4/user/tokens" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq '.result[] | {name, status, policies}'

# Quick permission tests via flarectl
flarectl zone list          # Tests Zone:Read
flarectl user info          # Tests User Details:Read
flarectl dns list --zone example.com  # Tests DNS:Read
```

### Required Token Permissions by Command

| Command | Required Permission |
|---------|-------------------|
| `zone list/info` | Zone: Zone: Read |
| `zone create/delete` | Zone: Zone: Edit |
| `dns list` | Zone: DNS: Read |
| `dns create/update/delete` | Zone: DNS: Edit |
| `zone purge` | Zone: Cache Purge: Purge |
| `firewall rules list` | Zone: Firewall Services: Read |
| `firewall rules create/update/delete` | Zone: Firewall Services: Edit |
| `user info` | User: User Details: Read |

## Command Reference

See [references/command-reference.md](references/command-reference.md) for the complete command reference with all flags and examples covering:
- Zone management (list, info, create, delete, purge, export, lockdown)
- DNS record CRUD (list, create, update, create-or-update, delete)
- Firewall access rules (list, create, update, delete — IP/CIDR/ASN/country)
- User-agent blocking, page rules, IP ranges
- Command aliases quick reference

## Global Options

```
--json            Output as JSON instead of ASCII table
--account-id <id> Account ID (or set CF_ACCOUNT_ID)
--help, -h        Show help
--version, -v     Show version
```

Always use `--json` when parsing output programmatically.

## Common Workflows

### Add a zone and configure DNS

```bash
flarectl zone create --zone example.com --jumpstart
flarectl dns create --zone example.com --name www --type A --content 203.0.113.50 --proxy
flarectl dns create --zone example.com --name @ --type MX --content mail.example.com --priority 10
```

### Bulk DNS update (idempotent)

```bash
# create-or-update is an upsert — safe to run repeatedly
flarectl dns create-or-update --zone example.com --name app --type CNAME --content new-backend.example.com --proxy
```

### Purge cache

```bash
flarectl zone purge --zone example.com --everything
# Or selective:
flarectl zone purge --zone example.com --files "https://example.com/style.css"
```

### Export zone file (BIND format)

```bash
flarectl zone export --zone example.com > example.com.zone
```

### Block an IP via firewall

```bash
flarectl firewall rules create --zone example.com --value 198.51.100.1 --mode block --notes "Abuse"
```

## When to Use Wrangler Instead

| Need | Tool |
|------|------|
| DNS, zones, firewall, cache purge, zone export | **flarectl** |
| Workers, Pages, R2, KV, D1, Queues, Durable Objects | **Wrangler** |
| Full API surface or features not in either CLI | **curl + Cloudflare API** |
