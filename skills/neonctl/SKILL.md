---
name: neonctl
description: "DEPRECATED POINTER — this skill was renamed to `neon` when the Neon CLI itself was renamed from `neonctl` to `neon`. It exists only so existing installs receive the rename notice on their next update. Do not use it for real work: install and use the `neon` skill instead, which covers the current 4.x CLI (projects, branches, snapshots, Functions, buckets, Data API, inspect) plus the full neonctl-to-neon migration guide. If this skill triggers on a Neon or neonctl question, read the `neon` skill and answer from there."
license: MIT
metadata:
  author: kryptobaseddev
  version: "2.0.0"
  last_updated: "2026-09-16 12:20:00"
  category: databases
  tags: neon, postgres, cli, deprecated, moved
  superseded_by: neon
---

# `neonctl` → `neon` (this skill moved)

**This skill is a tombstone.** Its content now lives in the [`neon`](../neon/) skill, because the CLI it
documents was renamed: `neonctl` is now invoked as `neon`.

## What to do

Install the replacement and remove this one:

```bash
# symlink install (pulls future updates from git)
ln -sfn /path/to/awesome-skills/skills/neon ~/.claude/skills/neon
rm -rf ~/.claude/skills/neonctl

# or, with the skills installer
npx skills add neon
npx skills remove neonctl
```

Then answer the user's question from the `neon` skill, which covers the current 4.x command surface and a
dedicated migration reference at `references/migration-from-neonctl.md`.

## Why the rename, in one paragraph

Neon renamed the CLI to `neon` and moved it to the `neondatabase/neon-pkgs` repo. The old `neonctl` npm
package is **not** deprecated — it is published in lockstep as a compatibility alias that installs both the
`neon` and `neonctl` binaries, while the `neon` package installs only `neon`. The old 2.x line continues as
4.x under both names, so there is no 3.x to step through, and installing or upgrading now requires Node
20.19.0+. Credentials are unaffected: the 4.x CLI still reads `~/.config/neonctl/credentials.json`, so an
upgrade does not log you out.

The one trap worth repeating here, because it strands people mid-migration: the `neonctl` package declares
**both** binaries, so `npm uninstall -g neonctl` removes the `neon` symlink too, even when the `neon`
package is still installed. Reinstall with `npm i -g neon@latest` to restore it.

Everything else — the full command map, CI patterns, and a migration checklist — is in the `neon` skill.
