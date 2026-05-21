# Cluster & High Availability — Reference

Read this for `pvecm` (cluster), `ha-manager` (HA), and quorum recovery.

## Table of contents

1. [Cluster basics](#cluster-basics)
2. [Create / join / leave](#create--join--leave)
3. [Quorum, votes, and fencing](#quorum-votes-and-fencing)
4. [Single-node recovery (`expected 1`)](#single-node-recovery-expected-1)
5. [HA resources and groups](#ha-resources-and-groups)
6. [Affinity rules (PVE 9.0+)](#affinity-rules-pve-90)
7. [Dynamic Load Balancer (PVE 9.2+)](#dynamic-load-balancer-pve-92)
8. [Cross-cluster moves](#cross-cluster-moves)
9. [Common pitfalls](#common-pitfalls)

---

## Cluster basics

A Proxmox cluster:

- shares `/etc/pve` via pmxcfs (Corosync + SQLite-backed FUSE)
- uses Corosync for membership and quorum
- needs an odd number of voting members (3, 5, 7) OR a QDevice for 2-node
- requires a dedicated low-latency network (< 5 ms RTT, < 1 ms preferred)

A "node" can join only one cluster at a time. To re-cluster, wipe `/etc/pve`.

---

## Create / join / leave

```bash
# On the first node
pvecm create my-cluster

# On each additional node (run there)
pvecm add 10.0.0.10                    # IP of an existing member
# It will prompt for the root password of the existing node.

# Use a dedicated link for Corosync (best practice)
pvecm add 10.0.0.10 --link0 10.10.0.20,priority=20 --link1 10.20.0.20

# View status
pvecm status
pvecm nodes

# Remove a permanently-dead node from the surviving cluster
pvecm delnode pve03
# Then on each remaining node:
ssh root@pve01 'rm -rf /etc/pve/nodes/pve03'
```

---

## Quorum, votes, and fencing

Cluster is "quorate" when more than 50% of expected votes are present. By
default each node has 1 vote.

```bash
pvecm status                            # look for Quorate: Yes
pvecm expected <n>                      # change expected votes (emergency)
```

When quorum is lost, `/etc/pve` becomes read-only and you cannot start/stop
or change VMs. Fencing kicks in for HA-managed resources: the surviving
quorate partition will fence (power-off) nodes that lost quorum so HA can
restart their VMs safely elsewhere.

A 2-node cluster has no quorum after one node dies. Use a **QDevice**:

```bash
# On a third low-power machine (Pi, mini-PC), NOT a cluster member
apt install corosync-qnetd

# On every cluster node
apt install corosync-qdevice
pvecm qdevice setup 10.0.0.5 -f
```

The QDevice adds an external tiebreaker vote without being a cluster member.

---

## Single-node recovery (`expected 1`)

Only use when other nodes are permanently gone and you must recover VMs:

```bash
pvecm expected 1                       # force quorum on the last node
# /etc/pve becomes writable; back up VMs, then rebuild the cluster.
```

This is destructive — once you do it, do not re-introduce the old nodes
without a clean reinstall.

---

## HA resources and groups

```bash
# Add a VM to HA
ha-manager add vm:100 --state started --max_restart 3 --max_relocate 2

# Add a container
ha-manager add ct:200 --state started

# Define a group (e.g., pin web tier to specific nodes)
ha-manager groupadd web-tier --nodes "pve01:2,pve02:2,pve03:1" --nofailback 0
ha-manager set vm:100 --group web-tier

# Status
ha-manager status
ha-manager config

# Maintenance: disarm the HA stack cluster-wide (PVE 9.2+)
ha-manager set-disarm 1                # pause fencing & state changes
# ... do maintenance ...
ha-manager set-disarm 0                # rearm
```

`--state` options:
- `started` — keep running, restart on failure
- `stopped` — keep stopped (still HA-managed for fencing semantics)
- `disabled` — fully ignore

`--nofailback 0` means VMs return to higher-priority nodes when they recover.

---

## Affinity rules (PVE 9.0+)

Constrain where HA resources can co-locate. Two kinds:

```bash
# Positive affinity — keep these together
ha-manager affinity create webstack --positive --resources vm:100,vm:101,vm:102

# Negative affinity — keep these apart (e.g., DB replicas)
ha-manager affinity create db-spread --negative --resources vm:200,vm:201,vm:202
```

The scheduler respects affinity during placement, restart, and load
balancing.

---

## Dynamic Load Balancer (PVE 9.2+)

Built-in DRS equivalent. Off by default.

```bash
# Enable
ha-manager loadbalancer set --enabled 1 \
    --cpu-threshold 80 \
    --memory-threshold 85 \
    --check-interval 5m \
    --max-migrations 2

# Status
ha-manager loadbalancer status
```

Set conservative thresholds in production. Aggressive auto-migration in
storage-thrash conditions can degrade things further.

---

## Cross-cluster moves

Native Proxmox does not yet support cross-cluster live migration.
Workflow:

1. Stop or shutdown the VM.
2. `vzdump --remove 0 --compress zstd <vmid>` on the source cluster.
3. Copy the dump to the target cluster's backup storage.
4. `qmrestore <dump-file> <new-vmid> --storage <target-storage>` on the
   destination.
5. Update networking / firewall / HA membership.

Community tooling like PegaProx wraps this into a one-click "cross-cluster
migration" UX — see `references/pegaprox.md`.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `pvecm status` shows split-brain | Network partition between nodes | Verify Corosync links + ring0/1 reachability; fix MTU/firewall |
| `/etc/pve` is read-only | Lost quorum | Restore quorum (start missing node OR `pvecm expected N` if recovery) |
| HA VM never restarts after node death | Resource not added to HA OR `--state` is disabled | `ha-manager add vm:<id> --state started` |
| Fence loop — node keeps rebooting | Watchdog firing during slow boot | Check `/etc/default/pve-ha-manager`; ensure storage mounts before HA starts |
| QDevice silently inactive | Time drift between qnetd and nodes | `chronyc tracking` on all parties; offset must be < 100ms |
| Adding a node fails: "host with same name already in cluster" | Stale `/etc/pve/nodes/<name>` | `pvecm delnode <name>` then `rm -rf /etc/pve/nodes/<name>` |
