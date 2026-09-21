# Visual system, layout and responsiveness

19 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Hierarchy, tokens, alignment, state styling, reflow and input modes. The recurring failure here is designing for one screenshot at one width with content that is exactly the right length. Real content is longer, the user's font is bigger, and the viewport is 320px.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **VIS-001** | P1 | PROJECT | MUST use semantic tokens and shared primitives for recurring visual decisions. | Equivalent components resolve to the same semantic roles. | S00 | `S-TOKEN-HEX`, `S-TOKEN-ARBITRARY` |
| **VIS-002** | P2 | PROJECT | MUST establish page, section, content, and action hierarchy through consistent type, spacing, grouping, and emphasis. | The hierarchy remains clear with real content and without decorative imagery. | S00 | `S-SLOP-CARDNEST`, `S-SLOP-UNIFORM` |
| **VIS-003** | P2 | PROJECT | MUST preserve an intentional alignment system across labels, controls, text, and repeated items. | Layout remains aligned at long labels and supported text sizes. | S00 | _manual only_ |
| **VIS-004** | P1 | PROJECT | MUST provide meaningful default, hover where supported, focus, active, selected, disabled, pending, and error states where applicable. | State examples are implemented and tested rather than represented only in a design mockup. | S00 | _manual only_ |
| **VIS-005** | P1 | STANDARD | MUST NOT rely on hover for an essential action, label, or status. | Touch and keyboard users can discover and operate the same task. | S40 S00 | `S-HOVER-ONLY` |
| **VIS-006** | P2 | PROJECT | MUST reserve decorative effects for a defined purpose. MUST NOT add gradients, glass effects, oversized cards, or animation merely to signal modernity. | Every decorative layer preserves contrast, readability, and task hierarchy. | S00 | `S-SLOP-GRADIENT`, `S-SLOP-BLUR`, `S-SLOP-CARDNEST`, `S-SLOP-UNIFORM` |
| **VIS-007** | P1 | PROJECT | MUST keep icons stylistically consistent and provide visible labels when icon meaning is unfamiliar or consequential. | Icon-only controls have accessible names. Labels remain visible where required for comprehension. | S00 | `S-A11Y-ICONBTN`, `S-SLOP-EMOJI` |
| **VIS-008** | P1 | STANDARD | MUST test supported themes and forced-color behavior. MUST NOT encode essential state only in a background image or shadow. | Selected and focused states survive theme changes and relevant system overrides. | S39 S00 | `R-FORCED-COLORS` |
| **VIS-009** | P2 | PROJECT | MUST choose density for task needs rather than applying oversized consumer layouts to every data-heavy screen. | Representative records fit without sacrificing target size, readability, or critical context. | S00 | _manual only_ |
| **LAY-001** | P1 | PROJECT | MUST define content priority before arranging columns or cards. | At the narrowest supported layout, the primary task and essential context remain available. | S00 | _manual only_ |
| **LAY-002** | P1 | STANDARD | MUST use content-driven breakpoints and fluid sizing. MUST NOT design only for one screenshot width. | No unintended clipping, overlap, or page-level horizontal overflow at tested widths. | S05 S00 | `S-RESP-FIXEDPX`, `S-RESP-OVERFLOW`, `R-REFLOW` |
| **LAY-003** | P1 | PROJECT | MUST preserve meaningful document order when changing visual order. | Reading order, focus order, and visual task order remain compatible. | S00 | `R-FOCUS-WALK` |
| **LAY-004** | P1 | PROJECT | MUST support supported device orientations, text scaling, browser zoom, and system font settings. | The declared device matrix includes rotated and enlarged-text checks. | S00 | _manual only_ |
| **LAY-005** | P1 | STANDARD | MUST keep essential actions reachable when the virtual keyboard, safe-area inset, sticky header, or cookie banner is present. | The active field, its error, and the relevant action are not trapped behind overlays. | S06 S00 | `S-RESP-VH`, `S-RESP-SAFEAREA` |
| **LAY-006** | P1 | PROJECT | MUST preserve all essential information when converting a table or multi-column screen to a narrow layout. | The alternate representation retains labels, units, relationships, and actions. | S00 | `S-RESP-TABLE` |
| **LAY-007** | P1 | PROJECT | MUST NOT use truncation for the only visible presentation of a critical value, warning, or action label. | A keyboard- and touch-accessible full value is available when truncation is necessary. | S00 | `S-RESP-TRUNCATE` |
| **LAY-008** | P2 | STANDARD | MUST prevent sticky controls from stealing excessive reading space or covering the currently focused item. | Sticky behavior passes narrow viewport, text scaling, and focus checks. | S06 S00 | _manual only_ |
| **LAY-009** | P1 | STANDARD | MUST support pointer, touch, and keyboard according to declared platforms. MUST NOT assume a narrow viewport implies touch-only use. | Responsive layouts retain keyboard access and visible focus. | S41 S00 | `M-TOUCH-DEVICE` |
| **LAY-010** | P1 | PROJECT | MUST respect reduced-motion preferences as project policy. Replace nonessential movement with immediate or low-motion feedback. | The task remains understandable without animated movement. | S00 | `S-MOTION-REDUCE`, `S-3D-PERF`, `R-MOTION` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S05 |  — Understanding Reflow, SC 1.4.10 | official_explanation |
| S06 |  — Understanding Focus Not Obscured Minimum, SC 2.4.11 | official_explanation |
| S39 |  — Understanding Use of Color, SC 1.4.1 | official_explanation |
| S40 |  — Understanding Content on Hover or Focus, SC 1.4.13 | official_explanation |
| S41 |  — Understanding Keyboard, SC 2.1.1 | official_explanation |
