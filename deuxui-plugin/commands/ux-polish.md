---
description: The last pass — run every tier and produce the verdict.
argument-hint: "[path or url]"
---

Invoke the `deuxui` skill and follow `references/ops/polish.md`.

```bash
python3 scripts/doctor.py .
python3 scripts/ux_check.py . --json > .deuxui/reports/static.json
bash scripts/ux_browser.sh ${ARGUMENTS:-}
bash scripts/ux_native.sh --both          # if this ships to a phone
python3 scripts/manual_sheet.py --check
python3 scripts/ux_report.py --merge
```

Read `doctor.py` first, then lead the report with NOT_RUN.

Three things polish must not do: widen the contract so a departure stops being
one; disable a check to quiet the report; or record a manual PASS you performed
yourself — `vet_attestation` refuses a `who` that names the party making the
claim, and that refusal is the feature.

Finish by reading `report_self_audit`. It checks this report, not the product.
