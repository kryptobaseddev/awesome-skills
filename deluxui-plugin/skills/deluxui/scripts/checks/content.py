"""Copy, localisation, data presentation, destructive actions and image cost."""
from __future__ import annotations
import re
from . import check, finding
from ._util import read, strip_noncode

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")

# The defect is a message whose WHOLE content is vague. Substring matching also
# hits `error: undefined` in an object literal and "Update request failed with
# HTTP 503", which is a perfectly good message -- it names the status.
# Multi-word only. A bare "error" or "failed" is a status enum value in most
# codebases, not a message anyone reads.
VAGUE_PHRASE = re.compile(
    r"^(?:oops[,!.]?\s*)?"
    r"(?:something went wrong(?:\s*,?\s*please try again)?|"
    r"an?\s+(?:unknown|unexpected)\s+error(?:\s+(?:occurred|has occurred))?|"
    r"an error (?:occurred|has occurred)|unknown error|unexpected error|"
    r"(?:please\s+)?try again(?:\s+later)?|request failed|failed to load)"
    r"[\s.!]*$", re.I)
_STRING = re.compile(r"[\"'`]([^\"'`\n{}]{4,80})[\"'`]")
_JSX_TEXT = re.compile(r">\s*([A-Z][^<>{}\n]{4,80}?)\s*<")
_DEV_LOG = re.compile(r"\b(?:console|logger|log|debug|trace|Sentry|captureException)\s*\.")


@check("S-CONTENT-ERRORTEXT", exts=SRC)
def vague_errors(f, p):
    """A message that names neither what failed nor what to do next leaves the
    user with no move. UX-009 asks for the affected action and a real next step.

    Gated on the file rendering something: a fallback string in an IPC layer or
    a normaliser is a different concern from the message a user reads."""
    if not f.tags:
        return []
    out = []
    for rx in (_STRING, _JSX_TEXT):
        for m in rx.finditer(f.text):
            phrase = m.group(1).strip()
            if not VAGUE_PHRASE.match(phrase):
                continue
            line = f.text[:m.start()].count("\n") + 1
            line_text = f.text.split("\n")[line - 1]
            if _DEV_LOG.search(line_text):
                continue                      # a developer log is not UI copy
            out.append(finding("S-CONTENT-ERRORTEXT", f, line, phrase,
                               "This names neither what failed nor what to do about it, "
                               "so the user has no move. Say which operation failed and "
                               "give a real next step -- retry, change something, or who "
                               "to contact (UX-009, CONTENT-002).", "high"))
    if any("[object Object]" in ln for ln in f.text.split("\n")):
        line = next(i for i, ln in enumerate(f.text.split("\n"), 1)
                    if "[object Object]" in ln)
        out.append(finding("S-CONTENT-ERRORTEXT", f, line, "[object Object]",
                           "An object is being rendered as a string. The user sees "
                           "'[object Object]' where the reason should be.", "high"))
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


# `onDelete: "cascade"` in a Drizzle or Prisma schema is a foreign-key referential
# action. Nobody can press it, there is nothing to confirm, and no edit to the file
# makes the finding go away -- it was exactly half of this check's findings on a real
# app. Matched on the VALUE rather than by excluding schema paths, because the same
# option appears in migrations, generated clients and inline table definitions.
_REFERENTIAL = re.compile(r"""on(?:Delete|Update)\s*:\s*["']?"""
                          r"""(?:cascade|set\s*null|set\s*default|restrict|no\s*action)""",
                          re.I)
# A prop is a wire, not a handler. `<DangerZone onDelete={remove} />` puts the
# confirmation inside DangerZone -- and on the app this was found on, DangerZone made
# the operator TYPE THE COMPANY NAME, the strongest confirmation in the product, while
# the call site was reported as having none. Resolve the component and read it; if it
# cannot be found, keep the finding rather than assume.
_JSX_PROP = re.compile(r"<([A-Z][\w.]*)(?=[\s/>])")


def _confirmed_downstream(code: str, m, f, p) -> bool:
    if not re.match(r"on[A-Z]", m.group(0)):
        return False
    if "=" not in m.group(0):
        return False                      # `onDelete:` in an object, not a JSX prop
    open_at = code.rfind("<", max(0, m.start() - 400), m.start())
    if open_at < 0:
        return False
    tag = _JSX_PROP.match(code, open_at)
    if not tag:
        return False
    name = tag.group(1).split(".")[0]
    rel = (p.inventory or {}).get(name)
    if not rel:
        return False
    try:
        body = strip_noncode(read(p.root / rel))
    except OSError:
        return False
    return bool(re.search(r"confirm|AlertDialog|are you sure|undo|restore|"
                          r"type\s+the\s+|requireConfirm|window\.confirm", body, re.I))


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
    code = strip_noncode(f.text)
    for m in DESTRUCT.finditer(code):
        if NOT_DESTRUCTIVE.search(code[max(0, m.start() - 30):m.end() + 30]):
            continue
        if _REFERENTIAL.match(code[m.start():m.start() + 60]):
            continue
        win = code[max(0, m.start() - 400):m.start() + 1200]
        if re.search(r"confirm|AlertDialog|are you sure|undo|restore|trash|soft.?delete|"
                     r"requireConfirm|window\.confirm|toast\.\w*\(.*[Uu]ndo", win, re.I):
            continue
        if _confirmed_downstream(code, m, f, p):
            continue
        line = code[:m.start()].count("\n") + 1
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
