# Troubleshooting — Reference

Symptom-indexed playbook. Each entry is independent — jump straight to the
matching symptom.

## Table of contents

1. [Cannot connect via skill helpers](#cannot-connect-via-skill-helpers)
2. [Authentication issues](#authentication-issues)
3. [VM / container won't start](#vm--container-wont-start)
4. [Storage issues](#storage-issues)
5. [Network issues](#network-issues)
6. [Cluster / quorum issues](#cluster--quorum-issues)
7. [Backup / restore failures](#backup--restore-failures)
8. [Performance issues](#performance-issues)
9. [Logs to consult — by symptom](#logs-to-consult--by-symptom)

---

## Cannot connect via skill helpers

```bash
scripts/pmx-doctor
```

Then map the failing line:

| Failure | Where to look |
|---------|---------------|
| profile not loaded / no active profile | Run `scripts/pmx-onboard`; check `~/.config/proxmox-admin/active` |
| tcp X:22 unreachable | Firewall / routing / wrong host. Test from same shell: `nc -vz <host> 22` |
| ssh login failed: Permission denied (publickey) | Key not authorized OR wrong user. Re-run `ssh-copy-id`; check `ssh.user` |
| Host key verification failed | First connection. Set `strict_host_key_checking: accept-new` once |
| REST /version returned 401 | API token issue → see [api-tokens.md](api-tokens.md) |
| REST cert error | TLS verify on with self-signed cert. Set `verify_tls: false` or install real cert |

---

## Authentication issues

See dedicated guide: `references/api-tokens.md`. Quick triage:

```bash
# Check user's effective permissions
scripts/pmx-ssh 'pveum user permissions automation@pve --path /'

# Check token's effective permissions
scripts/pmx-ssh "pveum user token permissions automation@pve skill --path /"
```

Empty output on the token = token was created with `--privsep 1` and never
attached to an ACL. Either delete+recreate with `--privsep 0` or attach:

```bash
scripts/pmx-ssh "pveum acl modify / --token 'automation@pve!skill' --role pmx-skill --propagate 1"
```

---

## VM / container won't start

```bash
# Always start here
scripts/pmx-ssh 'qm config <vmid>'       # or pct config
scripts/pmx-ssh 'qm status <vmid>'

# Inspect the latest task
scripts/pmx-ssh 'tail -n 200 /var/log/pve/tasks/active'
scripts/pmx-ssh 'ls -la /var/log/pve/tasks/index'
```

Common causes:

| Error | Cause | Fix |
|-------|-------|-----|
| `can't lock file '/var/lock/qemu-server/lock-<vmid>.conf'` | Stale lock | `qm unlock <vmid>` (only after confirming no task is running) |
| `volume X does not exist` | Disk on storage that's offline | `pvesm status`; bring storage back; or edit config and re-attach |
| `kvm not available` | Nested virt disabled OR missing CPU flag | Host: `egrep -c '(vmx|svm)' /proc/cpuinfo`; enable VT-x/AMD-V in firmware |
| `failed to find iommu group` (passthrough) | IOMMU not on, OR device shared with host | Boot grub with `intel_iommu=on iommu=pt`; check `dmesg \| grep IOMMU` |
| Container: `tar exited with status 2` | Template tarball corrupt or wrong arch | `pveam download` again; `file local:vztmpl/...` |

---

## Storage issues

```bash
scripts/pmx-storage status
scripts/pmx-ssh 'lvs; vgs; df -h /var/lib/vz; zpool status'
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pvesm status` shows storage `inactive` | Mount failed | `mount -a`; `journalctl -xeu pvestatd` |
| Disk imports keep ending up as `unused0` | Forgot to attach after `qm disk import` | `qm set <vmid> --scsi0 <storage>:vm-<vmid>-disk-0` |
| Thin pool 95%+ full | Over-provisioning bit you | `lvs`; expand pool OR `vzdump` and delete unused volumes |
| Backup hangs on snapshot | Storage doesn't support snapshots | Switch `--mode suspend` or `--mode stop` |
| Snapshots disabled on shared LVM | PVE < 9.0 | Upgrade to PVE 9.0+ (thick LVM snapshots) |

---

## Network issues

```bash
scripts/pmx-ssh 'ip -br link; ip -br addr; brctl show'
scripts/pmx-ssh 'pvesh ls /cluster/sdn'   # SDN status
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| VM no carrier on `eth0` | Wrong bridge OR bridge port down | `qm config <vmid>`; verify bridge with `ip -br link` |
| Guest gets no DHCP lease | No DHCP server on VNet OR firewall blocks | Test `pct exec ... -- dhclient -v`; check upstream DHCP |
| VLAN trunking doesn't work | Bridge not VLAN-aware | `bridge-vlan-aware yes`; `ifreload -a` |
| `ifreload -a` drops mgmt link | Bridge port reconfig | Stage with `ifreload -a -n`; have console ready |
| Ceph slow / heartbeat misses | MTU mismatch storage bridge | `ping -M do -s 8972 <peer>`; align MTU end-to-end |

---

## Cluster / quorum issues

See `references/cluster-ha.md` for full coverage. Triage:

```bash
scripts/pmx-cluster status
scripts/pmx-ssh 'journalctl -u corosync --since "30 minutes ago" -p err'
```

If quorum is lost on a single-node recovery scenario only:
`scripts/pmx-ssh 'pvecm expected 1'`. Otherwise restore connectivity first.

---

## Backup / restore failures

```bash
scripts/pmx-backup list
scripts/pmx-ssh 'cat /var/log/pve/tasks/index | tail -n 20'
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `VM is locked (backup)` | Previous backup task died holding lock | `qm unlock <vmid>` after confirming no active task |
| PBS auth fails | Token expired OR password format wrong | Use `TOKENID:TOKENSECRET`; rotate via PBS |
| Restore: "storage X does not exist" | `--storage` mismatch | Pass `--storage <target>` explicitly |
| Restore is very slow over WAN | No bandwidth limit; CPU compression bottleneck | Use PBS sync-jobs locally then qmrestore from local copy |

---

## Performance issues

```bash
scripts/pmx-ssh 'pveperf'
scripts/pmx-ssh 'iostat -xz 1 5; vmstat 1 5'
scripts/pmx-ssh 'arc_summary | head -50'   # if ZFS
```

| Symptom | Likely fix |
|---------|-----------|
| Slow VM disk I/O | `--scsihw virtio-scsi-single`, `--scsi0 ...,iothread=1,ssd=1,discard=on` |
| Slow ZFS writes | Cap ARC; add SLOG with PLP NVMe; verify ashift |
| High CPU steal in guests | Over-committed pCPUs; reduce vcpu counts or migrate guests |
| Long live migration | Use 10 GbE+ on a dedicated migration network; tune `migration_speed` |
| Random latency spikes | Check `vmstat -wt 1` for swap-in; ZFS arc evictions; thermal throttling (`turbostat`) |

---

## Logs to consult — by symptom

| Symptom | Path |
|---------|------|
| Web/API errors | `journalctl -u pveproxy -u pvedaemon -e` |
| VM lifecycle errors | `/var/log/pve/tasks/active`, `/var/log/pve/tasks/index` |
| Cluster membership | `journalctl -u corosync -u pve-cluster -e` |
| HA decisions | `journalctl -u pve-ha-lrm -u pve-ha-crm -e` |
| Network reload | `journalctl -u networking -e`; `dmesg \| tail -50` |
| Backup jobs | `/var/log/vzdump/`; PBS UI → Tasks |
| Kernel issues | `dmesg --ctime`; `journalctl -k -p err` |
| Firewall drops | `journalctl -t kernel -g 'pve-fw'`; `pve-firewall debug` |
