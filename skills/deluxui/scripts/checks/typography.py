"""Reading quality: size, measure, leading, alignment and the space around text.

These are the defects that make a page tiring rather than broken, so they rarely
get filed — and they are disproportionately the ones that hurt readers with low
vision, dyslexia, or a small phone in bright sunlight.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")

# Tailwind's default type scale, in px, for the sizes that matter here.
TW_TEXT_PX = {"text-\\[10px\\]": 10, "text-\\[11px\\]": 11, "text-2xs": 10, "text-xs": 12}


def _line(t, pos):
    return t[:pos].count("\n") + 1


def _css_rules(text):
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        yield m.start(), m.group(1).strip(), m.group(2)


@check("S-TYPE-TINY")
def tiny_text(f, p):
    """Below about 12px, text stops being readable for a large share of people
    and cannot be fixed by zooming on a fixed-layout page (NUM-015)."""
    out = []
    if f.ext in CSS:
        for pos, sel, body in _css_rules(f.text):
            m = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
            if not m or float(m.group(1)) >= 12:
                continue
            out.append(finding("S-TYPE-TINY", f, _line(f.text, pos),
                               f"{sel[:36]} {{ font-size: {m.group(1)}px }}",
                               f"{m.group(1)}px is below the ~12px floor where text stops "
                               "being comfortably readable. Legal and caption text is where "
                               "this always creeps in, and it is exactly the text people "
                               "most need to read (NUM-015).", "medium"))
        return out[:8]
    for m in re.finditer(r"(?<![\w-])text-\[(\d+(?:\.\d+)?)px\]", f.text):
        if float(m.group(1)) >= 12:
            continue
        out.append(finding("S-TYPE-TINY", f, _line(f.text, m.start()), m.group(0),
                           f"{m.group(1)}px text. Below ~12px this is unreadable for many "
                           "people and no zoom fixes a fixed layout (NUM-015).", "medium"))
    return out[:8]


@check("S-TYPE-MEASURE")
def line_length(f, p):
    """Past about 75 characters the eye loses the line return. The fix is a
    max-width in ch, not a narrower window (NUM-016)."""
    out = []
    if f.ext in CSS:
        for pos, sel, body in _css_rules(f.text):
            m = re.search(r"max-width\s*:\s*(\d+(?:\.\d+)?)(ch|rem|px)", body)
            if not m:
                continue
            v, unit = float(m.group(1)), m.group(2)
            ch = v if unit == "ch" else (v * 2.2 if unit == "rem" else v / 8.0)
            if ch <= 80:
                continue
            out.append(finding("S-TYPE-MEASURE", f, _line(f.text, pos),
                               f"{sel[:30]} {{ max-width: {m.group(1)}{unit} }}",
                               f"About {ch:.0f} characters per line for reading content. "
                               "Past ~75 the return sweep starts failing and people re-read "
                               "lines (NUM-016).", "low"))
        return out[:6]
    for m in re.finditer(r"(?<![\w-])max-w-(\[(\d+)px\]|screen-2xl|full)\b", f.text):
        win = f.text[max(0, m.start() - 200):m.start() + 200]
        if not re.search(r"\bprose\b|article|<p[\s>]|paragraph|body-copy", win, re.I):
            continue
        out.append(finding("S-TYPE-MEASURE", f, _line(f.text, m.start()), m.group(0),
                           "Reading content with no character-based measure. Cap it around "
                           "65-75ch so the line return stays findable (NUM-016).", "low"))
    return out[:6]


@check("S-TYPE-LEADING")
def tight_leading(f, p):
    """Line height under about 1.4 on body copy crowds descenders into the next
    line, and WCAG's text-spacing criterion expects 1.5 to be survivable."""
    out = []
    if f.ext in CSS:
        for pos, sel, body in _css_rules(f.text):
            m = re.search(r"line-height\s*:\s*(\d?\.\d+|1)\s*(?:;|$)", body)
            fs = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
            if not m:
                continue
            lh = float(m.group(1))
            if lh >= 1.4 or (fs and float(fs.group(1)) >= 24):
                continue      # display type may legitimately be tighter
            out.append(finding("S-TYPE-LEADING", f, _line(f.text, pos),
                               f"{sel[:30]} {{ line-height: {m.group(1)} }}",
                               f"Leading of {lh} on body-sized text crowds the lines. Aim for "
                               "1.5, which is also what the text-spacing criterion expects "
                               "you to survive (NUM-010).", "low"))
        return out[:6]
    for m in re.finditer(r"(?<![\w-])leading-(none|tight)\b", f.text):
        win = f.text[max(0, m.start() - 160):m.start() + 160]
        if re.search(r"text-(?:3xl|4xl|5xl|6xl|7xl|8xl|9xl)|<h1|<h2", win):
            continue
        out.append(finding("S-TYPE-LEADING", f, _line(f.text, m.start()), m.group(0),
                           f"`leading-{m.group(1)}` on text that is not display-sized. "
                           "Descenders collide with the next line (NUM-010).", "low"))
    return out[:6]


@check("S-TYPE-ALLCAPS")
def all_caps_body(f, p):
    """Uppercase removes word-shape, which is one of the cues fluent readers
    rely on. Fine for a two-word label, punishing for a sentence."""
    out = []
    if f.ext in CSS:
        for pos, sel, body in _css_rules(f.text):
            if not re.search(r"text-transform\s*:\s*uppercase", body):
                continue
            fs = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
            if fs and float(fs.group(1)) <= 13:
                continue      # a small label is the legitimate use
            out.append(finding("S-TYPE-ALLCAPS", f, _line(f.text, pos), sel[:50],
                               "Uppercase applied at body size. It strips word shape and "
                               "slows reading measurably; keep it for short labels.", "low"))
        return out[:5]
    for t in f.tags:
        if t.name.lower() not in ("p", "li", "blockquote", "td"):
            continue
        if "uppercase" not in " ".join(t.classes()):
            continue
        out.append(finding("S-TYPE-ALLCAPS", f, t.line, " ".join(t.classes())[:60],
                           "Uppercase on a block of running text. It removes the word shapes "
                           "readers navigate by.", "low"))
    return out[:5]


@check("S-TYPE-JUSTIFY")
def justified_text(f, p):
    """Justification without hyphenation opens rivers of white space, and those
    rivers are a documented problem for dyslexic readers."""
    out = []
    pat = r"text-align\s*:\s*justify" if f.ext in CSS else r"(?<![\w-])text-justify\b"
    for m in re.finditer(pat, f.text):
        win = f.text[max(0, m.start() - 200):m.start() + 200]
        if re.search(r"hyphens\s*:\s*auto|hyphens-auto", win):
            continue
        out.append(finding("S-TYPE-JUSTIFY", f, _line(f.text, m.start()), m.group(0),
                           "Justified text with no hyphenation. The uneven word spacing "
                           "creates vertical rivers that are hard to read past, particularly "
                           "for dyslexic readers. Prefer ragged-right.", "low"))
    return out[:4]


@check("S-TYPE-TRACKING-WIDE")
def wide_tracking_body(f, p):
    """Wide tracking pulls letters out of words. It reads as styling at label
    size and as damage at paragraph size."""
    out = []
    if f.ext in CSS:
        for pos, sel, body in _css_rules(f.text):
            m = re.search(r"letter-spacing\s*:\s*0?\.(\d+)\s*em", body)
            fs = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
            if not m or int(m.group(1)[:2].ljust(2, "0")) < 10:
                continue
            if fs and float(fs.group(1)) <= 13:
                continue
            out.append(finding("S-TYPE-TRACKING-WIDE", f, _line(f.text, pos), sel[:40],
                               f"Letter-spacing of .{m.group(1)}em at body size separates "
                               "letters faster than the eye groups them into words.", "low"))
        return out[:5]
    for t in f.tags:
        if t.name.lower() not in ("p", "li", "blockquote"):
            continue
        if not re.search(r"tracking-(?:wider|widest)", " ".join(t.classes())):
            continue
        out.append(finding("S-TYPE-TRACKING-WIDE", f, t.line, " ".join(t.classes())[:60],
                           "Wide tracking on running text pulls letters out of words.",
                           "low"))
    return out[:5]


@check("S-TYPE-CRAMPED")
def cramped_padding(f, p):
    """Padding smaller than the text it surrounds reads as broken rather than
    dense, and it shrinks the hit area at the same time."""
    out = []
    if f.ext not in CSS:
        return out
    for pos, sel, body in _css_rules(f.text):
        fs = re.search(r"font-size\s*:\s*(\d+(?:\.\d+)?)px", body)
        pad = re.search(r"padding\s*:\s*(\d+(?:\.\d+)?)px", body)
        if not (fs and pad):
            continue
        size, pv = float(fs.group(1)), float(pad.group(1))
        need = max(4.0, size * 0.3)
        if pv >= need:
            continue
        out.append(finding("S-TYPE-CRAMPED", f, _line(f.text, pos), sel[:40],
                           f"{pv:g}px padding around {size:g}px text (about {need:.0f}px "
                           "would breathe). It reads as a rendering fault, and on a control "
                           "it shrinks the target too (NUM-005).", "low"))
    return out[:6]


@check("S-TYPE-EDGE")
def text_to_viewport_edge(f, p):
    """Text running to the edge of a phone screen is caught by the curve of the
    display and the user's thumb. A gutter is not decoration."""
    out = []
    if f.ext not in CSS:
        return out
    for pos, sel, body in _css_rules(f.text):
        if not re.search(r"^\s*body\s*$|^\s*(?:main|article|\.container)\s*$", sel.strip()):
            continue
        m = re.search(r"padding(?:-(?:left|right|inline))?\s*:\s*0(?:px)?\b", body)
        if not m and not re.search(r"padding", body):
            m = True
        if not m:
            continue
        out.append(finding("S-TYPE-EDGE", f, _line(f.text, pos), sel[:40],
                           "A top-level text container with no horizontal gutter. On a phone "
                           "the first and last characters sit under the screen curve and the "
                           "holding thumb -- 16px is the usual minimum (LAY-002).", "low"))
    return out[:3]
