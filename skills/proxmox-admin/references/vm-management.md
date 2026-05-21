# VM Management (`qm`) — Reference

Read this when working with KVM virtual machines. Mirrors the upstream `qm`
command surface plus practical 2026 defaults. Every CLI here runs on the
Proxmox node — invoke remotely via `scripts/pmx-ssh '<cmd>'` or use the
`scripts/pmx-vm` wrapper which applies profile defaults.

## Table of contents

1. [Lifecycle quick reference](#lifecycle-quick-reference)
2. [Create — modern defaults](#create--modern-defaults)
3. [Cloud-init provisioning](#cloud-init-provisioning)
4. [Cloud image → template workflow](#cloud-image--template-workflow)
5. [Hardware configuration](#hardware-configuration)
6. [Snapshots, clones, templates](#snapshots-clones-templates)
7. [Live and offline migration](#live-and-offline-migration)
8. [Guest agent and monitoring](#guest-agent-and-monitoring)
9. [GPU / PCIe passthrough](#gpu--pcie-passthrough)
10. [Common pitfalls](#common-pitfalls)

---

## Lifecycle quick reference

| Command | Effect |
|---------|--------|
| `qm start <vmid>` | Start (boots from current `boot` config) |
| `qm shutdown <vmid>` | Graceful ACPI shutdown (requires running guest agent for reliable behavior) |
| `qm stop <vmid>` | Hard power off — equivalent to pulling the plug |
| `qm reboot <vmid>` | Graceful reboot via guest agent or ACPI |
| `qm reset <vmid>` | Hard reset |
| `qm suspend <vmid>` | Pause to RAM |
| `qm resume <vmid>` | Resume from RAM |
| `qm unlock <vmid>` | Clear a stale config lock (only when no task is actually holding it) |
| `qm destroy <vmid>` | Delete VM and its disks |
| `qm destroy <vmid> --purge` | Also remove backup, replication, HA references |

---

## Create — modern defaults

Apply these defaults unless the user has stated otherwise. The
`pmx-vm create` helper bakes them in.

```bash
qm create $VMID \
  --name $NAME \
  --cores 2 --memory 2048 \
  --net0 virtio,bridge=vmbr0 \
  --scsi0 local-lvm:32 \
  --scsihw virtio-scsi-single \
  --machine q35 --bios ovmf \
  --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=1 \
  --cpu cputype=host \
  --ostype l26 \
  --agent enabled=1,fstrim_cloned_disks=1 \
  --serial0 socket --vga serial0
```

Why these:

- `virtio-scsi-single` enables one virtio-scsi controller per disk, unlocking
  per-disk `iothread=1`.
- `q35 + ovmf` is required for modern UEFI, secure boot, and PCIe passthrough.
- `cputype=host` exposes host CPU features → best performance and no
  cross-CPU surprises during live migration unless cluster CPUs differ.
- `agent enabled=1` is mandatory for reliable `shutdown`, backups with
  `fstrim`, and `qm agent ...` commands.
- `serial0 socket + vga serial0` lets `qm terminal <vmid>` work — invaluable
  for headless cloud images.

---

## Cloud-init provisioning

Cloud-init is the recommended way to inject network, users, SSH keys, and
arbitrary user-data into a fresh VM. Three pieces are required:

```bash
# 1. Attach a cloud-init drive (typically on ide2)
qm set $VMID --ide2 local-lvm:cloudinit

# 2. Set cloud-init properties (all optional, mix and match)
qm set $VMID --ciuser deploy
qm set $VMID --cipassword "$(openssl passwd -1 'tempPass!')"   # SHA-512 hash
qm set $VMID --sshkeys ~/.ssh/authorized_keys
qm set $VMID --ipconfig0 ip=10.0.0.110/24,gw=10.0.0.1
qm set $VMID --nameserver "1.1.1.1 8.8.8.8" --searchdomain lan

# 3. (Optional) Inject custom user-data from a snippet stored on a storage
#    with `snippets` content enabled (e.g., `local`).
qm set $VMID --cicustom "user=local:snippets/user-data-deploy.yaml"

qm set $VMID --boot order=scsi0
qm start $VMID
```

Snippets must be uploaded with `scp` or `pvesm`-managed storage. See
`assets/cloud-init-user-data.yaml` for a starting template.

> Cloud-init regenerates inside the guest **every boot** as long as the
> drive is attached. Detach it (`qm set $VMID --delete ide2`) to lock in
> the configuration after first boot.

---

## Cloud image → template workflow

The canonical "golden image" workflow:

```bash
IMG=jammy-server-cloudimg-amd64.img
URL=https://cloud-images.ubuntu.com/jammy/current/$IMG
VMID=9000

# Download on the node
wget -q -O /var/lib/vz/template/iso/$IMG $URL

# Create skeleton VM
qm create $VMID --name ubuntu-2204-template --memory 2048 --cores 2 \
  --net0 virtio,bridge=vmbr0 --machine q35 --bios ovmf \
  --efidisk0 local-lvm:1,efitype=4m,pre-enrolled-keys=1 \
  --scsihw virtio-scsi-single --cpu cputype=host --ostype l26 \
  --agent enabled=1 --serial0 socket --vga serial0

# Import cloud image, attach, configure cloud-init
qm disk import $VMID /var/lib/vz/template/iso/$IMG local-lvm
qm set $VMID --scsi0 local-lvm:vm-$VMID-disk-0,discard=on,iothread=1,ssd=1
qm set $VMID --boot order=scsi0
qm set $VMID --ide2 local-lvm:cloudinit

# Resize to a sensible base size (image is usually ~2 GiB)
qm disk resize $VMID scsi0 +30G

# Convert to template (irreversible)
qm template $VMID
```

Then clone for each new instance:

```bash
qm clone 9000 110 --name web-1 --full
qm set 110 --ciuser deploy --sshkeys ~/.ssh/authorized_keys \
           --ipconfig0 ip=10.0.0.110/24,gw=10.0.0.1
qm start 110
```

`pmx-vm from-image` automates the import+attach+cloudinit chain.

---

## Hardware configuration

```bash
# Resources
qm set $VMID --memory 8192 --cores 4 --sockets 1
qm set $VMID --balloon 2048             # min RAM when ballooning

# Disks
qm set $VMID --scsi1 local-lvm:50,discard=on,iothread=1,ssd=1
qm disk resize $VMID scsi0 +20G

# Move a disk between storages (live)
qm disk move $VMID scsi0 ceph-rbd --delete

# Network
qm set $VMID --net0 virtio,bridge=vmbr0,tag=10           # VLAN 10
qm set $VMID --net1 virtio,bridge=vmbr1,firewall=1

# CPU & NUMA
qm set $VMID --cpu cputype=host
qm set $VMID --numa 1                    # required for hot-add memory

# Hot-plug (must be enabled BEFORE start)
qm set $VMID --hotplug network,disk,cpu,memory,usb
```

`qm config $VMID` always shows the current canonical state.

---

## Snapshots, clones, templates

```bash
qm snapshot $VMID before-upgrade --description "before kernel upgrade"
qm listsnapshot $VMID
qm rollback $VMID before-upgrade
qm delsnapshot $VMID before-upgrade

# Clones
qm clone $VMID 200 --name copy --full         # full = independent disks
qm clone $VMID 200 --name linked              # linked = COW from template

# Template
qm template $VMID                              # irreversible
```

Note: snapshots require a storage that supports them. With PVE 9.0+, thick
LVM shared storage (FC/iSCSI SANs) supports snapshots too.

---

## Live and offline migration

```bash
qm migrate $VMID pve02 --online                # live, requires shared/SAN
qm migrate $VMID pve02                         # offline (shutdown then move)
qm migrate $VMID pve02 --online --with-local-disks   # migrate local disks too
```

If CPU types differ across nodes, set `cputype=x86-64-v3` (or older) for
broad compatibility.

---

## Guest agent and monitoring

Install `qemu-guest-agent` inside the guest, then:

```bash
qm set $VMID --agent enabled=1,fstrim_cloned_disks=1
qm agent $VMID ping
qm agent $VMID get-osinfo
qm agent $VMID fsfreeze-freeze         # then snapshot, then fsfreeze-thaw
qm agent $VMID exec -- bash -lc 'uptime'
```

Without the agent, `qm shutdown` falls back to ACPI and `vzdump --mode snapshot`
cannot quiesce filesystems.

---

## GPU / PCIe passthrough

Prereqs (node side, persistent):

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet intel_iommu=on iommu=pt"
update-grub

# /etc/modules
vfio
vfio_iommu_type1
vfio_pci
```

Find the device:

```bash
lspci -nn | grep -i nvidia
```

Bind to vfio-pci (one-time):

```bash
echo "options vfio-pci ids=10de:1234,10de:5678" > /etc/modprobe.d/vfio.conf
update-initramfs -u
reboot
```

Attach to VM:

```bash
qm set $VMID --machine q35
qm set $VMID --bios ovmf
qm set $VMID --hostpci0 0000:01:00,pcie=1,x-vga=1     # x-vga for primary GPU
```

Guests using GPUs should have `cpu host,hidden=1,flags=+pcid` to mask the
hypervisor from anti-VM checks.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TASK ERROR: can't lock file` | Previous task still running OR died holding lock | `ps -ef \| grep qm`; if no task, `qm unlock <vmid>` |
| `qm shutdown` hangs forever | No guest agent OR `agent enabled=0` | Install qemu-guest-agent; set `agent enabled=1`, reboot guest |
| Live migration fails: "incompatible CPU" | `cputype=host` across mixed CPUs | Use `cputype=x86-64-v3` cluster-wide |
| Disk imports as `unused0` | Not attached to a bus after import | `qm set ... --scsi0 local-lvm:vm-<vmid>-disk-0` then set boot order |
| Cloud-init values persist across reboots | Drive is still attached | `qm set <vmid> --delete ide2` once provisioned |
| VM stays at "BIOS" screen on q35+ovmf | EFI vars not persisted | Ensure `--efidisk0 ...,pre-enrolled-keys=1` was set BEFORE first boot |
| Slow disk I/O | scsihw=virtio-scsi-pci (single controller, no iothread) | Switch to `virtio-scsi-single`, set `iothread=1` per disk |
