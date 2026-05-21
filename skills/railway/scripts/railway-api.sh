#!/usr/bin/env bash
# Railway GraphQL API helper
# Usage: railway-api.sh '<graphql-query>' ['<variables-json>']
#
# Reads the Railway API token from ~/.railway/config.json (set by `railway login`).
# Falls back to RAILWAY_TOKEN environment variable for CI/CD environments.

set -e

if ! command -v jq &>/dev/null; then
  echo '{"error": "jq not installed. Install with: brew install jq (macOS) or apt install jq (Linux)"}'
  exit 1
fi

# Resolve token: env var first (CI), then config file (local dev)
TOKEN="${RAILWAY_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  CONFIG_FILE="$HOME/.railway/config.json"
  if [[ ! -f "$CONFIG_FILE" ]]; then
    echo '{"error": "Railway config not found and RAILWAY_TOKEN not set. Run: railway login"}'
    exit 1
  fi
  TOKEN=$(jq -r '.user.token' "$CONFIG_FILE")
fi

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
  echo '{"error": "No Railway token found. Run: railway login or set RAILWAY_TOKEN"}'
  exit 1
fi

if [[ -z "$1" ]]; then
  echo '{"error": "No query provided. Usage: railway-api.sh '\''<query>'\'' ['\''<variables>'\'']"}'
  exit 1
fi

# Build payload with query and optional variables
if [[ -n "$2" ]]; then
  PAYLOAD=$(jq -n --arg q "$1" --argjson v "$2" '{query: $q, variables: $v}')
else
  PAYLOAD=$(jq -n --arg q "$1" '{query: $q}')
fi

curl -s https://backboard.railway.com/graphql/v2 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"
