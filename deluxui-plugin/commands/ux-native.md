---
description: iOS and Android conformance — 38 rules, 34 static detectors, Simulator and emulator evidence.
argument-hint: "[ios|android|both]"
---

Invoke the `deluxui` skill. Read `references/ops/ios.md` for Apple hardware,
`references/ops/android.md` for Android, and `references/ops/audit-native.md` to
produce the report.

```bash
python3 scripts/doctor.py .              # can this machine capture anything
python3 scripts/ux_check.py . --json > .deluxui/reports/static.json
bash scripts/ux_native.sh --${ARGUMENTS:-both}
python3 scripts/ux_report.py --merge
```

The platform is measured from the tree, so nothing needs declaring. A project
that does not ship to a phone reports all 38 rules NOT_APPLICABLE, which is
correct.

Where `xcrun` or `adb` is absent, the evidence rules report NOT_RUN with the tool
that was missing. Report that as unverified, not as fine: a browser screenshot of
a React Native web build is not evidence about an iPhone. And a Simulator has no
thermals, no real GPU and no hands — any claim about posture, gesture feel,
refresh rate or performance names the hardware it was measured on or is withdrawn.
