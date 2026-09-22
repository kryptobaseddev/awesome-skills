"""The craft floor: the numeric ceilings and habits that separate a page someone
built from a page something assembled.

Derived from the impeccable skill's craft floor (Apache-2.0,
github.com/pbakaus/impeccable) and re-expressed as detectors bound to rule IDs,
so each one is a measurement with a threshold in `references/rules/thresholds.yaml`
rather than advice. impeccable states these as guidance for an agent to follow;
here they also have to survive being checked, which is the only reason to state a
number at all.

A floor is not a ceiling. Everything here green means the mechanics are not in
the way -- it says nothing about whether the design is any good, and a detector
that implied otherwise would be lying.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")
_TW_STEP = {"xs": 12, "sm": 14, "base": 16, "lg": 18, "xl": 20, "2xl": 24, "3xl": 30,
            "4xl": 36, "5xl": 48, "6xl": 60, "7xl": 72, "8xl": 96, "9xl": 128}


def _line(t, pos):
    return t[:pos].count("\n") + 1


def _hay(f):
    """Source text and CSS together, comments stripped -- a craft tell in a
    commented-out block is not shipping."""
    return strip_comments(f.css) if f.css else strip_comments(f.text)


# ---------------------------------------------------------------- type ceilings
@check("S-CRAFT-HERO-SCALE")
def hero_scale(f, p):
    """Above about 6rem a heading is shouting, not leading.

    Scale substitutes for hierarchy: if the h1 has to be 9rem to feel primary,
    the page has no other contrast doing that job."""
    out = []
    cap = float(p.num("type_craft", "display_max_rem", 6.0))
    hay = _hay(f)
    for m in re.finditer(r"clamp\([^)]*?(\d+(?:\.\d+)?)rem\s*\)", hay):
        v = float(m.group(1))
        if v <= cap:
            continue
        out.append(finding("S-CRAFT-HERO-SCALE", f, _line(hay, m.start()),
                           m.group(0)[:70],
                           f"clamp() tops out at {v:g}rem, past the {cap:g}rem display "
                           f"ceiling. Past this the page reads as loud rather than "
                           f"composed -- get the emphasis from weight, space and colour "
                           f"instead of size alone (VIS-002).", "medium"))
    for m in re.finditer(r"(?<![\w-])text-\[(\d+(?:\.\d+)?)rem\]", hay):
        if float(m.group(1)) > cap:
            out.append(finding("S-CRAFT-HERO-SCALE", f, _line(hay, m.start()), m.group(0),
                               f"{m.group(1)}rem is past the {cap:g}rem display ceiling "
                               f"(VIS-002).", "medium"))
    return out


@check("S-CRAFT-TYPE-FLAT")
def flat_hierarchy(f, p):
    """Adjacent type roles that are nearly the same size cannot carry different
    jobs. The reader cannot see a difference the designer intended."""
    out = []
    ratio = float(p.num("type_craft", "scale_step_ratio_min", 1.25))
    hay = _hay(f)
    sizes = set()
    for m in re.finditer(r"font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)", hay):
        v = float(m.group(1)) * (16.0 if m.group(2) == "rem" else 1.0)
        if 11 <= v <= 200:
            sizes.add(round(v, 1))
    for m in re.finditer(r"(?<![\w-])text-(xs|sm|base|lg|xl|[2-9]xl)(?![\w-])", hay):
        sizes.add(float(_TW_STEP[m.group(1)]))
    ladder = sorted(sizes)
    if len(ladder) < 3:
        return out                       # not enough of a scale to be flat
    tight = [(a, b) for a, b in zip(ladder, ladder[1:]) if a >= 12 and 1.0 < b / a < ratio]
    # One close pair is a deliberate optical step; three or more is a flat scale.
    if len(tight) < 3:
        return out
    pairs = ", ".join(f"{a:g}/{b:g}px" for a, b in tight[:4])
    out.append(finding("S-CRAFT-TYPE-FLAT", f, 1, pairs,
                       f"{len(tight)} adjacent type steps differ by less than "
                       f"{ratio:g}x ({pairs}). Steps this close read as one size with "
                       f"noise, so the hierarchy is carried by nothing. Cut the number "
                       f"of roles, or space the ones you keep (VIS-002, NUM-015).",
                       "low"))
    return out


@check("S-CRAFT-FAMILIES")
def family_count(f, p):
    """More than three families reads as indecision, not richness. One face with
    real weight contrast almost always beats three competing ones."""
    out = []
    cap = int(p.num("type_craft", "family_count_max", 3))
    hay = _hay(f)
    fams = set()
    for m in re.finditer(r"font-family\s*:\s*([^;}\n]+)", hay):
        first = m.group(1).split(",")[0].strip().strip("'\"")
        if first and not re.match(r"^(?:var\(|inherit|initial|unset|sans-serif|serif|"
                                  r"monospace|system-ui|ui-\w+)$", first, re.I):
            fams.add(first.lower())
    if len(fams) <= cap:
        return out
    out.append(finding("S-CRAFT-FAMILIES", f, 1, ", ".join(sorted(fams)[:6]),
                       f"{len(fams)} font families in one file, past the {cap} that a "
                       f"system can carry (display + body + optional mono). Pair on a "
                       f"contrast axis or use one family in several weights -- families "
                       f"that are similar but not identical read as a mistake (VIS-002).",
                       "low"))
    return out


@check("S-CRAFT-BALANCE")
def heading_balance(f, p):
    """`text-wrap: balance` costs nothing and fixes the two-word orphan line that
    makes a heading look accidental."""
    out = []
    hay = _hay(f)
    if re.search(r"text-wrap\s*:\s*balance|text-balance|text-wrap-balance", hay):
        return out
    # If the project adopted balance anywhere, a base style is probably carrying
    # it and a per-file absence means nothing. Reporting it 35 times across a
    # codebase is how a real point turns into noise nobody reads.
    if re.search(r"text-wrap\s*:\s*balance|text-balance", p.css_text or ""):
        return out
    heads = re.findall(r"<h[123][\s>]", f.text or "")
    if len(heads) < 5:
        return out
    out.append(finding("S-CRAFT-BALANCE", f, 1, f"{len(heads)} headings, no balance",
                       "No `text-wrap: balance` on any heading in a file with "
                       f"{len(heads)} of them. Without it a heading breaks wherever the "
                       "container ends, which is how a two-word orphan line appears at "
                       "one width and not another. `text-wrap: pretty` does the same for "
                       "long prose (VIS-002).", "low"))
    return out


# ------------------------------------------------------------------ depth rules
@check("S-CRAFT-HALO")
def glow_halo(f, p):
    """A shadow with no offset is not depth. Light comes from somewhere; a ring of
    colour on every side comes from nowhere and reads as a sticker."""
    out = []
    hay = _hay(f)
    for m in re.finditer(r"box-shadow\s*:\s*(?:inset\s+)?0\s+0\s+(\d+(?:\.\d+)?)px"
                         r"(?:\s+(\d+(?:\.\d+)?)px)?\s+(?:rgba?\([^)]*\)|#[0-9a-f]{3,8}|"
                         r"oklch\([^)]*\)|hsla?\([^)]*\))", hay, re.I):
        blur = float(m.group(1))
        if blur < 6:
            continue                     # a tight ring is a focus style, not a glow
        out.append(finding("S-CRAFT-HALO", f, _line(hay, m.start()), m.group(0)[:64],
                           "A zero-offset coloured glow. Depth needs an offset and a "
                           "soft blur, because light has a direction -- a ring on all "
                           "four sides is decoration standing in for elevation. If it is "
                           "a focus ring, say so with outline or ring utilities (VIS-006).",
                           "low"))
    return out


@check("S-CRAFT-HARD-SHADOW")
def hard_offset_shadow(f, p):
    """A zero-blur offset block shadow is a specific costume. Worn by a design
    that did not choose neobrutalism, it is a borrowed style."""
    out = []
    hay = _hay(f)
    neo = re.search(r"neobrutal|brutalis|\bneo-brutal", hay, re.I)
    if neo:
        return out
    for m in re.finditer(r"box-shadow\s*:\s*(-?\d+)px\s+(-?\d+)px\s+0(?:px)?\s",
                         hay, re.I):
        if abs(int(m.group(1))) < 2 and abs(int(m.group(2))) < 2:
            continue
        out.append(finding("S-CRAFT-HARD-SHADOW", f, _line(hay, m.start()),
                           m.group(0).strip()[:56],
                           "A hard offset shadow with no blur. That is the neobrutalist "
                           "signature, and nothing in this file claims that world -- so "
                           "it reads as a costume rather than a depth system. Give the "
                           "shadow a blur, or commit to the style deliberately (VIS-006).",
                           "low"))
    return out


@check("S-CRAFT-CARD-RADIUS")
def card_radius(f, p):
    """Cards live around 12-16px. Much rounder and a content container starts
    looking like a pill, which is a control."""
    out = []
    lo = float(p.num("depth", "card_radius_min_px", 12))
    hi = float(p.num("depth", "card_radius_max_px", 16))
    hay = _hay(f)
    for m in re.finditer(r"border-radius\s*:\s*(\d+(?:\.\d+)?)px", hay):
        v = float(m.group(1))
        if v <= hi or v > 60:
            continue                     # >60 is a deliberate circle/pill, not drift
        ctx = hay[max(0, m.start() - 260):m.start() + 120]
        if not re.search(r"\bcard\b|\bpanel\b|\btile\b|\bsurface\b", ctx, re.I):
            continue
        out.append(finding("S-CRAFT-CARD-RADIUS", f, _line(hay, m.start()),
                           m.group(0),
                           f"{v:g}px radius on a card. Cards read best at {lo:g}-{hi:g}px; "
                           f"past that a content surface starts reading as a control. "
                           f"Pills are for small controls (VIS-006).", "low"))
    return out


# ----------------------------------------------------------------- motion rules
@check("S-CRAFT-HIDDEN-AT-REST")
def hidden_at_rest(f, p):
    """The worst motion bug there is: content that only becomes visible when a
    reveal fires. Transitions do not run on a hidden tab or in a headless render,
    so the section ships blank and nobody sees it in development."""
    out = []
    hay = strip_comments(f.text or "")
    for m in re.finditer(r"(?:opacity-0|opacity\s*:\s*0\b|invisible|"
                         r"visibility\s*:\s*hidden)", hay):
        win = hay[max(0, m.start() - 320):m.start() + 320]
        revealed = re.search(r"(?:IntersectionObserver|inView|useInView|whileInView|"
                             r"data-(?:aos|reveal|animate)|\banimate-(?:in|fade)|"
                             r"scroll-?trigger|\bisVisible\b|\bhasEntered\b)", win, re.I)
        if not revealed:
            continue
        if re.search(r"prefers-reduced-motion|@starting-style", win):
            continue
        out.append(finding("S-CRAFT-HIDDEN-AT-REST", f, _line(hay, m.start()),
                           m.group(0),
                           "Content hidden at rest and revealed by a scroll animation. "
                           "Transitions are paused on inactive tabs and never fire in "
                           "headless renderers or for search crawlers, so this section "
                           "ships blank. Animate up from an already-visible default "
                           "instead (LAY-010, A11Y-010).", "medium"))
    return out


@check("S-CRAFT-EASING")
def easing_choice(f, p):
    """Entrances want exponential ease-out. `ease-in-out` on an entrance makes the
    thing crawl in; bounce and elastic are a template's idea of personality."""
    out = []
    hay = _hay(f)
    for m in re.finditer(r"(?:transition-timing-function|animation-timing-function|"
                         r"transition)\s*:[^;}\n]*?\b(ease-in-out|linear)\b", hay):
        win = hay[max(0, m.start() - 200):m.start() + 200]
        if not re.search(r"enter|appear|reveal|fade-?in|slide-?in|animate", win, re.I):
            continue
        out.append(finding("S-CRAFT-EASING", f, _line(hay, m.start()), m.group(0)[:56],
                           f"`{m.group(1)}` on an entrance. An entrance should decelerate "
                           "-- exponential ease-out (quart/quint/expo) arrives and settles; "
                           "ease-in-out starts slowly, which reads as lag (NUM-018).",
                           "low"))
    for m in re.finditer(r"cubic-bezier\(\s*[\d.]+\s*,\s*(-[\d.]+)\s*,[^)]*\)", hay):
        out.append(finding("S-CRAFT-EASING", f, _line(hay, m.start()), m.group(0)[:56],
                           "A negative control point means overshoot -- bounce or elastic. "
                           "It reads as a template's personality rather than this "
                           "product's. Ease out without overshoot (NUM-018).", "low"))
    return out


# ------------------------------------------------------------- browser surfaces
@check("S-CRAFT-SURFACES")
def browser_surfaces(f, p):
    """The parts nobody drew still carry the design.

    Selection colour, the caret, the scrollbar, the focus ring, underline offset
    and tabular numerals all ship with browser defaults that belong to no design
    system. Theming them is the cheapest signal a page was built rather than
    assembled, and it is the thing models skip most reliably."""
    out = []
    if not f.css:
        return out
    css = strip_comments(f.css)
    # Only meaningful for a stylesheet that is actually defining a system.
    if len(css) < 1200 or not re.search(r":root|@theme|--\w+\s*:", css):
        return out
    have = {
        "text selection (::selection)": r"::selection",
        "the text caret (caret-color)": r"caret-color",
        "the focus ring (:focus-visible)": r":focus-visible",
        "scrollbars (scrollbar-color or ::-webkit-scrollbar)":
            r"scrollbar-color|::-webkit-scrollbar",
        "underline offset (text-underline-offset)": r"text-underline-offset",
    }
    missing = [name for name, pat in have.items() if not re.search(pat, css, re.I)]
    if len(missing) < 3:
        return out
    out.append(finding("S-CRAFT-SURFACES", f, 1, f"{len(missing)} unthemed",
                       "This stylesheet defines a design system but leaves the browser's "
                       "own surfaces at their defaults: " + "; ".join(missing) +
                       ". None of these belong to any design system until you say so, and "
                       "they are visible on every page. Theming them from the palette is "
                       "the cheapest thing that makes a page look built (VIS-001, VIS-006).",
                       "low"))
    return out


# --------------------------------------------------------------- page scaffolds
@check("S-CRAFT-SECTION-NUMBERS")
def numbered_sections(f, p):
    """01 / 02 / 03 above headings implies a sequence. Usually there is none, and
    the numbers are a rhythm the page borrowed."""
    out = []
    hay = strip_comments(f.text or "")
    nums = re.findall(r">\s*(0[1-9])\s*<", hay)
    if len(set(nums)) < 3:
        return out
    m = re.search(r">\s*0[1-9]\s*<", hay)
    out.append(finding("S-CRAFT-SECTION-NUMBERS", f, _line(hay, m.start()),
                       ", ".join(sorted(set(nums))[:5]),
                       f"{len(set(nums))} zero-padded section numbers. Numbering implies "
                       "the order carries information the reader needs; if it does not, "
                       "the numbers are decoration that makes every section look like a "
                       "step in a process (VIS-006, CONTENT-001).", "low"))
    return out


@check("S-CRAFT-ICON-TILE")
def icon_tile_stack(f, p):
    """An icon in a tinted rounded square, repeated down a feature list, is the
    default feature-grid shape. It is what gets reached for when nobody decided
    what the section should look like."""
    out = []
    hay = strip_comments(f.text or "")
    tiles = re.findall(r"(?:rounded-(?:lg|xl|2xl)|border-radius)[^\"'`>]{0,80}?"
                       r"bg-\w+-(?:50|100|200)\b", hay)
    if len(tiles) < 3:
        return out
    m = re.search(r"(?:rounded-(?:lg|xl|2xl))[^\"'`>]{0,80}?bg-\w+-(?:50|100|200)\b", hay)
    out.append(finding("S-CRAFT-ICON-TILE", f, _line(hay, m.start()),
                       m.group(0)[:64],
                       f"{len(tiles)} icons in tinted rounded tiles. This is the default "
                       "feature-grid shape, so it reads as generated regardless of the "
                       "icons in it. Let the content set the shape -- or drop the tile and "
                       "give the icon the heading's colour (VIS-006).", "low"))
    return out


@check("S-CRAFT-STRIPES")
def stripe_background(f, p):
    """Repeating stripes and grid overlays are textures from a world -- graph
    paper, a blueprint, a canvas. Applied to a page that has no such world they
    are noise with a gradient function behind it."""
    out = []
    hay = _hay(f)
    for m in re.finditer(r"repeating-(?:linear|conic)-gradient\(", hay):
        ctx = hay[max(0, m.start() - 400):m.start() + 400]
        if re.search(r"blueprint|graph|grid-?paper|canvas|map|ruler|measur|"
                     r"barber|awning|caution|hazard", ctx, re.I):
            continue
        out.append(finding("S-CRAFT-STRIPES", f, _line(hay, m.start()), m.group(0),
                           "A repeating-gradient stripe or grid as background texture. "
                           "That pattern belongs to something -- graph paper, a blueprint, "
                           "a canvas. With no such material in the design it is noise. "
                           "Backgrounds are surfaces; texture them from the subject's "
                           "world or leave them flat (VIS-006).", "low"))
    return out


@check("S-CRAFT-GRADIENT-TEXT")
def gradient_text(f, p):
    """Gradient text fails contrast across part of its own run, by construction:
    the ratio changes along the glyphs and only the darkest stop was checked."""
    out = []
    hay = _hay(f)
    for m in re.finditer(r"(?:bg-clip-text[^\"'`]{0,60}text-transparent|"
                         r"text-transparent[^\"'`]{0,60}bg-clip-text|"
                         r"-webkit-background-clip\s*:\s*text)", hay):
        out.append(finding("S-CRAFT-GRADIENT-TEXT", f, _line(hay, m.start()),
                           m.group(0)[:60],
                           "Gradient text. The contrast ratio varies along the run, so "
                           "part of it fails whatever the darkest stop measures -- and it "
                           "is the most recognisable generated-UI signature there is. "
                           "Emphasis comes from weight and size (NUM-001, VIS-006).",
                           "medium"))
    return out


# -------------------------------------------------------------------- z-index
@check("S-CRAFT-ZINDEX")
def zindex_scale(f, p):
    """999 and 9999 are not values, they are a hope that nothing is higher. A
    stacking order you cannot read is one you cannot debug."""
    out = []
    cap = int(p.num("zindex", "arbitrary_max", 100))
    hay = _hay(f)
    seen = set()
    for m in re.finditer(r"(?:z-index\s*:\s*|(?<![\w-])z-\[)(\d{3,6})", hay):
        v = int(m.group(1))
        if v <= cap or v in seen:
            continue
        seen.add(v)
        out.append(finding("S-CRAFT-ZINDEX", f, _line(hay, m.start()), m.group(0),
                           f"z-index {v}. Above {cap} these stop being a scale and become "
                           "a bidding war; the next overlay picks a bigger number and the "
                           "order is no longer stated anywhere. Name the layers instead "
                           "-- dropdown, sticky, backdrop, modal, toast, tooltip "
                           "(VIS-001).", "low"))
    return out


# ------------------------------------------------------------- colour on colour
@check("S-CRAFT-GRAY-ON-COLOR", exts=SRC)
def gray_on_color(f, p):
    """Grey text on a chromatic surface looks washed out however good its contrast
    ratio is: the surface has hue and the text has none, so it reads as faded
    rather than secondary. Tint it from the surface's own hue.

    Walks the tag tree rather than a text window. The pair is genuinely
    parent-surface plus child-text, so a window is tempting -- but inside a
    conditional className the true branch's `bg-blue-600 text-white` and another
    branch's `text-gray-400` sit side by side in the source and share no element.
    The tree cannot make that mistake."""
    _BG = re.compile(r"^(?:\w+:)*bg-(?:red|orange|amber|yellow|lime|green|emerald|teal|"
                     r"cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-([4-9]\d{2})$")
    _FG = re.compile(r"^(?:\w+:)*text-(?:gray|grey|slate|zinc|neutral|stone)-"
                     r"([3-6]\d{2})$")
    out = []
    for t in f.tags:
        if t.closing:
            continue
        fg = next((c for c in t.classes() if _FG.match(c)), None)
        if not fg:
            continue
        # nearest ancestor that sets a saturated surface
        anc, bg, depth = t.parent, None, 0
        while anc is not None and depth < 4:
            bg = next((c for c in anc.classes() if _BG.match(c)), None)
            if bg:
                break
            anc, depth = anc.parent, depth + 1
        if not bg:
            continue
        out.append(finding("S-CRAFT-GRAY-ON-COLOR", f, t.line, f"{bg} + {fg}",
                           f"`{fg}` inside `{bg}`. Neutral grey over a chromatic surface "
                           "reads as washed out rather than secondary, because the "
                           "surface carries hue and the text carries none. Derive the "
                           "secondary tone from the surface's own hue, or use a "
                           "transparency of the foreground (VIS-001, NUM-001).", "low"))
    return out
