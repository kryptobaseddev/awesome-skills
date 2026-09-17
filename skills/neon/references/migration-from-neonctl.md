# Migrating from `neonctl` to `neon`

The Neon CLI is now invoked as `neon`. `neonctl` was the old name. Everything below was verified against
`neon` 4.18.1 and npm metadata on 2026-09-16.

## Table of Contents

- [What actually changed](#what-actually-changed)
- [The two packages](#the-two-packages)
- [Choose a migration path](#choose-a-migration-path)
- [The bin-symlink trap](#the-bin-symlink-trap)
- [Credentials survive the move](#credentials-survive-the-move)
- [Command-level changes](#command-level-changes)
- [Migrating CI and scripts](#migrating-ci-and-scripts)
- [Diagnosing a confused install](#diagnosing-a-confused-install)

## What actually changed

The rename is mostly cosmetic; the CLI's growth is not. Treat this as a major upgrade, not a `sed` job:

- **Binary name**: `neonctl` → `neon`.
- **Repository**: moved to [`neondatabase/neon-pkgs`](https://github.com/neondatabase/neon-pkgs/tree/main/packages/cli).
- **Version line**: the old `neonctl` 2.x series ran to **2.47.0**, then through **eleven 3.x releases (3.0.0–3.6.0)**, and is now on 4.x — under both package names, in lockstep. An install pinned to 2.x is several majors behind, not one.
- **Node floor**: 20.19.0+ is required to *install or upgrade*. An existing install keeps working on older Node; upgrading on Node 18 fails.
- **Scope**: 2.x managed projects, branches, databases, roles, connection strings, IP allow, and operations. 4.x adds snapshots, Functions, triggers, object-storage buckets, the Data API, Managed Better Auth (`neon-auth`), credentials, profiles, log querying, Postgres health inspection, `neon.ts` config-as-code, local Functions dev, and agent-tooling installers (`mcp`, `skills`, `plugins`).

Nothing in the 2.x command set was removed. Old invocations keep working under the new binary name.

## The two packages

Both are published from the same repo at the same version. `neonctl` is now a thin shim: its package
depends on `neon` at the identical version (`neonctl@4.18.1` → `neon@4.18.1`) and re-exposes it under both
command names, which is exactly why installing it gives you two binaries.

| Package | Binaries it installs | Use it when |
|---|---|---|
| `neon` | `neon` only | You want a clean cutover. |
| `neonctl` | `neon` **and** `neonctl` | Scripts you don't control still call `neonctl`. |

`neonctl` is **not** formally deprecated on npm — it carries no `deprecated` field, and its registry description now reads *"Compatibility command for the Neon CLI"*. So "is neonctl deprecated?" is best answered: the *name* is legacy, the *package* is current and published in lockstep, and installing it is the supported way to keep the old command working. Nobody has to rewrite their scripts on a deadline.

Homebrew is the exception: the formula is still named `neonctl` even though the CLI runs as `neon`.

```bash
brew install neonctl        # installs a CLI you invoke as `neon`
```

## Choose a migration path

**Full cutover** — only `neon` exists afterward. Prefer this when every caller is under your control:

```bash
npm i -g neon@latest
npm uninstall -g neonctl
npm i -g neon@latest        # see the bin-symlink trap below — this third step is not redundant
neon --version              # expect 4.x
```

**Compatibility** — both commands work, same code behind each:

```bash
npm uninstall -g neon       # avoid two packages fighting over the `neon` bin
npm i -g neonctl@latest
neon --version && neonctl --version    # identical versions
```

Don't install both packages. They each declare a `neon` binary, so whichever was installed last wins the symlink and the other's version becomes unreachable and confusing.

## The bin-symlink trap

This one bites during a cutover and the error message points nowhere useful.

The `neonctl` package declares **two** binaries, `neon` and `neonctl`. If `neonctl` is installed and you then run `npm uninstall -g neonctl`, npm removes *both* symlinks — including `neon`, even when the `neon` package is still installed. The package directory survives, so `npm ls -g` looks fine while the command is gone:

```
$ npm uninstall -g neonctl
$ neon --version
bash: neon: command not found
```

Nothing is corrupted — the package directory is intact, only the launcher is gone. Confirm before fixing:

```bash
PREFIX=$(npm prefix -g)
ls -l "$PREFIX/bin"/neon*                                    # the missing link
node "$PREFIX/lib/node_modules/neon/dist/cli.js" --version   # the program still runs
```

Fix by reinstalling the package whose binary was collateral damage:

```bash
npm i -g neon@latest
hash -r                 # clear the shell's cached "command not found"
```

A same-version reinstall does re-create the bin link (verified against npm 11 — it reports "changed N packages" rather than skipping as up to date). If your npm treats it as a no-op, force it:

```bash
npm i -g --force neon@latest
```

Order the steps to avoid the gap entirely: uninstall `neonctl` **first**, then install `neon`. Either way no credentials, context files, or project state are touched — they live outside `node_modules`.

## Credentials survive the move

`neon --help` reports the config directory default as `~/.config/neon`. In practice the 4.x CLI authenticates
from `~/.config/neonctl/credentials.json`, the legacy path, and leaves `~/.config/neon/` empty — verified on
a machine upgraded from 2.x, where `neon me` succeeds against the legacy file while the advertised directory
stays empty. (The file is not rewritten on every call, so don't use its mtime as the check; `neon me`
succeeding is the check.)

Consequences:

- Upgrading from `neonctl` **keeps you signed in**. No re-login step is needed, and a migration guide that tells users to re-authenticate is wasting their time.
- Don't rename or move `~/.config/neonctl/` to "finish" the migration — that is the live credential store.
- `$XDG_CONFIG_HOME` is honored if set.

If authentication does break after an upgrade, `neon login` rewrites the file; nothing else is required.

## Command-level changes

| Old (`neonctl` 2.x) | Now | Note |
|---|---|---|
| `neonctl <cmd>` | `neon <cmd>` | Same subcommands, same flags. |
| `neonctl auth` | `neon login` | `neon auth` remains as an alias. |
| `neonctl set-context --project-id <id>` | `neon link --project-id <id>` | `set-context` still works but is marked deprecated in `--help`. `link` validates IDs, resolves the org, can pin a branch, and pulls env vars. |
| — | `neon checkout <branch>` | New: pin a branch in `.neon` without relinking. |
| `neonctl completion` | `neon completion` | Unchanged; regenerate it so the script completes `neon`, not `neonctl`. |

Shell completion is worth redoing after a cutover, since the old block in `~/.bashrc` registers completions for a command that may no longer exist:

```bash
# remove the old ###-begin-neonctl-completions-### block from ~/.bashrc first
neon completion >> ~/.bashrc && source ~/.bashrc
```

New in 4.x and worth knowing when rewriting old scripts: `neon env pull` (replaces hand-rolled `connection-string` → `.env` plumbing), `neon snapshots` (replaces `branches restore` gymnastics for scheduled backups), and `neon api <path>` (authenticated passthrough to any Platform API route, which removes the need to hand-build `curl` calls with a bearer token).

## Migrating CI and scripts

1. Find the callers:

   ```bash
   grep -rn --include='*.sh' --include='*.yml' --include='*.yaml' --include='*.json' --include='*.ts' --include='*.js' -e 'neonctl' .
   ```

2. Replace the install step. In GitHub Actions:

   ```yaml
   - name: Install Neon CLI
     run: npm install -g neon@latest     # was: npm install -g neonctl
   ```

   Pinning to `latest` in CI is Neon's own recommendation — they prioritize CI stability over churn.

3. Rename invocations (`neonctl ` → `neon `), then re-read any line using `set-context` and decide whether `link` fits better.

4. Confirm the runner's Node is 20.19.0+. On an older runner the install step fails rather than falling back, so a job that previously worked breaks at install time with a version error — add `actions/setup-node` with `node-version: 20` (or newer) if it isn't already there.

5. Check that nothing parses `table` output. It truncates, and the 4.x tables are not column-identical to 2.x. Anything scripted should use `--output json`.

## Diagnosing a confused install

```bash
command -v neon neonctl          # which binaries exist, and from where
neon --version                   # 2.x here means the old CLI answering to a new name
npm ls -g --depth=0 | grep -E 'neon(ctl)?@'
```

Common states and what they mean:

| Symptom | Cause | Fix |
|---|---|---|
| `neon --version` prints 2.x | Old `neonctl` package owns the `neon` symlink | `npm uninstall -g neonctl && npm i -g neon@latest` |
| `neon: command not found` right after uninstalling `neonctl` | The bin-symlink trap | `npm i -g neon@latest` |
| `neonctl: command not found` after a cutover | Expected — that's the point | Use `neon`, or install `neonctl@latest` for compatibility |
| "Unknown command" for `snapshots`/`functions`/`env`/`link` | Still on 2.x | Upgrade, after checking Node ≥ 20.19.0 |
| Upgrade fails with a Node version error | Node < 20.19.0 | Upgrade Node first; the installed CLI keeps working meanwhile |
