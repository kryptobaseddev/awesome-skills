# Container Management (`pct`) — Reference

Read this when working with LXC containers. Companion to `vm-management.md`.

## Table of contents

1. [VM vs container — when to choose which](#vm-vs-container--when-to-choose-which)
2. [Templates: system vs OCI (PVE 9.1+)](#templates-system-vs-oci-pve-91)
3. [Create — modern defaults](#create--modern-defaults)
4. [Networking](#networking)
5. [Privileged vs unprivileged](#privileged-vs-unprivileged)
6. [Bind mounts and shared storage](#bind-mounts-and-shared-storage)
7. [Features (nesting, FUSE, NFS, keyctl)](#features-nesting-fuse-nfs-keyctl)
8. [Snapshots and clones](#snapshots-and-clones)
9. [Migration](#migration)
10. [Common pitfalls](#common-pitfalls)

---

## VM vs container — when to choose which

| Use a container when | Use a VM when |
|----------------------|---------------|
| Workload runs on Linux and trusts the host kernel | Workload needs Windows, BSD, or a different kernel |
| Density matters (RAM/CPU overhead minimal) | Strong isolation required (multi-tenant) |
| Fast startup (< 1s) | GPU/PCIe passthrough needed |
| Cattle-style microservices, build agents | Long-lived stateful systems with kernel modules |

Default to container unless one of the VM-only constraints applies.

---

## Templates: system vs OCI (PVE 9.1+)

```bash
pveam update                                       # refresh catalog
pveam available --section system                   # list system templates
pveam download local debian-12-standard_12.7-1_amd64.tar.zst
pveam list local                                   # what's downloaded

# PVE 9.1+: OCI images become first-class templates
pveam download local docker.io/library/nginx:1.27-alpine
```

System templates → full systemd container. OCI templates → either a system
container (if entrypoint is an init) or a lean application container (single
process). Application containers are more secure and use less RAM.

---

## Create — modern defaults

```bash
pct create $CTID local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst \
  --hostname web \
  --cores 2 --memory 2048 --swap 512 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1 \
  --start 1
```

Why these:

- `--unprivileged 1` is the security default in 2026. Avoid privileged
  containers unless the workload requires it (e.g., NFS server, FUSE mounts
  without `--features fuse=1`).
- `--features nesting=1` allows nested LXC and most Docker workloads inside
  the container to function (Docker also needs `keyctl=1` on some kernels).
- `--onboot 1` ensures auto-start at host boot.

---

## Networking

Static IPv4:

```bash
pct set $CTID --net0 name=eth0,bridge=vmbr0,ip=10.0.0.50/24,gw=10.0.0.1
pct set $CTID --nameserver "1.1.1.1 9.9.9.9" --searchdomain lan
```

VLAN tagged interface:

```bash
pct set $CTID --net0 name=eth0,bridge=vmbr0,tag=20,ip=dhcp
```

Multiple NICs:

```bash
pct set $CTID --net1 name=eth1,bridge=vmbr1,ip=dhcp
```

Inside the container, networking is configured by Proxmox at create/start —
do not write `/etc/network/interfaces` by hand for the managed interfaces.

---

## Privileged vs unprivileged

| Aspect | Unprivileged (default) | Privileged |
|--------|------------------------|------------|
| UID mapping | UIDs in container shifted by +100000 on host | 1:1 mapping |
| `root` inside | Constrained — cannot break out | Equivalent to host root |
| Bind-mounted files | Need correct mapped owner OR `idmap` | Native owner works |
| NFS / FUSE mounts | Require explicit `--features` | Just work |
| Recommended for | Almost everything | Workloads that genuinely need full root |

To convert later, back up and recreate. The flag is set at create time and
the recommended path is destroy + restore.

---

## Bind mounts and shared storage

```bash
# Host path -> container path (read/write)
pct set $CTID --mp0 /mnt/data/photos,mp=/photos

# Read-only bind mount
pct set $CTID --mp1 /etc/letsencrypt,mp=/etc/letsencrypt,ro=1

# Allocate a dedicated volume on a storage
pct set $CTID --mp2 local-lvm:50,mp=/var/lib/data
```

For unprivileged containers, ensure ownership inside maps to the right UID.
`chown -R 100000:100000 /mnt/data/photos` on the host gives root inside the
container ownership. Use `idmap` for advanced cases (see `man pct`).

---

## Features (nesting, FUSE, NFS, keyctl)

```bash
# Enable nesting (Docker inside LXC, podman, nested LXC)
pct set $CTID --features nesting=1

# FUSE (e.g., rclone mount, sshfs)
pct set $CTID --features nesting=1,fuse=1

# Allow NFS / CIFS clients inside container
pct set $CTID --features nesting=1,mount=nfs

# keyctl — needed by Docker daemon on some kernels
pct set $CTID --features nesting=1,keyctl=1
```

Features apply at start. Existing running containers must restart.

---

## Snapshots and clones

```bash
pct snapshot $CTID clean
pct listsnapshot $CTID
pct rollback $CTID clean
pct delsnapshot $CTID clean

pct clone $CTID 201 --hostname copy --full        # independent
pct clone $CTID 201 --hostname copy               # linked clone
```

Snapshots require a storage that supports them (ZFS, Btrfs, Ceph RBD, thin
LVM). On thick LVM or directory storage, snapshots are unavailable.

---

## Migration

Containers cannot be live-migrated (LXC has no live state).
Online migration is technically supported but results in a brief stop+resume:

```bash
pct migrate $CTID pve02 --restart 1               # stops, moves, starts
```

For zero-downtime moves, run two containers behind a load balancer and
shift traffic.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pct enter` returns "Permission denied" | Container is privileged + AppArmor confined or stopped | `pct status <ctid>`; if stopped, start it; otherwise `pct console` |
| Docker fails inside container | Missing `nesting=1` or `keyctl=1` | `pct set <ctid> --features nesting=1,keyctl=1`; restart container |
| Files inside bind mount owned by `nobody` | UID mapping mismatch | `chown 100000:100000` on host OR use `idmap` |
| `pct create` complains about "unsupported template" | OCI image on PVE < 9.1 | Use a system tarball template OR upgrade |
| Container won't start: `cgroup` errors | Mixing cgroup v1 / v2 | Boot host with `systemd.unified_cgroup_hierarchy=1` (default since PVE 7) |
| NFS mounts fail inside container | Missing `mount=nfs` feature | `pct set <ctid> --features ...,mount=nfs`; restart |
