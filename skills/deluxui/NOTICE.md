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

impeccable's Rust detection engine was **not** ported. deluxui ships as a skill directory
that gets copied into a runtime's skills folder, with `python3` + `pyyaml` as its only
dependency and no build step, so a compiled per-platform binary is not distributable in
this form. The checks here are independent Python implementations.

impeccable's own third-party notice records that its `ios.md` and `android.md` platform
references are distilled from ehmo's `platform-design-skills` (MIT,
https://github.com/ehmo/platform-design-skills). deluxui does not currently carry that
material; this note is here so the chain is not lost if it ever does.
