#!/usr/bin/env bash
# nb-cli-setup.sh — store the Gemini API key and/or set up gemini-cli image
# generation (nanobanana extension + GA model pin + auth audit).
#
# Usage: nb-cli-setup.sh [--set-key KEY|-] [--model flash|pro] [--fix-auth] [--full] [--dry-run]
#
#   --set-key KEY|-  store GEMINI_API_KEY in ~/.gemini/.env (chmod 600) and
#                    validate it against the API. Use '-' to paste the key
#                    with hidden input (never lands in shell history).
#                    ON ITS OWN this does ONLY key storage — no extension
#                    install, no other prompts. NEVER put keys in the skill
#                    folder — it is a git-tracked directory.
#   --model flash    pin gemini-3.1-flash-image (default — fast, cheap)
#   --model pro      pin gemini-3-pro-image (highest fidelity, best text)
#   --fix-auth       set security.auth.selectedType=gemini-api-key in
#                    ~/.gemini/settings.json (backs up the file first)
#   --full           run everything (key if given + extension + model + auth)
#   --dry-run        print what would change without changing it
#
# With no flags: full gemini-cli setup (extension + model pin + auth audit).
# NOTE: the extension install is INTERACTIVE (Google shows a consent prompt
# and a key wizard) — run it in a real terminal, not from a headless agent.
#
# Exit codes: 0 ok | 2 usage | 4 gemini-cli not installed | 1 failure

set -euo pipefail

MODEL_CHOICE="flash"
MODEL_EXPLICIT=0
FIX_AUTH=0
FULL=0
DRY=0
NEW_KEY=""
KEY_GIVEN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --model)
      [ $# -ge 2 ] || { echo "--model needs a value (flash|pro)" >&2; exit 2; }
      MODEL_CHOICE="$2"; MODEL_EXPLICIT=1; shift 2 ;;
    --set-key)
      [ $# -ge 2 ] || { echo "--set-key needs a value (or '-' for stdin)" >&2; exit 2; }
      NEW_KEY="$2"; KEY_GIVEN=1; shift 2 ;;
    --fix-auth) FIX_AUTH=1; shift ;;
    --full) FULL=1; shift ;;
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

# --set-key alone = key storage only; combine with --full/--model/--fix-auth
# to also run setup steps.
DO_SETUP=1
if [ "$KEY_GIVEN" -eq 1 ] && [ "$FULL" -eq 0 ] && [ "$MODEL_EXPLICIT" -eq 0 ] && [ "$FIX_AUTH" -eq 0 ]; then
  DO_SETUP=0
fi

if [ "$NEW_KEY" = "-" ]; then
  if [ -t 0 ]; then printf 'Paste API key (input hidden): ' >&2; stty -echo; fi
  IFS= read -r NEW_KEY || true
  if [ -t 0 ]; then stty echo; printf '\n' >&2; fi
  [ -n "$NEW_KEY" ] || { echo "no key received on stdin" >&2; exit 2; }
fi

ENV_FILE="$HOME/.gemini/.env"
set_env_var() { # name value
  mkdir -p "$HOME/.gemini"
  touch "$ENV_FILE"
  if grep -q "^$1=" "$ENV_FILE"; then
    sed -i.bak "s|^$1=.*|$1=$2|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$1" "$2" >>"$ENV_FILE"
  fi
  chmod 600 "$ENV_FILE"  # the file may hold an API key
}

run() {
  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] would execute: $*" >&2
  else
    "$@"
  fi
}

# 1. Store + validate the API key
if [ "$KEY_GIVEN" -eq 1 ]; then
  if [ "$DRY" -eq 1 ]; then
    echo "[dry-run] would store GEMINI_API_KEY in $ENV_FILE (chmod 600)" >&2
  else
    set_env_var GEMINI_API_KEY "$NEW_KEY"
    echo "✓ stored GEMINI_API_KEY in $ENV_FILE (chmod 600)"
    if command -v curl >/dev/null 2>&1; then
      BASE_URL="${GEMINI_API_BASE_URL:-https://generativelanguage.googleapis.com}"
      HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 \
        -H "x-goog-api-key: $NEW_KEY" \
        "$BASE_URL/${GEMINI_API_VERSION:-v1beta}/models/gemini-3.1-flash-image" 2>/dev/null || echo "000")
      case "$HTTP_CODE" in
        200) echo "✓ key validated against the Gemini API" ;;
        000) echo "? could not reach the API to validate the key (offline?) — stored anyway" ;;
        *)   echo "✗ WARNING: the API rejected this key (HTTP $HTTP_CODE) — regenerate at https://aistudio.google.com/apikey" >&2 ;;
      esac
    fi
  fi
  if [ "$DO_SETUP" -eq 0 ]; then
    echo ""
    echo "Done — the direct API path is ready:"
    echo "  bash \"$(dirname "$0")/nb-preflight.sh\"        # verify everything"
    echo "  python3 \"$(dirname "$0")/nb-generate.py\" \"a red apple\" --open"
    echo ""
    echo "Optional gemini-cli extension setup (interactive): $0 --full"
    exit 0
  fi
fi

command -v gemini >/dev/null 2>&1 || {
  if [ "$KEY_GIVEN" -eq 1 ]; then
    echo "gemini-cli not installed — key stored; skipped extension/model/auth setup" >&2
    echo "(the direct API path via nb-generate.py works without gemini-cli;" >&2
    echo " install later with: npm install -g @google/gemini-cli)" >&2
    exit 0
  fi
  echo "gemini-cli not installed. Install: npm install -g @google/gemini-cli" >&2
  exit 4
}

# 2. Extension install/update.
#    NOTE: `gemini extensions list` prints to STDERR in gemini-cli >= 0.46,
#    so capture both streams — and trust the install dir as ground truth.
EXT_LIST=$(gemini extensions list 2>&1 || true)
if grep -qi nanobanana <<<"$EXT_LIST" || [ -d "$HOME/.gemini/extensions/nanobanana" ]; then
  echo "nanobanana extension present — checking for updates"
  run gemini extensions update nanobanana || echo "WARN: extension update failed (non-fatal)" >&2
elif [ ! -t 0 ] && [ "$DRY" -eq 0 ]; then
  echo "SKIP: extension install needs an interactive terminal (Google shows a" >&2
  echo "      consent prompt). Run this yourself:" >&2
  echo "        gemini extensions install https://github.com/gemini-cli-extensions/nanobanana" >&2
else
  echo "installing nanobanana extension (interactive — answer the consent prompt)"
  run gemini extensions install https://github.com/gemini-cli-extensions/nanobanana
fi

# 2b. Pin the GA model in ~/.gemini/.env (gemini-cli loads it; overrides the
#     extension's deprecated preview default)
if [ "$DRY" -eq 1 ]; then
  echo "[dry-run] would set NANOBANANA_MODEL=$MODEL in $ENV_FILE" >&2
else
  set_env_var NANOBANANA_MODEL "$MODEL"
  echo "✓ pinned NANOBANANA_MODEL=$MODEL in $ENV_FILE"
fi

# 3. Auth audit
SETTINGS="$HOME/.gemini/settings.json"
AUTH_TYPE=""
[ -f "$SETTINGS" ] && AUTH_TYPE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('security',{}).get('auth',{}).get('selectedType',''))" "$SETTINGS" 2>/dev/null || true)
if [ "$AUTH_TYPE" = "gemini-api-key" ]; then
  echo "✓ auth: gemini-api-key"
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
    echo "✓ auth switched to gemini-api-key (backup saved)"
  fi
else
  echo "WARN: gemini-cli auth is '${AUTH_TYPE:-unset}', not 'gemini-api-key'." >&2
  echo "      Consumer OAuth stops working 2026-06-18. Fix: $0 --fix-auth" >&2
fi

# 4. Key presence reminder (env, key file, or just stored above)
HAVE_KEY="${GEMINI_API_KEY:-}${GOOGLE_API_KEY:-}${NANOBANANA_API_KEY:-}$NEW_KEY"
if [ -z "$HAVE_KEY" ] && [ -f "$ENV_FILE" ] && grep -qE '^(GEMINI|GOOGLE|NANOBANANA)_API_KEY=.+' "$ENV_FILE"; then
  HAVE_KEY="file"
fi
if [ -z "$HAVE_KEY" ]; then
  echo "WARN: no API key found. Create one at https://aistudio.google.com/apikey" >&2
  echo "      (billing/Tier 1 required for image models), then: $0 --set-key -" >&2
fi

echo ""
echo "done. Smoke test (costs ~\$0.05):  gemini --yolo '/generate a red apple on a white table'"
