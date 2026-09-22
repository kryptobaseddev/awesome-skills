"""Native platform conformance -- iOS and Android.

This was deuxui's only layer at zero automated coverage: three rules, all
manual, against impeccable's forty. The rules themselves come from the impeccable
skill's ios.md and android.md (Apache-2.0, github.com/pbakaus/impeccable), which
states them as guidance for an agent to follow. Here each one additionally has to
survive being checked, so a platform claim carries a verdict instead of a
promise.

Four dialects ship to these platforms and they do not look alike: SwiftUI, UIKit,
Jetpack Compose, Flutter, and React Native in a .tsx. A detector that can read
one dialect and not another says so per finding rather than reporting a clean
pass it did not earn -- `no_native_dialect` below is what keeps a Flutter project
from collecting a PASS from a Swift-only regex.

Everything here runs on the "native" surface only (see checks/_util.NATIVE_EXT
and ux_check.classify), so no web check ever reads a .swift file and no platform
check ever reads a .html one.
"""
from __future__ import annotations
import re
from pathlib import Path
from . import check, finding
from ._util import strip_comments

# The file kinds each family may draw a verdict from. Declared as one NATIVE set
# for both, an Android detector pooled a .swift file, found no Toast in it, and
# reported PASS -- the delta then showed fifteen Android rules "fixed" when the
# only Kotlin file in the project was deleted. A detector must not be able to
# pass on evidence from a platform it does not describe.
#
# Dart and the React Native extensions appear in both because a cross-platform
# file genuinely ships to both; a Swift file never ships to Android.
CROSS = (".dart", ".tsx", ".jsx", ".ts", ".js")
IOS_EXTS = (".swift",) + CROSS
AND_EXTS = (".kt", ".kts") + CROSS
IOS_ONLY = (".swift",)
AND_ONLY = (".kt", ".kts")


def on_ios(p):
    return "ios" in p.platforms


def on_android(p):
    return "android" in p.platforms


def _line(t, pos):
    return t[:pos].count("\n") + 1


def _src(f):
    """Comments stripped. A banned call in a commented-out block is not shipping,
    and half of every Swift file is documentation."""
    return strip_comments(f.text)


def dialect(f) -> str:
    if f.ext == ".swift":
        return "swiftui" if re.search(r"\bimport\s+SwiftUI\b", f.text) else "uikit"
    if f.ext in (".kt", ".kts"):
        return "compose" if re.search(r"androidx\.compose", f.text) else "views"
    if f.ext == ".dart":
        return "flutter"
    return "rn"


# ===================================================================== iOS
@check("S-IOS-SAFEAREA", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def safe_area(f, p):
    """Content under the Dynamic Island, the home indicator or a rounded corner is
    content the user cannot read or a control they cannot hit (IOS-001).

    `ignoresSafeArea()` with no `edges:` argument extends in every direction at
    once. That is right for a background and wrong for anything interactive, so
    the finding is raised where the ignored region contains a control."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.(?:ignoresSafeArea|edgesIgnoringSafeArea)\s*\(([^)]*)\)", t):
        arg = m.group(1).strip()
        unbounded = (arg == "" or ".all" in arg)
        if not unbounded:
            continue
        # A background gradient or colour legitimately bleeds edge to edge; a
        # container holding controls does not.
        window = t[max(0, m.start() - 400):m.start()]
        if not re.search(r"\b(?:Button|NavigationLink|TextField|Toggle|Stepper|Picker|"
                         r"List|Form|TabView|onTapGesture)\b", window):
            continue
        out.append(finding("S-IOS-SAFEAREA", f, _line(t, m.start()), m.group(0),
                           "This ignores the safe area in every direction on a container "
                           "that holds controls, which puts them under the Dynamic Island "
                           "or the home indicator. Name the edges you actually mean "
                           "-- `.ignoresSafeArea(edges: .top)` for a header image -- and "
                           "keep interactive content inside the insets (IOS-001).", "medium"))
    for m in re.finditer(r"position:\s*[\"']absolute[\"'][^}]{0,160}?\b(?:bottom|top)\s*:\s*0",
                         t):
        if re.search(r"useSafeAreaInsets|SafeAreaView|react-native-safe-area", f.text):
            continue
        out.append(finding("S-IOS-SAFEAREA", f, _line(t, m.start()),
                           " ".join(m.group(0).split())[:70],
                           "Absolutely positioned at the screen edge with no safe-area "
                           "inset in this file. On a device with a home indicator this "
                           "lands underneath it. Use `useSafeAreaInsets()` or wrap in "
                           "`SafeAreaView` (IOS-001).", "low"))
    return out[:4]


@check("S-IOS-NAVSTRUCTURE", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def nav_structure(f, p):
    """A tab bar carries 2 to 5 top-level *sections*. One tab is not a tab bar,
    six do not fit, and a tab that performs an action rather than switching
    section breaks the model the user has (IOS-002)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\bTabView\s*(?:\([^)]*\))?\s*\{", t):
        body = t[m.end():m.end() + 2600]
        tabs = len(re.findall(r"\.tabItem\s*\{", body))
        if tabs and not 2 <= tabs <= 5:
            out.append(finding("S-IOS-NAVSTRUCTURE", f, _line(t, m.start()),
                               f"TabView with {tabs} tabItem(s)",
                               f"{tabs} tabs. A tab bar holds 2 to 5 top-level sections: "
                               f"one is not a choice, six will not fit a label at large "
                               f"text sizes. Move the overflow into the sections it belongs "
                               f"to (IOS-002).", "medium"))
    screens = len(re.findall(r"<Tab\.Screen\b", t))
    if screens and not 2 <= screens <= 5:
        out.append(finding("S-IOS-NAVSTRUCTURE", f, 1,
                           f"{screens} Tab.Screen entries",
                           f"{screens} tab screens. A tab bar holds 2 to 5 top-level "
                           f"sections (IOS-002).", "medium"))
    return out


@check("S-IOS-EDGESWIPE", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def edge_swipe(f, p):
    """The left-edge back swipe is muscle memory older than most apps. Disabling
    it strands the user on a screen whose only exit is a button they have to find
    (IOS-003)."""
    out, t = [], _src(f)
    pats = [
        (r"interactivePopGestureRecognizer[?\s]*\.isEnabled\s*=\s*false",
         "This disables the left-edge back gesture for the whole navigation "
         "controller."),
        (r"gestureEnabled\s*:\s*false",
         "react-navigation's `gestureEnabled: false` removes the edge-swipe back "
         "from this screen."),
        (r"\.navigationBarBackButtonHidden\s*\(\s*true\s*\)",
         "Hiding the back button removes the visible exit; if the gesture is also "
         "suppressed the screen has none."),
    ]
    for pat, why in pats:
        for m in re.finditer(pat, t):
            out.append(finding("S-IOS-EDGESWIPE", f, _line(t, m.start()),
                               " ".join(m.group(0).split()),
                               why + " Leave the gesture alive; if this screen holds "
                               "unsaved work, guard the dismissal with a confirmation "
                               "rather than removing the way out (IOS-003).",
                               "high" if "interactivePop" in pat or "gestureEnabled" in pat
                               else "low"))
    return out[:4]


_IOS_SIZE = re.compile(r"""(?:\.system\s*\(\s*size:\s*|UIFont\.(?:systemFont|boldSystemFont)"""
                       r"""\s*\(\s*ofSize:\s*|\.font\s*=\s*\.systemFont\(ofSize:\s*)"""
                       r"""(\d+(?:\.\d+)?)""")
_RN_FONTSIZE = re.compile(r"fontSize\s*:\s*(\d+(?:\.\d+)?)")
_FLUTTER_FONTSIZE = re.compile(r"fontSize\s*:\s*(\d+(?:\.\d+)?)")


@check("S-IOS-DYNAMICTYPE", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def dynamic_type(f, p):
    """A hard-coded point size does not follow the user's reading size, so the
    accessibility setting that matters most to the most people does nothing
    (IOS-005).

    The system text styles -- .body, .headline, .caption -- scale. `.system(size:
    17)` is 17 points forever, including for the reader who set the largest
    accessibility size precisely because 17 is unreadable to them."""
    out, t = [], _src(f)
    d = dialect(f)
    if d in ("swiftui", "uikit"):
        for m in _IOS_SIZE.finditer(t):
            out.append(finding("S-IOS-DYNAMICTYPE", f, _line(t, m.start()), m.group(0),
                               f"Hard-coded {m.group(1)} pt. Use a system text style "
                               f"(.body, .headline, .footnote) so the text follows Dynamic "
                               f"Type, or scale this value with "
                               f"`@ScaledMetric` / `UIFontMetrics` (IOS-005).", "high"))
    elif d == "rn":
        if re.search(r"allowFontScaling\s*=?\s*\{?\s*false", t):
            for m in re.finditer(r"allowFontScaling\s*=?\s*\{?\s*false", t):
                out.append(finding("S-IOS-DYNAMICTYPE", f, _line(t, m.start()),
                                   m.group(0),
                                   "`allowFontScaling={false}` opts this text out of the "
                                   "user's reading size. Let it scale and fix the layout "
                                   "that cannot take it (IOS-005).", "high"))
    elif d == "flutter":
        for m in re.finditer(r"textScaleFactor\s*:\s*1(?:\.0)?\b", t):
            out.append(finding("S-IOS-DYNAMICTYPE", f, _line(t, m.start()), m.group(0),
                               "Pinning textScaleFactor to 1 ignores the system reading "
                               "size. Use `MediaQuery.textScalerOf(context)` and let the "
                               "layout adapt (IOS-005).", "high"))
    return out[:5]


@check("S-IOS-MINSIZE", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def min_text_size(f, p):
    """Below 11 pt is not a size choice; it is text the platform's own guidance
    says a reader cannot be expected to read (IOS-007)."""
    out, t = [], _src(f)
    floor = 11.0
    pats = (_IOS_SIZE if f.ext == ".swift" else
            (_FLUTTER_FONTSIZE if f.ext == ".dart" else _RN_FONTSIZE))
    for m in pats.finditer(t):
        v = float(m.group(1))
        if v >= floor or v < 4:          # < 4 is a border width or a spacing token
            continue
        out.append(finding("S-IOS-MINSIZE", f, _line(t, m.start()), m.group(0),
                           f"{v:g} pt is below the {floor:g} pt floor. Raise it, or if "
                           f"this is genuinely decorative, make it decorative -- text a "
                           f"user is expected to read cannot be this small (IOS-007).",
                           "high"))
    return out[:5]


@check("S-IOS-TARGET44", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def target_44pt(f, p):
    """44 by 44 points is the tappable minimum, and it is the *tappable* area,
    not the icon inside it (NUM-006).

    A 24-point icon in a 24-point frame is a control most thumbs miss. The fix is
    almost never a bigger icon -- it is padding, or `.contentShape()` with a
    frame that reaches 44."""
    out, t = [], _src(f)
    minpt = float(p.num("target_size", "ios_min_pt", 44))
    for m in re.finditer(r"\.frame\s*\(\s*width:\s*(\d+(?:\.\d+)?)\s*,\s*"
                         r"height:\s*(\d+(?:\.\d+)?)\s*\)", t):
        w, h = float(m.group(1)), float(m.group(2))
        if w >= minpt and h >= minpt:
            continue
        window = t[max(0, m.start() - 320):m.start()]
        if not re.search(r"\b(?:Button|NavigationLink|onTapGesture|Toggle)\b", window):
            continue
        if re.search(r"\.contentShape\s*\(|\.padding\s*\(", t[m.end():m.end() + 160]):
            continue                     # padding or an explicit hit shape follows
        out.append(finding("S-IOS-TARGET44", f, _line(t, m.start()), m.group(0),
                           f"{w:g}x{h:g} pt on a tappable control, under the {minpt:g} pt "
                           f"minimum. Keep the icon and grow the target: add padding, or "
                           f"`.frame(minWidth: {minpt:g}, minHeight: {minpt:g})` with "
                           f"`.contentShape(Rectangle())` (NUM-006).", "medium"))
    for m in re.finditer(r"<(?:Pressable|TouchableOpacity|TouchableHighlight)\b[^>]{0,400}",
                         t):
        blob = m.group(0)
        if "hitSlop" in blob:
            continue
        sz = re.search(r"(?:width|height)\s*:\s*(\d+)", blob)
        if sz and float(sz.group(1)) < minpt:
            out.append(finding("S-IOS-TARGET44", f, _line(t, m.start()),
                               " ".join(blob.split())[:70],
                               f"A touchable sized under {minpt:g} pt with no `hitSlop`. "
                               f"Add hitSlop or pad the control (NUM-006).", "low"))
    return out[:5]


@check("S-IOS-SEMANTICCOLOR", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def semantic_color(f, p):
    """A literal colour value carries no role, so it cannot resolve for Dark Mode
    or for Increase Contrast. The platform already has the roles (IOS-008).

    `Color(.label)` is the right colour in every appearance without a second code
    path. `Color(red: 0.1, green: 0.1, blue: 0.1)` is the wrong colour in one of
    them and nothing will tell you which."""
    out, t = [], _src(f)
    pats = (
        r"Color\s*\(\s*red:\s*[\d.]+",
        r"UIColor\s*\(\s*red:\s*[\d.]+",
        r"Color\s*\(\s*hex:",
        r"UIColor\s*\(\s*hex:",
        r"Color\s*\(\s*white:\s*[\d.]+",
    )
    for pat in pats:
        for m in re.finditer(pat, t):
            out.append(finding("S-IOS-SEMANTICCOLOR", f, _line(t, m.start()), m.group(0),
                               "A literal colour has no semantic role, so Dark Mode and "
                               "Increase Contrast cannot resolve it. Use a system colour "
                               "(`Color(.label)`, `Color(.secondarySystemBackground)`, "
                               "`Color(.separator)`) or an asset-catalog colour with both "
                               "appearances defined (IOS-008).", "medium"))
    return out[:5]


@check("S-IOS-DARKMODE", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def dark_mode(f, p):
    """Forcing one appearance means the user's system setting does nothing, and
    the appearance you skipped was never designed (IOS-009)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.preferredColorScheme\s*\(\s*\.(light|dark)\s*\)", t):
        out.append(finding("S-IOS-DARKMODE", f, _line(t, m.start()), m.group(0),
                           f"This pins the app to {m.group(1)} mode, so the system "
                           f"setting is ignored. If the other appearance is unfinished, "
                           f"that is the thing to fix -- design both and let the user "
                           f"choose (IOS-009).", "high"))
    for m in re.finditer(r"overrideUserInterfaceStyle\s*=\s*\.(light|dark)", t):
        out.append(finding("S-IOS-DARKMODE", f, _line(t, m.start()), m.group(0),
                           f"Overriding the interface style to {m.group(1)} ignores the "
                           f"user's setting (IOS-009).", "high"))
    return out[:4]


@check("S-IOS-TINT", scope="project", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def single_tint(f, p):
    """One tint colour tells the user what is actionable. Three tints tell them
    nothing, because the signal is no longer a signal (IOS-010)."""
    out = []
    tints, where = {}, {}
    for q in p.root.rglob("*.swift"):
        if any(part in ("build", ".build", "Pods", "DerivedData") for part in q.parts):
            continue
        try:
            txt = q.read_text(errors="replace")
        except OSError:
            continue
        for m in re.finditer(r"\.(?:tint|accentColor)\s*\(\s*([^)\n]{1,60})\)", txt):
            v = " ".join(m.group(1).split())
            if v.startswith(("nil", "$")):
                continue
            tints[v] = tints.get(v, 0) + 1
            where.setdefault(v, q.name)
    if len(tints) > 2:
        listed = ", ".join(f"{v} ({where[v]})" for v in sorted(tints, key=lambda v: -tints[v])[:5])
        out.append(finding("S-IOS-TINT", f, 1, f"{len(tints)} distinct tint values",
                           f"{len(tints)} different tints across the app: {listed}. One "
                           f"tint should mean 'this is actionable'. Pick it, put it in one "
                           f"place, and give the others a role of their own or take them "
                           f"out (IOS-010).", "low"))
    return out


@check("S-IOS-MATERIALS", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def system_materials(f, p):
    """A hand-rolled blur behind a bar is a costume: it does not adapt to
    appearance, it does not vibrate its foreground content, and it costs more
    than the material that does (IOS-011)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.blur\s*\(\s*radius:\s*(\d+(?:\.\d+)?)", t):
        near = t[max(0, m.start() - 300):m.end() + 300]
        if not re.search(r"\.opacity\s*\(|Color\s*\(|\.background\s*\(", near):
            continue
        if re.search(r"\.(?:ultraThin|thin|regular|thick|ultraThick)Material|"
                     r"UIBlurEffect|\.material\b", near):
            continue
        out.append(finding("S-IOS-MATERIALS", f, _line(t, m.start()), m.group(0),
                           "A blur-and-opacity stack standing in for a system material. "
                           "Use `.background(.ultraThinMaterial)` or "
                           "`.thinMaterial`: they adapt to appearance and to Reduce "
                           "Transparency, which this does not (IOS-011).", "low"))
    return out[:3]


@check("S-IOS-NATIVECONTROLS", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def native_controls(f, p):
    """Reinventing a switch is the most common native slop, and the copy is always
    worse: it loses the accessibility trait, the haptic, the animation curve and
    the behaviour under Reduce Motion (IOS-012)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\b(?:struct|class)\s+(\w*(?:Switch|Toggle|Stepper|"
                         r"SegmentedControl|Picker|ActionSheet|Alert))\b"
                         r"\s*:\s*\w*View\b", t):
        name = m.group(1)
        if name in ("Switch", "Toggle") and "Style" in t[m.start():m.start() + 120]:
            continue                     # a ToggleStyle is the sanctioned way to restyle
        out.append(finding("S-IOS-NATIVECONTROLS", f, _line(t, m.start()), m.group(0),
                           f"`{name}` reimplements a platform control. The system one "
                           f"already carries the accessibility trait, the haptic and the "
                           f"Reduce Motion behaviour this will not. If the look is the "
                           f"reason, restyle it -- `ToggleStyle`, `ButtonStyle` -- rather "
                           f"than rebuilding it (IOS-012).", "medium"))
    return out[:4]


_WEB_ICON_LIBS = re.compile(r"""from\s+["'](?:react-icons|lucide-react|@heroicons|"""
                            r"""feather-icons|font-awesome|@fortawesome|react-feather)""")


@check("S-IOS-SFSYMBOLS", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def sf_symbols(f, p):
    """A web icon set on iOS does not align to the text baseline, does not follow
    Dynamic Type, and has no weight to match the label beside it (IOS-013)."""
    out, t = [], _src(f)
    for m in _WEB_ICON_LIBS.finditer(t):
        out.append(finding("S-IOS-SFSYMBOLS", f, _line(t, m.start()), m.group(0),
                           "A web icon library on a native surface. SF Symbols align to "
                           "the baseline, scale with Dynamic Type and come in matching "
                           "weights; these do none of that. Use `Image(systemName:)` or "
                           "react-native-sfsymbols (IOS-013).", "medium"))
    return out[:3]


@check("S-IOS-MODALITY", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def modality(f, p):
    """Swipe-to-dismiss is how a sheet is closed. Disabling it is defensible
    exactly once -- unsaved work -- and then the confirmation has to exist, or the
    user is simply stuck (IOS-014)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.interactiveDismissDisabled\s*\(\s*(?:true\s*)?\)", t):
        near = t[max(0, m.start() - 600):m.end() + 900]
        if re.search(r"confirmationDialog|\.alert\s*\(|unsaved|isDirty|hasChanges", near,
                     re.I):
            continue
        out.append(finding("S-IOS-MODALITY", f, _line(t, m.start()), m.group(0),
                           "Swipe-to-dismiss is disabled with no confirmation nearby, so "
                           "the sheet has one exit and the user has to find it. Either "
                           "allow the gesture, or intercept it with a confirmation that "
                           "explains what would be lost (IOS-014).", "medium"))
    return out[:3]


@check("S-IOS-GROUPEDLIST", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def grouped_list(f, p):
    """Settings-shaped content wants the platform's grouped list. A bespoke card
    stack loses the section semantics, the separators, the swipe actions and the
    row-selection behaviour users expect there (IOS-015)."""
    out, t = [], _src(f)
    if not re.search(r"\b(?:Settings|Preferences|Account|Profile)\w*View\b", t):
        return out
    if re.search(r"\bList\b|\bForm\b|\.insetGrouped\b|UITableView", t):
        return out
    m = re.search(r"\bVStack\b", t)
    if not m:
        return out
    rows = len(re.findall(r"\bHStack\b", t))
    if rows < 4:
        return out
    out.append(finding("S-IOS-GROUPEDLIST", f, _line(t, m.start()),
                       f"settings-shaped view built from VStack with {rows} HStack rows",
                       "This is settings-shaped content assembled by hand. `List` with "
                       "`.listStyle(.insetGrouped)` or `Form` gives you sections, "
                       "separators, selection behaviour and the right metrics at every "
                       "Dynamic Type size for free (IOS-015).", "low"))
    return out


@check("S-IOS-TRANSITION", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def system_transitions(f, p):
    """A custom transition on a pushed screen contradicts the gesture that brought
    the user there, and the direction of travel stops meaning anything (IOS-016)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.transition\s*\(\s*(\.[\w.]+(?:\([^)]*\))?)", t):
        near = t[max(0, m.start() - 400):m.start()]
        if not re.search(r"NavigationLink|NavigationStack|navigationDestination", near):
            continue
        out.append(finding("S-IOS-TRANSITION", f, _line(t, m.start()), m.group(0),
                           "A custom transition on a navigation push. The platform's "
                           "slide is what the edge-swipe back reverses; replacing it "
                           "makes the gesture and the animation disagree (IOS-016).",
                           "low"))
    return out[:3]


@check("S-IOS-REDUCEMOTION", exts=IOS_EXTS, requires=on_ios, surfaces=("native",))
def reduce_motion_ios(f, p):
    """Reduce Motion exists because large parallax and slide animations make some
    people ill. An animation that never consults it does not have an accessibility
    gap -- it has a health one (IOS-017)."""
    out, t = [], _src(f)
    anim = list(re.finditer(r"\bwithAnimation\s*(?:\(|\{)|\.animation\s*\(\s*\.(?:spring|"
                            r"easeIn|easeOut|easeInOut|interpolatingSpring)", t))
    if not anim:
        return out
    if re.search(r"accessibilityReduceMotion|UIAccessibility\.isReduceMotionEnabled|"
                 r"AccessibilityReduceMotion|isReduceMotionEnabled|"
                 r"useReducedMotion|AccessibilityInfo", f.text):
        return out
    m = anim[0]
    out.append(finding("S-IOS-REDUCEMOTION", f, _line(t, m.start()),
                       f"{len(anim)} animation(s), no Reduce Motion check in this file",
                       "Nothing here reads Reduce Motion. Gate the movement on "
                       "`@Environment(\\.accessibilityReduceMotion)` (SwiftUI) or "
                       "`UIAccessibility.isReduceMotionEnabled` (UIKit) and cross-fade "
                       "instead of sliding when it is on (IOS-017).", "medium"))
    return out


# ================================================================= Android
@check("S-AND-ADAPTIVENAV", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def adaptive_nav(f, p):
    """A phone's bottom navigation bar shipped unchanged to a tablet puts the
    whole navigation an arm's length from where the hands are (AND-001)."""
    out, t = [], _src(f)
    # One match, reused. Written as two separate searches, the second was
    # narrower than the first and returned None on `NavigationBar { }` -- the
    # check raised, and the only reason that was visible at all is that a raising
    # check reports NOT_RUN instead of passing.
    m = re.search(r"\bNavigationBar\s*[({]|BottomNavigationView", t)
    if not m:
        return out
    if re.search(r"WindowSizeClass|calculateWindowSizeClass|windowWidthSizeClass|"
                 r"NavigationRail|NavigationDrawer|ModalNavigationDrawer|"
                 r"PermanentNavigationDrawer|adaptive", t):
        return out
    out.append(finding("S-AND-ADAPTIVENAV", f, _line(t, m.start()), m.group(0),
                       "A bottom navigation bar with no window size class anywhere in "
                       "this file, so the same bar ships to a tablet. Switch to "
                       "`NavigationRail` or a drawer at expanded width -- branch on "
                       "`calculateWindowSizeClass()`, not on a device check (AND-001).",
                       "medium"))
    return out


@check("S-AND-SYSTEMBACK", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def system_back(f, p):
    """Back is the one gesture every Android user has. A handler that swallows it
    without navigating leaves them with no way out but the app switcher
    (AND-002)."""
    out, t = [], _src(f)
    for m in re.finditer(r"BackHandler\s*\(([^)]*)\)\s*\{([^}]{0,200})\}", t, re.S):
        body = strip_comments(m.group(2)).strip()
        if body:
            continue                     # it does something; what, is not ours to judge
        out.append(finding("S-AND-SYSTEMBACK", f, _line(t, m.start()),
                           " ".join(m.group(0).split())[:80],
                           "This BackHandler consumes Back and does nothing, so Back "
                           "stops working on this screen. "
                           "Either drop the handler and let the event through, or "
                           "handle it by going somewhere -- confirming, closing a sheet, "
                           "popping the stack (AND-002).",
                           "medium"))
    for m in re.finditer(r"override\s+fun\s+onBackPressed\s*\(\s*\)\s*\{([^}]{0,120})\}", t):
        if re.search(r"super\.onBackPressed|navigat|finish", m.group(1)):
            continue
        out.append(finding("S-AND-SYSTEMBACK", f, _line(t, m.start()),
                           " ".join(m.group(0).split())[:80],
                           "`onBackPressed` overridden without calling super or "
                           "navigating, which traps the user on this screen (AND-002).",
                           "medium"))
    return out[:4]


@check("S-AND-INSETS", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def window_insets(f, p):
    """Edge-to-edge without insets means the bottom row of content sits under the
    navigation bar and the field you are typing in sits under the keyboard
    (AND-003)."""
    out, t = [], _src(f)
    m = re.search(r"enableEdgeToEdge\s*\(|WindowCompat\.setDecorFitsSystemWindows"
                  r"\s*\([^)]*,\s*false\s*\)", t)
    if not m:
        return out
    if re.search(r"WindowInsets|systemBarsPadding|safeDrawingPadding|imePadding|"
                 r"navigationBarsPadding|statusBarsPadding|displayCutoutPadding|"
                 r"ViewCompat\.setOnApplyWindowInsetsListener", t):
        return out
    out.append(finding("S-AND-INSETS", f, _line(t, m.start()), m.group(0),
                       "Edge-to-edge is on and nothing in this file applies the window "
                       "insets, so content runs under the status bar, the navigation bar "
                       "and the keyboard. Add `Modifier.safeDrawingPadding()` or the "
                       "specific `systemBarsPadding()` / `imePadding()` where each one "
                       "belongs (AND-003).", "high"))
    return out


@check("S-AND-TOPBAR", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def top_app_bar(f, p):
    """A screen inside a Scaffold with a hand-built header loses the top app bar's
    scroll behaviour, its overflow menu and its title metrics (AND-004)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\bScaffold\s*\(", t):
        body = t[m.end():m.end() + 1800]
        if re.search(r"topBar\s*=|TopAppBar|LargeTopAppBar|CenterAlignedTopAppBar", body):
            continue
        if not re.search(r"\bRow\s*\(|\bText\s*\(", body):
            continue
        out.append(finding("S-AND-TOPBAR", f, _line(t, m.start()), "Scaffold with no topBar",
                           "A Scaffold with no `topBar`. If this screen has a title or "
                           "actions, `TopAppBar` gives you the scroll behaviour, the "
                           "overflow menu and the insets handling that a hand-built header "
                           "does not (AND-004).", "low"))
    return out[:3]


@check("S-AND-TYPESCALE", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def type_scale(f, p):
    """Hand-picking a size per screen is how a product ends up with eleven type
    sizes and no hierarchy. The scale has roles for a reason (AND-005)."""
    out, t = [], _src(f)
    if f.ext not in (".kt", ".kts"):
        return out
    for m in re.finditer(r"fontSize\s*=\s*(\d+(?:\.\d+)?)\.(sp|dp)", t):
        out.append(finding("S-AND-TYPESCALE", f, _line(t, m.start()), m.group(0),
                           f"A literal {m.group(1)}.{m.group(2)} font size. Take the role "
                           f"from the scale -- "
                           f"`MaterialTheme.typography.bodyLarge`, `titleMedium`, "
                           f"`labelSmall` -- so the type system is one decision instead of "
                           f"one per call site (AND-005).", "high"))
    return out[:5]


@check("S-AND-SYSTEMFONT", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def android_font(f, p):
    """A brand face belongs in the theme, applied through the type scale. Set per
    call site it drifts, and the roles stop being comparable (AND-006)."""
    out, t = [], _src(f)
    if f.ext not in (".kt", ".kts"):
        return out
    for m in re.finditer(r"fontFamily\s*=\s*(FontFamily\s*\([^)]*\)|\w+Font\w*)", t):
        if re.search(r"MaterialTheme|Typography", t[max(0, m.start() - 200):m.start()]):
            continue
        out.append(finding("S-AND-SYSTEMFONT", f, _line(t, m.start()),
                           " ".join(m.group(0).split())[:60],
                           "A font family set at the call site rather than through the "
                           "theme. Put the brand face in the `Typography` you pass to "
                           "`MaterialTheme` once, so every role stays consistent "
                           "(AND-006).", "low"))
    return out[:4]


@check("S-AND-SP", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def scalable_sp(f, p):
    """Text sized in dp ignores the system font-size setting entirely. This is the
    Android equivalent of pinning point sizes, and it fails the same reader
    (AND-007)."""
    out, t = [], _src(f)
    if f.ext in (".kt", ".kts"):
        for m in re.finditer(r"fontSize\s*=\s*\d+(?:\.\d+)?\.dp", t):
            out.append(finding("S-AND-SP", f, _line(t, m.start()), m.group(0),
                               "Text sized in dp does not follow the system font-size "
                               "setting. Use `.sp` (AND-007).", "high"))
        for m in re.finditer(r"(?:lineHeight|letterSpacing)\s*=\s*\d+(?:\.\d+)?\.dp", t):
            out.append(finding("S-AND-SP", f, _line(t, m.start()), m.group(0),
                               "Text metrics in dp will not scale with the font size they "
                               "belong to. Use `.sp` (AND-007).", "medium"))
    for m in re.finditer(r'android:textSize\s*=\s*"[\d.]+(?:dp|px)"', t):
        out.append(finding("S-AND-SP", f, _line(t, m.start()), m.group(0),
                           "`textSize` in dp or px ignores the user's font-size setting. "
                           "Use sp (AND-007).", "high"))
    return out[:5]


@check("S-AND-ROLETOKENS", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def role_tokens(f, p):
    """`Color(0xFF1A1A1A)` is a value. `MaterialTheme.colorScheme.surface` is a
    decision that resolves for the light scheme, the dark scheme and the
    high-contrast variants (AND-008)."""
    out, t = [], _src(f)
    if f.ext not in (".kt", ".kts"):
        return out
    # A colour scheme's own arguments are where literals belong -- that IS the
    # palette. Everything outside those parentheses is a call site.
    exempt = []
    for s in re.finditer(r"(?:light|dark|dynamicLight|dynamicDark)ColorScheme\s*\(", t):
        depth, i = 0, s.end() - 1
        while i < len(t):
            if t[i] == "(":
                depth += 1
            elif t[i] == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        exempt.append((s.start(), i))
    if re.search(r"(?:Color|Theme|Palette)\.kts?$", f.rel):
        return out
    for m in re.finditer(r"Color\s*\(\s*0x[0-9A-Fa-f]{6,8}\s*\)", t):
        if any(a <= m.start() <= b for a, b in exempt):
            continue
        out.append(finding("S-AND-ROLETOKENS", f, _line(t, m.start()), m.group(0),
                           "A literal colour outside the theme. It carries no role, so "
                           "the dark and high-contrast schemes cannot resolve it. Use "
                           "`MaterialTheme.colorScheme.<role>` and define the literal once "
                           "in the colour scheme (AND-008).", "high"))
    return out[:5]


@check("S-AND-DYNAMICCOLOR", scope="project", exts=AND_EXTS, requires=on_android,
       surfaces=("native",))
def dynamic_color(f, p):
    """Dynamic Color is the one thing that makes an Android app feel like it
    belongs to its owner. Optional, but worth knowing you skipped it (AND-009)."""
    out = []
    theme, saw_dynamic = None, False
    for q in p.root.rglob("*.kt"):
        if any(part in ("build", ".gradle") for part in q.parts):
            continue
        try:
            txt = q.read_text(errors="replace")
        except OSError:
            continue
        if re.search(r"lightColorScheme\s*\(|darkColorScheme\s*\(", txt):
            theme = theme or q
        if re.search(r"dynamicLightColorScheme|dynamicDarkColorScheme|dynamicColorScheme",
                     txt):
            saw_dynamic = True
    if theme is not None and not saw_dynamic:
        out.append(finding("S-AND-DYNAMICCOLOR", f, 1,
                           f"colour scheme in {theme.name}, no dynamic scheme anywhere",
                           "A static colour scheme with no Dynamic Color path. On Android "
                           "12+ `dynamicLightColorScheme(context)` derives the scheme from "
                           "the user's wallpaper, with this scheme as the fallback. Skip it "
                           "deliberately if the brand requires it -- but skip it on "
                           "purpose (AND-009).", "low"))
    return out


@check("S-AND-DARKTHEME", scope="project", exts=AND_EXTS, requires=on_android,
       surfaces=("native",))
def dark_theme(f, p):
    """A light scheme with no dark one means the dark theme is an inversion the
    system performs and nobody designed (AND-010)."""
    out = []
    light, dark, where = False, False, None
    for q in p.root.rglob("*.kt"):
        try:
            txt = q.read_text(errors="replace")
        except OSError:
            continue
        if re.search(r"lightColorScheme\s*\(", txt):
            light, where = True, where or q
        if re.search(r"darkColorScheme\s*\(|isSystemInDarkTheme\s*\(", txt):
            dark = True
    if light and not dark:
        out.append(finding("S-AND-DARKTHEME", f, 1,
                           f"lightColorScheme in {where.name if where else 'theme'}, "
                           f"no darkColorScheme",
                           "A light colour scheme with no dark counterpart and no "
                           "`isSystemInDarkTheme()` branch. Define `darkColorScheme` and "
                           "choose its surfaces -- a dark theme is a design, not an "
                           "inversion (AND-010).", "medium"))
    return out


@check("S-AND-ELEVATION", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def tonal_elevation(f, p):
    """Material conveys elevation through surface tone. An arbitrary drop shadow
    on top of that reads as two depth systems disagreeing (AND-011)."""
    out, t = [], _src(f)
    if f.ext not in (".kt", ".kts"):
        return out
    for m in re.finditer(r"\.shadow\s*\(\s*(?:elevation\s*=\s*)?(\d+(?:\.\d+)?)\.dp", t):
        v = float(m.group(1))
        if v <= 1:
            continue
        near = t[max(0, m.start() - 300):m.end() + 200]
        if re.search(r"tonalElevation|CardDefaults|SurfaceDefaults|ElevatedCard", near):
            continue
        out.append(finding("S-AND-ELEVATION", f, _line(t, m.start()), m.group(0),
                           f"A {v:g}.dp shadow applied by hand. Material expresses "
                           f"elevation as surface tone: use `Surface(tonalElevation = "
                           f"{v:g}.dp)` or `ElevatedCard`, which give the tonal shift and "
                           f"the shadow the spec pairs with it (AND-011).", "medium"))
    return out[:4]


@check("S-AND-MATERIAL", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def material_components(f, p):
    """An iOS control on Android is the clearest possible signal that nobody
    looked at the app on this platform (AND-012)."""
    out, t = [], _src(f)
    for m in re.finditer(r"import\s+[\"']?package:flutter/cupertino\.dart[\"']?|"
                         r"\bCupertino(?:Button|Switch|Alert|Picker|NavigationBar|"
                         r"ActivityIndicator|SegmentedControl)\b", t):
        out.append(finding("S-AND-MATERIAL", f, _line(t, m.start()), m.group(0),
                           "A Cupertino (iOS-shaped) widget in a build that ships to "
                           "Android. Use the Material equivalent, or branch on the "
                           "platform so each gets its own (AND-012).", "high"))
    for m in re.finditer(r"\bimport\s+android\.widget\.Switch\b", t):
        out.append(finding("S-AND-MATERIAL", f, _line(t, m.start()), m.group(0),
                           "The framework `Switch` rather than "
                           "`com.google.android.material.switchmaterial.SwitchMaterial`, "
                           "so it will not take the Material theme (AND-012).", "medium"))
    return out[:4]


@check("S-AND-FAB", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def single_fab(f, p):
    """Two floating action buttons mean neither is the primary action (AND-013)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\bScaffold\s*\(", t):
        body = t[m.end():m.end() + 2400]
        n = len(re.findall(r"\bFloatingActionButton\s*\(|\bExtendedFloatingActionButton"
                           r"\s*\(|\bFloatingActionButton\b", body))
        if n > 1:
            out.append(finding("S-AND-FAB", f, _line(t, m.start()),
                               f"Scaffold with {n} floating action buttons",
                               f"{n} FABs on one screen. The FAB is the screen's single "
                               f"primary action -- promote one and move the rest into the "
                               f"app bar or the content (AND-013).", "medium"))
    return out[:3]


@check("S-AND-TOAST", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def snackbar_not_toast(f, p):
    """A toast cannot be acted on, cannot be dismissed, is not announced reliably,
    and on newer versions the system may not show it at all (AND-014)."""
    out, t = [], _src(f)
    for m in re.finditer(r"Toast\.makeText\s*\(|\bToast\.show\s*\(|"
                         r"ToastAndroid\.show\s*\(", t):
        out.append(finding("S-AND-TOAST", f, _line(t, m.start()), m.group(0).strip(),
                           "A toast for feedback. A snackbar can carry the action that "
                           "undoes what just happened, is announced to accessibility "
                           "services and respects the insets. Use `SnackbarHostState."
                           "showSnackbar()` (AND-014).", "medium"))
    return out[:4]


@check("S-AND-REDUCEMOTION", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def reduce_motion_android(f, p):
    """Android's 'Remove animations' setting is an accessibility setting, and an
    animation that never reads it ignores a person who asked (AND-015)."""
    out, t = [], _src(f)
    if f.ext not in (".kt", ".kts"):
        return out
    anim = list(re.finditer(r"\banimate\w*AsState\s*\(|\bAnimatedVisibility\s*\(|"
                            r"\bupdateTransition\s*\(|\btween\s*\(|\bspring\s*\(", t))
    if not anim:
        return out
    if re.search(r"ANIMATOR_DURATION_SCALE|animatorDurationScale|"
                 r"Settings\.Global\.getFloat|LocalAccessibilityManager|"
                 r"isReduceMotionEnabled|areAnimationsEnabled", f.text):
        return out
    m = anim[0]
    out.append(finding("S-AND-REDUCEMOTION", f, _line(t, m.start()),
                       f"{len(anim)} animation(s), no animation-scale check in this file",
                       "Nothing here reads the system animation scale. Read "
                       "`Settings.Global.ANIMATOR_DURATION_SCALE`; when it is 0, cut to "
                       "the end state or cross-fade instead of animating (AND-015).",
                       "medium"))
    return out


@check("S-AND-TARGET48", exts=AND_EXTS, requires=on_android, surfaces=("native",))
def target_48dp(f, p):
    """48 by 48 dp is the touch minimum, with 8 dp between adjacent targets
    (NUM-007)."""
    out, t = [], _src(f)
    mindp = float(p.num("target_size", "android_min_dp", 48))
    if f.ext in (".kt", ".kts"):
        for m in re.finditer(r"\.size\s*\(\s*(\d+(?:\.\d+)?)\.dp\s*\)", t):
            v = float(m.group(1))
            if v >= mindp:
                continue
            window = t[max(0, m.start() - 320):m.start()]
            if not re.search(r"\bclickable\b|\bIconButton\b|\bButton\b|\bonClick\b", window):
                continue
            if re.search(r"minimumInteractiveComponentSize|\.padding\s*\(",
                         t[m.end():m.end() + 140]):
                continue
            out.append(finding("S-AND-TARGET48", f, _line(t, m.start()), m.group(0),
                               f"{v:g}.dp on a clickable, under the {mindp:g} dp minimum. "
                               f"Keep the icon and grow the target: "
                               f"`Modifier.minimumInteractiveComponentSize()`, or "
                               f"`.size({mindp:g}.dp)` with the icon sized inside "
                               f"(NUM-007).", "medium"))
    for m in re.finditer(r'android:(?:layout_width|layout_height)\s*=\s*"(\d+)dp"', t):
        if float(m.group(1)) < mindp and re.search(r"Button|ImageButton|CheckBox|Switch",
                                                   t[max(0, m.start() - 400):m.start()]):
            out.append(finding("S-AND-TARGET48", f, _line(t, m.start()), m.group(0),
                               f"{m.group(1)}dp on a control, under the {mindp:g} dp "
                               f"minimum (NUM-007).", "medium"))
    return out[:5]


@check("S-IOS-SYSTEMFONT", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def ios_system_font(f, p):
    """A brand face can carry a display moment. It cannot carry body text, labels
    and controls without losing the metrics the platform tuned for reading at
    every Dynamic Type size (IOS-006)."""
    out, t = [], _src(f)
    for m in re.finditer(r"\.font\s*\(\s*(?:Font)?\.custom\s*\(\s*[\"']([^\"']+)[\"']", t):
        near = t[max(0, m.start() - 200):m.start()]
        if re.search(r"largeTitle|\bTitle\b|Hero|Display|Headline", near):
            continue
        out.append(finding("S-IOS-SYSTEMFONT", f, _line(t, m.start()),
                           " ".join(m.group(0).split())[:60],
                           f"`{m.group(1)}` on what looks like body or control text. The "
                           f"system face is metric-tuned for reading at every Dynamic Type "
                           f"size; a custom one is not. Keep the brand face for display "
                           f"roles, and if it must be used here, pair it with "
                           f"`relativeTo:` so it still scales (IOS-006).", "low"))
    return out[:4]


@check("S-IOS-LARGETITLE", exts=IOS_ONLY, requires=on_ios, surfaces=("native",))
def large_titles(f, p):
    """Large titles say "you are at the top of this section". Turned off globally
    they say nothing, and the user loses the only cue that distinguishes a root
    screen from a pushed one (IOS-004)."""
    out, t = [], _src(f)
    for m in re.finditer(r"prefersLargeTitles\s*=\s*false", t):
        out.append(finding("S-IOS-LARGETITLE", f, _line(t, m.start()), m.group(0),
                           "Large titles switched off for the whole navigation "
                           "controller. Set the display mode per screen instead -- large "
                           "at the root, inline on detail screens -- so depth stays "
                           "legible (IOS-004).", "low"))
    # `.inline` applied to the root of a NavigationStack is the same mistake said
    # in SwiftUI.
    for m in re.finditer(r"\.navigationBarTitleDisplayMode\s*\(\s*\.inline\s*\)", t):
        near = t[max(0, m.start() - 600):m.start()]
        if not re.search(r"NavigationStack\s*\{|NavigationView\s*\{", near):
            continue
        out.append(finding("S-IOS-LARGETITLE", f, _line(t, m.start()), m.group(0),
                           "An inline title on what appears to be the root of the stack. "
                           "Top-level screens take a large title that collapses on "
                           "scroll; inline belongs on pushed detail screens (IOS-004).",
                           "low"))
    return out[:3]
