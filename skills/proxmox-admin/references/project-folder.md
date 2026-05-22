# Project-Folder Pattern — Reference

The proxmox-admin skill supports two storage layouts for its connection
profiles, inventory, and related state:

1. **Home-dir layout** (default, since v1.0): `~/.config/proxmox-admin/`
2. **Project-folder layout** (since v1.2): a self-contained directory
   anywhere on disk, auto-detected by the presence of `.proxmox-admin/`

The project-folder layout is recommended for anything beyond the simplest
single-throwaway-profile case. It lets you keep profiles, inventory,
decisions, and runbooks together in a git-versioned, portable directory.

## Table of contents

1. [Why project folders](#why-project-folders)
2. [Layout](#layout)
3. [Resolution order](#resolution-order)
4. [Bootstrapping with `pmx-init`](#bootstrapping-with-pmx-init)
5. [Secret handling](#secret-handling)
6. [Cross-OS portability](#cross-os-portability)
7. [Migrating from `~/.config/`](#migrating-from-config)

---

## Why project folders

The default `~/.config/proxmox-admin/` layout works for the simplest case
but has structural weaknesses:

- Hidden from users (`~/.config/` is rarely browsed)
- Not version-controlled, no audit trail of changes
- Not portable across workstations without manual copy
- No natural place to store inventory, decisions, runbooks
- Mixes the workstation user's home dir with system administration

A project folder solves all of these. Everything about your Proxmox
systems lives in one git-versioned directory you own.

---

## Layout

```
<project>/
├── .proxmox-admin/           tool state — DO commit (small, useful)
│   ├── active                  active profile name (single line)
│   └── version                 schema version (currently "1")
├── profiles/                 connection profiles
│   ├── <system>.yaml           one per Proxmox system
│   └── README.md
├── inventory/                per-system documentation
│   ├── README.md
│   └── <system>/
│       ├── overview.md         hand-curated, NEVER touched by snapshot
│       ├── hardware.md         auto-snapshot
│       ├── network.md          auto-snapshot
│       ├── storage.md          auto-snapshot
│       ├── containers.md       auto-snapshot
│       └── vms.md              auto-snapshot (omitted if no VMs)
├── decisions/                ADR-style decision log (Nygard format)
│   ├── README.md
│   └── NNNN-<slug>.md
├── runbooks/                 step-by-step procedures
│   ├── README.md
│   └── <topic>.md
├── secrets/                  GITIGNORED — real secrets via env.sh
│   ├── .gitkeep
│   ├── env.sh.example          template
│   ├── env.sh                  REAL secrets — gitignored, never committed
│   └── README.md
├── .gitignore                excludes secrets/env.sh and similar
└── README.md                 "start here" for new clones
```

### What gets committed

| Path | Commit? | Rationale |
|------|---------|-----------|
| `.proxmox-admin/active` | yes | small, useful to share active-profile-name |
| `.proxmox-admin/version` | yes | schema version |
| `profiles/*.yaml` | yes | secrets are `${ENV:...}` refs, safe |
| `profiles/README.md` | yes | schema docs |
| `inventory/**/*.md` | yes | auto-generated but diff-worthy |
| `decisions/*.md` | yes | the whole point is durable history |
| `runbooks/*.md` | yes | shareable procedural knowledge |
| `secrets/env.sh.example` | yes | template, no real secrets |
| `secrets/env.sh` | **NO** | real secrets — `.gitignore`d |
| `secrets/*.key`, `*.pem` | **NO** | binary secrets — `.gitignore`d |

---

## Resolution order

The skill's `lib/profile.sh` resolves the active config directory in this
order, first match wins:

1. **Explicit `PMX_CONFIG_DIR` env var.** If set, use as-is. (Backwards
   compatible with all pre-v1.2 scripts and external tooling.)
2. **Project folder discovery.** Walks up from `$PWD` looking for any
   ancestor directory containing a `.proxmox-admin/` subdirectory. If
   found, uses that.
3. **Home-dir fallback.** `$HOME/.config/proxmox-admin/`. This is the
   original layout and remains the default for users who never run
   `pmx-init`.

Override individually with `PMX_PROFILE_DIR` and `PMX_ACTIVE_FILE` if you
want a non-standard split (rarely needed).

### Examples

```bash
# Sitting in a project folder — auto-detected
cd ~/projects/proxmox
pmx-doctor                          # uses ~/projects/proxmox/.proxmox-admin/

# Outside any project folder — falls back to home dir
cd /tmp
pmx-doctor                          # uses ~/.config/proxmox-admin/

# Explicit override (works anywhere)
PMX_CONFIG_DIR=/srv/proxmox-config pmx-doctor
```

---

## Bootstrapping with `pmx-init`

```bash
mkdir my-proxmox-project && cd my-proxmox-project
~/.claude/skills/proxmox-admin/scripts/pmx-init
```

`pmx-init` scaffolds the directory layout above. It is **idempotent** —
running it on an existing project skips files that already exist (use
`--force` to overwrite). Path can be passed explicitly:

```bash
pmx-init ~/projects/proxmox
```

After scaffolding, the recommended steps are:

```bash
cd <project>
cp secrets/env.sh.example secrets/env.sh
$EDITOR secrets/env.sh                  # fill in real PMX_*_TOKEN_SECRET values
source secrets/env.sh
~/.claude/skills/proxmox-admin/scripts/pmx-onboard   # create first profile
~/.claude/skills/proxmox-admin/scripts/pmx-doctor    # verify
git init -b main && git add . && git commit -m "initial scaffold"
```

---

## Secret handling

Profile YAML uses `${ENV:VAR_NAME}` references for any field that should
not be committed:

```yaml
api:
  user: "automation@pve"
  token_id: "skill"
  token_secret: "${ENV:PMX_HOMELAB_TOKEN_SECRET}"
```

At load time, the skill's `pmx_yaml_get` resolves the reference against
the current environment. The real value lives in `secrets/env.sh`:

```bash
# secrets/env.sh (GITIGNORED)
export PMX_HOMELAB_TOKEN_SECRET="<real-uuid>"
```

You source `secrets/env.sh` before running any `pmx-*` command:

```bash
source secrets/env.sh
pmx-doctor
```

### Rotating

1. Regenerate the token on the node:
   ```bash
   pmx-ssh 'pveum user token remove automation@pve skill; pveum user token add automation@pve skill --privsep 0'
   ```
2. Update `secrets/env.sh` with the new secret.
3. Re-source: `source secrets/env.sh` (or open a fresh shell).
4. Verify: `pmx-doctor` passes.

### Why not put the secret directly in the YAML?

You can — the skill still supports literal `token_secret: "abc..."`. But
that pattern leaks secrets through `git diff`, copy-paste, PR review, and
backup snapshots. The `${ENV:...}` indirection makes the profile safely
shareable while keeping the actual credential out of any tracked file.

---

## Cross-OS portability

The skill is bash-based and supports any OS with a POSIX shell. Tested
behavior:

| Concern | Linux | macOS | Windows (Git Bash / WSL) |
|---------|-------|-------|--------------------------|
| `$HOME` | `/home/<user>` | `/Users/<user>` | `/c/Users/<user>` (Git Bash) or `/home/<user>` (WSL) |
| Forward-slash paths in YAML | ✓ | ✓ | ✓ (Git Bash translates) |
| `chmod 600`/`700` | enforced | enforced | best-effort (advisory on NTFS) |
| Walk-up to root | terminates at `/` | terminates at `/` | terminates at drive root |
| Project folder anywhere | ✓ | ✓ | ✓ (in `/c/Users/...` etc.) |
| `ssh-copy-id` | available | available | NOT available in plain Git Bash — use web-UI shell instead |
| `bash` version | 4+ | typically 3.2 (we don't use bash-4-only features) | 4+ |

### Windows-specific notes

On Windows Git Bash, you may see warnings about `chmod` having no effect
on NTFS. This is normal — file permissions there are governed by Windows
ACLs, not POSIX modes. The `.gitignore` rules still prevent secrets from
being committed; the only loss is the defense-in-depth that POSIX `600`
would provide.

For `ssh-copy-id` alternatives on plain Git Bash:
- Use the Proxmox web UI shell (Datacenter → node → Shell) and paste your
  public key into `/root/.ssh/authorized_keys` manually
- Or use WSL, which has full OpenSSH including `ssh-copy-id`

---

## Migrating from `~/.config/`

Existing users with profiles in `~/.config/proxmox-admin/` don't need to
do anything. The skill keeps working unchanged. When you want to migrate:

```bash
# 1. Create a project folder
mkdir ~/projects/proxmox && cd ~/projects/proxmox
pmx-init

# 2. Copy existing profiles
cp ~/.config/proxmox-admin/profiles/*.yaml profiles/
cp ~/.config/proxmox-admin/active .proxmox-admin/active

# 3. Edit each profile to replace literal token_secret with ${ENV:VAR}
#    e.g. for profile homelab.yaml:
#      token_secret: "5cbf4c02-..."     ->     token_secret: "${ENV:PMX_HOMELAB_TOKEN_SECRET}"

# 4. Add the real value to secrets/env.sh
cp secrets/env.sh.example secrets/env.sh
echo 'export PMX_HOMELAB_TOKEN_SECRET="5cbf4c02-..."' >> secrets/env.sh
source secrets/env.sh

# 5. Verify
pmx-doctor

# 6. Optional: remove ~/.config/proxmox-admin/ once confident
#    (keep the SSH key files in ~/.ssh — those don't need to move)
```

The skill auto-detects `.proxmox-admin/` in `$PWD` so you don't need to
export `PMX_CONFIG_DIR` — just `cd` to the project folder.

---

## Related

- `references/onboarding.md` — first-time-setup walkthrough (now updated to mention project folders)
- `scripts/pmx-init` — the scaffolding command
- `scripts/pmx-inventory` — auto-generates inventory snapshots
- SKILL.md `## Project layout (recommended)` section
