---
description: Set up .deluxui/ project memory by inspecting this repo.
---

Run the deluxui `init` workflow.

Invoke the `deluxui` skill, then follow its `init` workflow (`references/workflows/init.md`). Infer everything you can from the
repo — framework, Tailwind major version, theme variables, component inventory, routes.
Ask at most three questions, and only the ones no repository contains: who uses this,
which actions are irreversible, and what must not change.

Fill in `ux.config.yaml` before you finish — every key in it is load-bearing:

- `app.api_pattern` is the request glob `ux_browser.sh` intercepts. Without it the
  aborted, empty and offline probes cannot run and every `STATE-*` rule is NOT_RUN.
- `app.dev_url`, `routes` and `viewports` become the runtime tier's defaults, so
  `/ux-audit` works with no arguments.
- `features:` decides which rules are NOT_APPLICABLE. Declare honestly.
- `exclude:` keeps generated or vendored directories out of the report.
