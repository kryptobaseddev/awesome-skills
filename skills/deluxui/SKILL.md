---
name: deluxui
description: "DEPRECATED POINTER — this skill was renamed to `deuxui` (DeuxUI). It exists only so existing installs receive the rename notice on their next update. Do not use it for real work: install and use the `deuxui` skill instead, which carries the whole 235-rule UX/UI contract, 246 detectors across static, browser, native, process and manual tiers, the wireframe and prototype review stages, the design decision ledger, and the release gate where NOT_RUN is never a pass. If this skill triggers on a UX, UI, design-system, accessibility, responsive or interface question, read the `deuxui` skill and answer from there."
license: Apache-2.0
metadata:
  author: kryptobaseddev
  version: "5.0.0"
  last_updated: "2026-09-22 02:30:00"
  category: frontend
  tags: ux, ui, design-system, deprecated, moved
  superseded_by: deuxui
---

# `deluxui` → `deuxui` (this skill moved)

**This skill is a tombstone.** Everything it contained now lives in the
[`deuxui`](../deuxui/) skill. Nothing was removed in the move.

## Why the name changed

**Deux is French for two — UX and UI.** The old name read as "deluxe UI", which
described a finish rather than the two disciplines the tool actually enforces.

## What to do

```bash
npx skills add kryptobaseddev/awesome-skills -s deuxui --copy -g
npx skills remove deluxui

# Claude Code plugin
claude plugin install deuxui@awesome-skills
claude plugin uninstall deluxui@awesome-skills
```

## What else changed

| Before | After |
|---|---|
| `skills/deluxui/` | `skills/deuxui/` |
| `deluxui-plugin` | `deuxui-plugin` |
| `.deluxui/` project state | `.deuxui/` |
| `DELUXUI_IMAGE_CMD`, `DELUXUI_NB_GENERATE` | `DEUXUI_IMAGE_CMD`, `DEUXUI_NB_GENERATE` |

A project that already has a `.deluxui/` directory keeps every record in it —
rename the directory to `.deuxui/` and nothing else needs to change. `ux_doctor`
and `ux_ledger.py state` both say so if they find the old one.

## Resources

- The replacement skill: [`../deuxui/SKILL.md`](../deuxui/SKILL.md)
