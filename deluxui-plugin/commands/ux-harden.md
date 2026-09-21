---
description: Harden accessibility, state coverage and destructive actions.
argument-hint: "[path or route]"
---

Run the deluxui `harden` workflow on $ARGUMENTS.

Invoke the `deluxui` skill, then follow its `harden` workflow (`references/workflows/harden.md`). Force the aborted,
empty and offline states with `ux_browser.sh --api` rather than reasoning about them,
and walk every irreversible action.
