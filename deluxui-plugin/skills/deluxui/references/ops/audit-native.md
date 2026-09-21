# audit-native — a code-level audit of the native app

The native counterpart to [../workflows/audit.md](../workflows/audit.md). It
documents; it does not fix.

Derived from impeccable's `audit.native` (Apache-2.0), with the scoring replaced
by rule-keyed statuses — see NOTICE.md.

## Why there is no score here

impeccable scores five dimensions 0–4. deluxui does not, on purpose: a composite
number lets a 2 in accessibility average away against a 4 in performance, and the
2 is someone unable to use the app. Each rule gets its own status, and NOT_RUN is
reported as loudly as FAIL because a rule nobody checked is not a rule that
passed.

## Run it

```bash
python3 scripts/doctor.py .              # what can run on this machine
python3 scripts/ux_check.py . --json > .deluxui/reports/static.json
bash scripts/ux_native.sh --both         # Simulator and emulator evidence
python3 scripts/manual_sheet.py --check  # the device questions
python3 scripts/ux_report.py --merge --release
```

`--release` is what makes an unrun applicable P0 or P1 block the gate rather than
merely appear in the count.

## The five dimensions, and where each one is settled

| Dimension | Automated | Needs a person |
|---|---|---|
| Accessibility | `S-IOS-DYNAMICTYPE`, `S-IOS-MINSIZE`, `S-IOS-TARGET44`, `S-AND-SP`, `S-AND-TARGET48`, `S-IOS-REDUCEMOTION`, `S-AND-REDUCEMOTION` | `M-SCREENREADER` — VoiceOver or TalkBack, one primary task, eyes closed |
| Platform conformance | the other 25 `S-IOS-*` / `S-AND-*` detectors | `M-JUDGE-NAV-PATTERN` |
| Appearance coverage | `R-IOS-APPEARANCE`, `R-AND-THEME` — both appearances and an enlarged text size, captured | reading the captures |
| Evidence integrity | `R-IOS-CAPTURE`, `R-AND-CAPTURE` — a real device or Simulator, named | `M-NATIVE-HARDWARE` |
| Performance and posture | nothing | `M-FIELD-PERF`, `M-NATIVE-HARDWARE`. A Simulator has no thermals, no real GPU and no hands. |

That last row is not a gap to be closed by a better detector. Startup time,
scroll smoothness, gesture feel and battery cost are properties of hardware, and
the honest report says which device produced each claim or withdraws the claim.

## What the report must say

- Which platforms were audited, and which were detected but not audited.
- For every NOT_RUN: the tool that was missing. "xcrun is not on PATH" is a
  fact a reader can act on; a blank cell is not.
- The device and identifier behind every capture. Display names collide.
- Legacy defects in scope: QA-006 forbids calling an existing defect out of scope
  when the change worsens it or depends on the broken path.

Fixes belong to [ios.md](ios.md), [android.md](android.md) and
[adapt-native.md](adapt-native.md).
