# Accessibility completeness

14 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

WCAG 2.2 A and AA, as implementation requirements. Two cautions the rulebook is explicit about: automated testing covers a minority of the criteria, and a changed-component audit does not make an application conformant.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **A11Y-001** | P1 | STANDARD | MUST provide meaningful structure, names, roles, values, and state exposure through native semantics or correct accessibility APIs. | Accessibility-tree inspection matches visible content and behavior. | S12 S00 | `S-A11Y-ICONBTN`, `S-A11Y-LABEL`, `S-A11Y-ARIAHIDDEN`, `R-AXE`, `M-SCREENREADER` |
| **A11Y-002** | P1 | STANDARD | MUST support keyboard operation for applicable functionality without timing-dependent keystrokes, subject to the criterion exception. | Complete key tasks using keyboard input alone. | S41 | `S-A11Y-DIVCLICK`, `R-FOCUS-WALK`, `M-KEYBOARD-TASK` |
| **A11Y-003** | P1 | STANDARD | MUST maintain a logical focus order and a visible focus indicator. MUST NOT remove focus styling without an accessible replacement. | Tab, reverse tab, activation, and dismissal remain predictable. | S06 S00 | `S-A11Y-TABINDEX`, `S-FOCUS-OUTLINE`, `R-FOCUS-WALK` |
| **A11Y-004** | P1 | STANDARD | MUST prevent keyboard traps. A modal may contain focus while open only with a working exit appropriate to the interaction. | The user can leave every interaction without a pointer. | S13 S00 | `S-MODAL-NATIVE`, `R-FOCUS-WALK` |
| **A11Y-005** | P1 | STANDARD | MUST provide non-color cues for meaning conveyed by color. | Status, errors, required fields, and chart distinctions remain understandable without identifying a particular hue. | S39 | `R-AXE`, `S-COLOR-ONLY` |
| **A11Y-006** | P1 | STANDARD | MUST expose relevant status messages programmatically without moving focus unnecessarily. | Assistive technology announces meaningful status without continuous redundant chatter. | S09 | `R-AXE`, `S-NAV-FOCUS-STEAL`, `M-SCREENREADER` |
| **A11Y-007** | P1 | STANDARD | MUST provide appropriate alternatives for images and media, including required captions and audio descriptions. | Every applicable non-text and time-based-media criterion is assessed. | S01 | `S-A11Y-ALT`, `S-CANVAS-A11Y`, `S-MEDIA-CAPTIONS`, `R-AXE` |
| **A11Y-008** | P1 | STANDARD | MUST support timeout adjustment or an applicable exception. MUST communicate session expiration and recovery without avoidable loss of permitted work. | Timeout tests record warning, extension, and preservation behavior. | S46 S00 | `S-A11Y-TIMEOUT` |
| **A11Y-009** | P1 | STANDARD | MUST provide alternatives to required dragging and path-based gestures where applicable. | The same task works through the required single-pointer and keyboard alternatives. | S42 S41 | `S-COMP-DRAG-ALT` |
| **A11Y-010** | P1 | PROJECT | MUST make optional motion stoppable and honor reduced-motion preferences. MUST avoid hazardous flashing content. | Motion-disabled and relevant flashing-safety checks pass. | S00 | `S-MOTION-REDUCE`, `S-3D-PERF`, `R-MOTION`, `S-CRAFT-HIDDEN-AT-REST` |
| **A11Y-011** | P1 | PROJECT | MUST use headings, landmarks, labels, page language, and link text appropriate to the content. | A screen-reader user can navigate the changed flow by structure and control name. | S00 | `S-A11Y-HEADING`, `R-AXE`, `M-SCREENREADER` |
| **A11Y-012** | P1 | STANDARD | MUST assess error recovery, authentication, help consistency, redundant entry, and focus obstruction, not only color contrast. | The complete changed process has an applicability assessment and evidence. | S01 S00 | `M-A11Y-PROCESS` |
| **A11Y-013** | P1 | PROJECT | MUST test generated content, third-party widgets, and embedded flows within the claimed release scope. | Known external component failures remain in the report rather than being hidden as dependencies. | S00 | `A-SCOPE-STATED` |
| **A11Y-014** | P1 | HEURISTIC | MUST NOT treat automated accessibility testing as complete coverage. | Manual keyboard, assistive technology, content, and interaction checks supplement scans. | S34 | `R-AXE`, `M-SCREENREADER` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S01 |  — Web Content Accessibility Guidelines 2.2 | normative_standard |
| S06 |  — Understanding Focus Not Obscured Minimum, SC 2.4.11 | official_explanation |
| S09 |  — Understanding Status Messages, SC 4.1.3 | official_explanation |
| S12 |  — Read Me First: ARIA Authoring Practices | official_non_normative_guidance |
| S13 |  — Dialog Modal Pattern | official_non_normative_guidance |
| S34 |  — Accessibility Testing | official_testing_documentation |
| S39 |  — Understanding Use of Color, SC 1.4.1 | official_explanation |
| S41 |  — Understanding Keyboard, SC 2.1.1 | official_explanation |
| S42 |  — Understanding Dragging Movements, SC 2.5.7 | official_explanation |
| S46 |  — Understanding Timing Adjustable, SC 2.2.1 | official_explanation |
