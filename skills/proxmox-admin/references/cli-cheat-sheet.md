# CLI Cheat Sheet — `qm`, `pct`, `pvesm`, `pvecm`, `pvesh`, `pveum`, `vzdump`

Compact one-screen reference. Most commands have richer variants in their
domain-specific reference file.

## VMs — `qm`

```bash
qm list                                    qm status <id>
qm start | shutdown | stop | reboot <id>   qm reset | suspend | resume <id>
qm config <id>                              qm set <id> --memory 4096 --cores 4
qm clone <src> <dst> --name X --full        qm template <id>
qm migrate <id> <node> --online             qm unlock <id>
qm destroy <id> [--purge]                   qm disk import <id> <img> <storage>
qm disk resize <id> scsi0 +20G              qm disk move <id> scsi0 <storage> --delete
qm snapshot <id> <name>                     qm rollback <id> <name>
qm listsnapshot <id>                        qm delsnapshot <id> <name>
qm agent <id> ping                          qm agent <id> get-osinfo
qm terminal <id>                            qm monitor <id>
```

Cloud-init: `qm set <id> --ide2 <storage>:cloudinit --ciuser X --sshkeys K --ipconfig0 ...`.
Full ladder in `vm-management.md`.

## Containers — `pct`

```bash
pct list                                   pct status <id>
pct start | shutdown | stop | reboot <id>  pct enter <id>     pct console <id>
pct exec <id> -- <cmd>                     pct config <id>
pct create <id> <template> --hostname X --memory M --cores N --rootfs <s>:GB \
   --net0 name=eth0,bridge=vmbrX,ip=dhcp --unprivileged 1 --features nesting=1
pct set <id> --memory 4096 --features nesting=1,keyctl=1
pct set <id> --mp0 /mnt/host,mp=/data       pct destroy <id>
pct snapshot <id> <name>                    pct rollback <id> <name>
pct clone <src> <dst> --hostname X --full   pct migrate <id> <node> --restart 1
```

## Storage — `pvesm` / `pveam`

```bash
pvesm status                                pvesm list <storage>
pvesm add <type> <id> ...                   pvesm remove <id>
pvesm set <id> --content images,backup,iso,vztmpl,snippets,rootdir
pveam update                                pveam available --section system
pveam download <storage> <template>         pveam list <storage>
```

## Cluster — `pvecm` and `ha-manager`

```bash
pvecm create <name>                         pvecm add <ip>
pvecm status                                pvecm nodes
pvecm delnode <name>                        pvecm expected <n>   (recovery only)
ha-manager add vm:<id> --state started --max_restart 3
ha-manager status                           ha-manager config
ha-manager groupadd web --nodes "pve01:2,pve02:2,pve03:1"
ha-manager set-disarm 1 | 0                 (PVE 9.2+)
ha-manager loadbalancer set --enabled 1 --cpu-threshold 80
```

## REST helpers — `pvesh`

```bash
pvesh ls /                                  pvesh get /nodes
pvesh get /cluster/resources?type=vm        pvesh get /nodes/<n>/qemu/<id>/config
pvesh create /nodes/<n>/qemu -i             # interactive create
pvesh set    /nodes/<n>/qemu/<id>/config -i
pvesh delete /nodes/<n>/qemu/<id>           pvesh apply /cluster/sdn
```

## Auth — `pveum`

```bash
pveum user add <user>@pve                   pveum user list
pveum role add <name> --privs "VM.Audit VM.PowerMgmt ..."
pveum acl modify <path> --user <u> --role <r> --propagate 1
pveum acl modify <path> --token '<u>!<id>' --role <r> --propagate 1
pveum user token add <u>@pve <id> --privsep 0|1
pveum user token list <u>@pve
pveum user token permissions <u>@pve <id> --path <p>
pveum user token Regen   <u>@pve <id>       # rotate secret
pveum user token delete  <u>@pve <id>       # revoke
```

## Backup — `vzdump`, `qmrestore`, `pct restore`

```bash
vzdump <id> [--all] --storage <s> --mode snapshot --compress zstd
vzdump <id> --prune-backups keep-last=3,keep-daily=7,keep-weekly=4
qmrestore <file> <vmid> --storage <s>
pct restore <ctid> <file> --storage <s>
```

## Firewall — `pve-firewall`

```bash
pve-firewall enable | disable | restart | status
# /etc/pve/firewall/cluster.fw  (datacenter rules)
# /etc/pve/nodes/<node>/host.fw (per-node)
# /etc/pve/firewall/<vmid>.fw   (per-guest)
```

## File system paths

```
/etc/pve/                            cluster config (pmxcfs FUSE; sync'd)
/etc/pve/qemu-server/<vmid>.conf     VM config
/etc/pve/lxc/<ctid>.conf             CT config
/etc/pve/storage.cfg                 storage definitions
/etc/pve/nodes/<node>/host.fw        per-node firewall
/etc/pve/firewall/cluster.fw         datacenter firewall
/var/lib/vz/template/iso/            ISO uploads
/var/lib/vz/template/cache/          LXC templates
/var/lib/vz/dump/                    vzdump output
/var/log/pve/tasks/                  task logs (active + index)
/var/log/vzdump/                     backup job logs
```

## One-liners

```bash
# Top resource hogs across the cluster
pvesh get /cluster/resources --output-format=json | \
  jq -r '.[] | select(.type=="qemu") | [.vmid,.name,.cpu,.mem] | @tsv' | \
  sort -k4 -nr | head

# Stale lock cleanup (only when you've confirmed no live task)
for f in /var/lock/qemu-server/lock-*.conf; do
  vmid=$(echo "$f" | sed 's/.*lock-\([0-9]*\)\.conf/\1/')
  qm unlock "$vmid" 2>/dev/null
done

# Show every running VM's primary disk and its size
for id in $(qm list | awk 'NR>1 && $3=="running" {print $1}'); do
  echo "VM $id:"; qm config $id | grep -E '^(scsi0|virtio0|sata0|ide0)'
done
```
