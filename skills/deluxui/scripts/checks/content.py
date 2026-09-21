"""Copy, localisation, data presentation, destructive actions and image cost."""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")

VAGUE_ERROR = re.compile(
    r"(?:Something went wrong|An error occurred|Oops[,!.]?\s*something|"
    r"Error occurred|Unknown error|An unexpected error|Try again later|"
    r"Failed to load|Request failed)(?=[\"'`.!<\s]|$)|"
    r"Error:\s*(?:undefined|null|\[object Object\])", re.I)


@check("S-CONTENT-ERRORTEXT", exts=SRC)
def vague_errors(f, p):
    out = []
    for m in VAGUE_ERROR.finditer(f.text):
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-CONTENT-ERRORTEXT", f, line, m.group(0),
                           "This tells the user nothing they can act on. Name the operation "
                           "that failed and the next step: what to retry, what to change, or "
                           "who to contact (UX-009, CONTENT-002).", "high"))
    return out


@check("S-CONTENT-I18N", exts=SRC, requires=lambda p: p.has_i18n)
def hardcoded_strings(f, p):
    """Only runs when the project already has i18n -- otherwise a hardcoded
    string is a choice, not a defect."""
    out = []
    for t in f.tags:
        if t.name.lower() not in ("h1", "h2", "h3", "button", "label", "a", "p", "th"):
            continue
        txt = re.sub(r"<[^>]*>", "", t.inner or "").strip()
        if len(txt) < 8 or "{" in txt or not re.search(r"[A-Za-z]{3}\s+[A-Za-z]{3}", txt):
            continue
        out.append(finding("S-CONTENT-I18N", f, t.line, txt[:80],
                           "Literal user-facing copy in a project that has translation set "
                           "up. It will ship untranslated and silently (CONTENT-004).",
                           "medium"))
    return out


@check("S-CONTENT-FORMAT", exts=SRC)
def locale_formatting(f, p):
    out = []
    # toLocaleDateString() with no argument already uses the user's locale, so it
    # is correct, not a defect. What matters is money formatted by hand and dates
    # stringified with no locale at all.
    for m in re.finditer(r"\.toFixed\(\s*2\s*\)|new Date\([^)]*\)\.toString\(\)|"
                         r"[\"'`]\$[\"'`]\s*\+\s*\w|\$\$\{", f.text):
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-CONTENT-FORMAT", f, line, m.group(0),
                           "Number, currency or date rendered without an explicit locale and "
                           "currency. Use Intl.NumberFormat / Intl.DateTimeFormat -- a bare "
                           "$ prefix and a US date are wrong for most of the world, and a "
                           "currency shown without its code is a real financial ambiguity "
                           "(CONTENT-005, CONTENT-006, FORM-014).", "medium"))
    return out


@check("S-TRUST-DESTRUCT", exts=SRC)
def destructive_no_recovery(f, p):
    out = []
    # Must look like a user-facing handler. Bare remove*/delete* hits platform
    # APIs (removeEventListener, localStorage.removeItem, Map.delete) far more
    # often than they hit a destructive user action.
    DESTRUCT = re.compile(r"\b(?:handle|on|do|confirm)(?:Delete|Remove|Destroy|Revoke|Wipe|"
                          r"Purge|Archive)\w*\s*(?::|=|\()")
    NOT_DESTRUCTIVE = re.compile(
        r"remove(?:EventListener|Item|Child|Attribute|Class|Listener|Query)|"
        r"delete(?:Property|Count)|\.(?:delete|remove)\(\s*\)")
    for m in DESTRUCT.finditer(f.text):
        if NOT_DESTRUCTIVE.search(f.text[max(0, m.start() - 30):m.end() + 30]):
            continue
        win = f.text[max(0, m.start() - 400):m.start() + 1200]
        if re.search(r"confirm|AlertDialog|are you sure|undo|restore|trash|soft.?delete|"
                     r"requireConfirm|window\.confirm|toast\.\w*\(.*[Uu]ndo", win, re.I):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-TRUST-DESTRUCT", f, line, m.group(0),
                           "Destructive action with no confirmation and no undo. Prefer undo "
                           "over a confirm dialog where the data can be held briefly -- "
                           "confirmations get clicked through, undo actually recovers the "
                           "mistake (UX-003, UX-005, TRUST-006).", "medium"))
    return out


@check("S-PERF-IMGDIM", exts=SRC)
def image_dimensions(f, p):
    out = []
    for t in f.tags:
        n = t.name.lower()
        if n != "img":
            continue
        if t.has("width", "height") or t.attr("fill") is not None:
            continue
        cls = " ".join(t.classes())
        if re.search(r"aspect-|h-\d|w-\d|size-\d|object-", cls):
            continue
        out.append(finding("S-PERF-IMGDIM", f, t.line, t.raw,
                           "No intrinsic size, so the page reflows when this loads -- that is "
                           "measured directly as CLS. Set width/height or an aspect-ratio "
                           "(PERF-003, NUM-012).", "high"))
    return out
