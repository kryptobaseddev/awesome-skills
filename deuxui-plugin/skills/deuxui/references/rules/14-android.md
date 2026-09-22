# Native Android platform

18 rules. Generated from `registry.yaml` by `scripts/build_rule_packs.py` -- edit the registry, not this file.

Material Design 3 conformance: adaptive navigation, the system Back contract, window insets, the type scale, colour roles, tonal elevation and the Material components. These apply when the project ships to Android, decided from the tree. The recurring failure is an iOS app wearing Android's skin -- a bottom bar copied to a tablet, a back arrow that ignores the system gesture, Cupertino-shaped controls, and text sized in dp so the system font setting does nothing.

`scripts/ux_native.sh --android` drives an emulator or device for the evidence rules.

| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |
|---|---|---|---|---|---|---|
| **AND-001** | P1 | PLATFORM | Match navigation to window size: navigation bar on compact width, rail or drawer on expanded width. | A phone bottom bar does not ship unchanged on a tablet. The breakpoint uses a window size class rather than a device check. | S48 S16 | `S-AND-ADAPTIVENAV` |
| **AND-002** | P1 | PLATFORM | Honour the system Back gesture and Back button. | Back leaves every screen. No handler consumes Back without providing the navigation the user asked for. | S48 S16 | `S-AND-SYSTEMBACK` |
| **AND-003** | P1 | PLATFORM | Go edge-to-edge and apply the window insets. | Status bar, navigation bar, display cutout and IME insets are all applied, so no content or control hides behind system chrome or the keyboard. | S48 S16 | `S-AND-INSETS` |
| **AND-004** | P2 | PLATFORM | Use a top app bar for screen context, paired with a FAB when the screen has one primary action. | The bar carries the screen's identity and its overflow actions rather than being reinvented per screen. | S48 S16 | `S-AND-TOPBAR` |
| **AND-005** | P1 | PLATFORM | Map text to the Material type scale roles. | Text takes a role from the scale. Sizes are not hand-picked per screen. | S48 S16 | `S-AND-TYPESCALE` |
| **AND-006** | P2 | PLATFORM | Keep body, labels and controls on the system face, theming a brand face in through the type scale. | A brand face is introduced through the theme, not per call site, and remains legible at the smallest role used. | S48 S16 | `S-AND-SYSTEMFONT` |
| **AND-007** | P1 | PLATFORM | Size text in sp so it follows the system font-size setting. | No text size is expressed in dp or px. Layout survives a large system font scale. | S48 S16 | `S-AND-SP`, `R-AND-THEME` |
| **AND-008** | P1 | PLATFORM | Use Material colour roles rather than literal colour values. | Colour comes from a role that resolves light, dark and contrast variants. Literals do not carry semantic meaning. | S48 S16 | `S-AND-ROLETOKENS` |
| **AND-009** | P2 | PLATFORM | Derive the scheme from Dynamic Color where it fits, with a static fallback. | Dynamic Color is applied on supported versions and a designed static scheme covers the rest. | S48 S16 | `S-AND-DYNAMICCOLOR` |
| **AND-010** | P1 | PLATFORM | Treat the dark theme as a designed scheme, not an inversion. | Both themes were viewed. Surface, text and state colours were chosen for each. | S48 S16 | `S-AND-DARKTHEME`, `R-AND-THEME` |
| **AND-011** | P2 | PLATFORM | Convey elevation through Material's surface tonal levels. | Elevation reads through tonal surface levels, with shadow only where the spec uses it. No arbitrary drop shadow substitutes. | S48 S16 | `S-AND-ELEVATION` |
| **AND-012** | P1 | PLATFORM | Use Material components rather than porting iOS controls or inventing equivalents. | No Cupertino-shaped switch, dialog or picker appears on Android. A custom control names the requirement Material could not meet. | S48 S16 | `S-AND-MATERIAL` |
| **AND-013** | P2 | PLATFORM | Use one FAB for one primary action. | At most one FAB per screen, and it carries the screen's primary action rather than a secondary one. | S48 S16 | `S-AND-FAB` |
| **AND-014** | P1 | PLATFORM | Use snackbars for transient feedback and dialogs only for decisions that must interrupt. | Transient feedback that may need an action is a snackbar rather than a toast. No dialog interrupts for something a snackbar could carry. | S48 S16 | `S-AND-TOAST` |
| **AND-015** | P1 | PLATFORM | Use the Material motion patterns and honour the system remove-animations setting. | Container transform, shared-axis and fade-through use standard easing and duration, and collapse to a crossfade or cut when animations are off. | S48 S16 | `S-AND-REDUCEMOTION` |
| **AND-016** | P1 | PROJECT | Produce screenshot evidence from an emulator or a connected device, never a browser. | Evidence names the device and serial that produced it, and covers every device class shipped. | S00 S48 | `R-AND-CAPTURE` |
| **AND-017** | P1 | PROJECT | Include the dark theme and an increased font scale in the verification pass. | Evidence exists for both themes and for at least one enlarged font scale. | S00 S48 | `R-AND-THEME` |
| **AND-018** | P2 | PROJECT | State whether evidence came from an emulator or from hardware. | Gesture, refresh-rate and performance claims name the hardware they were measured on, or are not made. | S00 S48 | `M-NATIVE-HARDWARE` |

## Sources cited above

| ID | Source | Type |
|---|---|---|
| S00 | This project — Original engineering policy | project_policy |
| S16 |  — Make Apps More Accessible | official_platform_guidance |
| S48 |  — Material Design 3 | official_platform_guidance |
