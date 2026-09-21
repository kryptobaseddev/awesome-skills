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
| `comp-spec` -- a reference image becomes region boxes with sampled palettes, and the rule that a region's MEDIUM follows from what the pixels are rather than from what feels buildable | `scripts/comp_spec.py`, `references/ops/visualize.md` | Reimplemented on a stdlib PNG decoder (`scripts/pngread.py`), so it needs no image model and no new dependency. The flat/plate/mixed classification is stated as thresholds on distinct-colour count and edge density rather than as judgement, and `mixed` is a reported outcome rather than a coin toss |
| `embed-prompt` -- generation context belongs inside the asset, not in a sidecar | `comp_spec.py --provenance` / `--read-provenance` | A PNG `tEXt` chunk written in place |
| The visual-contrast pixel sampling in `browser-bundle/35-visual.js` (canvas reads, percentiles) | `R-PIXEL-CONTRAST` in `scripts/ux_report.py` | Arrived at independently while fixing a false-positive class, then found to have landed on the same percentile approach. Noted here because the convergence is real even though the code is not shared |
| `generate-image` -- a comp produced by an image model | `scripts/ux_image.py` (`render`, `generate`, `prompt`, `verify`, `providers`), `references/ops/visualize.md` | Taken with three changes. The prompt is built from the contract -- the palette by role with its values, the families, the ladder, the radii, the one depth metaphor, what the visitor came to do, and the regions with their shares and mediums -- rather than from an adjective. Four providers are tried in order (a harness command, the `image-nanobanana` skill, the Gemini API, OpenAI) and each reports its own absence, so no-provider is NOT_RUN rather than a silent no-op. And what comes back is **measured**: `verify` requires every declared colour role to be present at real coverage, with a per-colour tolerance derived from the quantiser rather than a fixed one, and reports a colour that is close in magnitude but the opposite way round the hue wheel as a different world rather than a near miss. A generator alone never does that half, and without it an approved comp can be in a palette nobody declared |
| The deterministic half of a comp round | `ux_image.py render` | Not in impeccable and added here: a comp sheet drawn from the contract with no model, no key and no network. Every fill is a declared role, every size a declared rung, so it is conformant by construction and cannot be the thing that drifts -- and where the contract has blanks, the sheet names them on its face rather than presenting a placeholder as a proposal |
| `serve-question` -- an HTML decision page served to the user | `scripts/ux_question.py`, `references/ops/decide.md` | Taken, and made admissible. The page is themed from the project's own contract, shows each option's region table beside its comp (a page of three pictures with no structural claim collects an approval of the atmosphere), and refuses four things: an answer with no author, an author naming the agent, a reason under forty characters, and a timeout -- which records nothing and exits 3 rather than defaulting. The record carries a hash of exactly what was shown, so editing an approved comp afterwards makes the approval stale and the build gate says so |
| `build-phase` -- a state machine gating spec -> plates -> build | `scripts/ux_phase.py`, `references/ops/phase.md` | Taken, and made evidential. Entering `comp` snapshots the contract's hash, the git head and every UI file's hash; entering `verify` compares against it, so "the declaration came first" is measured from the repository rather than tracked as a state somebody advanced. A contract declared with no file changed since is reported as FAIL, because that is what a contract written to describe existing code looks like from outside. A brownfield project declares itself and gets the honest version. The refusal is wired to `PreToolUse`, so it arrives while the file is open, and the override is audited because a gate with no way past it gets bypassed by deleting the state file |
| `build-font-index` -- face availability and pairing | `scripts/fontindex.py`, `S-CONTRACT-FONT-AVAIL`, `VIS-010` | Taken, with one refusal: the faces installed on the build host are never treated as evidence that a visitor has them, because a build host's font list describes the build host. It looks for all five ways a face legitimately arrives and matches across spellings, so a contract naming `Söhne` resolves to `sohne-web-buch.woff2` on disk |
| The craft body -- the reference files behind each operation | `references/craft/` (thirteen files: type, colour, space, depth, composition, density, motion, imagery, iconography, voice, states, detail, plus the index) | Rewritten rather than adapted, and each file ends by naming the detectors that adjudicate its claims. Craft writing normally terminates in an exhortation -- *be intentional*, *respect the grid* -- and an exhortation cannot be wrong, so it cannot be checked, so it changes nothing. Where a claim resolves to no threshold, no declared field and no manual question, it is marked as taste |
| The thirty operations (`colorize`, `typeset`, `layout`, `shape`, `animate`, `delight`, `distill`, `bolder`, `quieter`, `overdrive`, `clarify`, `polish`, `craft`, `ios`, `android`, `adapt.native`, `audit.native`, `live`, `live-setup`, `generate`, `visualize`, `document`, `onboard`, `extract`, `adapt`, `doctor`, `routing`, `operate`, `new-work`, `hooks`) | `references/ops/` | Rewritten, and each one ends by naming the detectors that adjudicate its output, so an operation finishes in a status rather than an impression. Three gained a tool where impeccable states a judgement: `palette.py` for `colorize`, `typescale.py` for `typeset`, `ux_live.sh` for `live`. `audit.native`'s five 0–4 dimension scores were deliberately **not** carried — a composite lets a 2 in accessibility average against a 4 in performance, and the 2 is somebody unable to use the app |

### Still not taken

One capability remains impeccable's, and it is a real one:

| Not taken | Why |
|---|---|
| `live` variant generation -- selecting an element in the running app, having three AI-generated HTML+CSS variants hot-swapped in through the dev server's HMR, and accepting or discarding one in the browser | deluxui takes the first half and deliberately stops before the second. `scripts/ux_select.py` injects a selection overlay over CDP, so a person can click what is wrong and have it recorded as a request naming an operation and an element. What it does not do is patch the DOM with a generated variant: the change belongs in the source, where the dev server's own reload shows it and `ux_live.sh` measures the delta. That is a smaller feature and it is a position, not an omission -- a variant that exists only in the page has to be committed back afterwards, and impeccable's `live-manual-edits-buffer`, `live-commit-manual-edits` and per-framework adapters are the machinery that round trip needs. It is also the reason this one stays theirs: it is a Node subsystem, and deluxui ships python3 plus pyyaml with no build step |

Two things were taken and then deliberately narrowed, which is different from not
taking them:

- `audit.native`'s five 0-4 dimension scores. A composite lets a 2 in
  accessibility average against a 4 in performance, and the 2 is somebody unable
  to use the app.
- `visualize`'s "three comps" as a fixed number. Two is the minimum the decision
  page will serve, because one invites a rubber stamp; three remains the default.

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
