# Third-party notices

## impeccable

Parts of deluxui's design layer are derived from the **impeccable** skill by Paul Bakaus.

- **Upstream:** https://github.com/pbakaus/impeccable
- **License:** Apache License 2.0
- **Version referenced:** 4.1.0

Used with the upstream author's explicit permission, and in any case within the terms of
the Apache 2.0 license, which permits derivative works with attribution.

### What was taken, and what was changed

Nothing was copied verbatim. impeccable's craft doctrine and its operation shape were
re-expressed for a system whose contract is different: impeccable states guidance for an
agent to follow, while deluxui has to survive being checked, so a claim that could not be
bound to a detector or a declaration was either converted or left out.

| From impeccable | In deluxui | Change |
|---|---|---|
| The craft floor's numeric ceilings | `references/rules/thresholds.yaml` (`type_craft`, `depth`, `motion_craft`, `zindex`) and `scripts/checks/craftfloor.py` | Restated as machine-readable, overridable thresholds read through `Project.num`, each bound to a detector ID and a rule ID, each with a known-bad and known-good fixture |
| The visitor-mode model (persuade / experience / operate / read / native) | `references/design/visitor-modes.md` and `visitor_mode` in the visual contract | Rewritten; made a declared field that later checks read, rather than guidance |
| "Set the system" — declare roles and constraints before editing | `assets/templates/design.contract.yaml` and the `S-CONTRACT-*` checks | Turned into a machine-readable contract that detectors compare the artifact against, with NOT_RUN when nothing is declared |
| The operation shape: audit → declare → apply at system scale → verify | `references/workflows/design.md`, `references/workflows/uplift.md` | Split explicitly into greenfield and brownfield, with the brownfield path deriving the contract from existing code |
| Browser-surface theming as a craft signal | `S-CRAFT-SURFACES` | Converted from advice into a check that only fires on a stylesheet actually defining a system |
| `ios.md` and `android.md` — the platform rule sets, including their slop tests and their verification commands (`xcrun simctl`, `adb`) | `IOS-001`..`IOS-020` and `AND-001`..`AND-018` in `references/rules/registry.yaml`, 34 detectors in `scripts/checks/platform.py`, `scripts/ux_native.sh`, `references/ops/ios.md`, `references/ops/android.md` | Each guidance bullet became a rule with a severity, a class, a basis and an acceptance criterion, then a detector that reads SwiftUI, UIKit, Compose, Flutter or React Native source. The three evidence rules per platform became a runtime tier that captures light, dark and enlarged-text screenshots and records the device — and records the tool's absence as NOT_RUN where it cannot |
| The thirty operations (`colorize`, `typeset`, `layout`, `shape`, `animate`, `delight`, `distill`, `bolder`, `quieter`, `overdrive`, `clarify`, `polish`, `craft`, `ios`, `android`, `adapt.native`, `audit.native`, `live`, `live-setup`, `generate`, `visualize`, `document`, `onboard`, `extract`, `adapt`, `doctor`, `routing`, `operate`, `new-work`, `hooks`) | `references/ops/` | Rewritten, and each one ends by naming the detectors that adjudicate its output, so an operation finishes in a status rather than an impression. Three gained a tool where impeccable states a judgement: `palette.py` for `colorize`, `typescale.py` for `typeset`, `ux_live.sh` for `live`. `audit.native`'s five 0–4 dimension scores were deliberately **not** carried — a composite lets a 2 in accessibility average against a 4 in performance, and the 2 is somebody unable to use the app |

impeccable's Rust detection engine was **not** ported. deluxui ships as a skill directory
that gets copied into a runtime's skills folder, with `python3` + `pyyaml` as its only
dependency and no build step, so a compiled per-platform binary is not distributable in
this form. The checks here are independent Python implementations.

## platform-design-skills

impeccable's own third-party notice records that its `ios.md` and `android.md` platform
references are distilled from ehmo's **platform-design-skills**.

- **Upstream:** https://github.com/ehmo/platform-design-skills
- **License:** MIT

deluxui **does** now carry that material, by way of impeccable: the `IOS-*` and `AND-*`
rule families above trace back through impeccable's platform references to this work. The
chain is attribution-preserving in both directions — MIT and Apache-2.0 both permit the
derivation, and both require the notice, which is why this section exists rather than
being folded into the one above.

What deluxui adds on top is the verdict: each guidance bullet is a rule with a severity
and a source, bound to a detector that reads real source, and the platform's own
verification commands are wrapped in a tier that records what it could not run. The
underlying platform judgements — 44pt, 48dp, safe areas, Dynamic Type, the Material type
scale, the system Back contract — are Apple's and Google's, cited as `S47` and `S48` in
the source registry, and are not claimed as anyone's original work here.
