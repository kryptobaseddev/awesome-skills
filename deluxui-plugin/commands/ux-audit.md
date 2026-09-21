---
description: Full UX audit — static, runtime and manual tiers merged into a rule matrix and a release gate.
argument-hint: "[path or url]"
---

Run the deluxui `audit` workflow on $ARGUMENTS (default: this project and the dev URL
in `.deluxui/ux.config.yaml`).

Read `skills/deluxui/references/workflows/audit.md` and follow it. In short: declare
the product's features, run all three tiers, merge, and report.

Lead the report with how many rules were **not** checked. An audit that implies the
unchecked rules passed is worse than no audit.
