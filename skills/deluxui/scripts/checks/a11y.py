"""Semantics, names, focus, contrast and target size."""
from __future__ import annotations
import re
from . import check, finding
from ._util import Tag, ancestors, contrast_ratio, parse_color, tw_color

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")
DESTRUCTIVE = re.compile(r"\b(delete|remove|destroy|erase|wipe|revoke|cancel subscription|"
                         r"deactivate|close account|pay|purchase|charge|confirm)\b", re.I)
NAMED = ("aria-label", "aria-labelledby", "aria-describedby", "title", "alt", "label")


def _named(t: Tag) -> bool:
    return t.has(*NAMED) or bool(t.attr("aria-label") or t.attr("aria-labelledby"))


def _text_of(t: Tag) -> str:
    """Visible-ish text: markup stripped. JSX expressions count as possible text."""
    return re.sub(r"<[^>]*>", " ", t.inner or "").strip()


def _only_graphics(t: Tag) -> bool:
    """True when the element's content is exclusively icon-like markup."""
    inner = t.inner or ""
    if not inner.strip():
        return False
    if "{" in inner:            # an expression may render text -- do not guess
        return False
    stripped = re.sub(r"<[^>]*>", "", inner).strip()
    if stripped:
        return False
    return bool(re.search(r"<\s*(svg|Icon|[A-Z]\w*Icon|i\b|use|path)", inner))


# ------------------------------------------------------------------ semantics
@check("S-A11Y-ALT", exts=SRC)
def alt_text(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() not in ("img", "image"):
            continue
        if t.attr("aria-hidden") or t.attr("role") in ("presentation", "none"):
            continue
        if "alt" in t.attrs:
            continue
        out.append(finding("S-A11Y-ALT", f, t.line, t.raw,
                           'Add alt. Use alt="" only when the image is decorative '
                           "and the surrounding text already carries the meaning.",
                           "high"))
    return out


@check("S-A11Y-ICONBTN", exts=SRC)
def icon_only_button(f, p):
    out = []
    for t in f.tags:
        if not t.is_interactive() or t.self_closing:
            continue
        if _named(t) or not _only_graphics(t):
            continue
        if re.search(r"sr-only|visually-hidden|screen-reader", t.inner or ""):
            continue
        out.append(finding("S-A11Y-ICONBTN", f, t.line, t.raw,
                           "An icon-only control needs an accessible name: aria-label, "
                           "or visible text hidden with sr-only. Speech users activate "
                           "controls by their name.", "medium"))
    return out


@check("S-A11Y-LABEL", exts=SRC)
def input_label(f, p):
    out = []
    labelled = set()
    for t in f.tags:
        if t.name.lower() == "label":
            v = t.attr("for", "htmlFor")
            if v:
                labelled.add(v.strip("{}\"' "))
    wrapped = re.search(r"<(?:FormField|FormItem|FormLabel|FormControl)\b", f.text)
    has_label_cmp = re.search(r"<Label\b|<FormLabel\b", f.text)
    for t in f.tags:
        n = t.name
        if n not in ("input", "select", "textarea"):
            # Design-system wrappers (shadcn <Input>, Radix <Select>) are usually
            # named by a sibling <Label htmlFor>. The scanner cannot follow that
            # link, so reporting it would be a guess.
            continue
        if wrapped or has_label_cmp:
            continue
        if (t.attr("type") or "").lower() in ("hidden", "submit", "button", "reset", "image"):
            continue
        if _named(t) or t.attr("placeholder"):
            continue
        tid = (t.attr("id") or "").strip("{}\"' ")
        if tid and tid in labelled:
            continue
        if any(a.name.lower() == "label" for a in ancestors(t)):
            continue
        out.append(finding("S-A11Y-LABEL", f, t.line, t.raw,
                           "Associate a persistent visible label: <label for=id>, or "
                           "aria-label if the label is genuinely visual. A label that "
                           "disappears on entry is not a label.", "medium"))
    return out


@check("S-A11Y-PLACEHOLDER", exts=SRC)
def placeholder_as_label(f, p):
    out = []
    labelled = {(t.attr("for", "htmlFor") or "").strip("{}\"' ")
                for t in f.tags if t.name.lower() == "label"}
    for t in f.tags:
        if t.name.lower() not in ("input", "textarea") or not t.attr("placeholder"):
            continue
        if _named(t):
            continue
        tid = (t.attr("id") or "").strip("{}\"' ")
        if tid and tid in labelled:
            continue
        if any(a.name.lower() == "label" for a in ancestors(t)):
            continue
        out.append(finding("S-A11Y-PLACEHOLDER", f, t.line, t.raw,
                           "Placeholder is the only label here. It vanishes as soon as "
                           "the user types, taking the field's meaning with it. Add a "
                           "real label and keep the placeholder for format hints.", "high"))
    return out


@check("S-A11Y-DIVCLICK", exts=SRC)
def div_click(f, p):
    out = []
    for t in f.tags:
        PRESENTATIONAL = ("div", "span", "li", "td", "tr", "section", "article", "p")
        WRAPPERS = ("Card", "Box", "Flex", "Stack", "Paper", "Panel", "Tile",
                    "Row", "Container", "Surface", "CardContent", "CardHeader")
        if t.name.lower() not in PRESENTATIONAL and t.name not in WRAPPERS:
            continue
        if not t.has("onClick", "onclick", "on:click", "@click"):
            continue
        if t.attr("role") and t.has("tabIndex", "tabindex"):
            continue
        out.append(finding("S-A11Y-DIVCLICK", f, t.line, t.raw,
                           f"<{t.name}> renders a plain container, so this click target is "
                           "invisible to keyboard and assistive technology. Use a <button> "
                           "(or <a> for navigation) -- and if it already contains buttons, "
                           "make the inner action the only target instead.",
                           "high" if t.name.lower() in PRESENTATIONAL else "medium"))
    return out


@check("S-A11Y-HREFHASH", exts=SRC)
def fake_link(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() != "a":
            continue
        href = (t.attr("href") or "").strip()
        if href in ("#", "javascript:void(0)", "javascript:;"):
            out.append(finding("S-A11Y-HREFHASH", f, t.line, t.raw,
                               "This is an action wearing a link's clothes. Use <button>. "
                               "Links must go somewhere -- users middle-click and bookmark them.",
                               "high"))
    return out


@check("S-A11Y-TABINDEX", exts=SRC)
def positive_tabindex(f, p):
    out = []
    for t in f.tags:
        v = t.attr("tabIndex", "tabindex")
        if v is None:
            continue
        m = re.search(r"-?\d+", str(v))
        if m and int(m.group()) > 0:
            out.append(finding("S-A11Y-TABINDEX", f, t.line, t.raw,
                               "A positive tabindex reorders focus for the whole page and "
                               "desynchronises from visual order. Use 0, or fix the DOM order.",
                               "high"))
    return out


@check("S-A11Y-ARIAHIDDEN", exts=SRC)
def aria_hidden_focusable(f, p):
    out = []
    for t in f.tags:
        if str(t.attr("aria-hidden") or "").strip("{}\"' ").lower() not in ("true", ""):
            continue
        if t.attr("aria-hidden") is None:
            continue
        bad = t.is_interactive() or any(c.is_interactive() for c in t.children)
        if bad:
            out.append(finding("S-A11Y-ARIAHIDDEN", f, t.line, t.raw,
                               "aria-hidden on something focusable creates a control a "
                               "screen reader cannot see but a keyboard can still reach. "
                               "Remove aria-hidden, or remove it from the tab order too.",
                               "medium"))
    return out


@check("S-A11Y-NESTED", exts=SRC)
def nested_interactive(f, p):
    out = []
    for t in f.tags:
        if not t.is_interactive():
            continue
        for a in ancestors(t):
            if a.is_interactive():
                out.append(finding("S-A11Y-NESTED", f, t.line, t.raw,
                                   f"<{t.name}> is nested inside interactive <{a.name}>. "
                                   "Activating the inner control also fires the outer one. "
                                   "Move the action out of the clickable container.", "medium"))
                break
    return out


@check("S-A11Y-HEADING", exts=SRC)
def heading_skips(f, p):
    out, prev = [], None
    for t in f.tags:
        m = re.fullmatch(r"[hH]([1-6])", t.name)
        if not m:
            continue
        lvl = int(m.group(1))
        if prev is not None and lvl > prev + 1:
            out.append(finding("S-A11Y-HEADING", f, t.line, t.raw,
                               f"Heading jumps h{prev} to h{lvl}. Screen-reader users "
                               "navigate by this outline; a gap reads as missing content. "
                               "Style the size, keep the level.", "low"))
        prev = lvl
    return out


@check("S-A11Y-AUTOFOCUS", exts=SRC)
def autofocus_destructive(f, p):
    out = []
    for t in f.tags:
        if not t.has("autoFocus", "autofocus"):
            continue
        label = (t.attr("aria-label") or "") + " " + _text_of(t)
        if DESTRUCTIVE.search(label):
            out.append(finding("S-A11Y-AUTOFOCUS", f, t.line, t.raw,
                               "Autofocusing a destructive confirm means a stray Enter "
                               "commits it. Focus the dialog or the safe option instead.",
                               "medium"))
    return out


# ------------------------------------------------------------------ focus
_FOCUS_KEEP = re.compile(
    # Any focus-conditional utility counts as a focus treatment: a background or
    # text-colour change is as visible as a ring. Whether it is visible *enough*
    # is a contrast question, and only the runtime tier can answer that.
    # Deliberately excludes outline-none / outline-hidden: those are the tokens
    # being flagged, and matching them here made the check silently pass on the
    # exact defect it exists to find.
    r"focus-visible[:\-]|focus:(?!outline-(?:none|hidden))[\w\[-]|"
    r"group-focus|focus-within|:focus\b|&:focus|ring-offset|outline-offset|"
    # Radix-style roving focus marks the active item with a data attribute.
    r"data-\[highlighted\]|data-\[state=|data-\[focus|data-highlighted|"
    r"aria-selected:|aria-expanded:")


@check("S-FOCUS-OUTLINE")
def focus_outline(f, p):
    """Tailwind v4 split these: `outline-hidden` keeps the control visible in
    forced-colors mode, `outline-none` genuinely sets outline-style:none. Both
    need a replacement; only one of them also breaks high-contrast users."""
    out = []
    if f.css:
        for m in re.finditer(r"outline\s*:\s*(none|0)\s*[;}]", f.css, re.I):
            line = f.css[:m.start()].count("\n") + 1
            if _FOCUS_KEEP.search(f.css[max(0, m.start() - 600):m.start() + 600]):
                continue
            out.append(finding("S-FOCUS-OUTLINE", f, line, m.group(0),
                               "Focus outline removed with no visible replacement. Add a "
                               ":focus-visible style -- it shows for keyboard users without "
                               "putting a ring on every mouse click.", "high"))
        return out
    for m in re.finditer(r"(?:[\w-]+:)?outline-(none|hidden)\b", f.text):
        line = f.text[:m.start()].count("\n") + 1
        start = f.text.rfind("class", max(0, m.start() - 400), m.start())
        window = (f.text[start if start > 0 else max(0, m.start() - 200): m.start()]
                  + f.text[m.end(): m.end() + 300])
        if _FOCUS_KEEP.search(window):
            continue
        if m.group(1) == "none" and p.tailwind_major >= 4:
            msg = ("Tailwind v4 changed this: `outline-none` now sets outline-style:none, so "
                   "the indicator disappears even in forced-colors mode. If you only meant to "
                   "swap in your own ring, use `outline-hidden` and add focus-visible:ring-2.")
        elif m.group(1) == "none":
            msg = ("`outline-none` (v3) leaves a transparent outline for forced-colors mode, "
                   "but nothing visible replaces it here. Add focus-visible:ring-2. Note that "
                   "in v4 this utility is renamed `outline-hidden`.")
        else:
            msg = ("`outline-hidden` hides the default outline and nothing replaces it. "
                   "Add focus-visible:ring-2 -- v4's default ring is 1px, so state the width.")
        out.append(finding("S-FOCUS-OUTLINE", f, line, window.strip()[:120], msg, "high"))
    return out


# ------------------------------------------------------------------ contrast
def _classes_colors(classes, cssvars):
    fg = bg = None
    for c in classes:
        if re.match(r"^(?:[\w@\[\]-]+:)*text-", c) and fg is None:
            fg = tw_color(c, cssvars)
        elif re.match(r"^(?:[\w@\[\]-]+:)*bg-", c) and bg is None:
            bg = tw_color(c, cssvars)
    return fg, bg


@check("S-CONTRAST-PAIR", requires=lambda p: bool(p.cssvars))
def contrast_pair(f, p):
    out = []
    if f.css:
        for m in re.finditer(r"\{([^{}]*)\}", f.css):
            body = m.group(1)
            fgm = re.search(r"(?<!-)\bcolor\s*:\s*([^;]+)", body)
            bgm = re.search(r"background(?:-color)?\s*:\s*([^;]+)", body)
            if not (fgm and bgm):
                continue
            fg = parse_color(fgm.group(1), p.cssvars)
            bg = parse_color(bgm.group(1), p.cssvars)
            if not (fg and bg):
                continue
            r = contrast_ratio(fg, bg)
            if r < 4.5:
                line = f.css[:m.start()].count("\n") + 1
                out.append(finding("S-CONTRAST-PAIR", f, line,
                                   f"{fgm.group(1).strip()} on {bgm.group(1).strip()}",
                                   f"Contrast {r:.2f}:1 is below the 4.5:1 floor for normal "
                                   "text (NUM-001). Large text may use 3:1 -- confirm the "
                                   "rendered size first.", "medium"))
        return out
    for t in f.tags:
        cls = t.classes()
        if not cls:
            continue
        fg, bg = _classes_colors(cls, p.cssvars)
        if not fg:
            continue
        conf = "medium"
        if not bg:      # look a short way up for a surface; further than that and
            for depth, a in enumerate(ancestors(t)):   # the guess stops being useful
                if depth >= 3:
                    break
                _, abg = _classes_colors(a.classes(), p.cssvars)
                if abg:
                    bg, conf = abg, "low"
                    break
        if not bg:
            continue                    # unresolvable -> silent, reported as NOT_RUN scope
        r = contrast_ratio(fg, bg)
        if r < 4.5:
            out.append(finding("S-CONTRAST-PAIR", f, t.line,
                               " ".join(c for c in cls if "text-" in c or "bg-" in c),
                               f"Contrast {r:.2f}:1 against the nearest resolvable surface, "
                               "below the 4.5:1 floor for normal text (NUM-001). Verify with "
                               "the runtime tier -- the real background may differ.", conf))
    return out


# ------------------------------------------------------------------ target size
_SIZE = re.compile(r"^(?:\w+:)*(h|w|size)-(\d+(?:\.\d+)?|px)$")


def _px(token):
    m = _SIZE.match(token)
    if not m:
        return None, None
    v = m.group(2)
    return m.group(1), (1.0 if v == "px" else float(v) * 4)


@check("S-TARGET-SIZE", exts=SRC)
def target_size(f, p):
    out = []
    if not p.has_tailwind:
        return out
    for t in f.tags:
        if not t.is_interactive():
            continue
        dims = {}
        for c in t.classes():
            axis, px = _px(c)
            if axis:
                dims.setdefault(axis, px)
        if "size" in dims:
            dims["h"] = dims["w"] = dims["size"]
        if "h" not in dims and "w" not in dims:
            continue                    # padding-sized control -- cannot tell from source
        small = min(v for k, v in dims.items() if k in ("h", "w"))
        if small < 24:
            out.append(finding("S-TARGET-SIZE", f, t.line, " ".join(t.classes())[:100],
                               f"Hit area about {small:.0f}px, under the 24px floor "
                               "(NUM-004). Grow the target or add spacing that satisfies "
                               "the SC 2.5.8 exception.", "low"))
        elif small < 44:
            out.append(finding("S-TARGET-SIZE", f, t.line, " ".join(t.classes())[:100],
                               f"Hit area about {small:.0f}px. Meets the 24px standard but "
                               "is under the 44px coarse-pointer default (NUM-005). Fine "
                               "for dense desktop UI; check it on a phone.", "low"))
    return out
