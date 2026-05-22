# Kryptobaseddev's Awesome Skills

> A curated, validated collection of [Agent Skills](https://agentskills.io) for Claude Code and other agent runtimes.

Every skill in this repo is hand-written by [@kryptobaseddev](https://github.com/kryptobaseddev), validated against the [agentskills.io specification](https://agentskills.io/specification.md), and categorized for easy discovery. The skills below are auto-generated from each `SKILL.md` frontmatter — see the [pipeline](#pipeline) section for how the list stays current.

## What's a skill?

A **skill** is a self-contained folder (`name/SKILL.md` + optional `scripts/`, `references/`, `assets/`) that teaches an AI agent how to do one thing well. Agents discover skills by reading the `description` field at startup and load the full `SKILL.md` only when triggered. See [agentskills.io](https://agentskills.io) for the open specification.

## Install

Pick the install location that matches your agent runtime:

| Runtime | Skills directory |
|---|---|
| Claude Code (global) | `~/.claude/skills/` |
| Claude Code (project) | `<project>/.claude/skills/` |
| Codex CLI | `~/.agents/skills/` or `<project>/.agents/skills/` |

To install one skill:

```bash
# Symlink (recommended — pulls future updates from git)
ln -s /path/to/awesome-skills/skills/<skill-name> ~/.claude/skills/<skill-name>

# Or copy (snapshot)
cp -r /path/to/awesome-skills/skills/<skill-name> ~/.claude/skills/
```

To install all skills at once:

```bash
for d in /path/to/awesome-skills/skills/*/; do
  ln -sf "$d" ~/.claude/skills/
done
```

## Repository layout

```
awesome-skills/
├── README.md                    # this file (skills list auto-generated below)
├── registry.json                # machine-readable index of all skills
├── skill-validator.config.yml   # optional repo-wide validator overrides
├── scripts/
│   └── build_registry.py        # scans skills/, updates README + registry
├── .github/workflows/
│   ├── validate.yml             # runs skill-validator on PRs
│   └── registry.yml             # auto-updates README on push to main
├── .githooks/
│   └── pre-commit               # local registry update on commit
└── skills/
    ├── skill-validator/         # the validator itself (config-driven, general-purpose)
    ├── skill-evaluator/         # runtime quality eval + regression detection
    └── <every-other-skill>/
```

## Pipeline

The registry and this README's skills list update automatically:

| Trigger | What runs |
|---|---|
| `git commit` (local) | `.githooks/pre-commit` regenerates `registry.json` and the README skills block. Skip with `git commit --no-verify`. |
| Push to `main` | `.github/workflows/registry.yml` regenerates, commits, and pushes if changes are detected. |
| PR to any branch | `.github/workflows/validate.yml` runs `skill-validator` on every changed skill. Fails the PR on errors. |

Manual refresh:

```bash
python scripts/build_registry.py           # writes README + registry.json
python scripts/build_registry.py --dry-run # show what would change
python scripts/build_registry.py --check   # exit 1 if stale (CI-friendly)
```

## Category resolution

Each skill is assigned to one category. Resolution order:

1. **Explicit override** — `metadata.category: <slug>` in the skill's SKILL.md
2. **Rule-based match** — first match in [`skills/skill-validator/config/categories.yml`](skills/skill-validator/config/categories.yml) (keywords, name prefix, tags)
3. **Fallback** — "Other" 📦

To add a new category, edit `categories.yml` and rerun `build_registry.py`.

## Validation

Every skill in this repo passes the [`skill-validator`](skills/skill-validator/) compliance gauntlet:

- **Tier 1**: SKILL.md exists, valid YAML frontmatter, no forbidden fields
- **Tier 2**: Field types, lengths, regex patterns; recommended `metadata` keys (`author`, `version`, `last_updated`)
- **Tier 3**: Body under 500 lines, no placeholders, file references resolve
- **Tier 4** (opt-in): Manifest integration
- **Tier 5** (opt-in): Provider compatibility map

The validator is config-driven. Edit `skill-validator.config.yml` at the repo root to customize rules for this project. See [`skills/skill-validator/config/README.md`](skills/skill-validator/config/README.md) for the full schema.

Validate one skill locally:

```bash
python skills/skill-validator/scripts/validate.py skills/<skill-name>
```

Validate every skill:

```bash
for d in skills/*/; do
  echo "=== ${d} ==="
  python skills/skill-validator/scripts/validate.py "$d"
done
```

## Contributing a new skill

1. **Fork** this repo (or branch if you have write access).
2. **Generate scaffold** — copy an existing skill that's close to your concept, rename the directory, and edit the frontmatter.
3. **Required frontmatter** — `name` (matching directory), `description` (≤1024 chars with at least one trigger phrase like "Use when ..."), `metadata.author`, `metadata.version`, `metadata.last_updated` (format: `YYYY-MM-DD HH:MM:SS`).
4. **Validate** — `python skills/skill-validator/scripts/validate.py skills/<your-skill>`. Fix every error and warning.
5. **Regenerate registry** — `python scripts/build_registry.py` (or just commit; the pre-commit hook will do it).
6. **PR** — the CI runs the validator on every skill change; it'll block on errors.

## License

Each skill carries its own `license` field in its frontmatter. Repo scaffolding (`scripts/`, GitHub Actions, the README) is MIT.

---

## Skills

<!-- SKILLS-START -->

_15 skills across 11 categories — auto-generated from `skills/*/SKILL.md`. Last updated: 2026-05-21 20:22:57._

### 🧰 Skill Development

| Skill | Description |
|---|---|
| [`skill-evaluator`](skills/skill-evaluator/) | Eval-driven quality evaluation, regression detection, and auto-improvement of Agent Skills. Auto-generates challenging test cases unique to the target skill from its SKILL.md, runs A/B benchmarks (… |
| [`skill-validator`](skills/skill-validator/) | Validate any Agent Skill against the agentskills.io specification plus project- or skill-local rule overrides. Use when auditing a skill folder for compliance, preparing a skill for distribution, c… |

### 🌐 Browser & Web Automation

| Skill | Description |
|---|---|
| [`agent-browser`](skills/agent-browser/) | Browser automation CLI for AI agents. Use when the user needs to interact with websites, including navigating pages, filling forms, clicking buttons, taking screenshots, extracting data, testing we… |

### 💳 Payments & Commerce

| Skill | Description |
|---|---|
| [`payment-provider-oauth`](skills/payment-provider-oauth/) | Build OAuth connections for payment providers (Stripe Connect, Square) in SvelteKit applications. Use when creating booking platforms, marketplaces, or applications where businesses need to connect… |

### 🎨 Frontend & UI

| Skill | Description |
|---|---|
| [`svelte5-sveltekit`](skills/svelte5-sveltekit/) | Comprehensive guide for building modern web applications with Svelte 5 and SvelteKit. Use when creating Svelte components, implementing Svelte 5 runes ($state, $derived, $effect, $props), building … |

### 🖥️ Infrastructure & Sysadmin

| Skill | Description |
|---|---|
| [`proxmox-admin`](skills/proxmox-admin/) | Use this skill to administer a Proxmox VE 8.x/9.x host, node, or cluster remotely — provisioning, day-2 ops, troubleshooting, hardening, IaC, migration off VMware/ESXi. Covers KVM VMs (qm), LXC con… |

### ☁️ Cloud & Deployment

| Skill | Description |
|---|---|
| [`flarectl`](skills/flarectl/) | Cloudflare CLI management via the flarectl tool. Use when the user asks to manage Cloudflare zones, DNS records, firewall rules, cache purging, or zone exports using flarectl. Covers onboarding (in… |
| [`railway`](skills/railway/) | Operate Railway infrastructure: create projects, provision services and databases, manage object storage buckets, deploy code, configure environments and variables, manage domains and networking, s… |
| [`runpodctl`](skills/runpodctl/) | Runpod CLI (runpodctl) to manage your Runpod GPU workloads from the terminal. Use when you need to create or terminate GPU pods, list available GPU types and prices, inspect pod status, manage SSH … |

### 🗄️ Databases & ORMs

| Skill | Description |
|---|---|
| [`drizzle-orm`](skills/drizzle-orm/) | Expert guidance for Drizzle ORM and drizzle-kit, covering the v1.0.0-beta (RQBv2, defineRelations, new migration folder structure, consolidated validators) and stable 0.x releases. Includes Node 24… |
| [`neonctl`](skills/neonctl/) | Comprehensive Neon CLI (neonctl) management for serverless Postgres. Use when managing Neon projects, branches, databases, roles, connection strings, IP allowlists, operations, or authentication vi… |

### 📧 Communication & Email

| Skill | Description |
|---|---|
| [`resend`](skills/resend/) | Use when working with the Resend email API — sending transactional emails (single or batch), receiving inbound emails via webhooks, managing email templates, tracking delivery events, or setting up… |

### ✨ Code Quality & Refactoring

| Skill | Description |
|---|---|
| [`code-optimizer`](skills/code-optimizer/) | Deep code optimization audit using parallel specialist agents. Each agent hunts for performance anti-patterns, inefficiencies, and suboptimal code using pattern-based detection (Grep/Glob) WITHOUT … |

### 🛡️ Security

| Skill | Description |
|---|---|
| [`security-review`](skills/security-review/) | Threat-model-driven security review of a change, feature, or subsystem. Runs a STRIDE-style pass (Spoofing, Tampering, Repudiation, Info disclosure, Denial of service, Elevation of privilege), exam… |

### 💡 Quick Helpers

| Skill | Description |
|---|---|
| [`btw`](skills/btw/) | Ask a quick side question about your current work without derailing the main task. Answers from existing conversation context only — no tool calls, no file reads, single concise response. Use when … |

<!-- SKILLS-END -->

---

## Acknowledgements

- [agentskills.io](https://agentskills.io) — the open Agent Skills specification this repo targets.
- [Anthropic Skills reference repo](https://github.com/anthropics/skills) — initial inspiration for skill structure.
