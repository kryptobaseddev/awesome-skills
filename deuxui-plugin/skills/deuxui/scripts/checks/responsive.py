"""Layout, reflow and viewport ergonomics."""
from __future__ import annotations
import re
from . import check, finding
from ._util import ancestors

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


# A horizontal scroll box and a card layout are not equivalent answers to a
# table that does not fit. Cards move the data somewhere the user will find it;
# a scroll box moves it somewhere they will not -- sideways scrolling inside a
# vertically scrolling page is a gesture people do not discover, and it hides
# whatever is rightmost. In a data table that is the row actions. The old check
# accepted any `overflow-auto` (and any class containing "scroll") on the direct
# parent as a remedy, and scored exactly that table PASS in a field report.
_SCROLL = re.compile(r"(?<![\w-])overflow(?:-x)?-(?:auto|scroll)(?![\w-])|"
                     r"overflow-?[xX]?\s*:\s*['\"]?(?:auto|scroll)|<ScrollArea\b")
_CARDS = re.compile(r"(?<![\w-])hidden\s+(?:[\w-]+:)*(?:sm|md|lg|xl|2xl):(?:table|block)(?![\w-])|"
                    r"(?<![\w-])(?:max-)?(?:sm|md|lg|xl|2xl):hidden(?![\w-])|@container|"
                    r"(?<![\w-])@(?:sm|md|lg|xl):|@media[^{]*\bmax-width")
_STICKY_END = re.compile(r"(?<![\w-])sticky(?![\w-])[^>]*?(?<![\w-])(?:right|end)-0(?![\w-])|"
                         r"(?<![\w-])(?:right|end)-0(?![\w-])[^>]*?(?<![\w-])sticky(?![\w-])|"
                         r"position\s*:\s*['\"]?sticky")
_ACTION_HEAD = re.compile(r"^(?:actions?|edit|manage|options|more|menu|controls?)$", re.I)
_ACTION_COMPONENT = re.compile(r"(?:Button|Menu|Link|Action|Dropdown|Kebab)", re.I)


def _descendants(t):
    for c in t.children:
        yield c
        yield from _descendants(c)


def _text(tag):
    return " ".join(re.sub(r"<[^>]*>|\{[^{}]*\}", " ", tag.inner or "").split())


def _table_shape(table):
    """(column count, last header text, last column interactive, last column
    pinned) read from the markup. Rows built with .map() exist once in source,
    which is all this needs: the columns are the same on every row."""
    heads = [d for d in _descendants(table) if d.name.lower() == "th"
             and any(a.name.lower() == "thead" for a in _ancestors_until(d, table))]
    rows = [d for d in _descendants(table) if d.name.lower() == "tr"]
    if not heads and rows:
        heads = [c for c in rows[0].children if c.name.lower() in ("th", "td")]
    last_head = heads[-1] if heads else None
    last_cells = [cells[-1] for r in rows
                  if (cells := [c for c in r.children if c.name.lower() in ("td", "th")])]
    interactive = any(
        d.is_interactive() or _ACTION_COMPONENT.search(d.name) and d.name[:1].isupper()
        for cell in last_cells for d in _descendants(cell))
    label = _text(last_head) if last_head is not None else ""
    if _ACTION_HEAD.match(label):
        interactive = True
    pinned = any(_STICKY_END.search(c.raw) for c in ([last_head] if last_head else []) + last_cells)
    return len(heads), label, interactive, pinned


def _ancestors_until(t, stop):
    p = t.parent
    while p is not None and p is not stop:
        yield p
        p = p.parent


@check("S-RESP-TABLE", exts=SRC)
def table_narrow(f, p):
    out = []
    max_cols = p.num("responsive", "table_scroll_max_columns", 6)
    act_cols = p.num("responsive", "table_actions_min_columns", 4)
    for t in f.tags:
        if t.name.lower() != "table":
            continue
        up = [a for _i, a in zip(range(4), ancestors(t))]
        near = [t] + up + ([s for s in t.parent.children if s is not t] if t.parent else [])
        wrap = " ".join(x.raw for x in [t] + up)
        cards = any(_CARDS.search(x.raw) for x in near)
        scroll = bool(_SCROLL.search(wrap))
        if cards:
            continue
        if not scroll:
            out.append(finding("S-RESP-TABLE", f, t.line, t.raw,
                               "A table with no narrow-viewport strategy. Switch to a card "
                               "or stacked layout at narrow widths, keeping every label, unit "
                               "and row action (LAY-006). A scroll region is only enough for "
                               "a small table with no actions.", "medium"))
            continue
        ncols, label, interactive, pinned = _table_shape(t)
        if pinned or not (interactive and ncols >= act_cols or ncols > max_cols):
            continue
        last = f' ("{label}")' if label else ""
        why = ("its last column holds row actions" if interactive and ncols >= act_cols
               else f"{ncols} columns is more than {max_cols}")
        out.append(finding("S-RESP-TABLE", f, t.line, t.raw,
                           f"A {ncols or 'multi'}-column data table whose only narrow-width "
                           f"strategy is a horizontal scroll box, and {why}. Sideways "
                           "scrolling inside a page people scroll vertically is rarely "
                           f"discovered, so the rightmost column{last} is effectively "
                           "hidden (LAY-006). Switch to a card or stacked layout below a "
                           "breakpoint, or pin the last column with `sticky right-0` so "
                           "the actions stay in view.", "medium"))
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
