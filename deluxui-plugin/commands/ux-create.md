---
description: Build a new screen, flow or component against the UX contract.
argument-hint: "<what to build>"
---

Run the deluxui `create` workflow to build: $ARGUMENTS

Invoke the `deluxui` skill, then follow its `create` workflow (`references/workflows/create.md`). Before writing anything, run
`ux_check.py --inventory` — `PRESERVE > MODIFY > COMPOSE > CREATE` applies most
strongly to new surfaces, because that is where inventing feels most justified.

Write the component contract first, build semantics and states before styling, then
verify with both tiers.
