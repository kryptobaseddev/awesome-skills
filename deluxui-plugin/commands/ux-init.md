---
description: Set up .deluxui/ project memory by inspecting this repo.
---

Run the deluxui `init` workflow.

Read `skills/deluxui/references/workflows/init.md`. Infer everything you can from the
repo — framework, Tailwind major version, theme variables, component inventory, routes.
Ask at most three questions, and only the ones no repository contains: who uses this,
which actions are irreversible, and what must not change.

Set `api_pattern` in `ux.config.yaml` before you finish. Without it the forced-state
probes never run.
