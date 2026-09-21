# Numeric thresholds

20 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Every number this skill enforces, with its class. STANDARD values come from WCAG and are not negotiable within their scope. PROJECT values are defaults you may override in `.deluxui/ux.config.yaml` with a recorded reason. Machine-readable form: `references/rules/thresholds.yaml`.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **NUM-001** | P1 | STANDARD | Contrast at least 4.5:1 against the actual background. | Check all applicable text and states. Apply only documented SC 1.4.3 exceptions. | S03 | `S-CONTRAST-PAIR`, `S-CRAFT-DECOR`, `R-CONTRAST`, `R-PIXEL-CONTRAST`, `S-CRAFT-GRADIENT-TEXT`, `S-CRAFT-GRAY-ON-COLOR` |
| **NUM-002** | P1 | STANDARD | Contrast at least 3:1. Large means at least 18 pt regular or 14 pt bold, approximately 24 or 18.67 CSS px. | Verify rendered size and weight before using the lower ratio. | S03 | `S-CONTRAST-PAIR`, `R-CONTRAST` |
| **NUM-003** | P1 | STANDARD | At least 3:1 against adjacent colors for applicable UI component and graphical information. | Check necessary boundaries, states, and graphics. Respect SC 1.4.11 exceptions. | S04 | `R-CONTRAST`, `R-PIXEL-CONTRAST` |
| **NUM-004** | P1 | STANDARD | At least 24 by 24 CSS px, or a valid SC 2.5.8 exception. | Document spacing, equivalent, inline, user-agent, or essential exception where used. | S02 | `S-TARGET-SIZE`, `R-TARGET` |
| **NUM-005** | P1 | PROJECT | Default at least 44 by 44 CSS px actual hit area. | Use a larger area when the task warrants it. Any dense-UI exception still passes NUM-004. | S00 | `S-TARGET-SIZE`, `S-TYPE-CRAMPED`, `R-TARGET-COARSE` |
| **NUM-006** | P1 | PLATFORM | Adopt at least 44 by 44 pt for tappable controls. | Measure the tappable area rather than only the icon. | S15 | `S-IOS-TARGET44` |
| **NUM-007** | P1 | PLATFORM | Adopt at least 48 by 48 dp for touch targets. | Measure the touch area and check adjacent targets do not overlap. | S16 | `S-AND-TARGET48` |
| **NUM-008** | P1 | STANDARD | Support 200 percent text resizing without loss of content or functionality, subject to SC 1.4.4 exceptions. | Exercise controls, errors, menus, and dialogs after resizing. | S01 | `R-ZOOM` |
| **NUM-009** | P1 | STANDARD | Reflow at 320 CSS px width for vertical content or 256 CSS px height for horizontal content. | No two-dimensional scrolling except content that requires a two-dimensional layout for use or meaning. | S05 | `S-RESP-FIXEDPX`, `R-REFLOW` |
| **NUM-010** | P1 | STANDARD | Tolerate line height 1.5 times font size, paragraph spacing 2 times, letter spacing 0.12 em, and word spacing 0.16 em. | No content or function loss. These are override tolerances, not mandatory authored style values. | S07 | `S-TYPE-LEADING`, `R-TEXTSPACING` |
| **NUM-011** | P1 | STANDARD | AA baseline includes visible focus and focus not entirely hidden by authored content. Project target is fully visible focus. | Check sticky headers, banners, drawers, and virtual keyboards. Do not label a fixed 2 px ring as an AA requirement. | S01 S06 S00 | `S-FOCUS-OUTLINE`, `R-FOCUS-WALK`, `R-FORCED-COLORS`, `R-STICKY-OBSTRUCTION` |
| **NUM-012** | P1 | PROJECT | LCP at most 2.5 s, INP at most 200 ms, and CLS at most 0.1 at the 75th percentile. | Evaluate mobile and desktop separately. Lab measurements alone do not establish a field pass. | S14 | `S-PERF-IMGDIM`, `S-3D-PERF`, `R-VITALS`, `M-FIELD-PERF` |
| **NUM-013** | P1 | PROJECT | Target p95 at most 100 ms from input to perceptible acknowledgement. | Measure representative devices. Not a server completion deadline and not the same metric as INP. | S00 | `R-STATE-SLOW`, `S-PERF-BLOCKING` |
| **NUM-014** | P1 | PROJECT | At about 1 s, expose persistent pending status. Beyond about 10 s, add useful stage information and a recovery path. | Immediate acknowledgement remains required. Percent progress requires actual measurable progress. | S31 S00 | `S-STATE-LOADING`, `R-STATE-SLOW` |
| **NUM-015** | P2 | PROJECT | Default 1 rem for web body text. Usually 16 CSS px at the user default. Use native scalable text styles on native apps. | Respect user font settings. Dense secondary text needs a readability review. | S00 | `S-TYPE-TINY`, `S-VIDEO-LEGIBILITY`, `S-CRAFT-TYPE-FLAT`, `S-CONTRACT-TYPE-SCALE` |
| **NUM-016** | P2 | PROJECT | Starting range 45 to 75 ch for Latin-script reading content. | Do not apply as a hard limit to tables, labels, code, or every writing system. | S00 | `S-TYPE-MEASURE`, `R-MEASURE` |
| **NUM-017** | P2 | PROJECT | Use the existing scale. For a new system, start with 4-unit spacing increments and named exceptions. | Check optical alignment and real content. Do not force every dimension onto the scale. | S00 | `S-TOKEN-ARBITRARY` |
| **NUM-018** | P2 | PROJECT | Starting duration 120 to 240 ms for nonessential local transitions. | Respect reduced-motion preferences. Never delay functionality to finish animation. | S00 | `S-MOTION-REDUCE`, `S-CRAFT-MOTION`, `S-CRAFT-EASING`, `S-CONTRACT-MOTION` |
| **NUM-019** | P1 | PROJECT | Include 320, 390, 768, 1024, and 1440 CSS px widths plus content-driven boundary cases. | These are test widths, not mandatory breakpoints or a complete device matrix. | S00 | `R-REFLOW` |
| **NUM-020** | P0 | PROJECT | A repeated activation of one pending operation must not cause a second unintended commit. | Verify interface guarding plus server-supported deduplication or idempotency where required. | S00 | `S-STATE-DUPE`, `S-RETRY-SAFETY` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S01 |  — Web Content Accessibility Guidelines 2.2 | normative_standard |
| S02 |  — Understanding Target Size Minimum, SC 2.5.8 | official_explanation |
| S03 |  — Understanding Contrast Minimum, SC 1.4.3 | official_explanation |
| S04 |  — Understanding Non-text Contrast, SC 1.4.11 | official_explanation |
| S05 |  — Understanding Reflow, SC 1.4.10 | official_explanation |
| S06 |  — Understanding Focus Not Obscured Minimum, SC 2.4.11 | official_explanation |
| S07 |  — Understanding Text Spacing, SC 1.4.12 | official_explanation |
| S14 |  — Web Vitals | official_metric_guidance |
| S15 |  — UI Design Dos and Don’ts | official_platform_guidance |
| S16 |  — Make Apps More Accessible | official_platform_guidance |
| S31 |  — Response Times: The 3 Important Limits | original_practitioner_guidance |
