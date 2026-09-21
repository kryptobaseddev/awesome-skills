# android — conformance for Android

For Jetpack Compose, Android Views, React Native, Expo and Flutter shipping to
Android. Eighteen rules, `AND-001` to `AND-018`, plus `NUM-007`. The full table
is [../rules/14-android.md](../rules/14-android.md).

Derived from impeccable's `android.md` (Apache-2.0), with each rule bound to a
detector — see NOTICE.md.

## The slop test

Would a fluent Android user trust this, or trip on off-spec components? The most
common tell is an iOS app wearing Android's skin: a bottom-only navigation copied
from iPhone, a back arrow that ignores the system Back gesture, Cupertino-shaped
switches and dialogs.

Material Design 3 is the rulebook. The brand expresses **through** Material's
theming — colour roles, type scale, shape, motion — not around it. A
Material-everywhere cross-platform app that also ships to iPhone still owes iOS
its own guarantees on that hardware: safe-area insets, Reduce Motion, edge-swipe
back.

## Run it

```bash
python3 scripts/ux_check.py .            # the 16 static Android detectors
bash scripts/ux_native.sh --android      # emulator or device evidence
```

## What each detector reads

| Detector | Rule | The tell it looks for |
|---|---|---|
| `S-AND-ADAPTIVENAV` | AND-001 | a bottom nav bar with no window size class in the file |
| `S-AND-SYSTEMBACK` | AND-002 | `BackHandler { }` with an empty body, `onBackPressed` swallowing the event |
| `S-AND-INSETS` | AND-003 | `enableEdgeToEdge()` with no insets padding anywhere |
| `S-AND-TOPBAR` | AND-004 | a `Scaffold` with no `topBar` |
| `S-AND-TYPESCALE` | AND-005 | `fontSize = 14.sp` instead of a typography role |
| `S-AND-SYSTEMFONT` | AND-006 | a font family set at the call site rather than in the theme |
| `S-AND-SP` | AND-007 | text sized in dp or px |
| `S-AND-ROLETOKENS` | AND-008 | `Color(0xFF1A1A1A)` outside the colour scheme |
| `S-AND-DYNAMICCOLOR` | AND-009 | a static scheme with no Dynamic Color path |
| `S-AND-DARKTHEME` | AND-010 | `lightColorScheme` with no dark counterpart |
| `S-AND-ELEVATION` | AND-011 | a hand-applied `.shadow(elevation = 8.dp)` |
| `S-AND-MATERIAL` | AND-012 | a Cupertino widget, the framework `Switch` |
| `S-AND-FAB` | AND-013 | more than one FAB in a Scaffold |
| `S-AND-TOAST` | AND-014 | `Toast.makeText` where a snackbar belongs |
| `S-AND-REDUCEMOTION` | AND-015 | animation with no animation-scale check in the file |
| `S-AND-TARGET48` | NUM-007 | a clickable under 48dp with no minimum interactive size |

## Evidence

`scripts/ux_native.sh --android` flips the theme with
`adb shell cmd uimode night yes`, raises `font_scale` to 1.3 to catch the clipped
labels a fixed layout hides, and records the device class — a phone bottom bar
shipped unchanged to a tablet is exactly what AND-001 is about, and the capture
says which one it came from. It restores both settings afterwards.

Emulators give breadth. Gestures, refresh rates and performance need hardware,
and `M-NATIVE-HARDWARE` asks which one produced the claim.

Cross-platform: see [adapt-native.md](adapt-native.md) and [ios.md](ios.md).
