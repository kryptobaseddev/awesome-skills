# DESIGN: Project-folder pattern for proxmox-admin

**Status:** Proposed
**Authors:** session 2026-05-22 collaborative design
**Target version:** proxmox-admin v1.2.0 (next minor after current v1.1.1)
**Implementation status:** design only — no code changes in this proposal

## Problem

The current skill stores all state under `~/.config/proxmox-admin/`:

```
~/.config/proxmox-admin/
├── active                    # name of active profile
└── profiles/<name>.yaml      # connection details (token secrets inline by default)
```

This pattern works for the simplest case (one user, one workstation, one
Proxmox node) but breaks down quickly for real use:

1. **Hidden from the user.** A new user has to be told where their data lives.
2. **Not version-controlled.** Profile changes, decisions, and inventory drift away from each other.
3. **Not portable.** Moving to a new workstation requires manually copying `~/.config/proxmox-admin/` + the SSH keys it references.
4. **Not collaborative.** Two admins of the same Proxmox can't share configuration easily.
5. **Not auditable.** No record of what changed when, by whom, or why.
6. **No place for non-connection data.** Inventory, decisions, runbooks all accumulate somewhere — but `~/.config/` is the wrong place.
7. **Mixes user identity with system identity.** The workstation user's home dir holds everything as if user-scope == system-scope.

Real-world usage of this skill (dogfooded in `/mnt/projects/proxmox/`)
shows users want a **project folder** that contains everything about their
Proxmox systems, lives in git, and is portable across workstations.

## Goals

1. Let users keep all their Proxmox configuration + documentation in a
   single project directory that they own and version-control.
2. Don't break existing `~/.config/proxmox-admin/` installs — they keep
   working unchanged.
3. Make secret handling first-class: secrets in env vars, profile YAML
   safely committable.
4. Provide scaffolding so a new user doesn't have to invent the structure.
5. Provide an inventory snapshot tool so live state can be captured into
   diffable markdown.

## Non-goals

- This is NOT a Terraform/Ansible replacement. Those tools exist for
  declarative provisioning; this skill remains an interactive-ops tool.
- We are NOT proposing to require a project folder. The home-dir fallback
  stays as the default for first-touch users.
- We are NOT designing a secret management system. We document the env-var
  reference pattern (already supported by `lib/profile.sh`) and leave key
  rotation, vaulting, etc. to the user.

## Proposed project-folder layout

```
<project>/
├── .proxmox-admin/                 Tool state (small, can stay in git)
│   ├── active                      Name of active profile (single line)
│   └── version                     Schema version (currently "1")
├── profiles/                       Connection profiles
│   ├── <system>.yaml               One per Proxmox system
│   └── README.md                   Schema reference + onboarding flow
├── inventory/                      Per-system documentation
│   ├── README.md
│   └── <system>/                   One subdir per system
│       ├── overview.md             Hand-curated one-pager
│       ├── hardware.md             Auto-snapshot
│       ├── network.md              Auto-snapshot
│       ├── storage.md              Auto-snapshot
│       ├── containers.md           Auto-snapshot
│       └── vms.md                  Auto-snapshot (omit if no VMs)
├── decisions/                      ADR-style decision log
│   ├── README.md
│   └── NNNN-<slug>.md
├── runbooks/                       Step-by-step procedures
│   ├── README.md
│   └── <topic>.md
├── secrets/                        GITIGNORED — real secrets via env.sh
│   ├── .gitkeep
│   ├── env.sh.example              Template
│   └── README.md                   Secret-handling conventions
├── .gitignore                      Excludes secrets/env.sh, *.bak, etc.
└── README.md                       "Start here"
```

A dogfood instance of this exact layout lives at `/mnt/projects/proxmox/`.

## Proposed changes to the skill

### Change 1: Profile-directory discovery in `scripts/lib/profile.sh`

Current behavior:

```bash
PMX_CONFIG_DIR="${PMX_CONFIG_DIR:-$HOME/.config/proxmox-admin}"
PMX_PROFILE_DIR="${PMX_PROFILE_DIR:-$PMX_CONFIG_DIR/profiles}"
PMX_ACTIVE_FILE="${PMX_ACTIVE_FILE:-$PMX_CONFIG_DIR/active}"
```

Proposed behavior:

```bash
# 1. Explicit override via env wins (existing behavior — backwards compatible)
# 2. Walk up from PWD looking for .proxmox-admin/ — auto-detect project folder
# 3. Fall back to ~/.config/proxmox-admin/ — current default behavior

pmx_resolve_config_dir() {
  # 1. Explicit override
  if [ -n "${PMX_CONFIG_DIR:-}" ]; then
    printf '%s' "$PMX_CONFIG_DIR"
    return
  fi

  # 2. Walk up from cwd looking for .proxmox-admin/
  local d="$PWD"
  while [ "$d" != "/" ] && [ "$d" != "" ]; do
    if [ -d "$d/.proxmox-admin" ]; then
      printf '%s' "$d/.proxmox-admin"
      return
    fi
    d="$(dirname "$d")"
  done

  # 3. Fall back to home-dir default
  printf '%s' "${HOME}/.config/proxmox-admin"
}

PMX_CONFIG_DIR="$(pmx_resolve_config_dir)"
PMX_PROFILE_DIR="${PMX_PROFILE_DIR:-$PMX_CONFIG_DIR/profiles}"
PMX_ACTIVE_FILE="${PMX_ACTIVE_FILE:-$PMX_CONFIG_DIR/active}"
```

**Backwards compatibility:** users with `~/.config/proxmox-admin/` but no
project folder see no change. Users with a project folder see it auto-detected.

**Cross-OS:** uses only `$PWD`, `$HOME`, `dirname`, and `[`/`-d` tests, which
work on Linux, macOS, and Windows-via-Git-Bash identically. The walk-up
loop terminates correctly on all three (`/` on POSIX, `/c/` on Git Bash
on Windows reaching its root via `dirname`).

### Change 2: New `scripts/pmx-init` command

```bash
pmx-init [<dir>]
```

Scaffolds the directory structure described above. Default `<dir>` is `.`
(current directory). Creates:

- `.proxmox-admin/active` (empty until first profile added)
- `.proxmox-admin/version` (`1`)
- `profiles/`, `inventory/`, `decisions/`, `runbooks/`, `secrets/` (with READMEs)
- `secrets/env.sh.example` (template referencing `PMX_*_TOKEN_SECRET` and the path env vars)
- `.gitignore` (excludes `secrets/env.sh`, `*.bak`, common editor junk)
- `README.md` (project quickstart and conventions)

**Idempotent:** running `pmx-init` over an existing project does not
overwrite files. It prints a diff of what would be created and asks for
confirmation.

**Cross-OS:** uses standard POSIX file ops + heredocs. Path separators are
forward-slash throughout (`mkdir -p inventory/<system>` works on all
three OSes). File modes (`chmod 700` for `.proxmox-admin/`, `chmod 600`
for `secrets/`) are advisory on Windows NTFS — we log a warning rather
than fail.

### Change 3: New `scripts/pmx-inventory` command

```bash
pmx-inventory snapshot [--profile <name>]
pmx-inventory diff [--profile <name>]      # show diff vs last snapshot
pmx-inventory show [--profile <name>] hardware|network|storage|containers|vms
```

The `snapshot` subcommand reads the active profile, queries the live node,
and writes/updates markdown files under `inventory/<profile>/`:

- `hardware.md` — CPU, RAM, disks (with SMART), NICs
- `network.md` — bridges, IPs (host + CTs), firewall mode
- `storage.md` — pools, datasets, LVM, NFS mounts, backup jobs
- `containers.md` — full LXC inventory with role/IP/priv-status
- `vms.md` — KVM VM inventory (skipped if `qm list` returns empty)

Each generated file has a "last synced" footer and a "How to refresh"
section. `overview.md` is NEVER touched by snapshot — that's hand-curated.

`pmx-inventory diff` runs the same queries but compares to the on-disk
files without writing — useful for "what's changed since I last
snapshotted?" without altering working tree.

**Output format:** stable markdown so that successive snapshots produce
small, focused diffs. Ordering of items is deterministic (sorted by
VMID, then by IP, etc.).

### Change 4: `pmx-onboard` defaults to project dir when detected

Currently `pmx-onboard` writes to `$PMX_PROFILE_DIR` which defaults to
`~/.config/proxmox-admin/profiles/`. After Change 1, if the user runs
`pmx-onboard` from inside a project folder, the discovery logic naturally
picks the project's `.proxmox-admin/` and the new profile lands there.

The only change to `pmx-onboard` itself is the banner message — print
the resolved `PMX_PROFILE_DIR` so the user sees where the profile is
going BEFORE they answer questions.

### Change 5: SKILL.md updates

Add a new section after "Onboarding workflow":

```markdown
## Project layout (recommended)

For anything beyond a single throwaway profile, we recommend creating a
**project folder** that holds your connection profiles, inventory,
decisions, and runbooks together in version control.

```bash
mkdir my-proxmox-project && cd my-proxmox-project
~/.claude/skills/proxmox-admin/scripts/pmx-init
```

The skill auto-detects `.proxmox-admin/` in the current directory (or any
parent) and uses it as the config root. Falls back to `~/.config/` if no
project folder is found.

See the dogfood example in our docs and the `pmx-init`-generated README
for layout details.
```

Plus a one-line note in the Overview section that the home-dir default
is the fallback, not the only option.

## Cross-OS portability matrix

| Concern | Linux | macOS | Windows-via-Git-Bash | Windows-via-WSL |
|---------|-------|-------|----------------------|-----------------|
| `$HOME` resolution | `/home/<user>` | `/Users/<user>` | `/c/Users/<user>` | `/home/<user>` |
| Forward-slash paths | ✓ | ✓ | ✓ | ✓ |
| `chmod 600` | enforced | enforced | advisory (warn, don't fail) | enforced |
| `chmod 700` on dirs | enforced | enforced | advisory (warn, don't fail) | enforced |
| `dirname` / `$PWD` | ✓ | ✓ | ✓ | ✓ |
| Walk-up to root | terminates at `/` | terminates at `/` | terminates at `/c/` (or current drive root) | terminates at `/` |
| `ssh-copy-id` | available | available | NOT available — use web-UI shell or manual `authorized_keys` paste | available |
| `ssh-keygen` | available | available | available (via OpenSSH for Windows or Git Bash) | available |
| Secret in env var | `export PMX_X=...` | same | same | same |
| `bash 4+` | yes | usually `bash 3.2` (skill should test ≥ 3.2 for macOS) | yes | yes |

**Implication:** the skill should NOT assume bash 4+ features. Several
existing scripts use `printf -v` and `[[ ... ]]` which are fine. Avoid
associative arrays unless we drop macOS native bash support.

## Migration path for existing users

Users on the current `~/.config/proxmox-admin/` layout don't need to do
anything. Their setup keeps working. When they want to migrate:

```bash
# 1. Create a new project folder somewhere
mkdir ~/projects/proxmox && cd ~/projects/proxmox
pmx-init

# 2. Copy existing profiles
cp ~/.config/proxmox-admin/profiles/*.yaml profiles/
cp ~/.config/proxmox-admin/active .proxmox-admin/

# 3. Edit each profile to replace literal token_secret with ${ENV:VAR}
# 4. Add the secret to secrets/env.sh and source it
# 5. Verify: pmx-doctor

# 6. Optional: remove ~/.config/proxmox-admin/ once confident
```

A future `pmx-migrate-to-project` command could automate steps 2-4. Not
in scope for this design.

## Implementation order

If we accept this design, the implementation tasks would be:

1. Add `pmx_resolve_config_dir` to `scripts/lib/profile.sh` (Change 1)
2. Write `scripts/pmx-init` (Change 2)
3. Write `scripts/pmx-inventory` (Change 3) — biggest scope
4. Minimal update to `scripts/pmx-onboard` (Change 4)
5. Update `SKILL.md` and `references/onboarding.md` (Change 5)
6. Add a new reference `references/project-folder.md` with the full layout spec
7. Bump skill version to v1.2.0

Estimated effort: ~6-10 hours of scripting + ~2 hours of doc writing,
spread across whatever cadence fits.

## Open questions

- **Snapshot format:** stay pure markdown (current proposal) or add JSON
  sidecar files for tooling? Probably markdown-only — keep human-readable
  as the primary mode, add JSON only if someone wants to script over it later.

- **Multi-system vs single-system layout:** the proposal nests `inventory/<system>/`
  even for single-system setups. Cleaner long-term but adds nesting up front.
  Alternative: flatten by default, recommend nesting only when adding a second.
  Recommendation: keep nesting (the dogfood instance confirms it's fine
  ergonomically and avoids reorganization later).

- **Should `pmx-init` initialize a git repo automatically?** Pro: less work
  for the user. Con: not everyone wants their config in git. Recommendation:
  print "Recommended: `git init && git add . && git commit -m 'initial'`"
  at the end of `pmx-init`, but don't run it.

## Related

- ADR 0007 in the dogfood repo at `/mnt/projects/proxmox/decisions/0007-skill-project-folder-pattern.md` records the underlying decision
- The dogfood project at `/mnt/projects/proxmox/` exercises the proposed layout end to end
