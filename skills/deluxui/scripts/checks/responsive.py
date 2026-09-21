"""Layout, reflow and viewport ergonomics."""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")


@check("S-RESP-VH")
def viewport_units(f, p):
    """100vh is wrong on every phone: it ignores the retracting browser chrome,
    so the bottom of the layout sits under the URL bar. dvh/svh/lvh exist."""
    out = []
    for m in re.finditer(r"(?<![\w-])(100vh|h-screen|min-h-screen|max-h-screen)\b", f.text):
        line = f.text[:m.start()].count("\n") + 1
        tok = m.group(1)
        fix = {"100vh": "100dvh", "h-screen": "h-dvh",
               "min-h-screen": "min-h-dvh", "max-h-screen": "max-h-dvh"}[tok]
        out.append(finding("S-RESP-VH", f, line, tok,
                           f"Use {fix}. `{tok}` measures the viewport as if the mobile "
                           "browser chrome were hidden, so content ends up under it. Use "
                           "svh when you need the smallest stable height.", "high"))
    return out


@check("S-RESP-FIXEDPX")
def fixed_widths(f, p):
    out = []
    pat = (r"(?<![\w-])w-\[(\d{3,4})px\]" if f.ext in SRC
           else r"(?<![\w-])(?:min-)?width\s*:\s*(\d{3,4})px")
    for m in re.finditer(pat, f.text):
        px = int(m.group(1))
        if px <= 320:
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-RESP-FIXEDPX", f, line, m.group(0),
                           f"{px}px fixed width overflows a 320px viewport (NUM-009). Prefer "
                           "a max-width with a fluid basis, and size components against "
                           "their container with @container rather than the page width.",
                           "medium"))
    return out


@check("S-RESP-OVERFLOW")
def overflow_masking(f, p):
    out = []
    for m in re.finditer(r"(?<![\w-])overflow-x-hidden|overflow-x\s*:\s*hidden", f.text):
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-RESP-OVERFLOW", f, line, m.group(0),
                           "overflow-x:hidden usually hides a layout bug rather than fixing "
                           "it -- the content is still out there, just unreachable. Find what "
                           "overflows at 320px first.", "low"))
    return out


@check("S-RESP-TABLE", exts=SRC)
def table_narrow(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() != "table":
            continue
        scope = (t.parent.raw if t.parent else "") + " ".join(t.classes())
        if re.search(r"overflow-x-auto|overflow-auto|scroll|@container|hidden\s+\w+:table|"
                     r"md:table|sm:hidden", scope):
            continue
        line = t.line
        out.append(finding("S-RESP-TABLE", f, line, t.raw,
                           "A table with no narrow-viewport strategy. Either let it scroll "
                           "inside a labelled scroll region, or switch to a card layout at "
                           "narrow widths -- but keep every label, unit and row action "
                           "(LAY-006).", "low"))
    return out


@check("S-RESP-TRUNCATE")
def truncation(f, p):
    out = []
    for m in re.finditer(r"(?<![\w-])(truncate|text-ellipsis|line-clamp-\d)\b", f.text):
        line = f.text[:m.start()].count("\n") + 1
        win = f.text[max(0, m.start() - 300):m.start() + 300]
        if re.search(r"title=|aria-label|Tooltip|tooltip|<details|popover", win):
            continue
        out.append(finding("S-RESP-TRUNCATE", f, line, m.group(1),
                           "Truncated text with no way to read the full value. Fine for "
                           "decorative copy; not for a name, amount, error or action label "
                           "(LAY-007). Expose the full value on focus as well as hover.",
                           "low"))
    return out


@check("S-RESP-SAFEAREA")
def safe_area(f, p):
    """Fixed bottom bars land under the home indicator and gesture bar unless
    they add the safe-area inset. This is still one of the most common
    phone-only defects (LAY-005)."""
    out = []
    for m in re.finditer(r"(?<![\w-])(fixed|sticky)\b[^\n]{0,160}?(bottom-0|bottom\s*:\s*0)",
                         f.text):
        line = f.text[:m.start()].count("\n") + 1
        win = f.text[max(0, m.start() - 300):m.start() + 400]
        if "safe-area-inset" in win or "pb-safe" in win or "env(" in win:
            continue
        out.append(finding("S-RESP-SAFEAREA", f, line, m.group(0),
                           "A pinned bottom bar with no safe-area inset sits under the home "
                           "indicator on modern phones. Add "
                           "padding-bottom: env(safe-area-inset-bottom).", "medium"))
    return out
