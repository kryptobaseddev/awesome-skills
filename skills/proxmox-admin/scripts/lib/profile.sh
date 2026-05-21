#!/usr/bin/env bash
# proxmox-admin / lib / profile.sh
# Shared library sourced by every pmx-* helper.
#
# Responsibilities:
#   * Locate and load the active connection profile (~/.config/proxmox-admin).
#   * Parse the YAML into shell variables WITHOUT requiring `yq`.
#   * Expose helpers: pmx_ssh, pmx_api, pmx_require, pmx_active_profile.
#   * Resolve ${ENV:VAR} secret references at read time.
#
# Source this file with:   . "$(dirname "$0")/lib/profile.sh"
#
# Conventional exit codes used across all pmx-* scripts:
#   0   success
#   2   usage / argument error (also: --help shown)
#   3   no active profile / profile not found
#   4   missing required binary (ssh, curl, etc.)
#   5   connection error (TCP / SSH / REST)
#   6   authentication error (SSH key, API token, ACL)
#   7   precondition not met (e.g. cv4pve-cli not installed)
#   1   generic runtime failure / unexpected error

set -u
set -o pipefail

PMX_CONFIG_DIR="${PMX_CONFIG_DIR:-$HOME/.config/proxmox-admin}"
PMX_PROFILE_DIR="${PMX_PROFILE_DIR:-$PMX_CONFIG_DIR/profiles}"
PMX_ACTIVE_FILE="${PMX_ACTIVE_FILE:-$PMX_CONFIG_DIR/active}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
pmx_log()  { printf '[pmx] %s\n' "$*" >&2; }
pmx_warn() { printf '[pmx][warn] %s\n' "$*" >&2; }
pmx_die()  {
  # pmx_die [<exit-code>] <message...>
  local code=1
  if [[ "${1:-}" =~ ^[0-9]+$ ]]; then code="$1"; shift; fi
  printf '[pmx][fatal] %s\n' "$*" >&2
  exit "$code"
}

# pmx_json_escape <string> — minimal JSON-string escaper for stdlib-free output.
pmx_json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}

# ---------------------------------------------------------------------------
# pmx_require <cmd>...   bail if any binary is missing.
# ---------------------------------------------------------------------------
pmx_require() {
  local missing=()
  local c
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || missing+=("$c")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    pmx_die 4 "missing required commands: ${missing[*]}"
  fi
}

# ---------------------------------------------------------------------------
# pmx_yaml_get <file> <dotted.path>   ->   prints value (empty if absent).
#
# Minimal YAML reader for the flat / 2-level structure used by the profile
# schema. Avoids a hard dep on yq. Supports:
#   * top-level scalars      e.g. "name"
#   * nested objects 1 deep  e.g. "host.address", "ssh.user"
#   * env reference          e.g. "${ENV:PMX_TOKEN_SECRET}" -> $PMX_TOKEN_SECRET
#
# Quoting: strips surrounding double or single quotes from the value.
# ---------------------------------------------------------------------------
pmx_yaml_get() {
  local file="$1" path="$2"
  local parent child val
  if [[ "$path" == *.* ]]; then
    parent="${path%%.*}"
    child="${path#*.}"
    val="$(awk -v p="$parent" -v c="$child" '
      BEGIN { in_block = 0 }
      # detect entry into the parent block: "parent:" possibly with whitespace
      $0 ~ "^" p ":[[:space:]]*$" { in_block = 1; next }
      # exit the block when we hit a new top-level key (no leading space)
      in_block && /^[A-Za-z_][A-Za-z0-9_]*:/ { in_block = 0 }
      in_block && $0 ~ "^[[:space:]]+" c ":" {
        # strip key, leading whitespace, and trailing comments
        sub("^[[:space:]]+" c ":[[:space:]]*", "", $0)
        sub("[[:space:]]+#.*$", "", $0)
        print $0
        exit
      }
    ' "$file")"
  else
    val="$(awk -v k="$path" '
      $0 ~ "^" k ":" {
        sub("^" k ":[[:space:]]*", "", $0)
        sub("[[:space:]]+#.*$", "", $0)
        print $0
        exit
      }
    ' "$file")"
  fi

  # Trim surrounding quotes.
  val="${val%\"}"; val="${val#\"}"
  val="${val%\'}"; val="${val#\'}"

  # Resolve ${ENV:NAME} references.
  if [[ "$val" =~ ^\$\{ENV:([A-Z_][A-Z0-9_]*)\}$ ]]; then
    local ref="${BASH_REMATCH[1]}"
    val="${!ref-}"
  fi

  # Expand leading ~ in identity file / known hosts paths.
  # Note: ${val#~/} would tilde-expand the pattern itself, so use ${val:2}.
  case "$val" in
    '~/'*) val="$HOME/${val:2}" ;;
    '~')   val="$HOME" ;;
  esac

  printf '%s' "$val"
}

# ---------------------------------------------------------------------------
# pmx_active_profile [<name>]
#   With no arg: prints the profile name recorded in $PMX_ACTIVE_FILE
#                (or the value of $PMX_PROFILE env var).
#   With one arg: writes that name as the new active profile.
# ---------------------------------------------------------------------------
pmx_active_profile() {
  if [ "$#" -ge 1 ]; then
    local name="$1"
    [ -f "$PMX_PROFILE_DIR/$name.yaml" ] || pmx_die 3 "no such profile: $name"
    mkdir -p "$PMX_CONFIG_DIR"
    printf '%s\n' "$name" > "$PMX_ACTIVE_FILE"
    pmx_log "active profile set to: $name"
    return 0
  fi
  if [ -n "${PMX_PROFILE:-}" ]; then
    printf '%s' "$PMX_PROFILE"; return 0
  fi
  if [ -f "$PMX_ACTIVE_FILE" ]; then
    head -n1 "$PMX_ACTIVE_FILE"
  else
    return 1
  fi
}

# ---------------------------------------------------------------------------
# pmx_load_profile [<name>]
#   Sets the following env vars from the resolved YAML:
#
#     PMX_NAME, PMX_HOST, PMX_NODE, PMX_API_PORT, PMX_SSH_PORT,
#     PMX_VERIFY_TLS, PMX_CA_BUNDLE,
#     PMX_SSH_USER, PMX_SSH_KEY, PMX_SSH_KNOWN_HOSTS,
#     PMX_SSH_STRICT, PMX_SSH_PROXY_JUMP,
#     PMX_API_USER, PMX_API_TOKEN_ID, PMX_API_TOKEN_SECRET,
#     PMX_DEFAULT_STORAGE_VM, PMX_DEFAULT_STORAGE_CT, ...
#
# Then echoes a single line summary to stderr.
# ---------------------------------------------------------------------------
pmx_load_profile() {
  local name="${1:-}"
  if [ -z "$name" ]; then
    name="$(pmx_active_profile 2>/dev/null || true)"
  fi
  [ -n "$name" ] || pmx_die 3 "no active profile. Run: scripts/pmx-onboard or set PMX_PROFILE."
  local file="$PMX_PROFILE_DIR/$name.yaml"
  [ -f "$file" ] || pmx_die 3 "profile not found: $file"

  PMX_NAME="$(pmx_yaml_get "$file" name)"
  PMX_HOST="$(pmx_yaml_get "$file" host.address)"
  PMX_NODE="$(pmx_yaml_get "$file" host.node)"
  PMX_API_PORT="$(pmx_yaml_get "$file" host.api_port)"; PMX_API_PORT="${PMX_API_PORT:-8006}"
  PMX_SSH_PORT="$(pmx_yaml_get "$file" host.ssh_port)"; PMX_SSH_PORT="${PMX_SSH_PORT:-22}"
  PMX_VERIFY_TLS="$(pmx_yaml_get "$file" host.verify_tls)"; PMX_VERIFY_TLS="${PMX_VERIFY_TLS:-false}"
  PMX_CA_BUNDLE="$(pmx_yaml_get "$file" host.ca_bundle)"

  PMX_SSH_USER="$(pmx_yaml_get "$file" ssh.user)"; PMX_SSH_USER="${PMX_SSH_USER:-root}"
  PMX_SSH_KEY="$(pmx_yaml_get "$file" ssh.identity_file)"
  PMX_SSH_KNOWN_HOSTS="$(pmx_yaml_get "$file" ssh.known_hosts_file)"
  PMX_SSH_STRICT="$(pmx_yaml_get "$file" ssh.strict_host_key_checking)"; PMX_SSH_STRICT="${PMX_SSH_STRICT:-accept-new}"
  PMX_SSH_PROXY_JUMP="$(pmx_yaml_get "$file" ssh.proxy_jump)"

  PMX_API_USER="$(pmx_yaml_get "$file" api.user)"
  PMX_API_TOKEN_ID="$(pmx_yaml_get "$file" api.token_id)"
  PMX_API_TOKEN_SECRET="$(pmx_yaml_get "$file" api.token_secret)"

  PMX_DEFAULT_STORAGE_VM="$(pmx_yaml_get "$file" defaults.storage_vm)"
  PMX_DEFAULT_STORAGE_CT="$(pmx_yaml_get "$file" defaults.storage_ct)"
  PMX_DEFAULT_STORAGE_ISO="$(pmx_yaml_get "$file" defaults.storage_iso)"
  PMX_DEFAULT_STORAGE_BACKUP="$(pmx_yaml_get "$file" defaults.storage_backup)"
  PMX_DEFAULT_BRIDGE="$(pmx_yaml_get "$file" defaults.bridge)"
  PMX_DEFAULT_CPU_TYPE="$(pmx_yaml_get "$file" defaults.cpu_type)"
  PMX_DEFAULT_SCSIHW="$(pmx_yaml_get "$file" defaults.scsihw)"
  PMX_DEFAULT_MACHINE="$(pmx_yaml_get "$file" defaults.machine)"
  PMX_DEFAULT_BIOS="$(pmx_yaml_get "$file" defaults.bios)"
  PMX_DEFAULT_OSTYPE="$(pmx_yaml_get "$file" defaults.ostype)"
  PMX_DEFAULT_CORES="$(pmx_yaml_get "$file" defaults.cores)"
  PMX_DEFAULT_MEMORY="$(pmx_yaml_get "$file" defaults.memory_mb)"
  PMX_DEFAULT_DISK="$(pmx_yaml_get "$file" defaults.disk_size_gb)"

  export PMX_NAME PMX_HOST PMX_NODE PMX_API_PORT PMX_SSH_PORT \
         PMX_VERIFY_TLS PMX_CA_BUNDLE \
         PMX_SSH_USER PMX_SSH_KEY PMX_SSH_KNOWN_HOSTS PMX_SSH_STRICT PMX_SSH_PROXY_JUMP \
         PMX_API_USER PMX_API_TOKEN_ID PMX_API_TOKEN_SECRET \
         PMX_DEFAULT_STORAGE_VM PMX_DEFAULT_STORAGE_CT PMX_DEFAULT_STORAGE_ISO \
         PMX_DEFAULT_STORAGE_BACKUP PMX_DEFAULT_BRIDGE PMX_DEFAULT_CPU_TYPE \
         PMX_DEFAULT_SCSIHW PMX_DEFAULT_MACHINE PMX_DEFAULT_BIOS \
         PMX_DEFAULT_OSTYPE PMX_DEFAULT_CORES PMX_DEFAULT_MEMORY PMX_DEFAULT_DISK

  pmx_log "profile loaded: $PMX_NAME ($PMX_SSH_USER@$PMX_HOST:$PMX_SSH_PORT)"
}

# ---------------------------------------------------------------------------
# pmx_ssh_args   -> array of SSH options for `ssh` and `scp`.
# Echoes the args on stdout, one per line, so the caller can readarray them.
# ---------------------------------------------------------------------------
pmx_ssh_args() {
  printf -- '-o\nBatchMode=yes\n'
  printf -- '-o\nStrictHostKeyChecking=%s\n' "$PMX_SSH_STRICT"
  if [ -n "${PMX_SSH_KNOWN_HOSTS:-}" ]; then
    printf -- '-o\nUserKnownHostsFile=%s\n' "$PMX_SSH_KNOWN_HOSTS"
  fi
  if [ -n "${PMX_SSH_KEY:-}" ]; then
    printf -- '-i\n%s\n' "$PMX_SSH_KEY"
    printf -- '-o\nIdentitiesOnly=yes\n'
  fi
  if [ -n "${PMX_SSH_PROXY_JUMP:-}" ]; then
    printf -- '-o\nProxyJump=%s\n' "$PMX_SSH_PROXY_JUMP"
  fi
  printf -- '-p\n%s\n' "$PMX_SSH_PORT"
}

# ---------------------------------------------------------------------------
# pmx_ssh <remote-command...>
#   Runs the given shell command on the Proxmox host. Quotes are preserved.
# ---------------------------------------------------------------------------
pmx_ssh() {
  [ -n "${PMX_HOST:-}" ] || pmx_die "profile not loaded; call pmx_load_profile first"
  local args=()
  mapfile -t args < <(pmx_ssh_args)
  ssh "${args[@]}" "$PMX_SSH_USER@$PMX_HOST" -- "$@"
}

# ---------------------------------------------------------------------------
# pmx_api <METHOD> <path> [curl-args...]
#   Calls the Proxmox REST API using the loaded token credentials.
#   <path> begins with /api2/json/...  Returns the raw JSON on stdout.
# ---------------------------------------------------------------------------
pmx_api() {
  [ -n "${PMX_HOST:-}" ] || pmx_die "profile not loaded; call pmx_load_profile first"
  [ -n "${PMX_API_USER:-}" ]         || pmx_die "no api.user in profile"
  [ -n "${PMX_API_TOKEN_ID:-}" ]     || pmx_die "no api.token_id in profile"
  [ -n "${PMX_API_TOKEN_SECRET:-}" ] || pmx_die "no api.token_secret in profile (set env or store securely)"
  local method="$1" path="$2"; shift 2
  local url="https://$PMX_HOST:$PMX_API_PORT$path"
  local auth="Authorization: PVEAPIToken=${PMX_API_USER}!${PMX_API_TOKEN_ID}=${PMX_API_TOKEN_SECRET}"
  local tls_args=()
  if [ "$PMX_VERIFY_TLS" = "true" ] || [ "$PMX_VERIFY_TLS" = "yes" ]; then
    [ -n "${PMX_CA_BUNDLE:-}" ] && tls_args+=(--cacert "$PMX_CA_BUNDLE")
  else
    tls_args+=(-k)
  fi
  curl -sS -X "$method" "${tls_args[@]}" -H "$auth" -H "Accept: application/json" "$url" "$@"
}

# ---------------------------------------------------------------------------
# pmx_target_node
#   Echoes the node name to use in API calls. Defaults to host.node when set,
#   otherwise discovers the node via the API (/nodes).
# ---------------------------------------------------------------------------
pmx_target_node() {
  if [ -n "${PMX_NODE:-}" ]; then
    printf '%s' "$PMX_NODE"; return 0
  fi
  local json
  json="$(pmx_api GET /api2/json/nodes 2>/dev/null || true)"
  printf '%s' "$json" | sed -n 's/.*"node":"\([^"]*\)".*/\1/p' | head -n1
}
