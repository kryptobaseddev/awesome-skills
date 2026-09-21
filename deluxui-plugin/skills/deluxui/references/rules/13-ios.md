# Native iOS platform

20 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

iOS and iPadOS conformance: safe areas, the system navigation model, Dynamic Type, semantic colours, the platform controls, and what counts as evidence. These apply when the project ships to Apple hardware -- SwiftUI, UIKit, React Native, Expo or Flutter -- and `ux_check.py` decides that by looking at the tree rather than asking. The recurring failure is a web app wearing an app's clothes: reinvented navigation, web-shaped controls, hover-dependent affordances, and point sizes that ignore the reading size the user chose.

`scripts/ux_native.sh --ios` drives a Simulator for the evidence rules. On a machine without Xcode it records that fact and the rules report NOT_RUN -- a browser screenshot of a web build is not evidence about an iPhone.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **IOS-001** | P1 | PLATFORM | Lay out inside the safe-area insets on every screen. | No control, text or gesture target sits under the notch, Dynamic Island, home indicator or a rounded corner, on every device class shipped. | S47 S15 | `S-IOS-SAFEAREA` |
| **IOS-002** | P1 | PLATFORM | Use the system navigation structure: tab bar for 2 to 5 top-level sections, navigation stack for hierarchy, sheet for a self-contained task. | Tab bar items are sections rather than actions. No second global navigation metaphor coexists with it. | S47 S15 | `S-IOS-NAVSTRUCTURE` |
| **IOS-003** | P1 | PLATFORM | MUST NOT disable, overlay or reinterpret the left-edge back gesture. | The edge-swipe back works on every pushed screen, including ones with a custom back button. | S47 S15 | `S-IOS-EDGESWIPE` |
| **IOS-004** | P2 | PLATFORM | Use large titles on top-level screens, collapsing to inline on scroll, and inline titles on deep detail screens. | Title display mode matches the screen's depth rather than being set once globally. | S47 S15 | `S-IOS-LARGETITLE` |
| **IOS-005** | P1 | PLATFORM | Use the system text styles so text follows the user's reading size. | No hard-coded point size carries body, label or control text. Layout survives the largest accessibility text size. | S47 S15 | `S-IOS-DYNAMICTYPE`, `R-IOS-APPEARANCE` |
| **IOS-006** | P2 | PLATFORM | Keep body, labels and controls on the system face; a brand face may carry display moments. | A custom face appears in display roles only, and the substituted metrics were checked at accessibility sizes. | S47 S15 | `S-IOS-SYSTEMFONT` |
| **IOS-007** | P1 | PLATFORM | Keep an 11 pt floor for any text a user is expected to read. | No text style resolves below 11 pt at the default reading size. | S47 S15 | `S-IOS-MINSIZE` |
| **IOS-008** | P1 | PLATFORM | Use semantic system colors for label, background, separator and tint roles. | Raw component values do not carry a semantic role, so Dark Mode and increased-contrast modes resolve without a second code path. | S47 S15 | `S-IOS-SEMANTICCOLOR` |
| **IOS-009** | P1 | PLATFORM | Treat Dark Mode as a designed appearance, not an inversion. | Both appearances were viewed. Neither forces the other, and asset catalogs carry both variants where images encode colour. | S47 S15 | `S-IOS-DARKMODE`, `R-IOS-APPEARANCE` |
| **IOS-010** | P2 | PLATFORM | Let one tint colour drive interactive elements. | Tint marks what is actionable. Decoration uses another role. | S47 S15 | `S-IOS-TINT` |
| **IOS-011** | P2 | PLATFORM | Use system materials for blur and translucency behind bars and sheets. | No hand-rolled blur-plus-opacity stack stands in for a system material. | S47 S15 | `S-IOS-MATERIALS` |
| **IOS-012** | P1 | PLATFORM | Use the platform controls for switches, steppers, segmented controls, pickers, action sheets, alerts, context menus and swipe actions. | A reimplemented control is justified by a named requirement the platform control cannot meet, and carries the same accessibility contract. | S47 S15 | `S-IOS-NATIVECONTROLS` |
| **IOS-013** | P2 | PLATFORM | Use SF Symbols for iconography. | Icons align to the text baseline, follow Dynamic Type, and come from one set rather than a web icon library. | S47 S15 | `S-IOS-SFSYMBOLS` |
| **IOS-014** | P1 | PLATFORM | Choose modality deliberately: sheet for a focused dismissible sub-task, full-screen cover for immersion. | Cancel and Done are unambiguous. Swipe-to-dismiss is honoured unless unsaved work requires a guard, and then the guard exists. | S47 S15 | `S-IOS-MODALITY` |
| **IOS-015** | P2 | PLATFORM | Use grouped or inset lists for settings-shaped content. | Settings-shaped content uses the platform list rather than a bespoke card stack. | S47 S15 | `S-IOS-GROUPEDLIST` |
| **IOS-016** | P2 | PLATFORM | Use the system transitions: push slides, sheets rise, dismissal reverses the entrance. | No custom transition contradicts the navigation model the gesture implies. | S47 S15 | `S-IOS-TRANSITION` |
| **IOS-017** | P1 | PLATFORM | Honour Reduce Motion. | With Reduce Motion on, parallax and large slides become a crossfade or an instant cut. Nothing is unreachable as a result. | S47 S15 | `S-IOS-REDUCEMOTION` |
| **IOS-018** | P1 | PROJECT | Produce screenshot evidence from a Simulator or device, never a browser. | Evidence names the device and the identifier that produced it, and covers every device class shipped. | S00 S47 | `R-IOS-CAPTURE` |
| **IOS-019** | P1 | PROJECT | Include Dark Mode and a large Dynamic Type size in the verification pass. | Evidence exists for both appearances and for at least one accessibility text size. | S00 S47 | `R-IOS-APPEARANCE` |
| **IOS-020** | P2 | PROJECT | State whether evidence came from a Simulator or from hardware. | Posture, gesture and performance claims name the hardware they were measured on, or are not made. | S00 S47 | `M-NATIVE-HARDWARE` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S15 |  — UI Design Dos and Don’ts | official_platform_guidance |
| S47 |  — Human Interface Guidelines | official_platform_guidance |
