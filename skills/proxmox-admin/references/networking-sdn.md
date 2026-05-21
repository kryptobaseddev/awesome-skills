# Networking & SDN — Reference

Read this for bridges, VLANs, bonds, and the SDN stack (zones, VNets,
fabrics, EVPN). PVE 9.0 introduced **SDN Fabrics** with OpenFabric / OSPF;
9.1 added richer SDN observability; 9.2 added native WireGuard and BGP
support inside SDN.

## Table of contents

1. [Network model overview](#network-model-overview)
2. [Bridges and bonds — `/etc/network/interfaces`](#bridges-and-bonds--etcnetworkinterfaces)
3. [SDN — when to enable, when not to](#sdn--when-to-enable-when-not-to)
4. [SDN zones (VLAN, VxLAN, EVPN, Simple)](#sdn-zones-vlan-vxlan-evpn-simple)
5. [SDN VNets and subnets](#sdn-vnets-and-subnets)
6. [SDN Fabrics (PVE 9.0+)](#sdn-fabrics-pve-90)
7. [BGP / EVPN / WireGuard (PVE 9.2+)](#bgp--evpn--wireguard-pve-92)
8. [Verifying and reloading](#verifying-and-reloading)
9. [Common pitfalls](#common-pitfalls)

---

## Network model overview

```
              ┌──────────────┐
   Internet ──┤ Router / FW  │
              └──────┬───────┘
                     │  (VLAN trunk)
              ┌──────┴───────┐
              │  Switch port │
              └──────┬───────┘
                     │
                 vmbr0  (Linux bridge or OVS, kernel-level)
                ╱     ╲
          tap-vm     veth-ct
         (KVM NIC)  (LXC NIC)
```

`vmbr0` is the default management bridge on a fresh install. Anything more
complex (multiple VLANs per guest, overlay networking, multi-cluster L3)
belongs in SDN.

---

## Bridges and bonds — `/etc/network/interfaces`

```text
auto lo
iface lo inet loopback

# Physical NICs (do not assign IPs here when used as bridge ports)
iface eno1 inet manual
iface eno2 inet manual

# Bond (LACP) for redundancy
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-mode 802.3ad
    bond-xmit-hash-policy layer3+4
    bond-miimon 100

# Management bridge on bond0, with VLAN-aware so guests can tag
auto vmbr0
iface vmbr0 inet static
    address 10.0.0.10/24
    gateway 10.0.0.1
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094

# Storage-only bridge (jumbo)
auto vmbr1
iface vmbr1 inet static
    address 10.10.0.10/24
    bridge-ports bond1
    bridge-stp off
    bridge-fd 0
    mtu 9000
```

Apply changes:

```bash
ifreload -a
```

`ifreload` works without dropping connections in 95% of cases. Reserve a
full `systemctl restart networking` for major refactors and have console
access ready.

---

## SDN — when to enable, when not to

Use SDN when:

- multiple VLANs per host with policy/QoS per VNet
- overlay networks across nodes (VxLAN/EVPN)
- consistent network config across a multi-node cluster
- shared inter-node routing (Fabrics) for Ceph or EVPN underlay

Stick with plain `vmbrX` when:

- single bridge, single VLAN
- two or three nodes with simple connectivity
- you do not want the per-node `pvesh apply` reload cycle

Enable SDN via Datacenter → SDN in the GUI, or CLI:

```bash
apt install libpve-network-perl  # already installed on default 8.1+
pvesh create /cluster/sdn         # apply current SDN state
```

---

## SDN zones (VLAN, VxLAN, EVPN, Simple)

```bash
# VLAN zone — tags VLAN IDs on an existing bridge
pvesh create /cluster/sdn/zones --zone vlan10 --type vlan --bridge vmbr0

# Simple zone — pure L2 segment, no VLAN, useful for management VNets
pvesh create /cluster/sdn/zones --zone simple-mgmt --type simple

# VxLAN zone — overlay across nodes
pvesh create /cluster/sdn/zones --zone vxlan-prod --type vxlan \
    --peers 10.10.0.10,10.10.0.11,10.10.0.12

# EVPN zone — multi-node L3 overlay (needs a controller; see Fabrics)
pvesh create /cluster/sdn/zones --zone evpn0 --type evpn \
    --controller frr0 --vrf-vxlan 9000
```

---

## SDN VNets and subnets

A VNet is the actual virtual L2 segment guests attach to.

```bash
pvesh create /cluster/sdn/vnets --vnet vmgmt --zone simple-mgmt
pvesh create /cluster/sdn/vnets/vmgmt/subnets --subnet 10.20.0.0/24 --gateway 10.20.0.1 --snat 1
pvesh create /cluster/sdn                     # apply changes
```

Attach a VM/CT to the VNet:

```bash
qm set 100 --net0 virtio,bridge=vmgmt
pct set 200 --net0 name=eth0,bridge=vmgmt,ip=10.20.0.50/24,gw=10.20.0.1
```

---

## SDN Fabrics (PVE 9.0+)

Fabrics let multiple nodes participate in a routed L3 network without
manual per-node FRR config. PVE 9.0 supports OpenFabric and OSPF.

```bash
pvesh create /cluster/sdn/fabrics --id underlay --protocol openfabric \
    --area 0001

pvesh create /cluster/sdn/fabrics/underlay/nodes --node pve01 --interfaces eno3
pvesh create /cluster/sdn/fabrics/underlay/nodes --node pve02 --interfaces eno3
pvesh create /cluster/sdn/fabrics/underlay/nodes --node pve03 --interfaces eno3
pvesh create /cluster/sdn
```

Typical use: a leaf-spine Ceph underlay, or the IP fabric beneath an EVPN
overlay.

---

## BGP / EVPN / WireGuard (PVE 9.2+)

PVE 9.2 added native BGP and WireGuard support inside SDN. These are
config-driven and use FRR under the hood:

```bash
# BGP controller for EVPN
pvesh create /cluster/sdn/controllers --controller frr0 --type bgp \
    --asn 64512 --peers 10.10.0.1
# Then route maps / prefix lists via the GUI or pvesh set
```

WireGuard tunnels can be declared as SDN-managed peers — useful to extend
a homelab cluster to a remote site without manual `wg-quick` files.
Consult `pvesh ls /cluster/sdn/controllers/<id>` for the exact options
since they evolve per minor release.

---

## Verifying and reloading

```bash
pvesh apply /cluster/sdn         # apply pending changes (alias: pvesh create /cluster/sdn)
ip -br link                       # confirm bridges and links
brctl show                        # legacy view
bridge -d link                    # VLAN config per port
ifquery -av                       # iproute2 view of /etc/network/interfaces
```

SDN status in the GUI (PVE 9.1+) now shows learned EVPN MACs, IP-VRFs, and
fabric routes inline — prefer it when troubleshooting unfamiliar topology.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `vmbr0` works, new VLANs don't tag | Bridge not VLAN-aware | Add `bridge-vlan-aware yes` + `bridge-vids 2-4094`; `ifreload -a` |
| Guest has IP but cannot reach gateway | SNAT not set on SDN subnet | `--snat 1` on subnet; reload SDN |
| EVPN flapping between nodes | Underlay not symmetric | Verify Fabrics underlay convergence with `vtysh -c 'show ip ospf neighbor'` |
| `ifreload -a` drops mgmt link | Bridge port reconfig replacing eno1 with bond0 | Stage via `ifreload -a -n` first; have console ready |
| Cloud-init VM gets no DHCP | Bridge MAC filtering / no DHCP server on VNet | Test with `pct exec ... -- dhclient -v`; check subnet DHCP server |
| Ceph slow due to MTU mismatch | Storage bridge missing `mtu 9000` end-to-end | Set on bridge AND switch ports AND guest interfaces |
