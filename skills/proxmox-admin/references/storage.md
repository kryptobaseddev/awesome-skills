# Storage (`pvesm`) — Reference

Read this for anything storage-related: pools, datastores, content types,
ZFS specifics, and PVE 9.0+ LVM thick snapshots.

## Table of contents

1. [Storage types at a glance](#storage-types-at-a-glance)
2. [Content types](#content-types)
3. [Inspect / add / remove](#inspect--add--remove)
4. [ZFS — recommended defaults for 2026](#zfs--recommended-defaults-for-2026)
5. [LVM-thin (default install)](#lvm-thin-default-install)
6. [Thick LVM snapshots (PVE 9.0+)](#thick-lvm-snapshots-pve-90)
7. [Ceph RBD](#ceph-rbd)
8. [NFS / CIFS](#nfs--cifs)
9. [Common pitfalls](#common-pitfalls)

---

## Storage types at a glance

| Type | Shared? | Snapshots | Best for |
|------|---------|-----------|----------|
| `dir` | No | Filesystem-level only (`qcow2`) | ISO/template storage; quick & simple |
| `lvm` (thick) | Optional | PVE 9.0+ on shared LVM | SAN-backed shared block storage |
| `lvmthin` | No | Yes | Local default; good performance |
| `zfspool` | No (replicated) | Yes | Local with snapshots, send/recv, dedup |
| `cifs` / `nfs` | Yes | Filesystem (qcow2) | Backup target, shared ISO/template |
| `rbd` (Ceph) | Yes | Yes | Hyperconverged cluster |
| `cephfs` | Yes | No (file-level) | Shared snippets, ISO, vztmpl |
| `pbs` | Yes | n/a (own deduplication) | Proxmox Backup Server target |
| `iscsi` / `iscsidirect` | Yes | No | Block-only target |

---

## Content types

Each storage declares which content types it can hold. Set with
`--content a,b,c` on `pvesm add`:

| Type | What it stores |
|------|----------------|
| `images` | VM disk images |
| `rootdir` | LXC container rootfs |
| `iso` | Bootable ISO files |
| `vztmpl` | LXC container templates (incl. OCI in PVE 9.1+) |
| `backup` | vzdump output |
| `snippets` | Cloud-init user-data, hook scripts |
| `import` | OVA / OVF import staging (PVE 8+) |

---

## Inspect / add / remove

```bash
pvesm status                               # all pools with usage %
pvesm list local                           # contents of `local`
pvesm list local-lvm --content images     # filter by content type

pvesm add nfs nfs-iso \
    --server 10.0.0.5 --export /exports/iso \
    --content iso,vztmpl,snippets --options vers=4.1

pvesm add zfspool fast-zfs --pool rpool/data \
    --content rootdir,images --sparse 1

pvesm set local --content iso,vztmpl,backup,snippets

pvesm remove old-storage
```

---

## ZFS — recommended defaults for 2026

```bash
# Create a pool (run BEFORE installing Proxmox if possible, or on extra disks)
zpool create -o ashift=12 fastpool mirror /dev/disk/by-id/X /dev/disk/by-id/Y

# 4Kn / modern NVMe — use ashift=13
# Always pin ashift; it cannot be changed later.

# Compression and atime
zfs set compression=lz4 fastpool
zfs set atime=off fastpool
zfs set xattr=sa fastpool

# Add to Proxmox
pvesm add zfspool fast-vms --pool fastpool/vms --content rootdir,images
```

ARC cap — homelabs should not let ZFS eat all RAM:

```bash
# /etc/modprobe.d/zfs.conf
options zfs zfs_arc_max=8589934592       # 8 GiB
update-initramfs -u
reboot
```

Consumer QLC drives + ZIL is a known killer. Use enterprise SSDs with PLP
for ZIL/SLOG, or disable sync writes on non-critical datasets:
`zfs set sync=disabled tank/scratch` (data loss risk on power failure).

---

## LVM-thin (default install)

The PVE installer creates `local-lvm` as a thin pool inside the `pve` VG.

```bash
lvs                                        # see thin pool usage
vgs
pvesm list local-lvm

# Extend the thin pool from free PVs / disks
vgextend pve /dev/sdb
lvextend -l +100%FREE /dev/pve/data

# Auto-balloon if thin pool fills
lvchange --metadataprofile pve-data /dev/pve/data
```

Thin pools fill silently. Watch `lvs` "Data%" — when >85%, expand or migrate
volumes. Once full, VMs go read-only.

---

## Thick LVM snapshots (PVE 9.0+)

Before 9.0, snapshots on thick (shared) LVM weren't supported. Now they
are — making FC/iSCSI SAN-backed Proxmox practical for snapshot-based
workflows.

```bash
pvesm add lvm san-block --vgname san_vg --content images,rootdir --shared 1
qm snapshot 100 pre-change                # works on thick LVM in PVE 9.0+
```

---

## Ceph RBD

```bash
# After Ceph cluster is up (use the GUI installer or `pveceph install`)
pveceph pool create rbd-vms --size 3 --pg_autoscale_mode on

# Add as Proxmox storage
pvesm add rbd ceph-vms --pool rbd-vms --content rootdir,images \
       --krbd 1 --username admin
```

Use the kernel RBD driver (`--krbd 1`) for VMs and CTs unless you specifically
need user-space `librbd` features.

---

## NFS / CIFS

```bash
pvesm add nfs backup-nas --server 10.0.0.20 --export /exports/backups \
       --content backup --options vers=4.1,soft,retrans=3

pvesm add cifs media --server 10.0.0.20 --share media --username readonly \
       --password "$(cat /root/.smbpass)" --content iso,vztmpl
```

For backups, `vers=4.1` is the safest default. Avoid `vers=3` unless the
target only speaks NFSv3.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pvesm status` shows storage `inactive` | Mount failed / network down | `mount -a`; check `journalctl -xeu pvestatd.service` |
| Backup fails: "no space left on device" | Thin pool full OR target storage out of space | `lvs` to check Data%; expand pool or move VMs |
| Cloud-init drive not appearing in storage | Storage has no `snippets`/`images` content type | `pvesm set <s> --content images,snippets,...` |
| ZFS pool degraded after disk swap | Replacement disk path differs | `zpool replace <pool> <old-id> /dev/disk/by-id/<new>` |
| LVM thick snapshot fails on PVE 8.x | Feature requires 9.0+ | Upgrade to PVE 9.0+ or use qcow2 on dir storage |
| Slow live migration with ZFS | No shared storage, copying via LAN | Set up replication + use `--with-local-disks` OR migrate to Ceph |
