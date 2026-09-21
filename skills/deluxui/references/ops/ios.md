# ios — conformance for iOS and iPadOS

For SwiftUI, UIKit, React Native, Expo and Flutter shipping to Apple hardware.
Twenty rules, `IOS-001` to `IOS-020`, plus `NUM-006`. The full table is
[../rules/13-ios.md](../rules/13-ios.md).

Derived from impeccable's `ios.md` (Apache-2.0), with each rule bound to a
detector — see NOTICE.md.

## The slop test

Would a fluent iPhone user trust this, or pause at off-spec controls? The tell is
"ported from a website": a reinvented navigation bar, a custom back gesture,
web-shaped buttons, hover-dependent affordances. Default to the platform's
components and depart only for a reason the user would thank you for.

On native, visitor mode narrows what expression may override. HIG conformance
governs structure, navigation and interaction in every mode; the brand expresses
through the layer the platform leaves open — tint, type, motion, content.

## Run it

```bash
python3 scripts/ux_check.py .        # the 18 static iOS detectors
bash scripts/ux_native.sh --ios      # Simulator evidence, if this is a Mac
```

The platform is detected from the tree — an `ios/` directory, an `.xcodeproj`, a
`Package.swift`, a react-native or expo dependency — so nothing needs declaring.
A project that does not ship to Apple hardware reports the whole family
NOT_APPLICABLE.

## What each detector reads

| Detector | Rule | The tell it looks for |
|---|---|---|
| `S-IOS-SAFEAREA` | IOS-001 | `ignoresSafeArea()` with no edges, around controls |
| `S-IOS-NAVSTRUCTURE` | IOS-002 | a tab bar with fewer than 2 or more than 5 sections |
| `S-IOS-EDGESWIPE` | IOS-003 | `interactivePopGestureRecognizer.isEnabled = false`, `gestureEnabled: false` |
| `S-IOS-LARGETITLE` | IOS-004 | `prefersLargeTitles = false` globally |
| `S-IOS-DYNAMICTYPE` | IOS-005 | `.system(size: 17)`, `allowFontScaling={false}` |
| `S-IOS-SYSTEMFONT` | IOS-006 | `.custom(...)` on body and control text |
| `S-IOS-MINSIZE` | IOS-007 | any text size under 11pt |
| `S-IOS-TARGET44` | NUM-006 | a tappable frame under 44pt with no padding or hit shape |
| `S-IOS-SEMANTICCOLOR` | IOS-008 | `Color(red:green:blue:)`, `UIColor(hex:)` |
| `S-IOS-DARKMODE` | IOS-009 | `.preferredColorScheme(.light)`, `overrideUserInterfaceStyle` |
| `S-IOS-TINT` | IOS-010 | more than two distinct tints across the app |
| `S-IOS-MATERIALS` | IOS-011 | a blur-and-opacity stack where a material belongs |
| `S-IOS-NATIVECONTROLS` | IOS-012 | a `struct MyToggle: View` reimplementing a platform control |
| `S-IOS-SFSYMBOLS` | IOS-013 | a web icon library imported on a native surface |
| `S-IOS-MODALITY` | IOS-014 | `.interactiveDismissDisabled()` with no confirmation nearby |
| `S-IOS-GROUPEDLIST` | IOS-015 | settings-shaped content built from stacks |
| `S-IOS-TRANSITION` | IOS-016 | a custom transition on a navigation push |
| `S-IOS-REDUCEMOTION` | IOS-017 | animation with no `accessibilityReduceMotion` in the file |

## Evidence

`IOS-018`, `IOS-019` and `IOS-020` are about what counts as proof.
`scripts/ux_native.sh --ios` captures light, dark and an accessibility text size
from a booted Simulator, naming the UDID — display names collide, the UDID never
does. Without Xcode it records that fact and the rules report NOT_RUN. A browser
screenshot of a React Native web build is not evidence about an iPhone, and a
Simulator cannot tell you anything about posture, gesture feel, refresh rate or
real performance — `M-NATIVE-HARDWARE` asks which device produced any claim that
needed one.

Cross-platform: see [adapt-native.md](adapt-native.md) and [android.md](android.md).
