"""Component contracts: labels, states, keyboard patterns, tables, uploads,
pagination, bulk actions and navigation semantics.

Most of these are things a native element or a vetted primitive gives you for
free, which is why COMP-001 comes first in the rulebook. What is checked here is
the cost of having built it by hand anyway.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import ancestors

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
VAGUE_LABEL = re.compile(r"^\s*(?:continue|ok|okay|yes|submit|next|done|confirm|proceed|go)\s*$",
                         re.I)
CONSEQUENTIAL = re.compile(r"pay|purchase|charge|delete|remove|destroy|cancel subscription|"
                           r"transfer|publish|revoke|deactivate|archive|refund", re.I)


def _label(t):
    return " ".join(re.sub(r"<[^>]*>", " ", t.inner or "").split()) or \
        str(t.attr("aria-label") or "")


@check("S-COMP-VAGUE-LABEL", exts=SRC)
def vague_button_label(f, p):
    """A button label is a promise about what happens next. "Continue" on a
    payment is a promise it does not keep (COMP-003)."""
    out = []
    for t in f.tags:
        if not t.is_interactive() or t.self_closing:
            continue
        lab = _label(t)
        if not VAGUE_LABEL.match(lab):
            continue
        win = f.text[max(0, t.start - 1200):t.start + 400]
        if not CONSEQUENTIAL.search(win):
            continue
        out.append(finding("S-COMP-VAGUE-LABEL", f, t.line, f'"{lab}"',
                           f'"{lab}" sits in a flow that charges, deletes or publishes. Name '
                           "the operation on the control -- speech users activate by the "
                           "visible word, and everyone else reads it as the consequence "
                           "(COMP-003).", "medium"))
    return out[:8]


@check("S-COMP-DISABLED-MUTE", exts=SRC)
def unexplained_disabled(f, p):
    """A disabled control with no reason is a dead end: screen readers skip it,
    and nobody can tell what would make it live (COMP-004)."""
    out = []
    for t in f.tags:
        val = str(t.attr("disabled") or t.attr("aria-disabled") or "")
        if not t.has("disabled", "aria-disabled"):
            continue
        # Disabled *while the request is in flight* is correct, and the pending
        # indicator is the explanation. Only a standing disable needs words.
        if re.search(r"pending|submitting|loading|isBusy|inFlight|saving|uploading|"
                     r"disabled\s*$", val, re.I):
            continue
        win = f.text[max(0, t.start - 500):t.end + 500]
        if re.search(r"title=|aria-describedby|Tooltip|helperText|because|"
                     r"requires|need to|first|until", win, re.I):
            continue
        out.append(finding("S-COMP-DISABLED-MUTE", f, t.line, t.raw[:70],
                           "A disabled control with nothing nearby saying why. Say what "
                           "would enable it, or leave it live and explain on activation "
                           "(COMP-004, FORM-007).", "low"))
    return out[:8]


@check("S-COMP-KEYBOARD-PATTERN", exts=SRC)
def handrolled_widget_keyboard(f, p):
    """Menus, tabs, listboxes, comboboxes and trees each have a published
    keyboard contract. Built by hand without one, they are mouse-only (COMP-005)."""
    out = []
    ROLES = ("menu", "menubar", "menuitem", "tablist", "tab", "listbox", "option",
             "combobox", "tree", "treeitem")
    if re.search(r"@radix-ui|@base-ui|@headlessui|@ark-ui|react-aria|bits-ui|reka-ui",
                 f.text):
        return out
    seen = set()
    for t in f.tags:
        role = (t.attr("role") or "").strip("{}\"' ")
        if role not in ROLES or role in seen:
            continue
        seen.add(role)
        # A component file keeps its handler beside its markup; a single HTML
        # document keeps it at the bottom, which is correct and was being read as
        # "no arrow keys in sight".
        win = (f.text if f.ext in (".html", ".htm")
               else f.text[max(0, t.start - 1500):t.start + 2500])
        if re.search(r"ArrowDown|ArrowUp|ArrowRight|ArrowLeft|onKeyDown|useRovingFocus",
                     win):
            continue
        out.append(finding("S-COMP-KEYBOARD-PATTERN", f, t.line, f'role="{role}"',
                           f'A hand-built role="{role}" with no arrow-key handling in sight. '
                           "The APG pattern for this widget is not optional -- without it "
                           "the control cannot be operated from a keyboard (COMP-005).",
                           "medium"))
    return out[:6]


@check("S-COMP-ACCORDION", exts=SRC)
def accordion_state(f, p):
    """An expander that does not announce its state leaves screen-reader users
    guessing whether anything happened (COMP-013)."""
    out = []
    for t in f.tags:
        if not t.is_interactive():
            continue
        cls = " ".join(t.classes()) + " " + str(t.attr("onClick") or "")
        if not re.search(r"accordion|collaps|expand|disclos|toggle", cls, re.I):
            continue
        if t.has("aria-expanded"):
            continue
        win = f.text[max(0, t.start - 400):t.start + 400]
        if re.search(r"<details|aria-expanded|@radix-ui|@base-ui|@headlessui", win):
            continue
        out.append(finding("S-COMP-ACCORDION", f, t.line, t.raw[:70],
                           "An expander with no aria-expanded and no aria-controls. Use "
                           "<details>/<summary>, or wire both attributes (COMP-013).",
                           "medium"))
    return out[:6]


@check("S-COMP-TABLE-SEMANTICS", exts=SRC)
def table_semantics(f, p):
    """Without header cells the relationship between a value and its column
    exists only visually, which is no relationship at all (COMP-014)."""
    out = []
    for t in f.tags:
        if t.name.lower() != "table":
            continue
        inner = t.inner or ""
        problems = []
        if "<th" not in inner and "<Th" not in inner:
            problems.append("no header cells")
        if re.search(r"onClick[^>]{0,80}sort|sortBy|handleSort", inner) and \
                "aria-sort" not in inner:
            problems.append("sortable columns with no aria-sort")
        if not problems:
            continue
        out.append(finding("S-COMP-TABLE-SEMANTICS", f, t.line, ", ".join(problems),
                           "A data table with " + " and ".join(problems)
                           + ". Screen-reader users navigate a table by its headers; "
                           "without them every cell is an orphan value (COMP-014).",
                           "medium"))
    return out[:6]


@check("S-COMP-UPLOAD", exts=SRC)
def upload_contract(f, p):
    """Constraints discovered by rejection are constraints discovered too late
    -- often after a slow upload on a phone (COMP-021)."""
    out = []
    for t in f.tags:
        if t.name.lower() != "input" or (t.attr("type") or "").lower() != "file":
            continue
        win = f.text[max(0, t.start - 900):t.start + 1200]
        missing = []
        if not (t.has("accept") or re.search(r"accept=", win)):
            missing.append("accepted types")
        if not re.search(r"maxSize|max_size|MAX_FILE|\bMB\b|size limit|fileSize", win, re.I):
            missing.append("a size limit")
        if not re.search(r"progress|percent|uploading|<progress", win, re.I):
            missing.append("upload progress")
        if not missing:
            continue
        out.append(finding("S-COMP-UPLOAD", f, t.line, t.raw[:60],
                           "File input with no " + ", no ".join(missing)
                           + " shown before selection. State the constraints up front "
                           "(COMP-021).", "medium"))
    return out[:6]


@check("S-COMP-TOAST-ONLY", exts=SRC)
def toast_only_confirmation(f, p):
    """A toast is gone in four seconds. Anything a user may need to act on or
    refer back to must survive it (COMP-022)."""
    out = []
    for m in re.finditer(r"toast(?:\.\w+)?\s*\(", f.text):
        win = f.text[m.start():m.start() + 320]
        if not CONSEQUENTIAL.search(win) and not re.search(
                r"receipt|reference|confirmation|invoice|order|transaction", win, re.I):
            continue
        after = f.text[max(0, m.start() - 600):m.start() + 900]
        if re.search(r"history|notification[s]?\s*(?:centre|center|list)|activity|"
                     r"audit|persist|\bsave\b|router\.push|redirect", after, re.I):
            continue
        out.append(finding("S-COMP-TOAST-ONLY", f, f.text[:m.start()].count("\n") + 1,
                           win.split("\n")[0][:70],
                           "A consequential confirmation delivered only as a toast. It "
                           "disappears, and with it any reference the user needed. Put it "
                           "somewhere durable as well (COMP-022).", "low"))
        break
    return out


@check("S-COMP-BULK-SCOPE", exts=SRC)
def bulk_action_scope(f, p):
    """"Select all" means the page to the user and the query to the server often
    enough that the difference has to be stated (COMP-024)."""
    out = []
    for m in re.finditer(r"selectAll|select_all|handleSelectAll|toggleAll|bulk(?:Action|Delete|Update)",
                         f.text, re.I):
        win = f.text[max(0, m.start() - 700):m.start() + 900]
        if re.search(r"selected(?:Count|\.length)|\{\s*\w*selected\w*\.length|"
                     r"all \d+|across all|matching", win, re.I):
            continue
        out.append(finding("S-COMP-BULK-SCOPE", f, f.text[:m.start()].count("\n") + 1,
                           m.group(0),
                           "A bulk action with no visible selected count or scope. The user "
                           "cannot tell whether this applies to the page they can see or "
                           "every matching record (COMP-024).", "low"))
        break
    return out


# ------------------------------------------------------------------ navigation
@check("S-NAV-CURRENT", exts=SRC)
def current_destination(f, p):
    """Highlighting the active link visually but not programmatically means
    screen-reader users have no 'you are here' (NAV-007)."""
    out = []
    navs = [t for t in f.tags if t.name.lower() == "nav" or
            (t.attr("role") or "") == "navigation"]
    if not navs:
        return out
    for n in navs:
        inner = n.inner or ""
        if "aria-current" in inner:
            continue
        if not re.search(r"isActive|pathname|activeClassName|aria-selected|data-active",
                         inner):
            continue
        out.append(finding("S-NAV-CURRENT", f, n.line, "<nav> with active styling",
                           "The active destination is marked visually but carries no "
                           'aria-current="page". The accessibility tree and the visible '
                           "selection should name the same item (NAV-007).", "medium"))
    return out[:4]


@check("S-NAV-TITLE", exts=SRC)
def route_title(f, p):
    """A route with no title gives a screen-reader user nothing on navigation
    and produces a browser history of identical entries (NAV-001)."""
    out = []
    rel = f.rel.replace("\\", "/")
    is_route = bool(re.search(r"(?:^|/)(?:pages|routes|app)/.*(?:page|index|\+page)\."
                              r"[jt]sx?$", rel))
    if not is_route or f.surface != "ui":
        return out
    if re.search(r"<title|useHead|document\.title|generateMetadata|export const metadata|"
                 r"<svelte:head|<Head>|Helmet", f.text):
        return out
    if not f.tags:
        return out
    out.append(finding("S-NAV-TITLE", f, 1, rel,
                       "A route component that never sets a document title. Screen readers "
                       "announce the title on navigation, and the browser history becomes a "
                       "column of identical entries without it (NAV-001).", "medium"))
    return out


# ------------------------------------------------------------------ forms
@check("S-FORM-ERROR-LINK", exts=SRC)
def error_association(f, p):
    """An error rendered next to a field is not attached to it. Without
    aria-describedby a screen reader reads the input and stops (FORM-006)."""
    out = []
    has_err = re.search(r"\berrors?\b|fieldError|errorMessage|touched", f.text)
    if not has_err:
        return out
    for t in f.tags:
        if t.name.lower() not in ("input", "select", "textarea"):
            continue
        if (t.attr("type") or "").lower() in ("hidden", "submit", "button"):
            continue
        if t.has("aria-describedby", "aria-errormessage", "aria-invalid"):
            continue
        name = (t.attr("name") or t.attr("id") or "").strip("{}\"' ")
        if not name:
            continue
        # The error must be scoped to THIS field. A form-level failure message
        # rendered elsewhere is not something the input should point at.
        scoped = re.search(rf"errors?\.\s*{re.escape(name)}\b|"
                           rf"errors?\[\s*[\"']{re.escape(name)}[\"']\s*\]|"
                           rf"\b{re.escape(name)}Error\b", f.text)
        if not scoped:
            continue
        out.append(finding("S-FORM-ERROR-LINK", f, t.line, t.raw[:70],
                           "A field with an error rendered nearby but no aria-describedby "
                           "or aria-invalid connecting them. The error exists visually and "
                           "nowhere else (FORM-006).", "medium"))
    return out[:8]


@check("S-FORM-LOST-INPUT", exts=SRC)
def input_lost_on_error(f, p):
    """Clearing the form on failure makes the user pay twice for one server
    error, and they usually do not come back (FORM-004)."""
    out = []
    for m in re.finditer(r"catch\s*\([^)]*\)\s*\{([^}]{0,400})", f.text):
        body = m.group(1)
        if not re.search(r"reset\s*\(|setValues?\s*\(\s*(?:\{\}|initial|empty)|"
                         r"clearForm|\.reset\(\)", body):
            continue
        out.append(finding("S-FORM-LOST-INPUT", f, f.text[:m.start()].count("\n") + 1,
                           body.strip()[:60],
                           "The form is reset inside an error handler. A server failure now "
                           "costs the user everything they typed (FORM-004).", "medium"))
    return out[:6]


@check("S-FORM-PASTE-BLOCK", exts=SRC)
def composition_and_paste(f, p):
    """Intercepting Enter or paste breaks IME composition and password managers,
    and the people it breaks it for are rarely the ones testing (FORM-015)."""
    out = []
    for m in re.finditer(r"onKeyDown[^\n]{0,160}", f.text):
        chunk = m.group(0)
        if "Enter" not in chunk:
            continue
        if re.search(r"isComposing|nativeEvent\.isComposing|keyCode\s*===?\s*229|"
                     r"shiftKey", chunk):
            continue
        if not re.search(r"submit|preventDefault", chunk, re.I):
            continue
        out.append(finding("S-FORM-PASTE-BLOCK", f, f.text[:m.start()].count("\n") + 1,
                           chunk[:70],
                           "Enter is intercepted to submit without checking isComposing. In "
                           "Japanese, Chinese and Korean input this submits mid-word, every "
                           "time (FORM-015).", "medium"))
    return out[:6]


@check("S-UX-FAKE-INTERACTIVE", exts=SRC)
def fake_interactive(f, p):
    """cursor:pointer on something that does nothing teaches users to distrust
    the cursor, which is one of the few affordances left (UX-011)."""
    out = []
    for t in f.tags:
        cls = " ".join(t.classes())
        if "cursor-pointer" not in cls:
            continue
        if t.is_interactive() or t.has("role", "tabIndex", "tabindex"):
            continue
        if t.has_spread():
            continue      # a spread may carry the handler; cannot tell, so do not claim
        if any(a.is_interactive() for a in ancestors(t)):
            continue
        out.append(finding("S-UX-FAKE-INTERACTIVE", f, t.line, cls[:70],
                           "cursor-pointer on an element with no handler, role or tab stop. "
                           "It looks clickable and is not (UX-011).", "low"))
    return out[:8]
