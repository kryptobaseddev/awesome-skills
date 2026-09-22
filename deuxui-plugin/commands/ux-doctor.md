---
description: What deuxui can and cannot check on this machine, and what each gap costs in rules.
argument-hint: "[path]"
---

Invoke the `deuxui` skill and run:

```bash
python3 scripts/doctor.py ${ARGUMENTS:-.}
```

Then read `references/ops/doctor.md` and report the three groups it describes:
install drift, setup drift, and truth drift. For anything marked GONE, say which
rules will report NOT_RUN until it is fixed — a page of NOT_RUN caused by a
missing browser is a different situation from unfinished work, and only one of
them is about the code.

Do not fix the project as a side effect. Name the command that would close each
gap and stop.
