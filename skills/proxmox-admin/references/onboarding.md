# Onboarding — Connection Profile Setup

Read this when the active profile is missing or `pmx-doctor` fails. Walks the
user through provisioning the SSH access, the API token, and the YAML profile
the rest of the skill depends on.

## Table of contents

1. [Prerequisites the user must supply](#prerequisites-the-user-must-supply)
2. [Step 1 — Create an SSH key and authorize it](#step-1--create-an-ssh-key-and-authorize-it)
3. [Step 2 — Create a least-privilege API token on the node](#step-2--create-a-least-privilege-api-token-on-the-node)
4. [Step 3 — Run the onboarding wizard](#step-3--run-the-onboarding-wizard)
5. [Step 4 — Verify the connection](#step-4--verify-the-connection)
6. [Multi-profile workflow](#multi-profile-workflow)
7. [Bastion / ProxyJump setup](#bastion--proxyjump-setup)
8. [Where files live](#where-files-live)
9. [Hardening checklist](#hardening-checklist)

---

## Prerequisites the user must supply

Before invoking `scripts/pmx-onboard`, confirm with the user:

| Item | Why we need it | How to obtain |
|------|----------------|---------------|
| Reachable hostname/IP | Targets all SSH + REST calls | `ip -4 addr` on the node, or DNS A record |
| Proxmox admin SSH user | Runs `qm`, `pct`, `pvesm`, etc. | Default `root@pam` (homelab) or a dedicated admin user |
| SSH private key path | Key-based auth (passwords blocked in profile) | `ls ~/.ssh/id_*` or generate one (Step 1) |
| API user@realm | Owns the API token | `pveum user list` |
| API token id + secret | Authenticates REST calls | `pveum user token add ...` (Step 2) |
| Default storage names | Lets helpers fill in defaults | `pvesm status` |
| Default bridge name | Networking defaults for create | `cat /etc/network/interfaces \| grep vmbr` |

Do **not** invent values. If the user does not know a field, prompt them and,
where applicable, show them the exact one-line command to discover it.

---

## Step 1 — Create an SSH key and authorize it

The skill only supports key-based SSH. Password auth is intentionally
disabled in profile defaults (`BatchMode=yes`).

Generate a dedicated key on the user's workstation:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_proxmox -C "proxmox-admin-skill"
```

Copy the public key to the Proxmox node (one-time, may need password):

```bash
ssh-copy-id -i ~/.ssh/id_ed25519_proxmox.pub root@<node-host>
```

Pin the host key in a dedicated `known_hosts` file (recommended for
production):

```bash
ssh-keyscan -p 22 <node-host> >> ~/.ssh/known_hosts_proxmox
```

If pinning, set `ssh.strict_host_key_checking: yes` in the profile.
Otherwise use `accept-new` for first-run discovery.

---

## Step 2 — Create a least-privilege API token on the node

Use the helper:

```bash
scripts/pmx-token-create skill /
```

…which runs the following on the node (the helper is just a thin wrapper):

```bash
# user
pveum user add automation@pve --comment "proxmox-admin skill" || true

# role with the privileges day-2 ops need
pveum role add pmx-skill --privs \
  "Datastore.Allocate Datastore.AllocateSpace Datastore.AllocateTemplate Datastore.Audit \
   Pool.Allocate VM.Allocate VM.Audit VM.Backup VM.Clone VM.Config.CDROM VM.Config.CPU \
   VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network \
   VM.Config.Options VM.Console VM.Migrate VM.Monitor VM.PowerMgmt VM.Snapshot \
   VM.Snapshot.Rollback SDN.Audit SDN.Use Sys.Audit Sys.Console Sys.Modify Sys.PowerMgmt"

# attach the role at the root path with propagation
pveum acl modify / --user automation@pve --role pmx-skill --propagate 1

# create the token. --privsep 0 means the token inherits the user's perms
# (simpler debugging). Use --privsep 1 + a second `acl modify --token ...` for
# defense-in-depth. See references/api-tokens.md.
pveum user token add automation@pve skill --privsep 0
```

The secret is printed **once**. Capture it into the wizard prompt (or
export `PMX_ONBOARD_API_TOKEN_SECRET` before running the wizard).

> If the user only needs **read-only** monitoring, swap the role line for:
> `pveum role add pmx-audit --privs "VM.Audit Datastore.Audit Sys.Audit SDN.Audit"`

---

## Step 3 — Run the onboarding wizard

```bash
scripts/pmx-onboard
```

The wizard:

- creates `~/.config/proxmox-admin/profiles/<name>.yaml` with mode `0600`
- marks that profile active (`~/.config/proxmox-admin/active`)
- writes secrets inline only when the user provides them; otherwise leaves
  `token_secret: "${ENV:PMX_TOKEN_SECRET}"` so the user can supply via env

For unattended setups, set these env vars first:

```
PMX_ONBOARD_name PMX_ONBOARD_host_address PMX_ONBOARD_ssh_user
PMX_ONBOARD_ssh_identity_file PMX_ONBOARD_api_user
PMX_ONBOARD_api_token_id PMX_ONBOARD_api_token_secret
```

---

## Step 4 — Verify the connection

```bash
scripts/pmx-doctor
```

Should print four `[ok]` lines. If any fails:

| Failure | Most likely cause | Fix |
|---------|-------------------|-----|
| `tcp ... unreachable` | Firewall or wrong host | Test with `nc -vz <host> 22` from same machine |
| `ssh login failed: Permission denied (publickey)` | Key not authorized or wrong user | Re-run `ssh-copy-id`; confirm `ssh.user` |
| `ssh login failed: Host key verification failed` | First-run pinning | Set `strict_host_key_checking: accept-new` once |
| `REST /version returned unexpected payload` | TLS cert mismatch | Set `verify_tls: false` or install a real cert |
| `REST call failed` (401/403) | Token privsep + missing ACL | See [api-tokens.md](api-tokens.md) |

---

## Multi-profile workflow

Each Proxmox node or cluster gets its own profile.

```bash
scripts/pmx-profile list          # show all + mark active
scripts/pmx-profile use prod-east # switch active
PMX_PROFILE=prod-east scripts/pmx-vm list   # one-shot override
```

Profiles are independent files; safe to edit by hand. Always re-run
`pmx-doctor` after editing.

---

## Bastion / ProxyJump setup

If the Proxmox node is only reachable through a bastion host, set in the
profile:

```yaml
ssh:
  user: root
  identity_file: ~/.ssh/id_ed25519_proxmox
  proxy_jump: ops@bastion.lan
```

The wrapper passes `-o ProxyJump=ops@bastion.lan` for every SSH call.

For the REST API (which goes direct, not via SSH), expose it through
a local port via a separate `ssh -L 8006:pve01.lan:8006 ops@bastion.lan`
session, then set `host.address: localhost`.

---

## Where files live

```
~/.config/proxmox-admin/
├── active                # one line: name of the active profile
└── profiles/
    ├── homelab.yaml      # mode 0600
    └── prod-east.yaml    # mode 0600
```

Override paths via env:
- `PMX_CONFIG_DIR` (defaults to `~/.config/proxmox-admin`)
- `PMX_PROFILE_DIR` (defaults to `$PMX_CONFIG_DIR/profiles`)
- `PMX_ACTIVE_FILE` (defaults to `$PMX_CONFIG_DIR/active`)
- `PMX_PROFILE` (one-shot active profile override)

---

## Hardening checklist

Before treating any profile as "production":

- [ ] `ssh.identity_file` is unique to this skill (not the user's main key)
- [ ] `ssh.known_hosts_file` is pinned and `strict_host_key_checking: yes`
- [ ] `host.verify_tls: true` once a real CA-signed cert is installed
- [ ] Token has `--privsep 1` and an ACL scoped narrower than `/`
- [ ] Profile file mode is `0600` (`stat -c %a ~/.config/proxmox-admin/profiles/*.yaml`)
- [ ] Secrets sourced via `${ENV:VAR}` or stored in an OS keyring rather than inline
