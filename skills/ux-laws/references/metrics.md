# Guardrails and metrics — what to hold the app to

A guardrail is a number with a source, a way to measure it, and a threshold that turns it into PASS, WARN or
FAIL. These thresholds are encoded in `scripts/scorecard.py → THRESHOLDS`; keep the two in sync if you tune
them.

Three kinds of threshold, and say which one you're citing:
- **Standard:** WCAG 2.2, Core Web Vitals. External, citable, non-negotiable for FAIL.
- **Law-anchored:** a Laws of UX number the site itself states (Doherty <400ms), or a rule from the component-systems set (44px targets, toast timings).
- **House guardrail (tunable):** this skill's default for drift and sprawl (≤9 font sizes, ≤5 radii, token adoption ≥0.8). Reasonable starting points, not research results. A project may tune them; record the reason in the report.

**Honest numbers.** Never claim a conversion or completion lift from fixing a law. You can claim measured
changes ("targets below 24px: 20 → 0", "checkout fields in one step: 12 → 4 across 3 steps", "LCP p75 3.1s →
2.2s"). You can't claim "+18% conversions" unless the product's own analytics show it after shipping.

## Contents
- Runtime guardrails (probe.js)
- Static guardrails (inventory.py)
- Manual guardrails
- Flow-cost metrics (the journey, not the screen)
- Component-system health
- Wiring it into CI

## Runtime guardrails (probe.js)
| id | Metric | PASS | FAIL at | Kind | Source |
|---|---|---|---|---|---|
| viewport_meta | Pages missing a usable `<meta name=viewport>` (or blocking zoom) | 0 | ≥1 | Standard | WCAG 1.4.4; MDN viewport meta |
| reflow | Horizontal scroll at any captured width | none | any | Standard | [WCAG 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) |
| targets_24 | Targets below 24×24 CSS px | 0 | ≥1 | Standard | [WCAG 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) (inline text links exempt) |
| targets_44 | Targets below 44px on touch | 0 | WARN only | Law-anchored | Fitts's Law; Apple HIG 44pt (Material: 48dp, a separate citation) |
| input_zoom | Inputs under 16px font on phones | 0 | ≥1 | Platform behavior | iOS Safari zooms on focus below 16px |
| unlabeled_fields | Fields without a programmatic label | 0 | ≥1 | Standard | WCAG 1.3.1, 3.3.2, 4.1.2 |
| type_hints | Email/phone/numeric fields without `type`/`inputmode` | 0 | WARN only | Law-anchored | Postel's Law |
| form_wall | Most visible fields in one form or step | ≤7 | ≥13 | House | Chunking, Hick's |
| primary_actions | Filled or gradient CTAs in the first viewport | ≤1 | ≥3 | Law-anchored | Hick's, Von Restorff |
| contrast | Text below 4.5:1 (3:1 large) | 0 | ≥1 | Standard | [WCAG 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) |
| tiny_text | Text under 12px | 0 | WARN only | House | Cognitive Load |
| images_alt | Images with no `alt` attribute | 0 | ≥1 | Standard | WCAG 1.1.1 |
| h1 | Pages without exactly one h1, or with skipped levels | 0 | WARN only | House | Chunking; WCAG 1.3.1 |
| nav_links | Top-level nav links | ≤7 | WARN only | Law-anchored (review trigger) | Hick's. **Not** a Miller 7±2 cap |
| fixed_chrome | Phone viewport share under fixed/sticky bars | ≤0.20 | ≥0.35 | House | Selective Attention |
| hover_only | Hover-reveal rules not inside `@media (hover: hover)` | 0 | WARN only | Law-anchored | Hover-vs-touch rule; Jakob's |
| font_families | Distinct font families rendered | ≤3 | ≥5 | House | Similarity |
| font_sizes | Distinct font sizes rendered | ≤9 | ≥14 | House | Similarity, Prägnanz |
| radii | Distinct border radii | ≤5 | ≥8 | House | Common Region; radius rules |
| shadows | Distinct box shadows | ≤4 | ≥7 | House | Common Region |
| gradients | Elements with gradient backgrounds | ≤1 | WARN only | House (anti-generic) | Von Restorff |
| copy_tells | Template phrases found ("Welcome back", "An error occurred"…) | 0 | WARN only | House | Mental Model, Peak-End |
| em_dashes | Em/en dashes in visible UI copy | 0 | WARN only | House (copy tell) | visual-quality.md §5 |
| emoji | Emoji used as UI icons or decoration | 0 | WARN only | House | Cognitive Load; icon lock |
| eyebrows | Small uppercase tracked labels on the page | ≤2 | WARN only | House | Selective Attention; visual-quality.md §6 |
| accent_hues | Distinct saturated hues on interactive elements | ≤2 | ≥4 | House (accent lock) | Von Restorff, Similarity |
| lcp | Largest Contentful Paint, one lab load | ≤2500ms | ≥4000ms | Standard (field p75) | [web.dev LCP](https://web.dev/articles/lcp) |
| cls | Cumulative Layout Shift, one lab load | ≤0.1 | ≥0.25 | Standard (field p75) | [web.dev CLS](https://web.dev/articles/cls) |

Lab LCP/CLS come from a single load on the auditor's machine. Core Web Vitals are assessed on the 75th
percentile of real users. Report lab numbers as leads, and prefer CrUX or RUM data when the project has it.

Contrast is measured on solid backgrounds only. Text over images or gradients counts as `unmeasurable`
and needs a manual check (or axe-core, which handles more cases).

## Static guardrails (inventory.py)
| id | Metric | PASS | FAIL at | Notes |
|---|---|---|---|---|
| token_adoption | `var(--token)` refs ÷ (refs + raw color and arbitrary literals) | ≥0.8 | <0.5 | Adjust for Tailwind themes: theme utility classes are tokens even without `var()` |
| families_split | UI families with >1 member | 0 | WARN only | Each one is a consolidation decision (merge or keep-separate-with-reason) |
| dup_names | Component names defined in several files | 0 | WARN only | Check for platform splits before reporting |
| bypass | Raw native controls where a primitive exists | 0 | ≥10 | Each bypass re-implements states and a11y |
| data_states | Data views missing loading, error or empty | 0 | ≥1 | Verify by following data up one level |

## Manual guardrails
Put these in `ux-audit/manual.json` and pass `--manual`; until then they're NOT_MEASURED.
```json
{ "inp_ms": 160, "feedback_ms": 280, "focus_visible": true, "keyboard_complete": true,
  "states_verified": 14, "states_total": 16 }
```
| id | Metric | PASS | FAIL at | Source |
|---|---|---|---|---|
| inp_ms | Interaction to Next Paint (field p75 if available) | ≤200 | ≥500 | [web.dev INP](https://web.dev/articles/inp) |
| feedback_ms | Slowest visible response to an action on the critical path | ≤400 | ≥1000 | [Doherty Threshold](https://lawsofux.com/doherty-threshold/) |
| focus_visible | Every control shows focus | true | false | WCAG 2.4.7 |
| keyboard_complete | Critical path doable by keyboard alone | true | false | WCAG 2.1.1 |
| states_coverage | Forced states that behaved ÷ states forced | 1.0 | <0.5 | Doherty, Postel's, Peak-End |

To get `feedback_ms` without tooling: in DevTools Performance, record the click and read the time to the next
visual change. In Playwright, wrap `click()` and `waitForSelector(<feedback>)` with `performance.now()`.

## Flow-cost metrics (the journey, not the screen)
Measure for each critical path in `flows.md`, and record before and after:
| Metric | How | Law |
|---|---|---|
| Screens to complete | count | Hick's, Goal-Gradient |
| Taps/clicks to complete (happy path) | count while walking | Fitts's, Parkinson's |
| Fields typed | count, minus fields that autofill would handle | Postel's, Tesler's |
| Decisions asked | count of choice points | Hick's, Choice Overload |
| Waits over 400ms without feedback | count | Doherty |
| Dead ends (no way forward on an error or empty screen) | count, target 0 | Peak-End |
| Survives refresh/Back mid-flow | yes/no per step | Zeigarnik |

These are the most persuasive numbers in a report, because anyone can re-count them.

## Component-system health
Track across iterations:
- primitives count, and the share of UI built from them (raw-element bypass trending to 0)
- families with more than one member, trending down, or each one justified in writing
- token adoption trending up; runtime sprawl (font sizes, radii, shadows) trending down
- the share of data views with all four states

## Wiring it into CI
The scripts are CI-friendly:
```bash
python3 scripts/inventory.py . --out ux-audit
node scripts/walk.mjs --base "$PREVIEW_URL" --routes-file ux-audit/routes.txt --out ux-audit/captures
python3 scripts/scorecard.py --inventory ux-audit/inventory.json --probes ux-audit/captures \
  --baseline ux-audit/baseline/scorecard.json --out ux-audit --gate   # exit 1 on any FAIL
```
Start with `--gate` off and a committed baseline, then turn the gate on once the FAILs are fixed, so the
ratchet only tightens. Copy the scripts into the repo (e.g. `tools/ux/`) rather than pointing CI at a skill
install path.
