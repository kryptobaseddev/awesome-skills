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
                          r"\bEmptyState\b|\bnoResults\b|!\w+\?\.length|\.length\s*>\s*0")


def _window(text, pos, before=700, after=1400):
    return text[max(0, pos - before):pos + after]


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
        if name in seen:
            continue
        seen.add(name)
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
        if ERROR_SIGNAL.search(win):
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
        if PENDING_SIGNAL.search(win):
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
