---
description: Build or audit a type ladder whose steps can actually carry different jobs.
argument-hint: "[body px]"
---

Invoke the `deluxui` skill and read `references/ops/typeset.md`.

Audit what is declared first:

```bash
python3 scripts/typescale.py --check .deluxui/design.contract.yaml
python3 scripts/ux_check.py . --detector S-CRAFT-TYPE-FLAT --detector S-CRAFT-FAMILIES \
        --detector S-TYPE-MEASURE --detector S-TYPE-LEADING
```

Build one:

```bash
python3 scripts/typescale.py --mode operate --body ${ARGUMENTS:-16}
python3 scripts/typescale.py --mode operate --body ${ARGUMENTS:-16} --contract
python3 scripts/typescale.py --mode operate --body ${ARGUMENTS:-16} --css
```

Run the mechanical scan and your own reading separately, and do not let the scan
anchor the reading. A clean scan is a floor, not proof of good typography.
