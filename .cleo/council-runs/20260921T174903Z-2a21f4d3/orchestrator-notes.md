# Orchestrator notes — refinements to the evidence pack

## Correction to evidence item 3 (made before Phase 2.5, disclosed to the Chairman)

Item 3 grepped only `references/`. Re-measured across the whole skill (excluding
`docs/`, which is the owner's source rulebook, not skill guidance):

| craft topic | where it appears |
|---|---|
| type scale | `references/preserve.md` (one passing mention, not guidance) |
| colour/color ramp | NONE |
| grid system / column grid / baseline grid | NONE |
| elevation | `assets/templates/DESIGN.md` — as a *prompt to fill in* |
| focal point / visual weight | NONE |
| vertical rhythm | NONE |
| font pairing | NONE |
| optical | `references/workflows/improve.md`, `references/rules/02-thresholds.md` |

The refinement that matters: `assets/templates/DESIGN.md` does name Type roles, Spacing
base unit, Elevation ("pick one metaphor"), Themes ("dark mode is not an inverted light
theme — it needs its own contrast and saturation decisions"), Motion and Density. So the
skill **captures** design decisions. It does not **help make** them. A template that asks
"How is depth expressed?" records an answer; it does not teach how to choose one.

Item 3's claim therefore stands in substance — there is no positive craft guidance — but
the skill is not as bare as a `references/`-only grep suggests.

## Additional measurement by the orchestrator: the 40-layer coverage map

Mapping the original plan's 40 reasoning layers (`docs/deluxui-plan-ideas.md:247-288`)
onto rules and non-inert detectors:

- **38 of 40 layers have automated coverage.**
- The 2 without are `35 Platform conventions` (iOS/Android native, 3 rules, manual only)
  and `39 Accessibility QA` (process attestation, 2 rules, manual only). Both are
  legitimately manual — a web CLI cannot automate "a screen-reader user completed this".

The important caveat, which is the whole question this council exists to answer: this map
measures coverage of each layer **as a constraint**, not as a generative craft. Layers
05 Visual hierarchy, 06 Gestalt, 15 Typography, 16 Colour, 17 Spacing and 18 Layout all
have rules and working detectors — but those detectors *check* a contrast ratio, a measure
in ch, a spacing multiple. None of them *compose*. Detectors detect; that is what they are.

## Feasibility probe run by the orchestrator: is design craft measurable?

The premise of any "make design verifiable" recommendation is that design-system
coherence can be measured and that the measurement discriminates. Tested against four
real codebases, counting Tailwind utility usage:

| project | files | type steps | arbitrary `text-[..]` | per file | hue families | colour tokens |
|---|---|---|---|---|---|---|
| keystone-casa | 124 | 12 | 2 | 0.016 | 12 | 52 |
| ClinoVate-saas | 171 | 11 | 3 | 0.018 | 9 | 65 |
| florida-grande-webapp | 401 | 17 | 51 | 0.127 | 23 | 106 |
| emdash | 515 | 12 | 88 | 0.171 | 18 | 99 |

Two findings, one of them counter to expectation:

1. **Step counts do not discriminate.** Every project uses 11–17 type steps and 19–22
   spacing steps. "Counts its scale steps" would be a useless check.
2. **Arbitrary escapes and palette breadth discriminate by ~10x.** Arbitrary `text-[..]`
   per file separates the disciplined projects (0.016–0.018) from the sprawling ones
   (0.127–0.171) by an order of magnitude. Hue families separate 9–12 from 18–23.

So design-system coherence IS measurable and falsifiable — but only on the axes that
measure *escapes from* a system, not the shape of the system itself. That is the same
epistemics the rest of the skill already runs on, and it is a precondition for any
recommendation that design craft can enter deluxui without becoming taste assertion.

Precedent already in the codebase: `scripts/checks/browser/measure.js` measures
characters-per-line **as actually rendered**, deriving average advance width from a
hidden probe span. That is a genuine typographic craft property made falsifiable through
computed style. It is the existence proof that the `computed` engine can carry craft.

## The decisive measurement: partitioning the 19 laws by source of truth

First Principles' atom 3 says a claim is checkable iff a decision procedure exists whose source of
truth lies outside the claimant, and that there are exactly three such sources: an external
standard, a prior declaration, or an observed outcome. Applying that partition to all 38 `verify:`
clauses (19 enforceable laws × 2), against detectors that already fire today:

**Laws with at least one verify clause an EXISTING detector already adjudicates — 14 of 19:**

| Law | verify clause | detector that already fires |
|---|---|---|
| LAW-02 Fitts | "Target bounds pass Section 06" | `S-TARGET-SIZE`, `R-TARGET`, `R-TARGET-COARSE` — a literal pointer |
| LAW-03 Jakob | "Keyboard and pointer behavior match the chosen platform pattern" | `S-COMP-KEYBOARD-PATTERN` |
| LAW-04 Proximity | "Every field error unambiguously belongs to its control" | `S-FORM-VALIDATION` |
| LAW-06 Doherty | "Verify waiting, failure, timeout, and retry states under throttling" | `R-STATE-ERROR/EMPTY/OFFLINE`, `R-VITALS` |
| LAW-07 Von Restorff | "Important differences remain understandable without relying only on color" | **`S-COLOR-ONLY`** — built this session, for A11Y-005 |
| LAW-08 Target distance | "Actions remain reachable with keyboard and touch" | `R-FOCUS-WALK` + `R-TARGET` |
| LAW-09 Serial position | "Required information appears before commitment" | `commitment.py` detectors |
| LAW-10 Peak-end | "Completion reflects the actual system state" | `S-STATE-OPTIMISTIC` |
| LAW-11 Zeigarnik | "Resume restores the correct confirmed draft" | `S-CONFLICT-OVERWRITE` |
| LAW-12 Prägnanz | "The task hierarchy survives real content and small viewports" | `R-REFLOW` at 320/390 |
| LAW-13 Similarity | "Users can distinguish static, selected, disabled, and actionable items" | `S-COMP-DISABLED-MUTE`, `S-UX-FAKE-INTERACTIVE` |
| LAW-15 Tesler | "Automated values have a clear origin and correction path" | `S-FORM-DERIVED-STALE` |
| LAW-16 Postel | "Ambiguous or malicious inputs are rejected safely with useful feedback" | `S-FORM-VALIDATION`, `safety.py` |
| LAW-20 Pareto | "Prioritization records frequency evidence or UNKNOWN plus impact" | the `report` tier / MEASURE rules |

**Laws whose every clause needs a human or an observed outcome — 5 of 19:** LAW-01 (Hick:
"users can locate the required option" — a usability session, nothing else), LAW-05 (Miller),
LAW-14 (uniform connectedness), LAW-18 (Parkinson), LAW-19 (Occam: "the simpler option satisfies
the same tasks" is a counterfactual comparison, which has no artifact to measure).

**Conclusion.** The Expansionist's claim survives: roughly 14 of 19 laws are already adjudicated by
machinery that runs on every scan — the missing artifact is an index, not a detector. And the
Contrarian's constraint survives with it: the 5-law remainder has no landing zone except the manual
bus, so the partition must be *published* (live / manual / unreachable) rather than flattened, or the
5 become exactly the laundering path described. The two findings are complements. That is what the
Chairman has to reconcile, and the partition above is the number that lets it be reconciled by
arithmetic instead of argument.

## A fourth inert mechanism, found while checking the Outsider's finding 3

`references/workflows/improve.md:13-19` instructs the user:

> ```
> agent-browser open <url> && agent-browser screenshot .deluxui/reports/baseline.png
> ```
> Without this, `R-BASELINE-DIFF` reports NOT_RUN and you have no way to show that the
> parts you were not asked to change did not move.

But `ux_report.py:293` sets `RUNTIME["R-BASELINE-DIFF"] = None`, and `:302` gives its reason as
*"No baseline screenshot was recorded before the change."* `ux_browser.sh` never calls
`agent-browser diff` at all. So a user who follows the instruction exactly still gets NOT_RUN, with
a message that **blames them for an omission that is the code's**. The instruction is futile and the
error message is actively misleading.

This is the same defect class as the four inert config keys fixed in v2.2.0 and the inert `laws:`
block: a documented mechanism with no implementation behind it. That makes three independent
instances of one pattern in this skill, which is itself the finding — the skill's failure mode is
not bad checks, it is **documented capabilities that were never wired**, and it has no test that
catches that class. `selftest.py` gained positive controls for config keys in v2.2.0; the same
discipline is not applied to laws, to `R-BASELINE-DIFF`, or to prose instructions generally.

The sharpest version: `improve.md:28-30` asserts *"The checks distinguish them; squinting does
not"* about three diagnoses — inconsistent scale steps, groups spaced like their contents
(LAW-04), and optical misalignment. No detector reads LAW-04, and "optical" has no definition
anywhere in `references/`. Two of the three named diagnoses have no check, in a sentence promising
the checks can tell them apart.

## Peer review corrected the recommendation's priority — recorded for the Chairman

The Contrarian's review of First Principles failed it on G2 for a claim the recommendation's
ordering rests on, and the correction holds when I check it myself:

First Principles claimed VIS-001 is *"currently adjudicated by `S-SLOP-PALETTE`,
`S-CRAFT-PALETTE-WARM`, `S-CRAFT-TYPESYSTEM`, `S-CRAFT-DEPTH`, `S-CRAFT-RHYTHM`, every one
`confidence: low`"*. Measured:

| detector | rules it actually carries | confidence |
|---|---|---|
| `S-TOKEN-HEX` | VIS-001 | **high** |
| `S-TOKEN-ARBITRARY` | VIS-001 | **high** |
| `S-SLOP-PALETTE` | VIS-001, VIS-006 | low |
| `S-CRAFT-PALETTE-WARM` | VIS-001, VIS-006 | low |
| `S-CRAFT-TYPESYSTEM` | VIS-002, VIS-006 — **not VIS-001** | low |
| `S-CRAFT-DEPTH` | VIS-006 — **not VIS-001** | low |
| `S-CRAFT-RHYTHM` | VIS-002, VIS-006 — **not VIS-001** | low |

Four detectors, not five; two of them high-confidence, and First Principles omitted exactly the
two that are high. This matters more than a miscount, because **`S-TOKEN-ARBITRARY` is the detector
that carries the one signal my feasibility probe found to discriminate by 10x** (arbitrary
`text-[..]`/`p-[..]` escapes: 0.016–0.018 per file in the disciplined corpora vs 0.127–0.171 in the
sprawling ones). The strongest available design-coherence measurement is therefore *already wired,
already high-confidence, and already bound to VIS-001*.

Consequence for the verdict: a machine-readable visual contract is NOT the highest-yield change for
VIS-001 — that ground is already held. Its value is confined to the axes where **no detector exists
at all**: the elevation set, the colour-ramp steps, the type-scale steps, the column grammar. That
is a real but narrower prize than First Principles argued, and the ordering must reflect it.

Also corrected: the status vocabulary has **five** fates, not four —
`PASS, FAIL, NOT_RUN, NOT_APPLICABLE, APPROVED_EXCEPTION` (`registry.yaml` meta). The fifth matters
here, because `APPROVED_EXCEPTION` is a landing zone for a declared deviation that neither
laundering nor a permanent NOT_RUN tail would provide.
