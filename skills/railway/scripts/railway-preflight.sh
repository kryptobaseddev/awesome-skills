#!/usr/bin/env bash
# Railway preflight check — verify CLI, auth, and project context
# Usage: railway-preflight.sh [--quiet]
#
# Exit codes:
#   0 — all checks pass
#   1 — CLI not installed
#   2 — not authenticated
#   3 — not linked to a project
#
# With --quiet, outputs JSON summary only.

set -e

QUIET=false
[[ "$1" == "--quiet" ]] && QUIET=true

errors=()
warnings=()

# 1. CLI installed
if ! command -v railway &>/dev/null; then
  errors+=("CLI not installed. Install: bash <(curl -fsSL cli.new) or npm i -g @railway/cli")
  if $QUIET; then
    echo '{"ok":false,"error":"cli_missing","message":"Railway CLI not installed"}'
  else
    echo "FAIL: Railway CLI not installed"
    echo "  Install: bash <(curl -fsSL cli.new)"
    echo "  Or: npm i -g @railway/cli"
    echo "  Or: brew install railway"
  fi
  exit 1
fi

# 2. CLI version
CLI_VERSION=$(railway --version 2>/dev/null || echo "unknown")

# 3. Authenticated
AUTH_OUTPUT=$(railway whoami --json 2>/dev/null || echo '{}')
if echo "$AUTH_OUTPUT" | grep -q '"error"' || [[ "$AUTH_OUTPUT" == "{}" ]]; then
  errors+=("Not authenticated")
  if $QUIET; then
    echo "{\"ok\":false,\"error\":\"not_authenticated\",\"version\":\"$CLI_VERSION\"}"
  else
    echo "FAIL: Not authenticated"
    echo "  Run: railway login"
  fi
  exit 2
fi

# 4. Project context
STATUS_OUTPUT=$(railway status --json 2>/dev/null || echo '{}')
PROJECT_ID=$(echo "$STATUS_OUTPUT" | grep -o '"projectId":"[^"]*"' | head -1 | cut -d'"' -f4)

if [[ -z "$PROJECT_ID" ]]; then
  warnings+=("Not linked to a project")
  LINKED=false
else
  LINKED=true
fi

# Output
if $QUIET; then
  if $LINKED; then
    echo "{\"ok\":true,\"version\":\"$CLI_VERSION\",\"linked\":true,\"projectId\":\"$PROJECT_ID\"}"
  else
    echo "{\"ok\":true,\"version\":\"$CLI_VERSION\",\"linked\":false,\"warning\":\"Not linked to a project. Run: railway link\"}"
  fi
else
  echo "Railway Preflight Check"
  echo "======================"
  echo "CLI version: $CLI_VERSION"
  echo "Authenticated: yes"
  if $LINKED; then
    echo "Project linked: yes ($PROJECT_ID)"
  else
    echo "Project linked: no (run: railway link --project <name>)"
  fi
  echo ""
  if [[ ${#warnings[@]} -gt 0 ]]; then
    echo "Warnings:"
    for w in "${warnings[@]}"; do echo "  - $w"; done
  else
    echo "All checks passed."
  fi
fi

if $LINKED; then
  exit 0
else
  exit 3
fi
