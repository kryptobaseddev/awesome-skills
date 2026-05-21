# Security Hardening — Reference

Apply selectively. Order matters: do (1)-(4) on every node; (5)-(8) when
exposing to untrusted networks.

## Table of contents

1. [SSH hardening](#1-ssh-hardening)
2. [Firewall — datacenter, node, VM/CT](#2-firewall--datacenter-node-vmct)
3. [TLS certificates (ACME via web GUI / CLI)](#3-tls-certificates-acme-via-web-gui--cli)
4. [Two-factor authentication](#4-two-factor-authentication)
5. [Realms (OIDC / LDAP / SAML)](#5-realms-oidc--ldap--saml)
6. [fail2ban](#6-fail2ban)
7. [Auditing and CVE monitoring](#7-auditing-and-cve-monitoring)
8. [Privileged operations checklist](#8-privileged-operations-checklist)

---

## 1. SSH hardening

```bash
# /etc/ssh/sshd_config.d/10-pmx-hardening.conf
PermitRootLogin prohibit-password    # key auth only for root
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitEmptyPasswords no
X11Forwarding no
AllowAgentForwarding no
ClientAliveInterval 60
ClientAliveCountMax 3
```

```bash
systemctl reload ssh
```

If creating a dedicated admin user (not root), grant cluster-wide root sudo
only for the few commands the user needs.

---

## 2. Firewall — datacenter, node, VM/CT

Proxmox firewall has three scopes:

| File | Scope |
|------|-------|
| `/etc/pve/firewall/cluster.fw` | Datacenter — defaults applied to every node |
| `/etc/pve/nodes/<node>/host.fw` | Node — overrides datacenter for this host |
| `/etc/pve/firewall/<vmid>.fw` | Per VM/CT — guest-level rules |

Enable the datacenter firewall:

```text
# /etc/pve/firewall/cluster.fw
[OPTIONS]
enable: 1
policy_in: DROP
policy_out: ACCEPT

[RULES]
IN ACCEPT -i management0 -source 10.0.0.0/24 -log nolog # mgmt LAN
IN ACCEPT -i management0 -p tcp -dport 22 -source 10.0.0.0/24 # SSH
IN ACCEPT -i management0 -p tcp -dport 8006 -source 10.0.0.0/24 # web/API
```

Then activate per-node:

```bash
pve-firewall enable
pve-firewall status
```

Before flipping `policy_in: DROP`, **always** add an allow rule for the
management subnet — otherwise you lock yourself out.

---

## 3. TLS certificates (ACME via web GUI / CLI)

```bash
# Add an ACME account (Let's Encrypt)
pvenode acme account register default admin@example.com

# Order a certificate for this node
pvenode acme cert order --force
```

DNS challenge with a supported provider (Cloudflare, etc.):

```bash
pvenode config set --acme domains=pve01.example.com \
    --acme-domains "pve01.example.com=plugin=cloudflare;CF_Account_ID=...;CF_Token=..."
pvenode acme cert order
```

After issuing, `host.verify_tls: true` should work in the profile and the
`-k` curl flag becomes unnecessary.

---

## 4. Two-factor authentication

TOTP is the simplest. Enable per-user under Datacenter → Users → TFA.
WebAuthn (FIDO2 hardware keys) is recommended for production admins.

```bash
# CLI: enable TOTP for a user
pveum user modify root@pam --comment "with TFA"
# Then login to the web UI as the user to enroll a TOTP secret.
```

API tokens bypass 2FA by design — that's why narrow ACLs on tokens matter.

---

## 5. Realms (OIDC / LDAP / SAML)

```bash
# OpenID Connect (e.g., Authentik, Keycloak)
pveum realm add corp-oidc --type openid \
    --issuer-url https://sso.example.com/application/o/proxmox/ \
    --client-id proxmox-cluster \
    --client-key 'CLIENT_SECRET' \
    --autocreate 1 --default-roles PVEAuditor

# LDAP
pveum realm add corp-ldap --type ldap \
    --server1 ldaps://ldap.example.com --user-attr uid \
    --base-dn 'ou=people,dc=example,dc=com' --secure 1
```

After adding the realm, users from it appear as `username@corp-oidc`.

---

## 6. fail2ban

```bash
apt install fail2ban
```

Drop in `/etc/fail2ban/jail.d/proxmox.conf`:

```ini
[proxmox]
enabled  = true
port     = 8006,https
filter   = proxmox
backend  = systemd
maxretry = 5
findtime = 10m
bantime  = 1h
```

And `/etc/fail2ban/filter.d/proxmox.conf`:

```
[Definition]
failregex = pvedaemon\[.*authentication failure; rhost=<HOST> user=.* msg=.*
ignoreregex =
```

Then:

```bash
systemctl restart fail2ban
fail2ban-client status proxmox
```

---

## 7. Auditing and CVE monitoring

```bash
# Show recent task logs
journalctl -u pvedaemon -u pveproxy -u pve-cluster --since "1 day ago"

# Per-node tasks (web UI also shows these)
ls -la /var/log/pve/tasks/

# Show what's running on a node
pvesh get /cluster/tasks
pvesh get /nodes/<node>/services
```

Subscribe to the Proxmox-announce mailing list and run `apt-listchanges` so
CVE-fixing point releases are surfaced before reboot. The community
PegaProx tool (community-maintained) also offers a CVE scanner that maps
Debian advisories to your installed package set.

---

## 8. Privileged operations checklist

Before any destructive operation (destroy, reformat storage, force quorum):

- [ ] Confirm the target VM/CT/storage with the user (`pmx-vm config <id>`)
- [ ] Take a snapshot if storage supports it
- [ ] Confirm a recent backup (`pvesm list <store> --content backup`)
- [ ] Note the change in `journalctl -p info -t custom-pmx-skill` for traceability
- [ ] Schedule outside production traffic windows when possible
- [ ] Have console access ready (`pvesh create /nodes/<n>/termproxy`)

Always run the equivalent `pmx-ssh 'qm config <id>'` BEFORE `pmx-vm destroy`.
