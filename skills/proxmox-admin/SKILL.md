---
name: proxmox-admin
description: Use this skill to administer a Proxmox VE 8.x/9.x host, node, or cluster remotely — provisioning, day-2 ops, troubleshooting, hardening, IaC, migration off VMware/ESXi. Covers KVM VMs (qm), LXC containers (pct; OCI in 9.1+), storage (pvesm; ZFS, LVM-thin, NFS, Ceph), networking and SDN (zones, VNets, Fabrics in 9.0+, BGP/WireGuard in 9.2+), clustering and HA (pvecm, ha-manager, Dynamic Load Balancer in 9.2+), backup/restore (vzdump, Proxmox Backup Server), API tokens (pveum), firewall and security, and IaC (Terraform bpg/Telmate, Ansible). Onboards a YAML connection profile (SSH key + API token + defaults) under ~/.config/proxmox-admin/ and drives ops via bundled SSH/REST helpers or cv4pve-cli. Trigger even when the user does not say "Proxmox" — e.g. "spin up a VM on my homelab", "the LXC container is OOMing", "web UI at port 8006", "vCenter alternative", ProxMox, PVE, PBS, ProxLB, PegaProx, vmbr0, vmid, cloud-init, GPU passthrough, ZFS pool, cluster quorum, qm, pct, pvesh.
license: MIT
metadata:
  author: github.com/kryptobaseddev
  version: "1.2.0"
  last_updated: "2026-05-22 17:00:00"
  compatibility: Requires SSH client, curl, and a POSIX shell (bash 3.2+) on the workstation; Linux, macOS, and Windows via Git Bash/WSL all supported. The Proxmox host must be PVE 8.0+ and reachable from the workstation. Optionally uses cv4pve-cli (auto-installed via scripts/pmx-cv4pve-install). No agent or extra package needed on the Proxmox node itself.
allowed-tools: Bash Read Write Edit Glob Grep
---

# Proxmox VE Administration

## Overview

This skill drives Proxmox VE 8.x/9.x **remotely** from the user's workstation.
It maintains a per-instance **connection profile** (SSH credentials + API
token + defaults). Every helper script reads the active profile, so the
agent never needs to ask the user for credentials twice.

The profile can live in either of two places:

1. **A project folder** that you own — recommended. Auto-detected when a
   `.proxmox-admin/` directory is found in `$PWD` or any ancestor. Lets
   you version-control profiles, inventory, decisions, and runbooks
   together. Scaffold with `scripts/pmx-init`. See
   [project-folder.md](references/project-folder.md).
2. **`~/.config/proxmox-admin/`** — the historical default. Used when no
   project folder is detected. Backwards compatible with all prior versions.

Two execution paths run side by side:

1. **SSH + curl helpers** (`scripts/pmx-*`) — always available, even with
   only an SSH key. Required for shell-level ops with no REST equivalent.
2. **cv4pve-cli** (`scripts/pmx-cv4`) — optional fast path. Single binary,
   kubectl-style contexts, full REST coverage. Recommended.

Profiles are the canonical source of truth. `pmx-cv4pve-sync` mirrors them
into cv4pve-cli contexts so the user never duplicates credentials.

## Decision tree — start here

```
Is there an active profile?
  (.proxmox-admin/active in cwd or ancestor, OR ~/.config/proxmox-admin/active)
├── NO  →  For a single-throwaway profile: read references/onboarding.md, run scripts/pmx-onboard.
│           For anything you want to keep:  run scripts/pmx-init <dir>, then pmx-onboard from inside.
│           See references/project-folder.md for the recommended pattern.
└── YES →  Run scripts/pmx-doctor to confirm reachability.
          ├── Any check fails       → references/troubleshooting.md
          └── All checks pass       → Pick the task lane below.
```

### Task lanes

| User intent | Primary helper | Deep reference |
|-------------|----------------|----------------|
| Provision / manage a VM | `scripts/pmx-vm` or `pmx-cv4 do start guest --guest X` | [vm-management.md](references/vm-management.md) |
| Provision / manage an LXC container | `scripts/pmx-ct` | [container-management.md](references/container-management.md) |
| Storage (ZFS, LVM-thin, NFS, Ceph) | `scripts/pmx-storage` | [storage.md](references/storage.md) |
| Networking / SDN (zones, VNets, Fabrics, BGP) | `scripts/pmx-ssh 'pvesh ...'` | [networking-sdn.md](references/networking-sdn.md) |
| Cluster, HA, quorum, dynamic load balancer | `scripts/pmx-cluster` | [cluster-ha.md](references/cluster-ha.md) |
| Backups, restore, PBS | `scripts/pmx-backup` | [backup-pbs.md](references/backup-pbs.md) |
| API tokens, roles, ACLs | `scripts/pmx-token-create` | [api-tokens.md](references/api-tokens.md) |
| Security hardening | (multiple) | [security-hardening.md](references/security-hardening.md) |
| Terraform / Ansible / IaC | n/a (delegate to provider) | [iac-terraform-ansible.md](references/iac-terraform-ansible.md) |
| PegaProx / multi-cluster orchestration | n/a (community tool) | [pegaprox.md](references/pegaprox.md) |
| Compare or install remote CLIs | `scripts/pmx-cv4pve-install` | [remote-cli-tools.md](references/remote-cli-tools.md) |
| Scaffold a project folder for this skill | `scripts/pmx-init` | [project-folder.md](references/project-folder.md) |
| Capture live state into diffable markdown | `scripts/pmx-inventory snapshot` | [project-folder.md](references/project-folder.md) |
| Look up any CLI flag fast | — | [cli-cheat-sheet.md](references/cli-cheat-sheet.md) |
| Anything broken | `scripts/pmx-doctor` | [troubleshooting.md](references/troubleshooting.md) |

## Project layout (recommended)

For anything beyond a single throwaway profile, scaffold a **project
folder** that holds connection profiles, inventory, decisions, and
runbooks together in version control:

```bash
mkdir my-proxmox-project && cd my-proxmox-project
~/.claude/skills/proxmox-admin/scripts/pmx-init
```

The skill auto-detects `.proxmox-admin/` in `$PWD` or any ancestor and
uses it as the config root. Falls back to `~/.config/proxmox-admin/` if
no project folder is found — backwards compatible with prior versions.

Full layout, secret-handling conventions, cross-OS notes, and migration
path from `~/.config/`: **[references/project-folder.md](references/project-folder.md)**.

## Onboarding workflow (first run)

Before any other action, if no profile exists yet:

```bash
# (Recommended) scaffold a project folder first
scripts/pmx-init <project-dir>
cd <project-dir>
cp secrets/env.sh.example secrets/env.sh
$EDITOR secrets/env.sh                  # fill in the token secret(s) later

# Profile creation + verification
scripts/pmx-onboard            # interactive wizard, writes 0600 YAML
scripts/pmx-doctor             # verifies SSH + REST reachability
scripts/pmx-inventory snapshot # capture initial inventory as diffable markdown
scripts/pmx-cv4pve-install     # optional but recommended
scripts/pmx-cv4pve-sync --activate
```

Full prerequisites and the discovery commands to gather the inputs the
wizard asks for: **[references/onboarding.md](references/onboarding.md)**.

If the user has no API token yet, the wizard can run without one; then:

```bash
scripts/pmx-token-create skill /      # creates user, role, ACL, token
# Capture the secret it prints once; re-run pmx-onboard to embed it
```

## Daily workflow (after onboarding)

```bash
# Pick / inspect profile
scripts/pmx-profile list                # mark active with *
scripts/pmx-profile use prod-east       # switch active

# Read-only sanity
scripts/pmx-cv4 get vms                 # or: pmx-cv4 get cts, get nodes
scripts/pmx-ssh 'pvesm status'

# Provision
scripts/pmx-vm create 110 web-1 --memory 4096
scripts/pmx-ct create 200 web debian-12-standard
scripts/pmx-vm cloudinit 110 --ciuser deploy --sshkeys ~/.ssh/id_ed25519.pub \
                              --ipconfig0 ip=10.0.0.110/24,gw=10.0.0.1

# Day-2 ops
scripts/pmx-vm start 110
scripts/pmx-backup run --all --mode snapshot --compress zstd
scripts/pmx-cluster status
```

## Working with multiple instances

Each Proxmox node or cluster gets its own profile file. Switch with
`pmx-profile use <name>` or one-shot via `PMX_PROFILE=<name>`. cv4pve-cli
contexts stay in sync automatically as long as the user re-runs
`pmx-cv4pve-sync` after profile changes.

## Conventions for the agent

- **Read before write.** Always run `pmx-vm config <id>` (or the API
  equivalent) before any destructive action. Cross-check the user's
  intent against the actual state.
- **No password auth.** SSH helpers force `BatchMode=yes`. If a profile
  needs new auth, edit the profile, do not pass passwords inline.
- **Secrets handling.** Token secrets in profiles use the `${ENV:VAR}`
  reference form by default. Do not echo secrets to the user; redact
  before quoting profile contents.
- **Prefer the REST/cv4pve path** for stateless reads and config sets.
  Reserve `pmx-ssh` for things with no REST endpoint (network config,
  pveperf, journalctl, file edits).
- **Profile is canonical.** Never write Proxmox credentials elsewhere on
  the workstation. Other tools (Terraform, Ansible, cv4pve-cli) should
  reference the same profile values.
- **Confirm before destruction.** `qm destroy`, `pct destroy`, `pvesm remove`,
  `pveum acl delete`, `pvecm delnode`, force-quorum recovery, and any
  `--purge` flag must be confirmed with the user — no exceptions.
- **2026 defaults.** `virtio-scsi-single` + `iothread=1`, `q35 + ovmf`,
  `cputype=host`, `agent enabled=1`, `--unprivileged 1` for containers,
  `--mode snapshot --compress zstd` for backups, `--privsep 0` only when
  the simpler debug path is wanted.

## Available scripts

Run `<script> --help` for the full interface of each. All scripts read the
active profile via the resolution order documented in
[references/project-folder.md](references/project-folder.md) — first
`$PMX_CONFIG_DIR` env, then auto-detected `.proxmox-admin/` in cwd or
ancestor, then `~/.config/proxmox-admin/`. They accept `PMX_PROFILE=<name>`
for one-shot override, and write JSON to stdout / diagnostics to stderr
when `--json` is supported.

| Script | Purpose | Notable flags |
|--------|---------|---------------|
| `scripts/pmx-init` | Scaffold a project folder with profiles/inventory/decisions/runbooks | `--force` to overwrite |
| `scripts/pmx-onboard` | Interactive wizard → YAML profile | env-driven (non-interactive) when `PMX_ONBOARD_*` set |
| `scripts/pmx-doctor` | TCP + SSH + REST + cv4pve checks | `--json` |
| `scripts/pmx-inventory` | Snapshot live state to diffable markdown | `snapshot \| diff \| show <cat>` |
| `scripts/pmx-profile` | list/use/show/path/remove/active | `list --json` |
| `scripts/pmx-ssh` | Run any shell command on the host | `-` reads command from stdin |
| `scripts/pmx-api` | Call REST API with the active token | forwards extra args to `curl` |
| `scripts/pmx-vm` | `qm` wrapper with profile defaults | `create`, `from-image`, `cloudinit`, `destroy --dry-run` |
| `scripts/pmx-ct` | `pct` wrapper with profile defaults | `create`, `from-oci`, `download-template` |
| `scripts/pmx-storage` | `pvesm` wrapper | `scan-iso`, `scan-vztmpl` |
| `scripts/pmx-cluster` | `pvecm` + `ha-manager` + cluster API | `resources --type vm` |
| `scripts/pmx-backup` | `vzdump` / `qmrestore` / `pct restore` | `--dry-run`, `restore vm|ct` |
| `scripts/pmx-token-create` | One-shot least-privilege pveum token | `PMX_ROLE`, `PMX_PRIVSEP`, `PMX_PRIVS` |
| `scripts/pmx-cv4pve-install` | Install Corsinvest cv4pve-cli locally | `PMX_CV4PVE_VERSION`, `PMX_CV4PVE_PREFIX` |
| `scripts/pmx-cv4pve-sync` | Mirror profiles → cv4pve contexts | `--activate`, `--skip` |
| `scripts/pmx-cv4` | cv4pve-cli auto-aligned to active profile | forwards all args |

`references/` and `assets/` are listed in the table at the top of this file.
Open them only when their topic comes up.
