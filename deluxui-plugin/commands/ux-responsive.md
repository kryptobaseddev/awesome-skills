---
description: Check and fix layout across the viewport matrix, down to 320px.
argument-hint: "[url or route]"
---

Run the deluxui `responsive` workflow on $ARGUMENTS.

Invoke the `deluxui` skill, then follow its `responsive` workflow
(`references/workflows/responsive.md`).

Measure at every width rather than reasoning about breakpoints: `ux_browser.sh` sets
320, 390, 768, 1024 and 1440 and reports real overflow, clipping and hit areas.
320px and 200% zoom are where this actually breaks.
