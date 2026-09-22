"""Navigation, async races, cancellation, and the performance a user feels.

These are behaviours rather than markup, so most are inferred from the shape of
the code that produces them. Confidence is set accordingly -- the point is to
put the question in front of someone, not to settle it.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import ancestors, strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro")


def _ln(t, pos):
    return t[:pos].count("\n") + 1


# ------------------------------------------------------------------ navigation
@check("S-NAV-DEEPLINK", exts=SRC)
def modal_state_not_addressable(f, p):
    """A view you cannot link to is a view you cannot share, bookmark, or return
    to with Back. Modal and tab state that lives only in component state quietly
    breaks all three (NAV-003)."""
    out = []
    for m in re.finditer(r"useState[^\n]{0,80}\b(?:isOpen|modalOpen|showModal|dialogOpen|"
                         r"activeTab|selectedTab|drawerOpen)\b", f.text):
        win = f.text[max(0, m.start() - 600):m.start() + 1200]
        if re.search(r"searchParams|useSearchParams|router\.(?:push|replace)|"
                     r"history\.(?:push|replace)|\$page\.url|route\.query", win):
            continue
        out.append(finding("S-NAV-DEEPLINK", f, _ln(f.text, m.start()), m.group(0)[:60],
                           "Modal or tab state held only in component state. It cannot be "
                           "linked to, Back closes the whole page instead of the panel, and "
                           "a refresh loses the user's place (NAV-003).", "low"))
        break
    return out


@check("S-NAV-LIST-CONTEXT", exts=SRC)
def list_context_lost(f, p):
    """Returning from a detail view to page one of an unfiltered list is the
    single most common way an interface wastes someone's work (NAV-004)."""
    out = []
    has_filter = re.search(r"\b(?:filter|sortBy|page|cursor|query|search)\b", f.text, re.I)
    if not has_filter:
        return out
    for m in re.finditer(r"router\.(?:push|navigate)\s*\(\s*[`\"'][^`\"']*/\$?\{?\w*id",
                         f.text):
        win = f.text[max(0, m.start() - 800):m.start() + 400]
        if re.search(r"searchParams|\?\w+=|state:\s*\{|returnTo|from=", win):
            continue
        out.append(finding("S-NAV-LIST-CONTEXT", f, _ln(f.text, m.start()), m.group(0)[:60],
                           "Navigating to a detail view without carrying the list's filters, "
                           "sort or page. Coming back lands on an unfiltered page one "
                           "(NAV-004).", "low"))
        break
    return out


_ROUTE_SKIP = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit",
               ".nuxt", "out", "coverage", "vendor", "__pycache__", ".venv", "venv",
               ".turbo", ".output", "tmp", "temp", "storybook-static", ".cache"}
_ROUTE_SKIP_PATH = ("/node_modules/", "/dist/", "/build/", "/.next/", "/coverage/",
                    "/tmp/", "/.git/")


_ROUTERS = ("react-router", "react-router-dom", "@tanstack/react-router", "next",
            "nuxt", "@sveltejs/kit", "vue-router", "astro", "remix", "@remix-run/react",
            "expo-router", "@angular/router", "wouter")


def _is_routed(p) -> bool:
    """Whether this project has routing at all.

    A router dependency, or a directory the conventions use for one. Deliberately
    generous: the cost of missing a routed project is one unreported rule, and the
    cost of firing on every unrouted one is a finding on every prototype."""
    if any(any(r in d for r in _ROUTERS) for d in (p.deps or ())):
        return True
    for name in ("routes", "pages", "app"):
        q = p.root / name
        if q.is_dir() and any(q.rglob("*")):
            return True
    return bool(list(p.root.glob("src/routes/*")) or list(p.root.glob("src/pages/*")))


@check("S-NAV-ERROR-ROUTE", scope="project")
def missing_error_routes(f, p):
    """An unhandled route or a forbidden record should land somewhere designed.
    The framework default is a stack trace or a blank page (NAV-008)."""
    out = []
    # A project with no routing has no route tree to handle. A single-file
    # prototype, a component library or a static page cannot define a 404 route,
    # and reporting one as missing is a finding nobody can act on -- which is how
    # a real signal gets trained out of a reader.
    if not _is_routed(p):
        return out
    # Read the route tree on disk, not the component inventory. The inventory is
    # built from component directories, so adding app/not-found.tsx or
    # +error.svelte -- the actual fix -- did not clear this rule, and NAV-008
    # could not be satisfied by doing the right thing.
    found_404, found_err, looked = False, False, 0
    for q in p.root.rglob("*"):
        if looked > 24000:
            break
        if q.is_dir():
            if q.name in _ROUTE_SKIP or q.name.startswith("."):
                continue
            continue
        looked += 1
        n = q.name.lower()
        rel = q.as_posix().lower()
        if any(x in rel for x in _ROUTE_SKIP_PATH):
            continue
        if re.match(r"^(?:not-found|404|\+error|error|global-error)\.(?:[jt]sx?|svelte|vue|astro|html)$", n) \
                or "[...slug]" in rel or "[[...]]" in rel or "catch-all" in rel:
            if n.startswith(("not-found", "404")) or "[...slug]" in rel or "catch-all" in rel:
                found_404 = True
            if n.startswith(("error", "+error", "global-error")):
                found_err = True
        if not found_err and re.search(r"errorboundary|error-boundary", n):
            found_err = True
    if not looked:
        return out                       # nothing on disk to judge
    missing = []
    if not found_404:
        missing.append("a not-found route")
    if not found_err:
        missing.append("an error boundary or error route")
    if not missing:
        return out
    out.append(finding("S-NAV-ERROR-ROUTE", f, 1, ", ".join(missing),
                       "The project defines " + " and ".join(missing).join(("no ", ""))
                       + ". An invalid URL or a failed load then shows the framework "
                       "default, which is a stack trace or nothing at all (NAV-008).",
                       "low"))
    return out


@check("S-NAV-FOCUS-STEAL", exts=SRC)
def focus_moved_in_background(f, p):
    """Focus moved by a timer or a poll yanks the cursor out of whatever the
    user was typing. It is the interface interrupting them (NAV-010)."""
    out = []
    for m in re.finditer(r"(?:setInterval|setTimeout)\s*\([^)]{0,200}", f.text):
        if not re.search(r"\.focus\s*\(|scrollIntoView|autoFocus", m.group(0)):
            continue
        out.append(finding("S-NAV-FOCUS-STEAL", f, _ln(f.text, m.start()), m.group(0)[:60],
                           "Focus or scroll moved from a timer. A background update must not "
                           "take the cursor away from someone mid-sentence (NAV-010, "
                           "A11Y-006).", "medium"))
    return out


# ------------------------------------------------------------------ async races
@check("S-STATE-RACE", exts=SRC)
def stale_response_overwrite(f, p):
    """Type fast enough and an older response lands after a newer one. Without
    an abort or a sequence guard the list shows the wrong query's results
    (STATE-007, COMP-018)."""
    out = []
    for m in re.finditer(r"\b(?:useEffect|\$effect|watchEffect)\s*\(", f.text):
        win = f.text[m.start():m.start() + 1400]
        if not re.search(r"fetch\s*\(|axios|\.then\s*\(|await ", win):
            continue
        if re.search(r"AbortController|signal\s*:|ignore|cancelled|canceled|"
                     r"isCurrent|isStale|abort\(\)|useQuery|useSWR", win):
            continue
        # An effect with an empty dependency array runs once and cannot race with
        # itself. The hazard is a re-running effect whose inputs change faster
        # than the responses come back.
        deps = re.search(r"\}\s*,\s*\[([^\]]*)\]\s*\)", win)
        if not deps or not deps.group(1).strip():
            continue
        out.append(finding("S-STATE-RACE", f, _ln(f.text, m.start()), "useEffect + fetch",
                           "An effect that fetches with no AbortController and no ignore "
                           "flag. When the inputs change quickly the older response can land "
                           "last and overwrite the newer one (STATE-007).", "medium"))
        break
    return out


@check("S-STATE-CANCEL", exts=SRC)
def cancel_semantics(f, p):
    """Closing a panel is not cancelling the work behind it. If the request
    keeps going, saying "Cancelled" is false (STATE-012)."""
    out = []
    for m in re.finditer(r"\b(?:onCancel|handleCancel|cancelUpload|abortRequest)\b", f.text):
        win = f.text[max(0, m.start() - 400):m.start() + 800]
        if re.search(r"abort\s*\(|AbortController|signal|\.cancel\s*\(|mutation\.reset", win):
            continue
        if not re.search(r"setOpen\s*\(\s*false|onClose|dismiss|close\(\)", win):
            continue
        out.append(finding("S-STATE-CANCEL", f, _ln(f.text, m.start()), m.group(0),
                           "Cancel closes the panel but nothing aborts the request or tells "
                           "the server. The operation completes anyway while the user "
                           "believes it stopped (STATE-012).", "medium"))
        break
    return out


# ------------------------------------------------------------------ components
@check("S-COMP-TOOLTIP-CRITICAL", exts=SRC)
def critical_info_in_tooltip(f, p):
    """A tooltip is not available to touch users and is easy to miss for
    everyone. Requirements and errors have to be visible (COMP-012)."""
    out = []
    for t in f.tags:
        title = t.attr("title")
        if not title:
            continue
        if re.search(r"required|must|error|invalid|minimum|maximum|at least|format|"
                     r"cannot|warning", str(title), re.I):
            out.append(finding("S-COMP-TOOLTIP-CRITICAL", f, t.line, str(title)[:60],
                               "A requirement or error carried only in a title tooltip. "
                               "Touch users never see it and it is not announced reliably. "
                               "Keep instructions and errors visible (COMP-012).", "medium"))
    return out


@check("S-COMP-ZERO-VS-MISSING", exts=SRC)
def zero_conflated_with_missing(f, p):
    """`value ?? 0` turns "we do not know" into "it is zero". On a dashboard
    that is a wrong number presented as a fact (COMP-016)."""
    out = []
    for m in re.finditer(r"(\w+)\s*(?:\?\?|\|\|)\s*0\b", f.text):
        win = f.text[max(0, m.start() - 200):m.start() + 200]
        # A badge count of 0 is honest. A price, balance or measured metric of 0
        # standing in for "unknown" is not.
        if not re.search(r"toFixed|toLocale|currency|Intl\.NumberFormat|\bamount\b|"
                         r"\btotal\b|\bbalance\b|\bprice\b|\brevenue\b|\bmetric\b|"
                         r"\baverage\b|\bpercent", win, re.I):
            continue
        out.append(finding("S-COMP-ZERO-VS-MISSING", f, _ln(f.text, m.start()), m.group(0),
                           f"`{m.group(0)}` renders a missing value as zero. Missing, zero "
                           "and stale are three different facts and a reader cannot tell "
                           "them apart once they all render as 0 (COMP-016).", "low"))
    return out


@check("S-COMP-PAGINATION", exts=SRC)
def pagination_contract(f, p):
    """Infinite scroll with no alternative traps keyboard users and makes the
    footer unreachable; page controls with no labels are unusable by name
    (COMP-019)."""
    out = []
    for m in re.finditer(r"\b(?:InfiniteScroll|useInfiniteQuery|loadMore|fetchNextPage|"
                         r"IntersectionObserver)\b", f.text):
        win = f.text[max(0, m.start() - 800):m.start() + 1200]
        if re.search(r"<button[^>]*>[^<]*(?:load more|show more)|aria-label|role=\"feed\"|"
                     r"aria-live", win, re.I):
            continue
        out.append(finding("S-COMP-PAGINATION", f, _ln(f.text, m.start()), m.group(0),
                           "Automatic infinite loading with no explicit control and no live "
                           "region. Keyboard users cannot trigger the next page and nothing "
                           "announces that more arrived (COMP-019).", "medium"))
        break
    return out


@check("S-COMP-DRAG-ALT", exts=SRC)
def drag_without_alternative(f, p):
    """Dragging requires a pointer, sustained precision, and a steady hand.
    SC 2.5.7 requires a single-pointer alternative (COMP-020, A11Y-009)."""
    out = []
    for m in re.finditer(r"\b(?:onDragStart|draggable|useDraggable|useSortable|"
                         r"DragDropContext|dnd-kit|react-beautiful-dnd)\b", f.text):
        win = f.text[max(0, m.start() - 900):m.start() + 1500]
        if re.search(r"onKeyDown|ArrowUp|ArrowDown|moveUp|moveDown|\bkeyboard\b|"
                     r"announcements|sensors.*Keyboard", win, re.I):
            continue
        out.append(finding("S-COMP-DRAG-ALT", f, _ln(f.text, m.start()), m.group(0),
                           "Drag-and-drop with no keyboard or single-pointer alternative. "
                           "Reordering must also work without dragging (COMP-020, A11Y-009, "
                           "WCAG SC 2.5.7).", "medium"))
        break
    return out


# ------------------------------------------------------------------ forms
@check("S-FORM-DERIVED-STALE", exts=SRC)
def stale_dependent_field(f, p):
    """Change the country and the old state stays selected. The form now holds
    a combination that cannot exist (FORM-008)."""
    out = []
    for m in re.finditer(r"onChange[^\n]{0,120}set(\w+)\s*\(", f.text):
        name = m.group(1)
        win = f.text[m.start():m.start() + 900]
        dependents = re.findall(rf"\b{name}\b[^\n]{{0,80}}(?:options|items|list|fetch)", win)
        if not dependents:
            continue
        if re.search(rf"set\w+\(\s*(?:''|\"\"|null|undefined|\[\])", win):
            continue
        out.append(finding("S-FORM-DERIVED-STALE", f, _ln(f.text, m.start()), m.group(0)[:60],
                           f"Changing `{name}` reloads a dependent field but never clears the "
                           "old selection. The form keeps a combination that is no longer "
                           "valid (FORM-008).", "low"))
        break
    return out


@check("S-FORM-REDUNDANT", exts=SRC)
def redundant_entry(f, p):
    """Asking for the same thing twice in one process is a WCAG failure as of
    2.2, not merely a courtesy (FORM-011)."""
    out = []
    names = {}
    for t in f.tags:
        if t.name.lower() not in ("input", "select", "textarea"):
            continue
        n = (t.attr("name") or t.attr("id") or "").strip("{}\"' ").lower()
        n = re.sub(r"(billing|shipping|delivery|home|work)[-_]?", "", n)
        if not n or (t.attr("type") or "").lower() in ("hidden", "submit", "button"):
            continue
        names.setdefault(n, []).append(t)
    for n, ts in names.items():
        if len(ts) < 2:
            continue
        out.append(finding("S-FORM-REDUNDANT", f, ts[1].line, f'"{n}" asked {len(ts)} times',
                           f"`{n}` is collected more than once in the same form. Reuse what "
                           "the user already gave you, or say why it must differ (FORM-011, "
                           "WCAG SC 3.3.7).", "low"))
    return out


@check("S-FORM-EXCESSIVE", exts=SRC)
def excessive_fields(f, p):
    """Every field is a reason to abandon. If nobody can say what a field is
    for, it should not be there (FORM-001)."""
    out = []
    forms = [t for t in f.tags if t.name.lower() == "form"]
    for form in forms:
        inner = form.inner or ""
        n = len(re.findall(r"<(?:input|select|textarea)", inner, re.I))
        optional = len(re.findall(r"optional", inner, re.I))
        if n < 12:
            continue
        out.append(finding("S-FORM-EXCESSIVE", f, form.line, f"{n} fields in one form",
                           f"{n} fields in a single form"
                           + (f", {optional} marked optional" if optional else
                              ", none marked optional")
                           + ". Each one is a reason to abandon; ask for what this step "
                           "needs and defer the rest (FORM-001).", "low"))
    return out


# ------------------------------------------------------------------ performance
@check("S-PERF-SKELETON-ARIA", exts=SRC)
def skeleton_announced(f, p):
    """A skeleton is decoration standing in for content. Announced to a screen
    reader it becomes meaningless noise, or worse, is read as data (PERF-008)."""
    out = []
    for t in f.tags:
        cls = " ".join(t.classes())
        if not re.search(r"skeleton|shimmer|placeholder-pulse|animate-pulse", cls, re.I):
            continue
        if t.has("aria-hidden", "aria-busy", "role"):
            continue
        win = f.text[max(0, t.start - 300):t.end + 300]
        if re.search(r"aria-hidden|aria-busy|role=\"status\"|sr-only", win):
            continue
        out.append(finding("S-PERF-SKELETON-ARIA", f, t.line, cls[:60],
                           "A loading skeleton with no aria-hidden and no aria-busy. Screen "
                           "readers announce the placeholder text as if it were the content "
                           "(PERF-008, A11Y-006).", "medium"))
    return out


@check("S-PERF-LONG-LIST", exts=SRC)
def unvirtualised_long_list(f, p):
    """Rendering thousands of rows blocks the main thread and every one of them
    costs layout, paint and memory (PERF-006, PERF-007)."""
    out = []
    if re.search(r"react-window|react-virtual|@tanstack/react-virtual|virtua|"
                 r"VirtualList|windowing", f.text):
        return out
    # Only where the data is actually LOADED here. A component mapping a prop is
    # bounded by whoever passes it, and flagging every one of those is noise.
    if not re.search(r"useQuery|useSWR|useInfiniteQuery|fetch\s*\(|supabase|\.from\(|"
                     r"prisma\.|drizzle|loadData", f.text):
        return out
    for m in re.finditer(r"\.map\s*\(", f.text):
        win = f.text[max(0, m.start() - 400):m.start() + 100]
        if not re.search(r"\b(?:rows|records|items|results|entries|data)\b", win):
            continue
        if not re.search(r"pageSize|limit|slice\(|take:|\btop\b|first:", win, re.I):
            out.append(finding("S-PERF-LONG-LIST", f, _ln(f.text, m.start()), m.group(0),
                               "A collection rendered with no page size, slice or "
                               "virtualisation in sight. If it can grow, every row costs "
                               "layout and paint, and input stops responding while it "
                               "renders (PERF-006, PERF-007).", "low"))
            break
    return out


@check("S-PERF-BLOCKING", exts=SRC)
def blocking_main_thread(f, p):
    """Synchronous work on the main thread freezes every input, including the
    one the user is making right now (PERF-004, PERF-007)."""
    out = []
    for m in re.finditer(r"\b(?:JSON\.parse|JSON\.stringify)\s*\([^)\n]{0,60}|"
                         r"\.sort\s*\(|\.filter\s*\([^)]{0,40}\)\.map", f.text):
        win = f.text[max(0, m.start() - 300):m.start() + 300]
        if not re.search(r"onChange|onInput|onKeyUp|handleSearch|onScroll", win):
            continue
        if re.search(r"useMemo|useDeferredValue|startTransition|debounce|throttle|worker",
                     win):
            continue
        out.append(finding("S-PERF-BLOCKING", f, _ln(f.text, m.start()), m.group(0)[:50],
                           "Heavy synchronous work inside an input handler, with no memo, "
                           "transition or debounce around it. Every keystroke waits for it "
                           "(PERF-004, PERF-007, NUM-013).", "low"))
        break
    return out


@check("S-A11Y-TIMEOUT", exts=SRC)
def session_timeout(f, p):
    """A session that expires silently discards work and gives no chance to
    extend it. SC 2.2.1 requires a warning and an extension (A11Y-008)."""
    out = []
    for m in re.finditer(r"\b(?:sessionTimeout|idleTimeout|SESSION_TIMEOUT|expiresIn|"
                         r"autoLogout|inactivityTimer)\b", f.text):
        win = f.text[max(0, m.start() - 700):m.start() + 1000]
        if re.search(r"warn|extend|stay signed|continue session|countdown|renew|"
                     r"keepAlive|refreshToken", win, re.I):
            continue
        out.append(finding("S-A11Y-TIMEOUT", f, _ln(f.text, m.start()), m.group(0),
                           "A session timeout with no warning and no way to extend it. "
                           "Anyone who reads slowly, uses assistive technology, or steps "
                           "away loses their work (A11Y-008, WCAG SC 2.2.1).", "medium"))
        break
    return out
