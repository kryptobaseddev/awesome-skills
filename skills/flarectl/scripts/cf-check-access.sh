#!/usr/bin/env bash
# cf-check-access.sh — Verify flarectl authentication and permissions
# Usage: bash cf-check-access.sh [zone-name]
#
# Checks:
# 1. flarectl is installed
# 2. Auth env vars are configured
# 3. Token/key is valid
# 4. Tests common permissions (zone read, user info, DNS read)

set -euo pipefail

ZONE="${1:-}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}PASS${NC}: $1"; }
fail() { echo -e "${RED}FAIL${NC}: $1"; }
warn() { echo -e "${YELLOW}WARN${NC}: $1"; }
info() { echo -e "INFO: $1"; }

echo "=== flarectl Access Check ==="
echo ""

# 1. Check flarectl installed
if command -v flarectl &>/dev/null; then
  pass "flarectl installed ($(flarectl --version 2>/dev/null || echo 'unknown version'))"
else
  fail "flarectl not found. Install: brew install flarectl"
  exit 1
fi

# 2. Check auth env vars
echo ""
echo "--- Authentication ---"
AUTH_METHOD="none"

if [[ -n "${CF_API_TOKEN:-}" ]]; then
  pass "CF_API_TOKEN is set"
  AUTH_METHOD="token"

  # Verify token via API. User-owned tokens verify at /user/tokens/verify; account-owned
  # tokens are rejected there (code 1000) and verify at /accounts/<id>/tokens/verify instead.
  if command -v curl &>/dev/null && command -v jq &>/dev/null; then
    VERIFY=$(curl -s "https://api.cloudflare.com/client/v4/user/tokens/verify" \
      -H "Authorization: Bearer $CF_API_TOKEN" 2>/dev/null || echo '{}')
    STATUS=$(echo "$VERIFY" | jq -r '.result.status // "unknown"' 2>/dev/null || echo "unknown")
    TOKEN_KIND="user-owned"
    if [[ "$STATUS" != "active" && -n "${CF_ACCOUNT_ID:-}" ]]; then
      VERIFY=$(curl -s "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/tokens/verify" \
        -H "Authorization: Bearer $CF_API_TOKEN" 2>/dev/null || echo '{}')
      STATUS=$(echo "$VERIFY" | jq -r '.result.status // "unknown"' 2>/dev/null || echo "unknown")
      TOKEN_KIND="account-owned"
    fi
    if [[ "$STATUS" == "active" ]]; then
      pass "API Token is valid and active ($TOKEN_KIND)"
    elif [[ -z "${CF_ACCOUNT_ID:-}" ]]; then
      fail "API Token verification failed (status: $STATUS)"
      echo "  If this is an account-owned token, set CF_ACCOUNT_ID and re-run (it verifies at /accounts/<id>/tokens/verify)"
    else
      fail "API Token verification failed (status: $STATUS)"
      echo "  Response: $(echo "$VERIFY" | jq -c '.messages // .errors' 2>/dev/null || echo "$VERIFY")"
    fi
  else
    warn "curl or jq not available — skipping token verification via API"
  fi
elif [[ -n "${CF_API_KEY:-}" && -n "${CF_API_EMAIL:-}" ]]; then
  pass "CF_API_KEY and CF_API_EMAIL are set"
  AUTH_METHOD="key"
  warn "Using Global API Key — this grants full account access. Consider switching to an API Token."
elif [[ -n "${CF_API_KEY:-}" ]]; then
  fail "CF_API_KEY is set but CF_API_EMAIL is missing (both required for Global API Key auth)"
  exit 1
elif [[ -n "${CF_API_EMAIL:-}" ]]; then
  fail "CF_API_EMAIL is set but CF_API_KEY is missing (both required for Global API Key auth)"
  exit 1
else
  fail "No authentication configured. Set CF_API_TOKEN or (CF_API_KEY + CF_API_EMAIL)"
  exit 1
fi

if [[ -n "${CF_ACCOUNT_ID:-}" ]]; then
  pass "CF_ACCOUNT_ID is set"
else
  info "CF_ACCOUNT_ID not set (optional — needed for account-scoped operations like zone create)"
fi

# 3. Test permissions
echo ""
echo "--- Permission Tests ---"

# Zone read
# --json is a global flag: it must come before the subcommand
if flarectl --json zone list &>/dev/null; then
  ZONE_COUNT=$(flarectl --json zone list 2>/dev/null | jq 'length' 2>/dev/null || echo "?")
  pass "Zone:Read — $ZONE_COUNT zone(s) accessible"
else
  fail "Zone:Read — cannot list zones (missing Zone:Zone:Read permission?)"
fi

# User info
if flarectl user info &>/dev/null; then
  pass "User:Read — user info accessible"
else
  warn "User:Read — cannot read user info (always fails for account-owned tokens; not needed for zone/DNS work)"
fi

# DNS read (if zone provided)
if [[ -n "$ZONE" ]]; then
  echo ""
  echo "--- Zone-Specific Tests: $ZONE ---"
  if flarectl --json dns list --zone "$ZONE" &>/dev/null; then
    RECORD_COUNT=$(flarectl --json dns list --zone "$ZONE" 2>/dev/null | jq 'length' 2>/dev/null || echo "?")
    pass "DNS:Read — $RECORD_COUNT record(s) in $ZONE"
  else
    fail "DNS:Read — cannot list DNS records for $ZONE"
  fi
else
  info "Pass a zone name as argument to test DNS access: bash cf-check-access.sh example.com"
fi

echo ""
echo "=== Check Complete ==="
