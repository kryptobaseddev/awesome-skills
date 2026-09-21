"""Visual craft tells: the moves a model reaches for when no design decision
was made. Grouped by the decision each one substitutes for, because that is how
you fix them -- not by deleting the symptom but by making the choice it replaced.

All low confidence by design. A deliberate choice looks identical to a reflex
from the outside; what separates them is whether anyone can say why.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")


def _line(t, pos):
    return t[:pos].count("\n") + 1


def _one(det, f, pos, snippet, msg, conf="low"):
    return [finding(det, f, _line(f.text, pos), snippet, msg, conf)]


@check("S-CRAFT-DEPTH")
def depth_metaphor(f, p):
    """Border and shadow are two different ways of saying 'this is a surface'.
    Using both on one element is two systems arguing; a glow on dark is a third."""
    out = []
    both = re.search(r"border(?:-\w+)?\s*:\s*1px[^;]*;[^}]*box-shadow\s*:[^;]*\b(?:1[6-9]|"
                     r"[2-9]\d)px", f.text) or \
        re.search(r"(?<![\w-])border(?![\w-])[^\"'`]{0,40}shadow-(?:lg|xl|2xl)", f.text)
    if both:
        out += _one("S-CRAFT-DEPTH", f, both.start(), both.group(0)[:60],
                    "A 1px border and a wide soft shadow on the same element. Pick one "
                    "depth metaphor -- the border says 'edge', the shadow says 'floating', "
                    "and together they say neither (VIS-006).")
    accent = re.search(r"border-(?:left|bottom|l|b)(?:-\d)?\s*:\s*[2-9]px[^;]*;[^}]*"
                       r"border-radius\s*:\s*(?:1[2-9]|[2-9]\d)px|"
                       r"border-[lb]-[2-8]\b[^\"'`]{0,40}rounded-(?:xl|2xl|3xl)", f.text)
    if accent:
        out += _one("S-CRAFT-DEPTH", f, accent.start(), accent.group(0)[:60],
                    "A thick accent border on a heavily rounded element. The straight "
                    "stripe fights the curve, and the stripe usually implies a category "
                    "system that does not exist (VIS-006).")
    glow = re.search(r"box-shadow\s*:\s*0\s+0\s+\d+px[^;]*(?:rgba?\([^)]*0?\.[3-9]|#[0-9a-f]{3,6})",
                     f.text, re.I)
    if glow and re.search(r"background(?:-color)?\s*:\s*(?:#[0-2][0-9a-f]|rgb\(\s*[0-3]?\d\s*,)",
                          f.text, re.I):
        out += _one("S-CRAFT-DEPTH", f, glow.start(), glow.group(0)[:60],
                    "A coloured glow on a dark surface. It reads as a screenshot of a "
                    "developer tool rather than a product, and it costs contrast on "
                    "anything sitting inside it (VIS-006).")
    return out[:4]


@check("S-CRAFT-TYPESYSTEM")
def type_system(f, p):
    """One family at four weights is not a pairing decision, it is the absence
    of one. A flat size scale is the same absence in the other direction."""
    out = []
    if f.ext in CSS or "@theme" in f.text:
        fams = set(re.findall(r"font-family\s*:\s*([^;]+)", f.text))
        weights = set(re.findall(r"font-weight\s*:\s*(\d00)", f.text))
        if len(fams) <= 1 and len(weights) >= 4:
            m = re.search(r"font-weight", f.text)
            out += _one("S-CRAFT-TYPESYSTEM", f, m.start(),
                        f"1 family, {len(weights)} weights",
                        "One typeface carrying the whole hierarchy through weight alone. "
                        "Weight is the weakest hierarchy signal available; size, colour and "
                        "space all outrank it (VIS-002).")
    # A component legitimately uses two sizes. This is about a PAGE with no
    # scale -- require page-shaped markup and real volume before judging.
    sizes = set(re.findall(r"(?<![\w-])text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl)\b", f.text))
    page_shaped = (len({t.name.lower() for t in f.tags} & {"main", "section", "article"}) > 0
                   or len([t for t in f.tags if re.fullmatch(r"[hH][1-4]", t.name)]) >= 3)
    if page_shaped and len(f.tags) > 25 and 0 < len(sizes) <= 2:
        out += _one("S-CRAFT-TYPESYSTEM", f, 0, f"only {len(sizes)} type sizes in use",
                    "A page of this size using one or two type sizes has no visual "
                    "hierarchy for a reader to skim by (VIS-002).")
    italic_serif = re.search(r"font-(?:family\s*:\s*[^;]*serif[^;]*;[^}]*font-)?style\s*:\s*italic"
                             r"|(?<![\w-])italic\b[^\"'`]{0,30}font-serif|"
                             r"font-serif[^\"'`]{0,30}(?<![\w-])italic\b", f.text)
    if italic_serif and re.search(r"text-(?:4xl|5xl|6xl|7xl)|font-size\s*:\s*(?:4[89]|[5-9]\d)px",
                                  f.text):
        out += _one("S-CRAFT-TYPESYSTEM", f, italic_serif.start(), italic_serif.group(0)[:50],
                    "Large italic serif display type. It is the default gesture for "
                    "'sophisticated' and it is recognisable as exactly that (VIS-006).")
    return out[:3]


@check("S-CRAFT-DECOR")
def decorative_reflex(f, p):
    """Decoration that carries no information: gradient text, stripe fills,
    edge tabs, and the tinted icon tile repeated down a feature list."""
    out = []
    gt = re.search(r"background-clip\s*:\s*text|(?<![\w-])bg-clip-text\b", f.text)
    if gt:
        out += _one("S-CRAFT-DECOR", f, gt.start(), gt.group(0),
                    "Gradient text. Part of every such run fails contrast against its own "
                    "background by construction, and it is the single most common "
                    "generated-hero treatment (NUM-001, VIS-006).", "medium")
    st = re.search(r"repeating-linear-gradient\s*\(", f.text)
    if st:
        out += _one("S-CRAFT-DECOR", f, st.start(), st.group(0),
                    "A repeating stripe fill. It draws the eye hard while meaning nothing, "
                    "and it interacts badly with scrolling on low-refresh displays "
                    "(VIS-006).")
    side = re.search(r"(?:writing-mode\s*:\s*vertical|rotate-(?:90|270)|"
                     r"transform\s*:\s*rotate\(-?90deg\))[^}]{0,120}"
                     r"position\s*:\s*fixed|position\s*:\s*fixed[^}]{0,120}"
                     r"writing-mode\s*:\s*vertical", f.text)
    if side:
        out += _one("S-CRAFT-DECOR", f, side.start(), side.group(0)[:50],
                    "A rotated tab pinned to the edge of the viewport. Vertical text is "
                    "slow to read and the tab usually covers content on small screens.")
    tiles = len(re.findall(r"rounded-(?:lg|xl|2xl)[^\"'`]{0,40}bg-\w+-(?:50|100|200)"
                           r"[^\"'`]{0,60}(?:<svg|Icon)", f.text))
    if tiles >= 3:
        m = re.search(r"rounded-(?:lg|xl|2xl)", f.text)
        out += _one("S-CRAFT-DECOR", f, m.start(), f"{tiles} tinted icon tiles",
                    f"{tiles} icons in tinted rounded squares down a list. It is the "
                    "default feature-grid shape, and the tiles add visual weight without "
                    "adding meaning (VIS-006).")
    return out[:4]


@check("S-CRAFT-PALETTE-WARM")
def default_warm_surface(f, p):
    """Cream is the colour a model picks when no palette was decided -- warm
    enough to feel considered, neutral enough to commit to nothing."""
    out = []
    for m in re.finditer(r"background(?:-color)?\s*:\s*(#(?:f[a-f0-9]{5})|rgb\(\s*25[0-5]\s*,"
                         r"\s*2[45]\d\s*,\s*2[23]\d)", f.text, re.I):
        hexv = m.group(1).lower()
        if not hexv.startswith("#"):
            continue
        try:
            r, g, b = (int(hexv[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            continue
        if r > 244 and g > 238 and b < g - 6 and r - b >= 8:
            out += _one("S-CRAFT-PALETTE-WARM", f, m.start(), m.group(0),
                        "A cream or warm off-white page surface. It is the reflex 'tasteful' "
                        "background; if the warmth is a brand decision, name it as a token "
                        "so it reads as one (VIS-001, VIS-006).")
            break
    return out


@check("S-CRAFT-MOTION")
def motion_reflex(f, p):
    """Bounce easing and hover-scaled imagery are the two motions that arrive
    without anyone deciding the interface should move at all."""
    out = []
    b = re.search(r"cubic-bezier\(\s*\.?\d*\.?\d+\s*,\s*-?[\d.]+\s*,\s*[\d.]+\s*,\s*"
                  r"([12]\.[2-9]\d*)\s*\)|(?<![\w-])ease-\[cubic-bezier|animate-bounce\b",
                  f.text)
    if b:
        out += _one("S-CRAFT-MOTION", f, b.start(), b.group(0)[:50],
                    "Bounce or elastic easing. Overshoot reads as playful once and as "
                    "unserious every time after, and it lengthens every interaction it "
                    "touches (NUM-018).")
    img = re.search(r"(?:hover:(?:scale|rotate)-\d+[^\"'`]{0,60}<img|"
                    r"img[^{]{0,40}:hover[^}]{0,80}transform\s*:\s*(?:scale|rotate))", f.text)
    if img:
        out += _one("S-CRAFT-MOTION", f, img.start(), img.group(0)[:50],
                    "An image that scales or rotates on hover. It is a recurring "
                    "generated-UI signature, it does not survive touch, and it costs a "
                    "repaint of the largest element on screen.")
    return out[:3]


@check("S-CRAFT-RHYTHM")
def spacing_rhythm(f, p):
    """When every gap is the same value there is no grouping, and the eye has
    to read the whole page to find its structure (LAW-04)."""
    out = []
    gaps = re.findall(r"(?<![\w-])(?:gap|space-y|space-x|mb|mt|py)-(\d{1,2})\b", f.text)
    if len(gaps) >= 10:
        uniq = set(gaps)
        top = max(set(gaps), key=gaps.count)
        if len(uniq) <= 2 or gaps.count(top) / len(gaps) > 0.8:
            m = re.search(r"(?<![\w-])(?:gap|space-y)-\d", f.text)
            out += _one("S-CRAFT-RHYTHM", f, m.start() if m else 0,
                        f"{len(gaps)} spacing utilities, {len(uniq)} distinct values",
                        "Near-uniform spacing everywhere. Proximity is the cheapest grouping "
                        "signal there is, and using one value throws it away -- related "
                        "things must sit closer than unrelated ones (LAW-04, VIS-002).")
    kickers = len(re.findall(r"<(?:p|span|div)[^>]{0,120}(?:uppercase|tracking-wid)[^>]*>"
                             r"\s*[A-Z][A-Za-z ]{2,24}\s*<", f.text))
    if kickers >= 3:
        m = re.search(r"uppercase", f.text)
        out += _one("S-CRAFT-RHYTHM", f, m.start(), f"{kickers} section kickers",
                    f"{kickers} sections each opening with the same uppercase micro-label. "
                    "It is a rhythm the content did not ask for (VIS-006).")
    numbered = len(re.findall(r">\s*0[1-9]\s*<|[\"'`]0[1-9][\"'`]\s*}", f.text))
    if numbered >= 3:
        m = re.search(r">\s*0[1-9]\s*<", f.text)
        out += _one("S-CRAFT-RHYTHM", f, m.start() if m else 0, f"{numbered} 0N markers",
                    "Zero-padded section numbers (01, 02, 03). A strong editorial signal "
                    "used decoratively, on content with no actual sequence.")
    return out[:3]


@check("S-CRAFT-VOICE", exts=SRC)
def copy_voice(f, p):
    """The house style of generated marketing copy: fragment cadence, em-dashes
    doing the work of sentence structure, and stage directions about itself."""
    out = []
    code = strip_comments(f.text)
    text_nodes = " ".join(re.findall(r">\s*([A-Z][^<>{}\n]{12,160})\s*<", code))
    if not text_nodes:
        return out
    dashes = text_nodes.count("—") + text_nodes.count(" -- ")
    words = max(1, len(text_nodes.split()))
    if dashes >= 3 and dashes / words > 0.012:
        out += _one("S-CRAFT-VOICE", f, code.find("—") if "—" in code else 0,
                    f"{dashes} em-dashes in {words} words of copy",
                    "Em-dashes carrying most of the sentence structure. It is a writing "
                    "tic rather than an interface decision, and it makes scanning harder "
                    "(CONTENT-001).")
    cadence = len(re.findall(r"\bNot\s+[a-z][\w ]{2,30}\.\s+[A-Z]", text_nodes))
    if cadence >= 2:
        out += _one("S-CRAFT-VOICE", f, 0, f"{cadence} 'Not X. Y.' constructions",
                    "The aphoristic 'Not X. Y.' cadence, repeated. It sounds decisive and "
                    "says very little; write what the thing does (CONTENT-001).")
    theater = re.search(r"\b(?:watch as|witness|behold|imagine a world|welcome to the future|"
                        r"this is where .{0,30} begins)\b", text_nodes, re.I)
    if theater:
        out += _one("S-CRAFT-VOICE", f, code.find(theater.group(0)), theater.group(0),
                    "Stage-direction copy narrating the product rather than describing it "
                    "(CONTENT-001).")
    h1 = re.search(r"(?<![\w-])text-(?:7xl|8xl|9xl)\b|font-size\s*:\s*(?:[89]\d|1\d\d)px", f.text)
    if h1:
        out += _one("S-CRAFT-VOICE", f, h1.start(), h1.group(0),
                    "Display type past roughly 72px. Scale substituting for hierarchy -- it "
                    "also forces a second, unrelated layout at narrow widths (VIS-002).")
    return out[:4]
