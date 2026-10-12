"""Pending, empty, error and duplicate-commit coverage.

Gated on the file actually rendering something: a route handler or a utility
module has no user-visible state to get wrong.

These are the states agents skip, because the happy path is the only one you
see while building. Every finding here is a state a real user will reach.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import strip_noncode

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro")

ASYNC_FETCH = re.compile(r"\b(?:await\s+)?(?:fetch|axios|ky|\$fetch|useQuery|useSWR|"
                         r"createQuery|useFetch|useAsyncData|useLoaderData)\s*[(<]")
MUTATION = re.compile(r"\b(?:useMutation|createMutation|useActionState|useFormState|"
                      r"useSubmit|onSubmit|handleSubmit)\b")
ERROR_SIGNAL = re.compile(r"\b(?:isError|error|onError|catch|\.rejected|errorElement|"
                          r"ErrorBoundary|status\s*===\s*[\"']error[\"'])\b")
PENDING_SIGNAL = re.compile(r"\b(?:isPending|isLoading|loading|pending|isFetching|"
                            r"isSubmitting|busy|Suspense|Skeleton|optimistic)\b")
EMPTY_SIGNAL = re.compile(r"\.length\s*(?:===?\s*0|<\s*1)|\.length\s*\?|isEmpty|"
                          r"\bEmptyState\b|\bnoResults\b|!\w+\??\.length|\.length\s*>\s*0")


def _window(text, pos, before=700, after=1400):
    return text[max(0, pos - before):pos + after]


# A query or mutation hook owns the state of the request it wraps, and the UI reads
# that state through its result -- `query.isPending` -- wherever the JSX happens to
# be, often hundreds of lines and several components below the call. A window around
# the call misses it; the binding finds it.
_HOOK_BINDING = re.compile(r"\b(?:const|let|var)\s+(\w+|\{[^}]*\})\s*=\s*(?:useQuery|"
                           r"useSuspenseQuery|useInfiniteQuery|useMutation|useSWR|"
                           r"createQuery|createMutation)\b")
_PENDING_PROPS = r"isPending|isLoading|isFetching|isInitialLoading|status|fetchStatus"
_ERROR_PROPS = r"isError|error|status"


def _hook_reads(text, pos, props):
    """True when the hook whose call (or queryFn/mutationFn) sits at `pos` has its
    `props` read anywhere in the file."""
    owner = None
    for b in _HOOK_BINDING.finditer(text, max(0, pos - 600), pos + 40):
        if b.start() <= pos:
            owner = b
    if owner is None:
        return False
    name = owner.group(1)
    if name.startswith("{"):
        return re.search(rf"\b(?:{props})\b", name) is not None
    return re.search(rf"\b{name}\s*\??\.\s*(?:{props})\b", text) is not None


# A `.map` is a rendered list only when its callback returns markup. `new Map(xs.map(...))`,
# a CSV `rows.map(r => r.join(","))` and a copy-to-clipboard string build have no empty
# state to show, and were the bulk of this rule's hits on a real TanStack app.
_ARROW_HEAD = re.compile(r"\s*(?:async\s+)?(?:\([^()]*\)|\w+)\s*(?::\s*[^=()]+)?=>\s*(\{)?|"
                         r"\s*function\s*\w*\s*\([^()]*\)\s*(\{)")
# `<option>` rows sit under a select whose placeholder option is the empty case.
_MARKUP = r"\(?\s*<(?!option\b)[A-Za-z>]"


def _maps_to_markup(text, end):
    a = _ARROW_HEAD.match(text, end)
    if not a:
        # `.map(renderRow)` / `.map(Row)` render; `.map(csvCell)` / `.map(String)` do not.
        return re.match(r"\s*(?:render\w*|(?!String\b|Number\b|Boolean\b)[A-Z]\w*)\s*\)",
                        text[end:]) is not None
    if a.group(1) or a.group(2):
        return re.search(rf"\breturn\s*{_MARKUP}", text[a.end():a.end() + 800]) is not None
    return re.match(rf"\s*{_MARKUP}", text[a.end():]) is not None


def _literal_list(text, name):
    """`const views = ["library", ...] as const` -- a list the author wrote out, which
    cannot come back empty."""
    d = re.search(rf"\b(?:const|let|var)\s+{name}\s*(?::[^=\n]+)?=\s*\[", text)
    if not d:
        return False
    depth, i = 0, d.end() - 1
    while i < len(text):
        depth += {"[": 1, "]": -1}.get(text[i], 0)
        if depth == 0:
            return "..." not in text[d.end():i]
        i += 1
    return False


@check("S-STATE-EMPTY", exts=SRC)
def empty_state(f, p):
    if not f.tags:
        return []
    """Only lists built from loaded data. A `.map` over a local constant, a
    toast queue or an inline citation list is allowed to render nothing --
    the empty state matters when the user is waiting to see their own data."""
    out = []
    if not ASYNC_FETCH.search(f.text) and not re.search(
            r"\bsupabase\b|\bprisma\b|\bdrizzle\b|\btrpc\b|from\s+[\"']@/lib/api", f.text):
        return out
    seen = set()
    for m in re.finditer(r"\b(\w+)\s*(?:\?\.)?\.map\s*\(", f.text):
        name = m.group(1)
        if name in seen or not _maps_to_markup(f.text, m.end()):
            continue
        seen.add(name)
        if _literal_list(f.text, name):
            continue
        if name[0].isupper() or name in (
                "Object", "Array", "React", "children", "toasts", "messages",
                "citations", "steps", "tabs", "columns", "fields", "options",
                "items_", "entries", "keys", "values", "chunks", "parts"):
            continue
        win = _window(f.text, m.start())
        if EMPTY_SIGNAL.search(win):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-STATE-EMPTY", f, line, m.group(0),
                           f"`{name}` is rendered as a list with no branch for the empty "
                           "case. An empty list and a failed load look identical to the "
                           "user. Say what is missing and offer the first action.", "medium"))
    return out


@check("S-STATE-ERROR", exts=SRC)
def error_state(f, p):
    if not f.tags:
        return []
    out = []
    for m in ASYNC_FETCH.finditer(f.text):
        win = _window(f.text, m.start())
        if ERROR_SIGNAL.search(win) or _hook_reads(f.text, m.start(), _ERROR_PROPS):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-STATE-ERROR", f, line, m.group(0),
                           "Async read with no visible failure path. When this rejects the "
                           "user gets a blank region or a spinner that never stops. Model "
                           "the failure and give it a retry (STATE-001, STATE-006).", "medium"))
    return out


@check("S-STATE-LOADING", exts=SRC)
def loading_state(f, p):
    if not f.tags:
        return []
    out = []
    for m in ASYNC_FETCH.finditer(f.text):
        win = _window(f.text, m.start())
        if PENDING_SIGNAL.search(win) or _hook_reads(f.text, m.start(), _PENDING_PROPS):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-STATE-LOADING", f, line, m.group(0),
                           "No pending state for this request. Acknowledge input within "
                           "about 100ms and show a persistent status past ~1s -- and "
                           "reserve the layout space so nothing jumps (NUM-013, NUM-014).",
                           "medium"))
    return out


# An import is where a name arrives, not where it is called. `import { useMutation }
# from "@tanstack/react-query"` names the hook and invokes nothing, so it can carry no
# in-flight guard and the finding has no fix. It was the top hit in every file that
# used the library, at line 4 or line 6, which is also how a real finding further
# down the same file got buried under it.
_IMPORT_LINE = re.compile(r"""^\s*(?:import\b|export\s+(?:\*|\{)|"""
                          r"""(?:const|let|var)\s+\{?[^=\n]*=\s*require\s*\()""")


def _on_import_line(text: str, pos: int) -> bool:
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return bool(_IMPORT_LINE.match(text[start:end if end != -1 else len(text)]))


@check("S-STATE-DUPE", exts=SRC)
def duplicate_submit(f, p):
    if not f.tags:
        return []
    out = []
    code = strip_noncode(f.text)
    seen_lines = set()
    for m in MUTATION.finditer(code):
        if _on_import_line(code, m.start()):
            continue
        win = _window(code, m.start(), 400, 1400)
        # Word-bounded. Bare `guard` matched inside `UnguardedSubmit`, so a
        # component named for the defect silenced the check that reports it --
        # substring matching on identifiers inverts the meaning of the evidence.
        if re.search(r"\bdisabled\b|\bisPending\b|\bisSubmitting\b|\bisLoading\b|"
                     r"\binFlight\b|\bguard(?:ed|ing)?\b|\bidempotenc|"
                     r"\babortControll|\bonce\b", win, re.I):
            continue
        line = f.text[:m.start()].count("\n") + 1
        # One construct, one finding. `const createMutation = useMutation({...})`
        # matched twice, because the variable name is in the same alternation as the
        # call it is assigned from -- two findings for one mutation is the kind of
        # duplication that makes a report look padded.
        if line in seen_lines:
            continue
        seen_lines.add(line)
        out.append(finding("S-STATE-DUPE", f, line, m.group(0),
                           "Nothing here stops a second activation while the first is still "
                           "in flight. Double-clicking a submit must not commit twice. Guard "
                           "in the UI and deduplicate on the server (STATE-003, NUM-020).",
                           "medium"))
    return out


@check("S-STATE-OPTIMISTIC", exts=SRC)
def optimistic_risk(f, p):
    if not f.tags:
        return []
    out = []
    for m in re.finditer(r"\b(?:onMutate|optimisticUpdate|useOptimistic|setOptimistic|"
                         r"optimisticData)\b", f.text):
        win = _window(f.text, m.start(), 400, 1600)
        risky = re.search(r"\b(delete|remove|destroy|pay|charge|refund|transfer|purchase|"
                          r"cancel|archive|revoke)\b", win, re.I)
        rollback = re.search(r"onError|rollback|revert|previous|snapshot|invalidate", win, re.I)
        if not risky or rollback:
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-STATE-OPTIMISTIC", f, line, m.group(0),
                           "Optimistic update on a consequential action with no rollback in "
                           "sight. Showing a payment or deletion as done before the server "
                           "confirms it is a lie the user acts on (STATE-004, STATE-005).",
                           "low"))
    return out
