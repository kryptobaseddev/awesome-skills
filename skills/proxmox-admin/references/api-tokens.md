# Proxmox API Tokens — pveum, least privilege, and gotchas

Authoritative for everything related to `pveum`. Read when:

- a 401/403 comes back from `pmx-api`
- the user asks to "limit what the skill can do"
- creating a new token from scratch (and `pmx-token-create` is not enough)
- rotating or revoking a leaked token

## Table of contents

1. [Two privilege models — pick first](#two-privilege-models--pick-first)
2. [Minimal create / list / regenerate / delete](#minimal-create--list--regenerate--delete)
3. [Recommended role profiles](#recommended-role-profiles)
4. [Resolving 401/403 systematically](#resolving-401403-systematically)
5. [Header format and curl examples](#header-format-and-curl-examples)
6. [Rotation and revocation](#rotation-and-revocation)
7. [Privilege reference (subset that matters)](#privilege-reference-subset-that-matters)

---

## Two privilege models — pick first

Proxmox tokens have a `privsep` flag set **at create time and never changed**:

| `--privsep` | Effective perms | When to use |
|-------------|-----------------|-------------|
| `0` (separation OFF) | Identical to the owning user | Quick start, fewer moving parts |
| `1` (separation ON, default) | Intersection of (user perms ∩ token perms) | Defense-in-depth: blast radius if leaked is < user |

> The most common 401/403 cause is creating with `--privsep 1` and forgetting
> to attach an ACL to the token itself. The token starts with **zero**
> privileges in that mode.

If a token already exists with the wrong privsep, **delete and recreate**.
Privsep is immutable post-creation.

---

## Minimal create / list / regenerate / delete

```bash
# Create user (idempotent)
pveum user add automation@pve --comment "skill"

# Create a role with the privs you want (see profiles below)
pveum role add pmx-skill --privs "VM.Audit VM.PowerMgmt ..."

# Attach role to the user at a path with propagation
pveum acl modify / --user automation@pve --role pmx-skill --propagate 1

# Token with separation OFF (token == user perms)
pveum user token add automation@pve skill --privsep 0

# Token with separation ON — also attach role to the TOKEN
pveum user token add automation@pve skill --privsep 1
pveum acl modify / --token 'automation@pve!skill' --role pmx-skill --propagate 1

# Inspect / regenerate / delete
pveum user token list automation@pve
pveum user token Regen automation@pve skill          # rotates the secret
pveum user token delete automation@pve skill          # revoke

# Check effective perms on a path
pveum user permissions automation@pve --path /
pveum user token permissions automation@pve skill --path /vms/100
```

> The token secret prints **once** at create or regenerate time. If lost,
> regenerate — there is no recovery.

---

## Recommended role profiles

Pick the smallest role that covers the user's needs.

### `pmx-audit` — read-only / monitoring

```
VM.Audit Datastore.Audit Sys.Audit SDN.Audit Pool.Audit
```

### `pmx-power` — start / stop / console only

```
VM.Audit VM.PowerMgmt VM.Console Sys.Audit
```

### `pmx-skill` — what `pmx-vm` / `pmx-ct` / `pmx-backup` need

```
Datastore.Allocate Datastore.AllocateSpace Datastore.AllocateTemplate
Datastore.Audit Pool.Allocate
VM.Allocate VM.Audit VM.Backup VM.Clone VM.Config.CDROM VM.Config.CPU
VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory
VM.Config.Network VM.Config.Options VM.Console VM.Migrate VM.Monitor
VM.PowerMgmt VM.Snapshot VM.Snapshot.Rollback
SDN.Audit SDN.Use
Sys.Audit Sys.Console Sys.Modify Sys.PowerMgmt
```

### `pmx-deploy` — Terraform/Ansible provisioning

Add to `pmx-skill`:

```
Sys.Audit Sys.Modify Realm.Allocate User.Modify Permissions.Modify
```

Note: `Permissions.Modify` is sensitive. Only grant if the provider creates
roles/ACLs.

---

## Resolving 401/403 systematically

1. Confirm header format — must be exactly:
   `Authorization: PVEAPIToken=USER@REALM!TOKENID=SECRET`
   (single `!`, single `=` before the UUID).

2. `pveum user token permissions <user@realm> <tokenid> --path /`
   - Empty output ⇒ token has no privileges. Either:
     - Recreate with `--privsep 0`, or
     - `pveum acl modify <path> --token 'user@realm!tokenid' --role X --propagate 1`

3. `pveum user permissions <user@realm> --path /`
   - If empty too: the underlying user has no perms — attach role to the user
     before re-checking the token.

4. Token can never exceed user perms. If a privilege is missing on the user,
   adding it to the token does nothing.

5. Path scoping matters. ACLs on `/vms/100` do not grant access to
   `/storage/local-lvm`. Use propagation (`--propagate 1`) or attach at `/`.

---

## Header format and curl examples

```bash
TOKEN='PVEAPIToken=automation@pve!skill=00000000-0000-0000-0000-000000000000'
HOST='https://pve01.lan:8006'

# Read API version
curl -sSk -H "Authorization: $TOKEN" "$HOST/api2/json/version"

# Cluster resources of type vm
curl -sSk -H "Authorization: $TOKEN" \
     "$HOST/api2/json/cluster/resources?type=vm"

# Create a VM via API
curl -sSk -H "Authorization: $TOKEN" \
     -X POST "$HOST/api2/json/nodes/pve01/qemu" \
     -d vmid=110 -d name=demo -d memory=2048 -d cores=2 \
     -d net0=virtio,bridge=vmbr0 -d scsi0=local-lvm:32
```

Every helper in `scripts/` constructs this header automatically from the
active profile.

---

## Rotation and revocation

Rotate every 90 days, or immediately on:

- token leak (committed to git, sent in chat, etc.)
- offboarding the skill from a host
- promotion / demotion of the owning user

```bash
# Rotate (new secret printed once)
pveum user token Regen automation@pve skill

# Then update the profile (or env var)
$EDITOR ~/.config/proxmox-admin/profiles/homelab.yaml

# Revoke if compromised
pveum user token delete automation@pve skill
```

---

## Privilege reference (subset that matters)

Full list: `pveum acl list-privs` on the node. The ones the skill commonly
touches:

| Privilege | Grants |
|-----------|--------|
| `VM.Audit` | Read VM config / status |
| `VM.PowerMgmt` | start/stop/shutdown/reset/suspend/resume |
| `VM.Console` | Access to VNC/serial console |
| `VM.Config.*` | Modify VM config (CPU, memory, disk, network, etc.) |
| `VM.Allocate` | Create / destroy / clone VMs |
| `VM.Backup` | Run vzdump on a VM |
| `VM.Migrate` | Live or offline migration |
| `VM.Snapshot[.Rollback]` | Take / rollback snapshots |
| `Datastore.Audit` | List storage |
| `Datastore.Allocate*` | Add / remove storage, allocate space |
| `SDN.Audit` / `SDN.Use` | View / attach guests to SDN VNets |
| `Sys.Audit` | Read node metrics, network, services |
| `Sys.Modify` | Apply node-level changes (network, services) |
| `Sys.Console` | Shell on the node (rare in token context) |
| `Sys.PowerMgmt` | Reboot / shutdown the node itself |
| `Pool.Allocate` | Manage resource pools |
