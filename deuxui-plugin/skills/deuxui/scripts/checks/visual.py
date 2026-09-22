"""Motion, hover dependence, dialogs, and the AI-tell catalogue."""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")

REDUCED = re.compile(r"prefers-reduced-motion|motion-reduce:|motion-safe:|"
                     r"useReducedMotion|shouldReduceMotion")


@check("S-MOTION-REDUCE", requires=lambda p: "prefers-reduced-motion" not in p.css_text)
def reduced_motion(f, p):
    """Vestibular disorders are not a niche. Anything that moves needs an
    honest still version -- including View Transitions and @starting-style,
    which people forget are animations at all."""
    out = []
    if REDUCED.search(f.text):
        return out
    hits = list(re.finditer(
        r"(?<![\w-])(animate-(?!none)[\w-]+|transition-(?:all|transform)|"
        r"startViewTransition|@starting-style|::view-transition|"
        r"animation\s*:\s*(?!none)|@keyframes)\b", f.text))
    if not hits:
        return out
    m = hits[0]
    line = f.text[:m.start()].count("\n") + 1
    what = m.group(1)
    extra = (" View Transitions animate by default -- wrap them in the same query."
             if "view-transition" in what.lower() or "startView" in what else "")
    out.append(finding("S-MOTION-REDUCE", f, line, f"{what} ({len(hits)} motion uses in file)",
                       "No reduced-motion path anywhere in this file. Honour "
                       "prefers-reduced-motion (Tailwind: the motion-reduce: variant) and "
                       "replace movement with an immediate state change, not a slower "
                       f"animation.{extra}", "high"))
    return out


@check("S-HOVER-ONLY", exts=SRC)
def hover_only(f, p):
    """Hover does not exist on touch and does not exist for keyboard. If a
    control only appears on hover, a large share of users never find it.

    Judged per element: a focus: utility on some other element nearby says
    nothing about whether this one is reachable."""
    REVEAL = re.compile(r"^(?:group-)?hover:(?:opacity-100|visible|flex|block|"
                        r"inline-flex|scale-100|translate-y-0)$")
    KEEP = re.compile(r"^(?:group-)?(?:focus|focus-visible|focus-within)[:-]|"
                      r"^group-focus")
    out = []
    for t in f.tags:
        cls = t.classes()
        if not any(REVEAL.match(c) for c in cls):
            continue
        if any(KEEP.match(c) for c in cls):
            continue
        out.append(finding("S-HOVER-ONLY", f, t.line, " ".join(cls)[:100],
                           "Revealed on hover only. Mirror it with focus-visible: or "
                           "group-focus-within: so keyboard users reach it, and make sure "
                           "touch users have another route to the same action "
                           "(VIS-005, COMP-011).", "medium"))
    return out


@check("S-MODAL-NATIVE", exts=SRC)
def hand_rolled_modal(f, p):
    """A hand-built modal has to re-implement focus trapping, Escape, inert
    background, scroll locking and the top layer. <dialog> and the popover
    attribute do all of it in the platform, correctly."""
    out = []
    for t in f.tags:
        role = (t.attr("role") or "").strip("{}\"' ")
        if role not in ("dialog", "alertdialog"):
            continue
        win = f.text[max(0, t.start - 500):t.end + 1500]
        if re.search(r"<dialog|showModal|\bpopover\b|Radix|@headlessui|DialogPrimitive|@base-ui|"
                     r"vaul|react-aria", win, re.I):
            continue
        missing = []
        if not re.search(r"\binert\b|aria-hidden", win):
            missing.append("inert background")
        if not re.search(r"Escape|keydown|onKeyDown", win):
            missing.append("Escape to dismiss")
        if not re.search(r"focus\(\)|autoFocus|initialFocus|focusTrap", win):
            missing.append("initial focus")
        if not t.has("aria-label", "aria-labelledby"):
            missing.append("accessible name")
        if not missing:
            continue
        out.append(finding("S-MODAL-NATIVE", f, t.line, t.raw,
                           "Hand-rolled dialog missing " + ", ".join(missing) +
                           ". Prefer <dialog> with showModal() (top layer, ::backdrop, "
                           "Escape and focus containment for free) or the popover attribute "
                           "for non-modal surfaces (COMP-007, COMP-008, A11Y-004).", "medium"))
    return out


# ------------------------------------------------------------------ AI tells
@check("S-SLOP-GRADIENT")
def gradients(f, p):
    out = []
    hits = list(re.finditer(r"bg-gradient-to-|bg-linear-to-|linear-gradient\(|"
                            r"bg-clip-text", f.text))
    if len(hits) < 3:
        return out
    m = hits[0]
    line = f.text[:m.start()].count("\n") + 1
    purple = bool(re.search(r"(from|via|to)-(purple|violet|indigo|fuchsia)-\d+", f.text)
                  and re.search(r"(from|via|to)-(blue|cyan|sky)-\d+", f.text))
    tail = (" The purple-to-blue gradient in particular is the single most "
            "recognisable generated-UI signature." if purple else "")
    out.append(finding("S-SLOP-GRADIENT", f, line, f"{len(hits)} gradient uses in one file",
                       "Gradients used as decoration rather than meaning. Pick one surface "
                       f"that earns it and let the rest be flat (VIS-006).{tail}", "medium"))
    return out


@check("S-SLOP-BLUR")
def glass(f, p):
    out = []
    hits = list(re.finditer(r"backdrop-blur|backdrop-filter\s*:\s*blur", f.text))
    if len(hits) < 3:
        return out
    m = hits[0]
    out.append(finding("S-SLOP-BLUR", f, f.text[:m.start()].count("\n") + 1,
                       f"{len(hits)} frosted-glass surfaces",
                       "Glass everywhere destroys the contrast you need for text and costs "
                       "real paint time on low-end devices. Reserve it for one floating "
                       "layer and verify contrast against the worst background behind it.",
                       "medium"))
    return out


def _css_card_classes(css: str) -> set[str]:
    """Class names whose own rule makes them a card: a radius plus a boundary.
    Without this the check only ever works on utility-first codebases, and a
    semantic `.card` nested three deep sails through."""
    found = set()
    for m in re.finditer(r"\.([\w-]+)\s*(?:,[^{]*)?\{([^{}]*)\}", css):
        body = m.group(2)
        if re.search(r"border-radius\s*:", body) and \
           re.search(r"box-shadow\s*:|border(?:-\w+)?\s*:", body):
            found.add(m.group(1))
    return found


@check("S-SLOP-CARDNEST", exts=SRC)
def nested_cards(f, p):
    out = []
    CARD = re.compile(r"(?:^|\s)(?:rounded-\w+|border|shadow)\b")
    css_cards = _css_card_classes(p.css_text or "") | _css_card_classes(f.text)

    def is_card(tag):
        cls = tag.classes()
        return bool(CARD.search(" ".join(cls))) or bool(set(cls) & css_cards)

    for t in f.tags:
        if not is_card(t):
            continue
        depth = 1
        for a in (t.parent, getattr(t.parent, "parent", None),
                  getattr(getattr(t.parent, "parent", None), "parent", None)):
            if a is not None and is_card(a):
                depth += 1
        if depth >= 3:
            out.append(finding("S-SLOP-CARDNEST", f, t.line, " ".join(t.classes())[:90],
                               f"Card nested {depth} deep. Each border repeats a boundary the "
                               "eye already had, and none of them means anything. Keep one "
                               "container and use spacing for the inner grouping (VIS-006).",
                               "medium"))
    return out


@check("S-SLOP-EMOJI", exts=SRC)
def emoji_ui(f, p):
    out = []
    EMOJI = re.compile("[\U0001F300-\U0001FAFF✀-➿☀-⛿]")
    for t in f.tags:
        if t.name.lower() not in ("h1", "h2", "h3", "h4", "button", "a", "label"):
            continue
        txt = re.sub(r"<[^>]*>", "", t.inner or "")
        if EMOJI.search(txt):
            out.append(finding("S-SLOP-EMOJI", f, t.line, txt.strip()[:80],
                               "Emoji in a heading or control. Screen readers read the full "
                               "Unicode name aloud, they render differently per platform, and "
                               "they rarely survive translation. Use a real icon with a label.",
                               "high"))
    return out


@check("S-SLOP-COPY")
def placeholder_copy(f, p):
    out = []
    PAT = re.compile(r"lorem ipsum|dolor sit amet|your company|acme (?:inc|corp)|"
                     r"john doe|jane doe|example\.com/your|replace this|"
                     r"elevate your \w+|unlock the power of|take your \w+ to the next level|"
                     r"seamlessly integrate|revolutioni[sz]e your", re.I)
    for m in PAT.finditer(f.text):
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-SLOP-COPY", f, line, m.group(0),
                           "Placeholder or stock marketing copy still in the source. Real "
                           "copy is content, not filler -- and filler hides the layout "
                           "problems that real content would expose (CONTENT-003).", "high"))
    return out


@check("S-SLOP-UNIFORM")
def uniform_treatment(f, p):
    """When every surface gets the same heavy radius and shadow there is no
    hierarchy left -- everything shouts, so nothing reads as primary."""
    out = []
    big = len(re.findall(r"(?<![\w-])(?:rounded-(?:3xl|4xl|full)|shadow-(?:2xl|xl))\b", f.text))
    total = len(re.findall(r"(?<![\w-])(?:rounded-[\w]+|shadow-[\w]+)\b", f.text))
    if total >= 8 and big / total > 0.6:
        out.append(finding("S-SLOP-UNIFORM", f, 1,
                           f"{big} of {total} radius/shadow utilities are the heaviest step",
                           "Uniform maximum radius and shadow flattens hierarchy: if every "
                           "card floats, none of them is the important one. Reserve the "
                           "heaviest treatment for the one surface that should dominate.",
                           "low"))
    return out


# ------------------------------------------------------------------ typographic tells
@check("S-SLOP-EYEBROW")
def eyebrow_label(f, p):
    """The small uppercase wide-tracked label above a heading. One is a design
    choice; one above every section is a rhythm nobody asked for, and it is a
    reliable signature of generated marketing pages."""
    out = []
    # The same treatment is written two ways: Tailwind utilities on the element,
    # or a semantic class whose rule lives in a stylesheet. Catch both, or this
    # only ever works on utility-first codebases.
    if f.css:
        for m in re.finditer(r"\{([^{}]*)\}", f.css):
            body = m.group(1)
            if not re.search(r"text-transform\s*:\s*uppercase", body):
                continue
            tracked = re.search(r"letter-spacing\s*:\s*0?\.(?:0[89]|[1-9])\d*\s*em", body)
            small = re.search(r"font-size\s*:\s*(?:1[0-2]px|0\.[5-7]\d*rem)", body)
            if not (tracked and small):
                continue
            out.append(finding("S-SLOP-EYEBROW", f, f.css[:m.start()].count("\n") + 1,
                               " ".join(body.split())[:70],
                               "An uppercase, wide-tracked, small-size rule -- the eyebrow "
                               "label above a heading. It adds hierarchy carrying no "
                               "information, and uppercase plus wide tracking is measurably "
                               "slower to read (VIS-006, VIS-002).", "low"))
        return out[:4]
    hits = []
    for t in f.tags:
        cls = " ".join(t.classes())
        style = str(t.attr("style") or "")
        upper = "uppercase" in cls or "text-transform:uppercase" in style.replace(" ", "")
        tracked = re.search(r"tracking-(?:wide|wider|widest)|letter-spacing\s*:\s*0?\.[12]",
                            cls + style)
        small = re.search(r"text-(?:xs|\[1[01]px\])|font-size\s*:\s*1[01]px", cls + style)
        if upper and (tracked or small):
            hits.append(t)
    if len(hits) >= 1:
        t = hits[0]
        n = len(hits)
        out.append(finding("S-SLOP-EYEBROW", f, t.line, " ".join(t.classes())[:80],
                           f"{'An' if n == 1 else f'{n}'} uppercase wide-tracked micro-label "
                           "above the heading. It adds a line of hierarchy that carries no "
                           "information, and uppercase plus wide tracking is measurably "
                           "slower to read (VIS-006, VIS-002).",
                           "low" if n == 1 else "medium"))
    return out


@check("S-TYPE-TRACKING")
def extreme_tracking(f, p):
    """Negative tracking on display type is a look. Past about -0.03em it starts
    closing counters and colliding diagonals, and at small sizes it is simply
    harder to read."""
    out = []
    for m in re.finditer(r"letter-spacing\s*:\s*(-0?\.\d+)\s*em|"
                         r"tracking-\[(-0?\.\d+)em\]|(-tracking-(?:tight|tighter))",
                         f.text):
        raw = m.group(1) or m.group(2)
        if raw is not None:
            if float(raw) > -0.035:
                continue
            desc = f"{raw}em"
        else:
            if "tighter" not in m.group(3):
                continue
            desc = m.group(3)
        out.append(finding("S-TYPE-TRACKING", f, f.text[:m.start()].count("\n") + 1,
                           m.group(0),
                           f"Tracking of {desc} closes letter counters and collides "
                           "diagonals. Tighten display type if you must, but check it at "
                           "the smallest size it renders (VIS-006).", "low"))
    return out[:6]


@check("S-SLOP-PALETTE")
def generated_palette(f, p):
    """Violet-to-blue is the palette a model reaches for when no palette was
    decided. A genuinely violet brand is fine -- what gives it away is the
    combination used as the whole identity, with no brand token behind it."""
    out = []
    cool = len(re.findall(r"\b(?:violet|purple|indigo|fuchsia)-[456]00\b", f.text))
    blue = len(re.findall(r"\b(?:blue|sky|cyan)-[456]00\b", f.text))
    hexes = re.findall(r"#(?:8b5cf6|a855f7|6366f1|7c3aed|3b82f6|0ea5e9|06b6d4)\b",
                       f.text, re.I)
    branded = re.search(r"--color-(?:brand|primary|accent)\b|\bbrand-\d00\b", f.text)
    score = (cool >= 2 and blue >= 1) or len(hexes) >= 3
    if not score or branded:
        return out
    m = re.search(r"\b(?:violet|purple|indigo|fuchsia)-[456]00\b|#(?:8b5cf6|6366f1|3b82f6)",
                  f.text, re.I)
    out.append(finding("S-SLOP-PALETTE", f, f.text[:m.start()].count("\n") + 1,
                       m.group(0),
                       "The violet-and-blue palette, used as the identity with no brand "
                       "token behind it. It is the most recognisable generated-UI signature "
                       "there is. Pick colours from the product, then name them as tokens "
                       "(VIS-001, VIS-006).", "low"))
    return out
