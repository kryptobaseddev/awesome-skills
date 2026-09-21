## Phase 3 — Chairman's verdict

### Recommendation

**deluxui does NOT handle all of UX and UI. It is world-class on validation, strong on UX engineering, and it is not a design director. Do not close that gap with design prose. Close it by wiring three capabilities the skill already owns and paid for — and fix its four false claims first, because those are the same defect class the owner has now hit three times.**

### Gate summary

| Advisor | Reviewed by | G1 Rigor | G2 Evidence | G3 Frame | G4 Action | Passes | Disposition | Weight |
|---|---|---|---|---|---|---|---|---|
| Contrarian | Executor | PASS | FAIL | PASS | PASS | 3/4 | Modify | high |
| First Principles | Contrarian | PASS | FAIL | PASS | PASS | 3/4 | Modify | high |
| Expansionist | First Principles | PASS | FAIL | PASS | PASS | 3/4 | Modify | high |
| Outsider | Expansionist | PASS | FAIL | PASS | PASS | 3/4 | Modify | high |
| Executor | Outsider | FAIL | FAIL | PASS | FAIL | 1/4 | Modify | low |

Every advisor failed G2. That uniformity is itself the run's finding: five independent passes each stretched a citation while the artifact's own arithmetic survived every audit (`lint_rules.py` prints exactly what `SKILL.md` claims). The analyses are sound; their pointers were not. I have re-derived every load-bearing number myself and cite only what I verified.

### Why this, not the alternatives

**Not "add a design-craft library"** — the A/B measured zero delta (17/18 vs 17/18) on knowledge-shaped assertions, and design prose is knowledge-shaped by construction. Matching impeccable's 6,576 lines optimises the one axis measured as flat, while every unbound claim adds a NOT_RUN whose only fates are reader desensitisation or silencing.

**Not "stay a pure verification engine"** — that option does not exist for composition. Verification requires something declared to verify against, and declaring it *is* the generative act. The either/or in the question is a false decomposition; the real axis is one-dimensional: does the skill capture design intent at the moment of choosing? Today, no.

**Not "replace impeccable"** — it wins outright on composition and deluxui wins outright on verification. Two skills, two jobs.

### The answer to the owner's question

**Validation: yes, decisively.** 38 of the plan's 40 reasoning layers have automated coverage; the 2 that do not (`35 Platform conventions`, `39 Accessibility QA`) are legitimately manual. 190 rules, 166 detectors, three tiers, and a gate where an unchecked P0 blocks a release. Nothing numeric in the marketing surface is inflated.

**Testing: yes.** The runtime tier forces the offline, aborted and empty states nobody tests, measures real hit areas and rendered characters-per-line, and walks focus. `measure.js` is the existence proof that craft properties can be measured rather than asserted.

**Design: no.** The entire positive design vocabulary is one 67-line catalogue of moves to avoid. `create.md` reaches the generative moment and says "then style it", then stops. Zero files cover colour ramps, focal weight, grid grammar or an elevation system as *guidance* — `DESIGN.md` asks for an elevation metaphor without teaching how to choose one. Tested against "a very seasoned executive UX and UI designer": the artifact supports "seasoned reviewer who can block a release" completely and "designer" nowhere — and, as the Outsider found, it does not describe itself as one either, except at three marketing edges.

**Versus impeccable: they are complements, and the comparison the owner wanted has a clean answer.** On verification deluxui wins outright — impeccable has no rule registry, no gate, no NOT_RUN discipline. On composition impeccable wins outright: 6,576 prose lines across 28 files with `colorize`, `typeset`, `layout`, `shape`, `brand`, `animate`, `delight`, `polish` as *generative operations*, against deluxui's 1,079 lines with none. Keep both. The co-residency risk the Contrarian names is real but currently **benign precisely because deluxui has no craft surface** — a model reads them as auditor plus designer. Giving deluxui a craft surface is what would create the collision.

### Reconciling the contradiction

The Expansionist wants the laws activated; the Contrarian shows the only landing zone for the unautomatable remainder — the manual attestation bus at `ux_report.py:531` — is the mechanism that defeats the gate, and that `self_audit`'s GOV-006 would *notarise* the laundering. Both are right, and First Principles supplies the reconciliation: **partition the `verify:` clauses by their source of truth before binding any of them.** I measured that partition rather than argue it — **14 of 19 enforceable laws already have at least one `verify:` clause that an existing detector adjudicates today**; LAW-02's is literally "Target bounds pass Section 06", and LAW-07's "important differences remain understandable without relying only on color" is `S-COLOR-ONLY`, built this session. Five laws (LAW-01, 05, 14, 18, 19) have no artifact to measure and must be *published as unreachable*, not parked in a manual bucket.

The Contrarian's constraint therefore stands as a hard rule, not a caution: **no craft rule may enter through the manual tier.** Where a project deliberately departs, the fifth status fate — `APPROVED_EXCEPTION`, which First Principles overlooked by counting four — is the honest landing zone.

### What each advisor got right

- **Contrarian:** a craft rule bound to a manual detector becomes a self-attested PASS that the report's own honesty audit certifies — the laundering commit `a5f431d` was written to stop.
- **First Principles:** a design claim is checkable only against a declaration made *before* the choice; the hole at `create.md:28` is missing **capture**, not missing guidance. Conformance removes taste from the verdict instead of resolving it.
- **Expansionist:** 19 `verify:` clauses, a per-route × per-viewport screenshot corpus written and never read, and a `DESIGN.md` no script opens are all already paid for. The missing artifact is an index.
- **Outsider:** `index.md:31` and `registry.yaml:15` claim "19 enforceable laws" and nothing enforces one; `SKILL.md` never mentions laws at all.
- **Executor:** ship the measurement before arguing about `colorize.md` — but its criterion `unreachable 0` **cannot fail** (manual detectors are not in `inert`, so parking all 20 laws in `M-DESIGN-REVIEW` satisfies it in ninety seconds with N=0), and its new ERROR would force a false coverage claim about LAW-17, which the registry marks `enforceable: false`, `verify: []`, "Evaluate LAW-16 once."

### Conditions on the recommendation

The recommendation holds only under these four conditions. Remove any one and it becomes the thing the Contrarian describes.

1. **No craft rule enters through the manual attestation tier.** A rule with no computable engine is published as unreachable or takes `APPROVED_EXCEPTION` against a declared deviation. It never becomes a self-attested PASS.
2. **Any declaration used as a source of truth must precede the code it governs, and be immutable during it.** A record written after the emission is a rationalisation and will always show conformance; the sequencing is the entire epistemic content.
3. **Every documented mechanism gets a positive control before it ships.** This is the third inert-mechanism instance; the class is the defect, not the instances.
4. **Zero lines of new design prose.** If a proposed addition teaches the model something it already knows, it fails the A/B that measured 17/18 vs 17/18.

### Order of work

1. **Fix the four false claims.** "19 enforceable laws" (two places); `improve.md`'s baseline instruction, which is futile because `R-BASELINE-DIFF` is hardcoded NOT_RUN with a reason that *blames the user* for the code's omission; `improve.md:28`'s "the checks distinguish them" naming three diagnoses of which two have no check and one ("optical") has no definition; `SKILL.md`'s silence on the laws. Zero design value, pure integrity — and this is the third instance of one pattern (inert config keys → inert laws → inert baseline diff), so the real fix is a **positive control per documented mechanism**, the discipline `selftest.py` already gained for config in v2.2.0.
2. **Implement `R-BASELINE-DIFF`** — `agent-browser diff screenshot --baseline` exists, the corpus is already generated every run, and this makes the preserve ladder's central claim measured instead of argued.
3. **Index the laws**, with the denominator at 19, the partition published per tier, and a stated floor for N so the number can fail.
4. **Only then** a visual contract, confined to the axes with *no* detector — elevation set, ramp steps, type scale, column grammar. Not VIS-001: that ground is already held at high confidence by `S-TOKEN-ARBITRARY`, which carries the one signal my feasibility probe found to discriminate by 10x (arbitrary escapes, 0.016–0.018/file disciplined vs 0.127–0.171/file sprawling).
5. **Add no design prose.** The A/B measured zero delta on knowledge-shaped assertions and 15x on verifiability-shaped ones. Matching impeccable's line count optimises the one axis measured as flat.

### Next 60-minute action

Add an optional `laws:` key to `references/rules/detectors.yaml`, populated from the 14 laws whose `verify:` clauses existing detectors already adjudicate. Extend `scripts/lint_rules.py` to reject unknown law ids, compute reachability over **`enforceable`-true laws only** (19, excluding LAW-17), count manual-only separately from live, and print `laws with a live detector N  manual-only M  unreachable U`. Assert a floor — `N >= 12` — so the criterion can fail. Change no check module and write no prose.

**Expected outcome:** `lint_rules.py` exits 0 printing `N=14 M=0 U=5` with the five unreachable laws named, and `selftest.py` still prints `SELFTEST PASS` with `fired on bad: 65`.

### Confidence

**High.** Every structural claim in this verdict was re-verified against source by the Chairman, and the two quantitative claims that drive the ordering — the 14/19 law partition and the 10x escape-rate discrimination — were measured, not reasoned.
