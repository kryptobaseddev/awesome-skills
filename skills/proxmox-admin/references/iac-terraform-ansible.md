# Infrastructure as Code — Terraform, Ansible, OpenTofu

Read this when the user wants to provision Proxmox declaratively rather
than via one-off CLI calls. The recommended split:

- **Terraform / OpenTofu** — provision VMs/CTs, storage, networks (day 0/1).
- **Ansible** — configure guests after they exist (day 2+).
- **The skill's helpers** — interactive ops, troubleshooting, ad hoc tasks.

## Table of contents

1. [Provider choices](#provider-choices)
2. [Terraform — bpg/proxmox example](#terraform--bpgproxmox-example)
3. [Terraform — Telmate/proxmox example](#terraform--telmateproxmox-example)
4. [Ansible — proxmox & community.general](#ansible--proxmox--communitygeneral)
5. [Authentication for IaC](#authentication-for-iac)
6. [Common pitfalls](#common-pitfalls)

---

## Provider choices

| Provider | Status | Notes |
|----------|--------|-------|
| `bpg/proxmox` | Active, modern (2024+) | Recommended for new projects. Cloud-init, SDN, full state. |
| `Telmate/proxmox` | Legacy, still maintained | Lots of community modules; slower feature pace. |
| `community.general` Ansible | Maintained | `proxmox_kvm`, `proxmox` (LXC), `proxmox_snap`, etc. |
| `proxmoxer` (Python) | Library | Use for custom automation, not declarative IaC. |

Both Terraform providers connect via API token (created with `pveum`).

---

## Terraform — bpg/proxmox example

```hcl
terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66"
    }
  }
}

variable "pmx_endpoint" { type = string }
variable "pmx_token_user" { type = string }
variable "pmx_token_id"   { type = string }
variable "pmx_token_secret" { type = string, sensitive = true }

provider "proxmox" {
  endpoint  = var.pmx_endpoint                        # https://pve01.lan:8006
  api_token = "${var.pmx_token_user}!${var.pmx_token_id}=${var.pmx_token_secret}"
  insecure  = true                                    # set false once TLS is real
  ssh {
    agent    = true
    username = "root"
  }
}

resource "proxmox_virtual_environment_vm" "web" {
  name      = "web-1"
  node_name = "pve01"

  agent { enabled = true }
  cpu   { type = "host", cores = 2 }
  memory { dedicated = 2048 }

  disk {
    datastore_id = "local-lvm"
    size         = 32
    interface    = "scsi0"
    iothread     = true
    ssd          = true
    discard      = "on"
  }

  network_device { bridge = "vmbr0", model = "virtio" }

  initialization {
    datastore_id = "local-lvm"
    user_account {
      username = "deploy"
      keys     = [trimspace(file("~/.ssh/id_ed25519.pub"))]
    }
    ip_config {
      ipv4 { address = "10.0.0.110/24", gateway = "10.0.0.1" }
    }
  }
}
```

Run with the token secret in env (never inline):

```bash
export TF_VAR_pmx_token_secret="$(pass show pmx/api/skill)"
terraform plan
terraform apply
```

---

## Terraform — Telmate/proxmox example

```hcl
provider "proxmox" {
  pm_api_url          = "https://pve01.lan:8006/api2/json"
  pm_api_token_id     = "automation@pve!terraform"
  pm_api_token_secret = var.pmx_token_secret
  pm_tls_insecure     = true
}

resource "proxmox_vm_qemu" "web" {
  name        = "web-1"
  target_node = "pve01"
  clone       = "ubuntu-2204-template"
  full_clone  = true
  cores       = 2
  memory      = 2048
  scsihw      = "virtio-scsi-single"
  bootdisk    = "scsi0"

  network { model = "virtio", bridge = "vmbr0" }
  disk    { type = "scsi", storage = "local-lvm", size = "32G", ssd = 1, discard = "on", iothread = 1 }

  ipconfig0  = "ip=10.0.0.110/24,gw=10.0.0.1"
  ciuser     = "deploy"
  sshkeys    = file("~/.ssh/id_ed25519.pub")
}
```

---

## Ansible — proxmox & community.general

Inventory snippet:

```ini
[proxmox]
pve01.lan ansible_user=root ansible_ssh_private_key_file=~/.ssh/id_ed25519_proxmox
```

Create a container declaratively:

```yaml
- hosts: proxmox
  tasks:
    - name: ensure web container
      community.general.proxmox:
        api_host: "{{ inventory_hostname }}"
        api_user: automation@pve
        api_token_id: ansible
        api_token_secret: "{{ pmx_token_secret }}"
        validate_certs: false
        vmid: 200
        node: pve01
        hostname: web
        ostemplate: local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst
        storage: local-lvm
        unprivileged: true
        cores: 2
        memory: 2048
        netif: '{"net0":"name=eth0,bridge=vmbr0,ip=dhcp"}'
        state: present
```

Then `proxmox: state=started` and use a normal Ansible play to configure
the container.

---

## Authentication for IaC

- Always use API tokens, **never** ticket auth (no rotation, no revocation).
- Store secrets in `pass`/`age`/`sops`/Vault — never commit.
- Scope the token to a dedicated role (see `references/api-tokens.md`).
- Pin TLS once the node has a real cert; flip `insecure`/`validate_certs`
  to `false`.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Terraform `403` on apply | Token missing `VM.Allocate` / `Datastore.AllocateSpace` | Re-grant via `pveum role modify` |
| Plan churns every run | Provider reading config it didn't write (manual GUI edits) | Either move everything into TF OR ignore those attrs with `lifecycle.ignore_changes` |
| Cloud-init IP not applied | Forgot `--ide2 storage:cloudinit` OR missed regen | `qm set <id> --delete ide2`, re-add, `qm start` |
| Telmate provider hangs on large clones | Default 30s timeout | `task_timeout = 600` in the resource |
| Ansible `proxmox_kvm` says "no changes" but VM is wrong | Module compares config keys, not values | Switch to `bpg/proxmox` via Terraform OR run `qm set` from a shell task |
