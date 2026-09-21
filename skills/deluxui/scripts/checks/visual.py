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


@check("S-SLOP-CARDNEST", exts=SRC)
def nested_cards(f, p):
    out = []
    CARD = re.compile(r"(?:^|\s)(?:rounded-\w+|border|shadow)\b")
    for t in f.tags:
        if not CARD.search(" ".join(t.classes())):
            continue
        depth = 1
        for a in (t.parent, getattr(t.parent, "parent", None),
                  getattr(getattr(t.parent, "parent", None), "parent", None)):
            if a is not None and CARD.search(" ".join(a.classes())):
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
