---
description: Set deuxui up in a project it has never seen — in the order that pays.
argument-hint: "[path]"
---

Invoke the `deuxui` skill and follow `references/ops/onboard.md`.

```bash
python3 scripts/doctor.py ${ARGUMENTS:-.}
python3 scripts/ux_check.py ${ARGUMENTS:-.} 2>&1 | tail -30
python3 scripts/derive_contract.py --write
python3 scripts/manual_sheet.py --write
```

Then fill in, highest value first: the irreversible and external actions in
`PRODUCT.md` (nothing in the code states these, and they drive the whole
destructive-action family), then `exclude`, then `app.dev_url` and `api_pattern`,
then `features`.

Do not start by disabling checks. `disabled_checks` moves a rule to NOT_RUN,
never to PASS, and the report names which config narrowed the scope. If a detector
is genuinely wrong on this codebase, that is a bug worth reporting rather than a
setting worth flipping.
