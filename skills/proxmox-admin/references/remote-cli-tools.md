# Remote CLI Tools — cv4pve-cli (primary) and alternatives

This skill targets **cv4pve-cli** as the single remote CLI. It is a
kubectl-style binary from Corsinvest that talks to the Proxmox REST API,
supports context switching, and ships built-in aliases for almost every
day-to-day operation. Two other tools (`pvecontrol`, `pman`) are listed for
completeness but are not required and the skill does not ship installers
for them.

## Table of contents

1. [Why cv4pve-cli is the default](#why-cv4pve-cli-is-the-default)
2. [Install and sync workflow](#install-and-sync-workflow)
3. [How profiles map to cv4pve contexts](#how-profiles-map-to-cv4pve-contexts)
4. [Daily commands](#daily-commands)
5. [Shell completion](#shell-completion)
6. [When to reach for pvecontrol or pman (optional)](#when-to-reach-for-pvecontrol-or-pman-optional)

---

## Why cv4pve-cli is the default

- **Single binary** — no Python venv, no pipx, no LXC overhead.
- **Token-based** — uses the same API token already in our profiles.
- **Cluster-aware** — `--guest <name|id>` auto-resolves the owning node,
  so the agent never has to track which VM lives where.
- **Full API surface** — `cv4pve-cli api get|set|create|delete <path>`
  mirrors `pvesh` from a workstation.
- **300+ aliases** — `get vms`, `do start guest --guest web`,
  `top`, `events`, `cluster show`, etc.
- **JSON output** — `--output json` is deterministic and LLM-friendly.

The remaining native helpers (`pmx-ssh`, `pmx-vm`, `pmx-ct`, `pmx-backup`)
stay relevant for shell-level work that has no REST endpoint (e.g. editing
`/etc/network/interfaces`, running `pveperf`, `journalctl`).

---

## Install and sync workflow

```bash
# 1. Install the binary. Prefix is auto-selected:
#    - root or /usr/local/bin writable        → /usr/local/bin
#    - sudo available + interactive (or NOPASSWD) → /usr/local/bin (via sudo)
#    - otherwise                              → $HOME/.local/bin (no sudo)
#    Override with PMX_CV4PVE_PREFIX.
scripts/pmx-cv4pve-install
# Optional pinning / prefix override:
PMX_CV4PVE_VERSION=v8.3.0           scripts/pmx-cv4pve-install
PMX_CV4PVE_PREFIX=$HOME/.local/bin  scripts/pmx-cv4pve-install
PMX_CV4PVE_PREFIX=/usr/local/bin    scripts/pmx-cv4pve-install   # force system path

# 2. Mirror your YAML profiles into cv4pve-cli contexts (idempotent).
scripts/pmx-cv4pve-sync --activate

# 3. Verify.
cv4pve-cli config list
cv4pve-cli api get /version
```

Re-run `pmx-cv4pve-sync` whenever you add or rotate a profile.
`pmx-doctor` warns if the active profile is not the active cv4pve context.

---

## How profiles map to cv4pve contexts

| Profile field | cv4pve-cli flag |
|---------------|-----------------|
| `name` | context name |
| `host.address` | `--host` |
| `host.api_port` | `--port` |
| `host.verify_tls` | `--validate-certificate true|false` |
| `api.user!api.token_id=api.token_secret` | `--api-token <user@realm!id=uuid>` |

A profile without an API token (SSH-only profile) is **skipped** by the
sync — cv4pve-cli needs token or password auth. Use `pmx-token-create` to
provision one if missing.

---

## Daily commands

Most everything has both a long and short form. Skill helpers use the
explicit `api` form when scripted.

```bash
# Cluster overview
cv4pve-cli get vms                           # all VMs across active context
cv4pve-cli get cts                           # containers
cv4pve-cli get nodes
cv4pve-cli cluster show

# Direct REST
cv4pve-cli api get /version
cv4pve-cli api get /nodes
cv4pve-cli api get '/cluster/resources?type=vm' --output json
cv4pve-cli api set /nodes/pve01/qemu/100/config --memory 4096

# Guest auto-resolution (no need to know which node)
cv4pve-cli do start  guest --guest web
cv4pve-cli do stop   guest --guest web
cv4pve-cli do reboot guest --guest web
cv4pve-cli do console guest --guest web      # SPICE/VNC info

# Live monitoring
cv4pve-cli top                               # htop-style across cluster
cv4pve-cli events --tail

# Bulk shapes (great for the LLM)
cv4pve-cli get vms --output json | jq '.[] | select(.status=="running") | .vmid'
```

When in doubt, `cv4pve-cli <category> --help` enumerates every alias.

---

## Shell completion

```bash
# Bash
cv4pve-cli completion bash | sudo tee /etc/bash_completion.d/cv4pve-cli >/dev/null

# Zsh
mkdir -p ~/.zsh/completions
cv4pve-cli completion zsh > ~/.zsh/completions/_cv4pve-cli
# add to .zshrc:  fpath=(~/.zsh/completions $fpath); autoload -U compinit && compinit

# PowerShell (cross-platform pwsh)
cv4pve-cli completion powershell > $PROFILE.CurrentUserAllHosts
```

Completion queries the live API for VM names, storage IDs, etc. — handy
when typing interactively.

---

## When to reach for pvecontrol or pman (optional)

These are NOT installed by the skill. Use them only if you specifically
want a feature they offer that cv4pve-cli lacks.

### pvecontrol (Enix, Python)

Use when you need **smart hypervisor draining** with custom
`cpufactor` / `memoryminimum` policies during node maintenance. Install
manually:

```bash
pipx install pvecontrol     # or pip install --user pvecontrol
mkdir -p ~/.config/pvecontrol
$EDITOR ~/.config/pvecontrol/config.yaml
```

A minimal config bootstrapped from a proxmox-admin profile:

```yaml
clusters:
  homelab:
    host: <profile.host.address>
    user: <profile.api.user>
    token_name: <profile.api.token_id>
    token_value: <profile.api.token_secret>
    verify_ssl: false
    cpufactor: 1.0
    memoryminimum: 512
```

Then:

```bash
pvecontrol -c homelab vm list
pvecontrol -c homelab node evacuate pve01     # smart drain
```

### pman / proxmox-manager (TimInTech, Bash TUI)

Runs **on the Proxmox node**, not the workstation. It's a curses-style
menu wrapping `qm`/`pct`. Useful for humans inside an interactive
`ssh -t root@<node>` session — irrelevant for agent-driven ops.

To install on the node (one-time, irreversible to nothing-of-value):

```bash
scripts/pmx-ssh '
  apt-get -y install git
  git clone --depth=1 https://github.com/TimInTech/proxmox-manager /opt/proxmox-manager
  ln -sf /opt/proxmox-manager/pman /usr/local/bin/pman
'
ssh -t -i ~/.ssh/id_ed25519_proxmox root@<host> pman
```

Then forget about it unless you find yourself reaching for menus.

---

## Summary

For 99% of LLM-driven Proxmox ops:

- `cv4pve-cli` (via `pmx-cv4` or directly) for everything REST.
- `pmx-ssh` / `pmx-vm` / `pmx-ct` for shell-level work the REST API can't do.
- Profiles in `~/.config/proxmox-admin/profiles/*.yaml` are the only source
  of credentials — everything else is generated from them.
