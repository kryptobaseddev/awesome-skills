#!/usr/bin/env bash
# nb-preflight.sh — verify everything needed to generate watermark-free images
# via the Gemini API (Nano Banana), and report gemini-cli readiness.
#
# Usage: nb-preflight.sh [--quiet]
#
# Checks (fatal):
#   python3 + curl available; an API key set (GEMINI_API_KEY / GOOGLE_API_KEY /
#   NANOBANANA_API_KEY); the key is accepted by the API and can see the GA
#   image model.
# Checks (informational):
#   gemini-cli presence/version/auth mode; nanobanana extension; NANOBANANA_MODEL.
#
# NOTE: a passing preflight does not prove billing — model metadata is readable
# by un-billed keys, which still get 429s on their first real generation
# (image models have zero free-tier quota).
#
# Exit codes:
#   0 — ready to generate
#   2 — usage error
#   4 — missing required binary (python3/curl)
#   5 — network error reaching the Gemini API
#   6 — no API key, or key rejected
#
# With --quiet, prints a single-line JSON summary on stdout instead of the report.

set -euo pipefail

QUIET=0
case "${1:-}" in
  "") ;;
  --quiet) QUIET=1 ;;
  -h|--help) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "unknown argument: $1 (usage: nb-preflight.sh [--quiet])" >&2; exit 2 ;;
esac

BASE_URL="${GEMINI_API_BASE_URL:-https://generativelanguage.googleapis.com}"
API_VERSION="${GEMINI_API_VERSION:-v1beta}"
MODEL="gemini-3.1-flash-image"

PASS=()
WARN=()

say() { [ "$QUIET" -eq 1 ] || printf '%s\n' "$1"; }

fail_json() { # code message
  if [ "$QUIET" -eq 1 ]; then
    printf '{"ok":false,"exit":%s,"error":"%s"}\n' "$1" "$2"
  else
    printf 'FAIL  %s\n' "$2"
  fi
  exit "$1"
}

# 1. Required binaries
for bin in python3 curl; do
  if command -v "$bin" >/dev/null 2>&1; then
    PASS+=("$bin available")
  else
    fail_json 4 "missing required binary: $bin"
  fi
done

# 2. API key — environment first, then ~/.gemini/.env (written by
#    nb-cli-setup.sh --set-key; also read by gemini-cli and nb-generate.py)
API_KEY="${GEMINI_API_KEY:-${GOOGLE_API_KEY:-${NANOBANANA_API_KEY:-}}}"
KEY_SOURCE="environment"
if [ -z "$API_KEY" ] && [ -f "$HOME/.gemini/.env" ]; then
  API_KEY=$(python3 - "$HOME/.gemini/.env" <<'PY'
import sys
names = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "NANOBANANA_API_KEY")
try:
    for line in open(sys.argv[1]):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if k.strip() in names and v:
            print(v)
            break
except OSError:
    pass
PY
)
  KEY_SOURCE="$HOME/.gemini/.env"
fi
if [ -n "$API_KEY" ]; then
  PASS+=("API key found ($KEY_SOURCE)")
else
  fail_json 6 "no API key: export GEMINI_API_KEY=... or store one with nb-cli-setup.sh --set-key (create at https://aistudio.google.com/apikey; image models need billing enabled — they are NOT on the free tier)"
fi

# 3. Key works against the GA image model
RESP=$(mktemp)
trap 'rm -f "$RESP"' EXIT
HTTP_CODE=$(curl -sS -o "$RESP" -w '%{http_code}' --max-time 20 \
  -H "x-goog-api-key: $API_KEY" \
  "$BASE_URL/$API_VERSION/models/$MODEL" 2>/dev/null) || fail_json 5 "network error reaching $BASE_URL"
if [ "$HTTP_CODE" = "200" ]; then
  PASS+=("key accepted; $MODEL visible")
elif [ "$HTTP_CODE" = "400" ] && grep -q -e 'API_KEY_INVALID' -e 'API key not valid' "$RESP"; then
  # Google rejects bad keys with 400 API_KEY_INVALID, not 401/403
  fail_json 6 "API key rejected (HTTP 400 API_KEY_INVALID) — regenerate at https://aistudio.google.com/apikey"
elif [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  fail_json 6 "API key rejected (HTTP $HTTP_CODE) — regenerate at https://aistudio.google.com/apikey"
elif [ "$HTTP_CODE" = "404" ]; then
  WARN+=("model $MODEL not visible to this key (HTTP 404) — key may be scoped to an old API version")
else
  WARN+=("unexpected HTTP $HTTP_CODE probing $MODEL — generation may still work")
fi

# 4. gemini-cli (optional path — informational only)
GCLI_VERSION=""
GCLI_AUTH=""
EXT_INSTALLED="false"
if command -v gemini >/dev/null 2>&1; then
  GCLI_VERSION=$(gemini --version 2>/dev/null | head -1 || true)
  PASS+=("gemini-cli $GCLI_VERSION installed")
  SETTINGS="$HOME/.gemini/settings.json"
  if [ -f "$SETTINGS" ]; then
    GCLI_AUTH=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('security',{}).get('auth',{}).get('selectedType',''))" "$SETTINGS" 2>/dev/null || true)
    case "$GCLI_AUTH" in
      oauth-personal|oauth*)
        WARN+=("gemini-cli auth is '$GCLI_AUTH' — consumer OAuth stops working 2026-06-18 (Antigravity migration), and image generation needs a billed API key anyway. Run nb-cli-setup.sh") ;;
      gemini-api-key)
        PASS+=("gemini-cli auth uses API key") ;;
      *)
        WARN+=("gemini-cli auth type: '${GCLI_AUTH:-unset}'") ;;
    esac
  fi
  EXT_LIST=$(gemini extensions list 2>/dev/null || true)
  if grep -qi nanobanana <<<"$EXT_LIST"; then
    EXT_INSTALLED="true"
    PASS+=("nanobanana extension installed")
    case "${NANOBANANA_MODEL:-}" in
      "")          WARN+=("NANOBANANA_MODEL unset — the extension defaults to a deprecated -preview model (shut down 2026-06-25). Run nb-cli-setup.sh") ;;
      *-preview)   WARN+=("NANOBANANA_MODEL='$NANOBANANA_MODEL' is a deprecated preview id (shut down 2026-06-25) — switch to gemini-3.1-flash-image or gemini-3-pro-image") ;;
      *)           PASS+=("NANOBANANA_MODEL=$NANOBANANA_MODEL") ;;
    esac
  else
    WARN+=("nanobanana extension not installed (optional — only needed for the gemini-cli path; run nb-cli-setup.sh)")
  fi
else
  WARN+=("gemini-cli not installed (optional — direct API via nb-generate.py works without it)")
fi

# Report
if [ "$QUIET" -eq 1 ]; then
  python3 - "$GCLI_VERSION" "$GCLI_AUTH" "$EXT_INSTALLED" <<'PY' "${WARN[@]:-}"
import json, sys
gcli, auth, ext = sys.argv[1], sys.argv[2], sys.argv[3]
warns = [w for w in sys.argv[4:] if w]
print(json.dumps({"ok": True, "exit": 0, "api_key": True,
                  "gemini_cli": gcli or None, "gemini_cli_auth": auth or None,
                  "nanobanana_extension": ext == "true", "warnings": warns}))
PY
else
  for p in "${PASS[@]}"; do printf 'OK    %s\n' "$p"; done
  for w in "${WARN[@]:-}"; do [ -n "$w" ] && printf 'WARN  %s\n' "$w"; done
  say "ready: generate with scripts/nb-generate.py"
  say "note: preflight cannot verify billing — an un-billed key still 429s on first generation"
fi
exit 0
