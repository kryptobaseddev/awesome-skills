#!/usr/bin/env bash
# moonpay-preflight.sh — Verify the local environment is ready for a MoonPay
# integration before you write code, so failures point at config, not bugs.
#
# Checks:
#   1. node / python3 / curl availability (for signing + verification helpers)
#   2. MoonPay keys in the environment, with prefix + test/live consistency
#   3. (optional, --probe) live connectivity to the MoonPay widget API
#
# Keys it looks for (any subset; integrations rarely need all three):
#   MOONPAY_PUBLISHABLE_KEY   pk_test_… / pk_live_…   (safe in the browser)
#   MOONPAY_SECRET_KEY        sk_test_… / sk_live_…   (server-only: URL signing, server API)
#   MOONPAY_WEBHOOK_KEY       webhook signing key from dashboard → Developers
#
# Usage:
#   bash moonpay-preflight.sh            # local checks only
#   bash moonpay-preflight.sh --probe    # also curl the public currencies endpoint
#
# Exit codes: 0 ready · 2 usage · 4 missing binary · 5 network · 6 key problem
set -uo pipefail

PROBE=0
[ "${1:-}" = "--probe" ] && PROBE=1
[ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && { sed -n '2,20p' "$0"; exit 2; }

ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; }

RC=0
ENV=""   # tracks test vs live to flag mixed keys

echo "MoonPay preflight"
echo "-----------------"

echo "Tooling:"
for bin in curl; do
  command -v "$bin" >/dev/null 2>&1 && ok "$bin found" || { bad "$bin not found"; RC=4; }
done
command -v node    >/dev/null 2>&1 && ok "node found ($(node -v 2>/dev/null))"   || warn "node not found — sign-url.js / verify-webhook.js need it"
command -v python3 >/dev/null 2>&1 && ok "python3 found ($(python3 -V 2>&1))"     || warn "python3 not found — sign_url.py / verify_webhook.py need it"

# --- key checks -------------------------------------------------------------
check_key() {
  local name="$1" val="$2" want_prefix="$3"
  if [ -z "$val" ]; then
    warn "$name not set"
    return
  fi
  if [[ "$val" == ${want_prefix}test_* ]]; then
    ok "$name set (sandbox / test)"
    [ -z "$ENV" ] && ENV=test
    [ "$ENV" = live ] && { bad "$name is TEST but another key is LIVE — do not mix environments"; RC=6; }
  elif [[ "$val" == ${want_prefix}live_* ]]; then
    ok "$name set (production / live)"
    [ -z "$ENV" ] && ENV=live
    [ "$ENV" = test ] && { bad "$name is LIVE but another key is TEST — do not mix environments"; RC=6; }
  else
    bad "$name does not start with ${want_prefix}test_ / ${want_prefix}live_ — wrong key type?"
    RC=6
  fi
}

echo "Keys:"
check_key "MOONPAY_PUBLISHABLE_KEY" "${MOONPAY_PUBLISHABLE_KEY:-}" "pk_"
check_key "MOONPAY_SECRET_KEY"      "${MOONPAY_SECRET_KEY:-}"      "sk_"
if [ -n "${MOONPAY_WEBHOOK_KEY:-}" ]; then ok "MOONPAY_WEBHOOK_KEY set"; else warn "MOONPAY_WEBHOOK_KEY not set (needed only if you consume webhooks)"; fi

# Guard against the classic, dangerous mistake.
case "${MOONPAY_PUBLISHABLE_FRONTEND:-}" in
  sk_*) bad "A secret key (sk_…) appears in a frontend-exposed var — secret keys must stay server-side"; RC=6 ;;
esac

# --- optional live probe ----------------------------------------------------
if [ "$PROBE" = 1 ]; then
  echo "Connectivity:"
  if command -v curl >/dev/null 2>&1; then
    CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://api.moonpay.com/v3/currencies" 2>/dev/null)
    if [ "$CODE" = "200" ]; then
      ok "widget API reachable (GET /v3/currencies → 200)"
    elif [ -z "$CODE" ] || [ "$CODE" = "000" ]; then
      bad "could not reach api.moonpay.com (network/DNS/proxy?)"; RC=5
    else
      warn "api.moonpay.com responded HTTP $CODE"
    fi
  else
    warn "curl missing — skipping probe"
  fi
fi

echo "-----------------"
if [ "$RC" = 0 ]; then
  echo "Ready. Note: preflight validates key FORMAT, not validity — the first signed"
  echo "request (or a 401) is what confirms a key is real and enabled."
else
  echo "Issues found (exit $RC). Fix the ✗ items above."
fi
exit $RC
