# adapt-native — move a native design to a different context

Another device class, orientation, platform or origin. The trap is treating
adaptation as scaling.

Derived from impeccable's `adapt.native` (Apache-2.0) — see NOTICE.md.

## Assess before planning

1. **Source context.** What was this designed for, and what did it assume?
   Phone-only? Portrait-only? One platform's idioms? A website?
2. **Target context.** Which device class, orientation, platform and posture —
   one-handed on the move, or two-handed at rest?
3. **What breaks.** Navigation that does not fit, layouts that stretch instead of
   restructuring, gestures that do not exist there.

## Phone to tablet

**Restructure, do not stretch.** A scaled-up phone UI on a tablet is the failure
mode, and on Android it is a rule: `AND-001` and `S-AND-ADAPTIVENAV` fail a
bottom navigation bar that ships unchanged to expanded width.

- Navigation changes shape: an iOS tab bar may stay or become a sidebar; an
  Android navigation bar becomes a rail or a drawer.
- Use the width: split view, list-plus-detail, multi-column grids, popovers where
  a phone used a sheet.
- Multitasking is a size, not an edge case. iPad Split View and Android
  multi-window hand you a phone-width window on a tablet, and size-class-driven
  layout handles both for free. Branch on the size class, never on the device.

## Orientation and foldables

Landscape restructures — side-by-side panes, repositioned controls. Never clip
and never letterbox. Lock orientation only when the task genuinely demands it,
because a locked orientation is unusable for someone whose device is mounted.
Foldables react to posture through window size classes: test folded, unfolded and
tabletop.

## Platform to platform

Translate idioms; never transplant them. `S-AND-MATERIAL` fails a Cupertino
control on Android for exactly this reason.

| iOS | Android |
|---|---|
| Tab bar | Navigation bar / rail / drawer |
| Edge-swipe back | Predictive Back gesture and button |
| Switch, segmented control, system pickers | Material switch, chips, Material pickers |
| Action sheet | Bottom sheet or Material dialog |
| SF Symbols, system face, Dynamic Type | Material Symbols, system face, sp scaling |
| Semantic system colours, materials | Material colour roles, tonal elevation |
| System push and sheet transitions | Container transform, shared-axis, fade-through |

Rebuild navigation and controls in the target's vocabulary. Carry the brand's
expressive layer — palette intent, type accent, motion personality — through the
target's theming system, not around it.

## Web to native

Reconform, do not reflow. Web navigation becomes the platform's model.
HTML-shaped controls become platform controls. Hover affordances become
touch-first ones, because hover does not exist and `S-HOVER-ONLY` is the web
version of the same mistake. Pixel type becomes Dynamic Type or sp.

Then treat the result to the whole platform reference. The slop test in
[ios.md](ios.md) and [android.md](android.md) is the acceptance bar, not a
stretch goal.

## Verify

```bash
python3 scripts/ux_check.py .            # both platform families
bash scripts/ux_native.sh --both         # captures per device class
```

`ux_native.sh` records the device class it captured from, so a tablet claim has a
tablet behind it. `M-TOUCH-DEVICE` asks the question no capture answers: use it
one-handed on a real phone and name what your thumb could not reach.
