#!/usr/bin/env bash
# nb-cli-setup.sh — make gemini-cli image generation production-safe.
#
# Installs/updates the nanobanana extension, pins NANOBANANA_MODEL to a GA
# model id (the extension's built-in default is a deprecated -preview id that
# shuts down 2026-06-25), and audits the auth mode (consumer OAuth stops
# working 2026-06-18; image generation requires a billed API key regardless).
#
# Usage: nb-cli-setup.sh [--model flash|pro] [--fix-auth] [--dry-run]
#
#   --model flash   pin gemini-3.1-flash-image (default — fast, cheap)
#   --model pro     pin gemini-3-pro-image (highest fidelity, best text)
#   --fix-auth      set security.auth.selectedType=gemini-api-key in
#                   ~/.gemini/settings.json (backs up the file first)
#   --dry-run       print what would change without changing it
#
# Exit codes: 0 ok | 2 usage | 4 gemini-cli not installed | 1 failure

set -euo pipefail

MODEL_CHOICE="flash"
FIX_AUTH=0
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --model)
      [ $# -ge 2 ] || { echo "--model needs a value (flash|pro)" >&2; exit 2; }
      MODEL_CHOICE="$2"; shift 2 ;;
    --fix-auth) FIX_AUTH=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$MODEL_CHOICE" in
  flash) MODEL="gemini-3.1-flash-image" ;;
  pro)   MODEL="gemini-3-pro-image" ;;
  *) echo "--model must be flash or pro (got '$MODEL_CHOICE')" >&2; exit 2 ;;
esac

command -v gemini >/dev/null 2>&1 || {
  echo "gemini-cli not installed. Install: npm install -g @google/gemini-cli" >&2
  exit 4
}

run() {
  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] would execute: $*" >&2
  else
    "$@"
  fi
}

# 1. Extension install/update
EXT_LIST=$(gemini extensions list 2>/dev/null || true)
if grep -qi nanobanana <<<"$EXT_LIST"; then
  echo "nanobanana extension present — checking for updates"
  run gemini extensions update nanobanana || echo "WARN: extension update failed (non-fatal)" >&2
else
  echo "installing nanobanana extension"
  run gemini extensions install https://github.com/gemini-cli-extensions/nanobanana
fi

# 2. Pin the GA model in ~/.gemini/.env (gemini-cli loads it; overrides the
#    extension's deprecated preview default)
ENV_FILE="$HOME/.gemini/.env"
if [ "$DRY" -eq 1 ]; then
  echo "[dry-run] would set NANOBANANA_MODEL=$MODEL in $ENV_FILE" >&2
else
  mkdir -p "$HOME/.gemini"
  touch "$ENV_FILE"
  if grep -q '^NANOBANANA_MODEL=' "$ENV_FILE"; then
    sed -i.bak "s|^NANOBANANA_MODEL=.*|NANOBANANA_MODEL=$MODEL|" "$ENV_FILE"
  else
    printf 'NANOBANANA_MODEL=%s\n' "$MODEL" >>"$ENV_FILE"
  fi
  echo "pinned NANOBANANA_MODEL=$MODEL in $ENV_FILE"
  echo "  (also export it in your shell profile if you script gemini outside the CLI)"
fi

# 3. Auth audit
SETTINGS="$HOME/.gemini/settings.json"
AUTH_TYPE=""
[ -f "$SETTINGS" ] && AUTH_TYPE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('security',{}).get('auth',{}).get('selectedType',''))" "$SETTINGS" 2>/dev/null || true)
if [ "$AUTH_TYPE" = "gemini-api-key" ]; then
  echo "auth: gemini-api-key (good)"
elif [ "$FIX_AUTH" -eq 1 ]; then
  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] would set security.auth.selectedType=gemini-api-key in $SETTINGS (backup first)" >&2
  else
    cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)" 2>/dev/null || true
    python3 - "$SETTINGS" <<'PY'
import json, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except FileNotFoundError:
    data = {}
except json.JSONDecodeError as err:
    print(f"ERROR: {path} is not valid JSON ({err}) — fix it by hand "
          f"(a backup was just saved next to it)", file=sys.stderr)
    sys.exit(1)
data.setdefault("security", {}).setdefault("auth", {})["selectedType"] = "gemini-api-key"
json.dump(data, open(path, "w"), indent=2)
PY
    echo "auth switched to gemini-api-key (backup saved). Ensure GEMINI_API_KEY is exported."
  fi
else
  echo "WARN: gemini-cli auth is '${AUTH_TYPE:-unset}', not 'gemini-api-key'." >&2
  echo "      Consumer OAuth stops working 2026-06-18, and image generation needs a" >&2
  echo "      billed API key in any case. Re-run with --fix-auth to switch (and" >&2
  echo "      export GEMINI_API_KEY first)." >&2
fi

# 4. Key presence reminder
if [ -z "${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}${NANOBANANA_API_KEY:-}" ]; then
  echo "WARN: no API key in environment. Create one at https://aistudio.google.com/apikey" >&2
  echo "      (billing/Tier 1 required for image models) and: export GEMINI_API_KEY=..." >&2
fi

echo "done. Smoke test:  gemini --yolo '/generate a red apple on a white table'"
