# flarectl Command Reference

## Table of Contents
- [Zone Management](#zone-management)
- [DNS Record Management](#dns-record-management)
- [Firewall Access Rules](#firewall-access-rules)
- [User-Agent Blocking](#user-agent-blocking)
- [Other Commands](#other-commands)
- [Command Aliases](#command-aliases)

## Zone Management

### List zones
```bash
flarectl zone list
flarectl zone list --json
```
Output: ID, Name, Plan, Status

### Zone info
```bash
flarectl zone info --zone example.com
```
Output: ID, Zone, Plan, Status, Name Servers, Paused, Type

### Create zone
```bash
flarectl zone create --zone example.com [--jumpstart] [--account-id <id>]
```
- `--jumpstart` — auto-fetch existing DNS records
- `--account-id` — target account

### Delete zone
```bash
flarectl zone delete --zone example.com
```

### Activation check
```bash
flarectl zone check --zone example.com
```
Verifies nameserver configuration.

### List zone DNS (shortcut)
```bash
flarectl zone dns --zone example.com
```
Equivalent to `flarectl dns list --zone example.com`.

### Purge cache
```bash
# Everything
flarectl zone purge --zone example.com --everything

# Specific URLs (repeatable flag)
flarectl zone purge --zone example.com --files "https://example.com/style.css" --files "https://example.com/app.js"

# By cache tags (Enterprise only)
flarectl zone purge --zone example.com --tags "tag1" --tags "tag2"

# By hostnames
flarectl zone purge --zone example.com --hosts "www.example.com"

# By prefixes
flarectl zone purge --zone example.com --prefixes "example.com/assets"
```
At least one of `--everything`, `--files`, `--tags`, `--hosts`, or `--prefixes` required.

### Zone lockdown
```bash
flarectl zone lockdown --zone example.com \
  --urls "/api/*" --targets "ip" --values "198.51.100.4"
```
Number of `--targets` and `--values` must match.

### Export zone file (BIND format)
```bash
flarectl zone export --zone example.com
```
Outputs to stdout. Redirect to save: `> example.com.zone`

## DNS Record Management

### List records
```bash
flarectl dns list --zone example.com
flarectl dns list --zone example.com --type A
flarectl dns list --zone example.com --name www.example.com
flarectl dns list --zone example.com --content 1.2.3.4
flarectl dns list --zone example.com --id <record-id>
```
Output: ID, Type, Name, Content, Proxied, TTL

### Create record
```bash
flarectl dns create --zone example.com --name www --type A --content 203.0.113.50 --ttl 3600
flarectl dns create --zone example.com --name app --type CNAME --content myapp.example.com --proxy
flarectl dns create --zone example.com --name example.com --type MX --content mail.example.com --priority 10
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--zone` | Yes | — | Zone name |
| `--name` | Yes | — | Record name (subdomain or FQDN) |
| `--type` | Yes | — | A, AAAA, CNAME, MX, TXT, SRV, etc. |
| `--content` | Yes | — | Record value |
| `--ttl` | No | 1 (auto) | TTL in seconds |
| `--proxy` | No | false | Proxy through Cloudflare (orange cloud) |
| `--priority` | No | 0 | For MX records |

### Update record
```bash
flarectl dns update --zone example.com --id <record-id> --content 203.0.113.51
```
Requires `--id`. Other flags optional (updates only what's specified).

### Create or update (upsert)
```bash
flarectl dns create-or-update --zone example.com --name app --type CNAME --content new.example.com --proxy
```
Matches on name + type. Updates first match if found, creates if not. Same flags as `create`.

### Delete record
```bash
flarectl dns delete --zone example.com --id <record-id>
```

## Firewall Access Rules

Scope: user (default), zone (`--zone`), or account (`--account`).

### List rules
```bash
flarectl firewall rules list
flarectl firewall rules list --zone example.com
flarectl firewall rules list --account "My Account"
flarectl firewall rules list --value 8.8.8.8 --mode block
```

### Create rule
```bash
flarectl firewall rules create --value 8.8.8.8 --mode block --notes "Block bad actor"
flarectl firewall rules create --zone example.com --value 203.0.113.0/24 --mode challenge
flarectl firewall rules create --value 13335 --mode whitelist --notes "Cloudflare ASN"
flarectl firewall rules create --value CN --mode block --notes "Block country"
```

Modes: `block`, `challenge`, `whitelist`, `js_challenge`

Auto-detection of `--value`: IP → `ip` target, CIDR → `ip_range`, integer → `asn`, other → `country`.

### Update rule
```bash
flarectl firewall rules update --id <rule-id> --mode challenge --notes "Updated"
```

### Create or update (upsert)
```bash
flarectl firewall rules create-or-update --value 8.8.8.8 --mode block --notes "Updated block"
```

### Delete rule
```bash
flarectl firewall rules delete --id <rule-id>
flarectl firewall rules delete --id <rule-id> --zone example.com
```

## User-Agent Blocking

### List rules
```bash
flarectl user-agents list --zone example.com --page 1
```

### Create rule
```bash
flarectl user-agents create --zone example.com --mode block --value "BadBot/1.0" --description "Block bot"
```
Modes: `block`, `challenge`, `js_challenge`, `whitelist`. Add `--paused` to create paused.

### Update rule
```bash
flarectl user-agents update --zone example.com --id <rule-id> --mode challenge --value "BadBot/2.0"
```

### Delete rule
```bash
flarectl user-agents delete --zone example.com --id <rule-id>
```

## Other Commands

### Cloudflare IP ranges (no auth required)
```bash
flarectl ips
flarectl ips --ip-type ipv4
flarectl ips --ip-type ipv6
```

### User info
```bash
flarectl user info
```
Output: ID, Email, Username, Name, 2FA

### Page rules
```bash
flarectl pagerules list --zone example.com
```

### Origin CA root certificate
```bash
flarectl origin-ca-root-cert --algorithm ecc
flarectl origin-ca-root-cert --algorithm rsa
```

## Command Aliases

| Full | Short |
|------|-------|
| `flarectl zone list` | `flarectl z l` |
| `flarectl zone info` | `flarectl z i` |
| `flarectl zone create` | `flarectl z c` |
| `flarectl zone export` | `flarectl z x` |
| `flarectl zone dns` | `flarectl z d` |
| `flarectl dns list` | `flarectl d l` |
| `flarectl dns create` | `flarectl d c` |
| `flarectl dns update` | `flarectl d u` |
| `flarectl dns create-or-update` | `flarectl d o` |
| `flarectl dns delete` | `flarectl d d` |
| `flarectl firewall rules list` | `flarectl f r l` |
| `flarectl firewall rules create` | `flarectl f r c` |
| `flarectl user-agents list` | `flarectl ua l` |
| `flarectl ips` | `flarectl i` |
| `flarectl user info` | `flarectl u i` |
