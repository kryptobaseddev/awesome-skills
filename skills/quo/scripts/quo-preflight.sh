#!/usr/bin/env bash
# quo-preflight.sh — Verify the local environment is ready for a Quo (formerly
# OpenPhone) API integration BEFORE you write code, so failures point at config,
# not bugs.
#
# Checks:
#   1. node / curl availability (for the helper scripts + a live probe)
#   2. A Quo API key in the environment (QUO_API_KEY, with OPENPHONE_API_KEY as
#      a legacy fallback), and the classic "Bearer-prefix" mistake
#   3. (optional, --probe) a live, authenticated GET /v1/phone-numbers so a real
#      401/403 vs 200 tells you whether the key actually works
#
# The Quo API authenticates with the RAW key in the Authorization header — there
# is NO "Bearer " prefix. Base URL: https://api.quo.com/v1 (api.openphone.com/v1
# is an identical legacy alias). Rate limit: 10 requests/second per key.
#
# Usage:
#   bash quo-preflight.sh            # local checks only
#   bash quo-preflight.sh --probe    # also call the live phone-numbers endpoint
#
# Exit codes: 0 ready · 2 usage · 4 missing binary · 5 network · 6 key problem
set -uo pipefail

PROBE=0
case "${1:-}" in
  --probe) PROBE=1 ;;
  -h|--help) sed -n '2,28p' "$0"; exit 2 ;;
  "") ;;
  *) echo "unknown arg: $1 (try --probe or --help)"; exit 2 ;;
esac

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }

RC=0
BASE_URL="${QUO_BASE_URL:-https://api.quo.com/v1}"

echo "Quo (OpenPhone) preflight"
echo "-------------------------"

echo "Tooling:"
command -v curl >/dev/null 2>&1 && ok "curl found" || { bad "curl not found"; RC=4; }
command -v node >/dev/null 2>&1 && ok "node found ($(node -v 2>/dev/null))" \
  || warn "node not found — verify-webhook.js / send-message.js need Node 18+"

echo "API key:"
# Prefer QUO_API_KEY; accept the legacy OPENPHONE_API_KEY so older setups work.
KEY="${QUO_API_KEY:-${OPENPHONE_API_KEY:-}}"
KEY_SRC="QUO_API_KEY"
[ -z "${QUO_API_KEY:-}" ] && [ -n "${OPENPHONE_API_KEY:-}" ] && KEY_SRC="OPENPHONE_API_KEY (legacy)"

if [ -z "$KEY" ]; then
  bad "No QUO_API_KEY (or OPENPHONE_API_KEY) in the environment"
  warn "Generate one at: Quo workspace → Settings → API (owner/admin only)"
  RC=6
else
  ok "Key found via \$$KEY_SRC (${#KEY} chars)"
  # The value must be the RAW key. A leading "Bearer " is the #1 auth mistake.
  case "$KEY" in
    Bearer\ *|bearer\ *)
      bad "Key starts with 'Bearer ' — Quo does NOT use Bearer. Store the raw key only."
      RC=6 ;;
  esac
  # API keys must not contain spaces (Quo disallows spaces in key names/values).
  case "$KEY" in
    *" "*) warn "Key contains a space — double-check you copied it intact" ;;
  esac
fi

if [ "$PROBE" = 1 ]; then
  echo "Live probe ($BASE_URL/phone-numbers):"
  if [ -z "$KEY" ]; then
    warn "skipped — no key to probe with"
  elif ! command -v curl >/dev/null 2>&1; then
    warn "skipped — curl not available"
  else
    CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
      "$BASE_URL/phone-numbers?maxResults=1" -H "Authorization: $KEY" 2>/dev/null) || {
        bad "network error reaching $BASE_URL"; exit 5; }
    case "$CODE" in
      200) ok "200 OK — key is valid and the workspace has phone numbers" ;;
      401) bad "401 Unauthorized — key missing/invalid (check for a stray Bearer prefix)"; RC=6 ;;
      403) warn "403 Forbidden — key valid but lacks permission or a setting is off" ;;
      429) warn "429 Too Many Requests — rate limited (10 req/s/key); retry with backoff" ;;
      000) bad "no HTTP response — DNS/proxy/network problem"; exit 5 ;;
      *)   warn "HTTP $CODE — unexpected; inspect the response body manually" ;;
    esac
  fi
fi

echo "-------------------------"
[ "$RC" = 0 ] && echo "Ready. Auth header = 'Authorization: <raw key>' (no Bearer). Rate limit = 10 req/s." \
             || echo "Not ready — resolve the ✗ items above (exit $RC)."
exit $RC
