# PegaProx — Community Multi-Cluster Orchestrator

Read this only when the user explicitly mentions PegaProx, ProxLB,
cross-cluster live migration, or vCenter-style multi-cluster control.

> PegaProx is **community-maintained** (AGPL-3.0), not affiliated with
> Proxmox Server Solutions GmbH. Validate any install script and pin
> a known-good version before production use. Always check the official
> repo for current install instructions; do not run an install script
> off cached docs.

## When PegaProx adds value

- 2+ Proxmox clusters or many standalone nodes to manage from one UI
- You want DRS-style auto-balancing across nodes (ProxLB engine)
- Cross-cluster live migration of running VMs
- Centralized OIDC / Entra ID / Keycloak / Authentik SSO without per-node
  realm config
- Bulk CVE scanning across the fleet

If you are on PVE 9.2+ with the **built-in Dynamic Load Balancer**, much
of what people previously needed PegaProx for is now native — evaluate
that first.

## Install location

Run PegaProx in a dedicated LXC container or small Debian VM so it does
not interfere with cluster maintenance. Sample sizing:

| Fleet | RAM | CPU | Disk |
|-------|-----|-----|------|
| 1-3 nodes | 1 GB | 1 vCPU | 4 GB |
| 4-10 nodes | 2 GB | 2 vCPU | 8 GB |
| > 10 nodes | 4+ GB | 4 vCPU | 16+ GB |

```bash
scripts/pmx-ct create 999 pegaprox debian-12-standard \
    --memory 2048 --cores 2 --rootfs local-lvm:8 \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp
scripts/pmx-ct exec 999 -- bash -c 'apt update && apt -y install curl ca-certificates'
# Then follow the upstream install script from the official repo.
```

## Connecting a cluster to PegaProx

PegaProx connects to each Proxmox cluster via an API token, exactly the
flow the skill already uses. Reuse the `pmx-skill` token or create a
dedicated `pegaprox` token with a broader role if you want PegaProx to
modify config (vs. read-only monitoring).

```bash
# Dedicated read+migrate role for PegaProx
pveum role add pegaprox --privs \
  "VM.Audit VM.Migrate VM.PowerMgmt Datastore.Audit \
   Sys.Audit SDN.Audit Pool.Audit"
pveum acl modify / --user automation@pve --role pegaprox --propagate 1
pveum user token add automation@pve pegaprox --privsep 0
```

Then in the PegaProx UI: Datacenter → Add → IP + 8006 + token, repeat per
cluster.

## ProxLB (load balancer)

ProxLB is the open-source engine PegaProx uses for DRS. It can run
standalone (without PegaProx) — useful if the goal is purely auto-balancing.

Typical thresholds for homelab:

```
CPU high water mark   : 80%
Memory high water mark: 85%
Sample window         : 5 minutes
Max concurrent migrations: 2
Allow auto-migrate    : evening hours only (custom cron window)
```

In a power-sensitive homelab, configure aggressive consolidation at night
+ wake-on-LAN scripts so idle nodes can spin down.

## Cross-cluster migration

PegaProx wraps the `vzdump → scp → qmrestore` workflow with an
optimization layer (parallel streams, no temp storage on source).
For one-off migrations without PegaProx, see
[cluster-ha.md#cross-cluster-moves](cluster-ha.md#cross-cluster-moves).

## Validation checklist

Before relying on PegaProx in production:

- [ ] Pin a specific release version (no `:latest`, no curl|bash from main)
- [ ] Verify the binary or container image hash against the project release
- [ ] Run for at least 1 week in observe-only mode (no auto-migration)
- [ ] Confirm fail-safe: PegaProx outage must not disrupt the underlying clusters
- [ ] Test cross-cluster migration with a throwaway VM end-to-end
- [ ] Verify the API tokens are scoped to PegaProx-specific needs (not root)
- [ ] Snapshot/back-up PegaProx itself before any major upgrade

## Resources

- Proxmox VE official docs — https://pve.proxmox.com/pve-docs/
- ProxLB engine — https://github.com/gyptazy/ProxLB
- PVE 9.2 built-in load balancer — `ha-manager loadbalancer` (see cluster-ha.md)
