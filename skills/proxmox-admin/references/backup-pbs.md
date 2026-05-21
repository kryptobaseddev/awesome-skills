# Backup, Restore, and Proxmox Backup Server (PBS) — Reference

Read this for `vzdump`, retention/prune, and PBS integration.

## Table of contents

1. [Decision tree — vzdump vs PBS](#decision-tree--vzdump-vs-pbs)
2. [vzdump basics](#vzdump-basics)
3. [Scheduled jobs](#scheduled-jobs)
4. [PBS — connect a node to a Backup Server](#pbs--connect-a-node-to-a-backup-server)
5. [Restore (VMs and CTs)](#restore-vms-and-cts)
6. [File-level restore from PBS](#file-level-restore-from-pbs)
7. [Retention and prune](#retention-and-prune)
8. [Verify, GC, and ransomware protection](#verify-gc-and-ransomware-protection)
9. [Common pitfalls](#common-pitfalls)

---

## Decision tree — vzdump vs PBS

| Need | Use |
|------|-----|
| Local-only, small homelab, < 10 guests | `vzdump` to a `dir` storage |
| Multi-node cluster, deduplication wanted | **PBS** (incremental, dedup, encryption) |
| Off-site or air-gapped copy | PBS with `sync-job` to a second PBS |
| File-level restore | PBS (vzdump can do it too, but slower) |

PBS is free, runs on a low-power Debian box, and is the recommended path
for anything beyond a single node.

---

## vzdump basics

```bash
vzdump 100                                            # one VM/CT, default storage
vzdump 100 200 300 --storage local --mode snapshot --compress zstd
vzdump --all --storage local --mode snapshot --compress zstd \
       --exclude 999 --mailto admin@example.com

# Modes
#   snapshot — uses storage snapshot; minimal downtime (best)
#   suspend  — pauses guest briefly during copy
#   stop     — full shutdown for backup; safest for non-snapshot storage
```

Always prefer `--mode snapshot`. Falls back automatically if storage doesn't
support it.

---

## Scheduled jobs

GUI: Datacenter → Backup → Add. CLI alternative — drop a file under
`/etc/pve/jobs.cfg`:

```
vzdump: daily-2am
    schedule mon..sun 02:00
    enabled 1
    storage local
    mode snapshot
    compress zstd
    all 1
    mailnotification failure
    mailto admin@example.com
    prune-backups keep-daily=7,keep-weekly=4,keep-monthly=6
```

Apply: the cluster scheduler reads `jobs.cfg` automatically (pmxcfs).

---

## PBS — connect a node to a Backup Server

On the PBS host (one-time):

```bash
proxmox-backup-manager datastore create main /srv/pbs/main
proxmox-backup-manager user create skill@pbs
proxmox-backup-manager acl update /datastore/main DatastoreBackup --auth-id skill@pbs
proxmox-backup-manager user generate-token skill@pbs pve --comment "pve cluster"
# Capture the secret printed once.
```

On the Proxmox node:

```bash
pvesm add pbs main-backup \
    --server pbs.lan \
    --datastore main \
    --username skill@pbs \
    --password 'TOKENID:TOKENSECRET' \
    --fingerprint 'AA:BB:CC:...' \
    --encryption-key autogen \
    --content backup
```

Then change the backup job:

```
vzdump: nightly
    schedule daily 02:00
    storage main-backup
    mode snapshot
    all 1
```

PBS handles dedup and incremental forever — no need to set "full vs
incremental" cadence.

---

## Restore (VMs and CTs)

```bash
# Plain vzdump file
qmrestore /var/lib/vz/dump/vzdump-qemu-100-XXXX.vma.zst 100 --storage local-lvm
pct restore 200 /var/lib/vz/dump/vzdump-lxc-200-XXXX.tar.zst --storage local-lvm

# Restore from PBS — same commands; the file path is a vmid+timestamp
qmrestore main-backup:backup/vm/100/2026-05-01T02:00:00Z 100 --storage local-lvm

# Restore to a NEW vmid (clone-like)
qmrestore main-backup:backup/vm/100/2026-05-01T02:00:00Z 110 --storage local-lvm
```

`pmx-backup restore vm|ct` wraps the path lookup.

---

## File-level restore from PBS

```bash
# List available backups
proxmox-backup-client list --repository skill@pbs@pbs.lan:main

# Mount a snapshot read-only
proxmox-backup-client mount \
    vm/100/2026-05-01T02:00:00Z drive-scsi0.img.fidx \
    /mnt/restore \
    --repository skill@pbs@pbs.lan:main
```

Or use the PBS GUI → Datastore → Snapshot → File Browser for the
point-and-click flow.

---

## Retention and prune

```bash
# On the Proxmox side (per backup job)
prune-backups keep-last=3,keep-daily=7,keep-weekly=4,keep-monthly=6,keep-yearly=1

# Manual prune
vzdump 100 --prune-backups keep-last=3,keep-daily=7 --storage local

# PBS-side prune (run on the PBS host)
proxmox-backup-manager prune main \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 6
```

PBS prune just marks chunks unreachable; **garbage collection** (GC) is
what reclaims disk:

```bash
proxmox-backup-manager garbage-collection start main
proxmox-backup-manager garbage-collection status main
```

Schedule GC nightly via PBS's "GC Schedule" datastore setting.

---

## Verify, GC, and ransomware protection

```bash
# Verify a datastore
proxmox-backup-manager verify start main --outdated-after 7

# Namespaces & sync jobs for off-site copy
proxmox-backup-manager datastore create offsite-mirror /srv/pbs/offsite
proxmox-backup-manager sync-job create nightly-mirror \
    --store offsite-mirror --remote primary-pbs --remote-store main \
    --schedule 'mon..sun 03:00'
```

Best practice 3-2-1:
- 3 copies of data
- 2 different media (local PBS + cloud or off-site PBS)
- 1 off-site

With PBS namespaces + immutable retention, ransomware on the source cluster
cannot delete the off-site copies.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Backup fails "VM is locked (backup)" | Previous task didn't release lock | `qm unlock <vmid>` (after confirming no live task) |
| PBS storage shows 0% used despite many backups | Stats not updated; GC pending | Run GC; refresh datastore stats |
| Restore picks the wrong storage | `--storage` omitted; default of source used | Always pass `--storage` explicitly for cross-storage restore |
| Sync job lagging behind | Network bottleneck OR small chunk window | Tune `--max-depth`; check PBS metrics dashboard |
| Encryption key lost | No backup of `/etc/pve/priv/storage/<id>.enc` | Recover from a key escrow OR data is unrecoverable — back up keys! |
| Mounted file restore is read-only on writes | PBS mounts are always RO — by design | Copy files out, modify, then restore VM if needed |
