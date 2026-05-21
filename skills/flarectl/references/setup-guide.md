# flarectl Setup & Onboarding Guide

## Installation

### Homebrew (macOS and Linux)
```bash
brew install flarectl
```

### Go Install (requires Go 1.22+)
```bash
go install github.com/cloudflare/cloudflare-go/cmd/flarectl@latest
```

### Verify
```bash
flarectl --version
```

## Authentication Setup

### Option 1: API Token (Recommended)

API Tokens are scoped to specific permissions — safer and preferred.

**Create a token:**
1. Go to Cloudflare Dashboard → My Profile → API Tokens
2. Click "Create Token"
3. Choose a template or create custom with specific permissions
4. Copy the token (shown only once)

**Configure:**
```bash
export CF_API_TOKEN="your-api-token-here"
```

Add to shell profile (`~/.bashrc`, `~/.zshrc`, or `~/.profile`) for persistence:
```bash
echo 'export CF_API_TOKEN="your-api-token-here"' >> ~/.bashrc
source ~/.bashrc
```

### Option 2: Global API Key (Legacy — NOT recommended)

The Global API Key grants full access to everything in the account. Use only when API Tokens are not supported.

**Find your Global API Key:**
1. Go to Cloudflare Dashboard → My Profile → API Tokens
2. Scroll down to "Global API Key"
3. Click "View" and confirm

**Configure:**
```bash
export CF_API_KEY="your-global-api-key"
export CF_API_EMAIL="your-email@example.com"
```

### Comparison

| | API Token | Global API Key |
|---|---|---|
| **Access** | Scoped to specific permissions | Full access to entire account |
| **Security** | Safer — limited blast radius | Dangerous — full account control |
| **Revocable** | Individual tokens can be revoked | Revoking requires regeneration |
| **Multiple** | Create many tokens for different uses | One key per account |
| **Audit** | Per-token activity logs | Single key, harder to trace |
| **Env vars** | `CF_API_TOKEN` | `CF_API_KEY` + `CF_API_EMAIL` |
| **Where to find** | Create Token button | Profile → API Tokens → scroll down → "Global API Key" → View |

### Authentication Precedence

flarectl checks in this order:
1. If `CF_API_TOKEN` is set and non-empty → uses API Token auth exclusively
2. If `CF_API_TOKEN` is unset → requires both `CF_API_KEY` and `CF_API_EMAIL`
3. If neither → exits with: `"No CF_API_KEY or CF_API_TOKEN environment set"`

### Optional: Account ID

```bash
export CF_ACCOUNT_ID="your-account-id"
```

Or pass per-command: `--account-id <id>`. Required for account-scoped operations like `zone create`.

### Important: flarectl vs Wrangler Env Vars

These are NOT interchangeable:

| Tool | Token Var | Key Var | Email Var |
|------|-----------|---------|-----------|
| flarectl | `CF_API_TOKEN` | `CF_API_KEY` | `CF_API_EMAIL` |
| Wrangler | `CLOUDFLARE_API_TOKEN` | `CLOUDFLARE_API_KEY` | `CLOUDFLARE_EMAIL` |

## Verifying Setup

```bash
# Test authentication works
flarectl user info

# Test zone access
flarectl zone list

# Verify API Token validity (API Token only)
curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq .
```

## Recommended Token Permissions

For general flarectl usage, create an API Token with:

- **Zone: Zone: Read** — list and inspect zones
- **Zone: Zone: Edit** — create/delete zones
- **Zone: DNS: Read** — list DNS records
- **Zone: DNS: Edit** — create/update/delete DNS records
- **Zone: Cache Purge: Purge** — purge cache
- **Zone: Firewall Services: Read** — list firewall rules
- **Zone: Firewall Services: Edit** — manage firewall rules

Scope the token to specific zones when possible for tighter security.
