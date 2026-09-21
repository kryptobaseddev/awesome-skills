# polish — the last pass, and the one that produces the verdict

Every other craft operation hands off here. Polish is not "make it prettier"; it
is the pass where the work stops being a set of edits and becomes a result with a
status.

Derived from impeccable's `polish` (Apache-2.0), with a verdict attached — see
NOTICE.md.

## Run everything

```bash
python3 scripts/doctor.py .                      # what can even run here
python3 scripts/ux_check.py . --json > .deluxui/reports/static.json
bash scripts/ux_browser.sh http://localhost:5173 --routes /,/settings
bash scripts/ux_native.sh --both                 # if this ships to a phone
python3 scripts/manual_sheet.py --check          # what still needs a person
python3 scripts/ux_report.py --merge
```

Read `doctor.py` first. A page of NOT_RUN caused by a missing browser is a
different situation from a page of NOT_RUN caused by unfinished work, and only
one of them is about the code.

## The passes, in order of what they cost to fix later

1. **Every state.** Empty, loading, error, offline, permission-denied, the
   maximum content length, the single-item case. `ux_browser.sh --api` forces
   most of them so you can look rather than reason.
2. **Every input mode.** Keyboard through the whole task. Pointer. Touch, one
   handed. Screen reader for one primary task.
3. **Every appearance.** Light, dark, forced-colors, 200% zoom, the largest text
   size.
4. **Every width.** 320 up, and the reflow probe rather than a guess.
5. **The craft floor.** The sixteen `S-CRAFT-*` detectors. These are mechanical
   and cheap; clearing them says only that nothing is in the way.
6. **The contract.** Everything in the code is a declared value or a recorded
   departure.

## What polish must not do

Not widen the contract so that a departure stops being one. Not disable a check
to quiet a report — `disabled_checks` moves a rule to NOT_RUN, never to PASS, and
the report says which config silenced it. Not record a manual PASS the polisher
performed themselves; `vet_attestation` refuses a `who` that names the party
making the claim, and that refusal is the feature.

## The verdict

`ux_report.py --merge` prints NOT_RUN first, on purpose. It is the count of rules
nothing has checked, and it is not a pass. A release gate is BLOCKED by a failing
P0 or P1 **and** by an unrun applicable one, because "we did not look" and "it is
fine" are not the same sentence.

Finish by reading `report_self_audit`: it checks this document, not the product —
whether every PASS traces to a detector that ran, whether an attestation is doing
work a measurement should have done, and whether config narrowed the scope.

Next: [../verification/evidence.md](../verification/evidence.md).
