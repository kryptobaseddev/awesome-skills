#!/usr/bin/env bash
# neon-preflight.sh — report the state of the Neon CLI install before doing real work.
#
# Answers, in one shot: is `neon` present, is it the modern 4.x CLI or a stale
# `neonctl` 2.x under a new name, does Node meet the upgrade floor, are we
# authenticated, and is there a project context in this directory.
#
# Exit codes: 0 = ready, 1 = blocking problem (not installed / not authenticated).
# Warnings alone do not fail the run, so this is safe to call at the top of a script.

set -uo pipefail

ok=0
warn=0
fail=0

say()  { printf '%s\n' "$*"; }
pass() { printf '  \033[32m✓\033[0m %s\n' "$*"; ok=$((ok+1)); }
note() { printf '  \033[33m!\033[0m %s\n' "$*"; warn=$((warn+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; fail=$((fail+1)); }

say ""
say "=== Neon CLI preflight ==="
say ""

# ── 1. Binary presence ────────────────────────────────────────────────────────
say "CLI"
neon_bin=$(command -v neon 2>/dev/null || true)
neonctl_bin=$(command -v neonctl 2>/dev/null || true)

if [[ -z "$neon_bin" ]]; then
  bad "\`neon\` not found on PATH"
  if [[ -n "$neonctl_bin" ]]; then
    note "\`neonctl\` exists at $neonctl_bin — the CLI was renamed; install the new one:"
    say  "      npm i -g neon@latest"
  else
    say  "      install with: npm i -g neon@latest   (needs Node 20.19.0+)"
  fi
  say ""
  say "Result: NOT READY"
  exit 1
fi
pass "neon found at $neon_bin"

# ── 2. Version ────────────────────────────────────────────────────────────────
version=$(neon --version 2>/dev/null | tr -d '[:space:]')
major="${version%%.*}"
if [[ -z "$version" ]]; then
  note "could not read \`neon --version\`"
elif [[ "$major" =~ ^[0-9]+$ ]] && (( major >= 4 )); then
  pass "version $version (modern CLI)"
else
  bad "version $version — this is the legacy neonctl line answering to \`neon\`"
  say  "      snapshots, functions, buckets, data-api, inspect, logs, env and link are all missing here."
  say  "      upgrade: npm uninstall -g neonctl && npm i -g neon@latest"
fi

# ── 3. The compatibility alias ────────────────────────────────────────────────
if [[ -n "$neonctl_bin" ]]; then
  neonctl_version=$(neonctl --version 2>/dev/null | tr -d '[:space:]')
  if [[ "$neonctl_version" != "$version" ]]; then
    note "\`neonctl\` ($neonctl_version) and \`neon\` ($version) are different versions"
    say  "      two packages are installed and fighting over the \`neon\` symlink."
    say  "      pick one: \`npm uninstall -g neonctl\` (then reinstall neon), or install only neonctl@latest."
  else
    pass "neonctl alias present at the same version ($neonctl_version)"
  fi
fi

# ── 4. Node floor for upgrades ────────────────────────────────────────────────
say ""
say "Runtime"
if command -v node >/dev/null 2>&1; then
  node_version=$(node -v | sed 's/^v//')
  node_major=${node_version%%.*}
  node_minor=$(printf '%s' "$node_version" | cut -d. -f2)
  node_patch=$(printf '%s' "$node_version" | cut -d. -f3)
  if (( node_major > 20 )) || { (( node_major == 20 )) && { (( node_minor > 19 )) || { (( node_minor == 19 )) && (( node_patch >= 0 )); }; }; }; then
    pass "Node $node_version meets the 20.19.0 upgrade floor"
  else
    note "Node $node_version is below 20.19.0 — the installed CLI keeps working, but upgrades will fail"
  fi
else
  note "node not found — fine if the CLI was installed as a standalone binary or via Homebrew"
fi

# ── 5. Authentication ─────────────────────────────────────────────────────────
say ""
say "Authentication"
if [[ -n "${NEON_API_KEY:-}" ]]; then
  pass "NEON_API_KEY is set (takes precedence over stored credentials)"
fi

if me_json=$(neon me --output json 2>/dev/null); then
  email=$(printf '%s' "$me_json" | sed -n 's/.*"email"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)
  pass "authenticated${email:+ as $email}"
else
  bad "not authenticated — run \`neon login\`, or export NEON_API_KEY"
fi

# credentials live at the legacy path even on 4.x; report what is actually there
for d in "${XDG_CONFIG_HOME:-$HOME/.config}/neonctl" "${XDG_CONFIG_HOME:-$HOME/.config}/neon"; do
  if [[ -f "$d/credentials.json" ]]; then
    pass "credentials at $d/credentials.json"
  fi
done

# ── 6. Project context ────────────────────────────────────────────────────────
say ""
say "Context"
ctx=""
dir=$PWD
while [[ "$dir" != "/" ]]; do
  if [[ -f "$dir/.neon" ]]; then ctx="$dir/.neon"; break; fi
  dir=$(dirname "$dir")
done

if [[ -n "$ctx" ]]; then
  pass "context file: $ctx"
  sed -n 's/.*"\(orgId\|projectId\|branch\)"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/      \1 = \2/p' "$ctx"
  [[ "$ctx" != "$PWD/.neon" ]] && note "inherited from a parent directory — confirm it points where you expect"
else
  note "no .neon context file — commands need --project-id, or run \`neon link\`"
fi

# ── 7. psql (optional) ────────────────────────────────────────────────────────
if command -v psql >/dev/null 2>&1; then
  pass "psql available (\`neon psql\` and --psql will work)"
else
  note "psql not found — only affects \`neon psql\` and --psql"
fi

say ""
if (( fail > 0 )); then
  say "Result: NOT READY — $fail blocking, $warn warning(s)"
  exit 1
fi
say "Result: READY — $ok check(s) passed${warn:+, $warn warning(s)}"
exit 0
