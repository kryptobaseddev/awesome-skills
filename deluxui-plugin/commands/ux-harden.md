---
description: Harden accessibility, state coverage and destructive actions.
argument-hint: "[path or route]"
---

Run the deluxui `harden` workflow on $ARGUMENTS.

Read `skills/deluxui/references/workflows/harden.md` and follow it. Force the aborted,
empty and offline states with `ux_browser.sh --api` rather than reasoning about them,
and walk every irreversible action.
