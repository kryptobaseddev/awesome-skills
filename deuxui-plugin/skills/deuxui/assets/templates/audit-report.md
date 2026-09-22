# UX audit — <product / scope>

**Scope.** Routes, viewports, tiers run, browser and version, date. Be exact: a
changed-component audit does not make an application conformant (GOV-009), and the
reader cannot judge the findings without knowing what was looked at.

**Decision.** `BLOCKED` / `CONDITIONAL` / `READY`, and the one-sentence reason.

## What was not checked

First, deliberately. The count of `NOT_RUN` rules and what they are — usually the
manual tier. A reader who does not know what was skipped cannot use anything below.

## Blocking

P0 and P1 failures. For each: rule ID, where, what happens to the user, what fixes it.
Ordered by severity, not by file.

## Should fix

P2 failures and low-confidence findings worth a look.

## Verified

What was checked and passed, by tier. This is what makes the audit auditable.

## Not applicable

Feature-gated rules the product does not reach, and which feature gates each.

## Exceptions in force

Existing `EXC-` records touching this scope, with their review dates.

## Evidence

Commands run, report paths, screenshot paths, who did the manual passes and when.

---

*Rule matrix: `.deuxui/reports/agent_report.yaml`. Rule text and sources:
`references/rules/`.*
