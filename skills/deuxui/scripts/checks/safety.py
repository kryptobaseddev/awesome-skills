"""P0 checks: privacy, trust, credentials, and the state transitions that lie.

Everything here is severity P0 in the registry -- safety, privacy, security,
data integrity, or irreversible harm. These are the rules where a false negative
costs a user something they cannot get back, so the checks lean toward reporting
a suspicion with a stated confidence rather than staying silent.
"""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")

SECRET = (r"password|passwd|secret|token|api[_-]?key|apikey|auth|credential|"
          r"ssn|social_?security|credit_?card|card_?number|cvv|cvc|iban|"
          r"private_?key|session_?id|bearer")
PII = r"email|phone|address|dob|birth|full_?name|first_?name|last_?name|postcode|zip"


def _line(text, pos):
    return text[:pos].count("\n") + 1


# ------------------------------------------------------------------ NAV-009
@check("S-PRIVACY-URL", exts=SRC)
def secrets_in_url(f, p):
    """A URL is the least private place in a browser: it lands in history, in
    the referer header, in server logs, and in every screenshot someone posts."""
    out = []
    pats = [
        (rf"[?&]({SECRET})=", "query string"),
        (rf"searchParams\.(?:set|append)\(\s*[\"'`]({SECRET})", "searchParams"),
        (rf"(?:router\.(?:push|replace)|history\.(?:push|replace)State|location\.href\s*=)"
         rf"[^\n;]{{0,120}}?[?&]({PII}|{SECRET})=", "client navigation"),
    ]
    for pat, where in pats:
        for m in re.finditer(pat, f.text, re.I):
            out.append(finding("S-PRIVACY-URL", f, _line(f.text, m.start()), m.group(0)[:70],
                               f"Sensitive value in a {where}. URLs are stored in history, "
                               "sent in the Referer header, and logged by every proxy in the "
                               "path. Put it in a POST body or a server session (NAV-009).",
                               "high"))
    return out


# ------------------------------------------------------------------ TRUST-005 / FORM-012
@check("S-SECRET-LOG", exts=SRC)
def secrets_in_logs(f, p):
    """Anything logged reaches somewhere you did not choose: a terminal, a log
    aggregator, an error reporter, a support ticket screenshot."""
    out = []
    sinks = (r"console\.(?:log|info|warn|error|debug)|logger\.\w+|"
             r"Sentry\.(?:capture\w*|setContext|setUser)|"
             r"(?:analytics|track|gtag|mixpanel|posthog|amplitude)\w*\s*[\.(]")
    for m in re.finditer(rf"(?:{sinks})\s*\([^)\n]{{0,200}}", f.text, re.I):
        chunk = m.group(0)
        # A descriptive message that merely mentions the word is not a leak:
        # console.error('Error updating password:', err) logs `err`. Strip every
        # string literal first and look at what is actually being passed.
        args = re.sub(r"[\"'`][^\"'`]*[\"'`]", "''", chunk)
        hit = re.search(rf"\b({SECRET})\b", args, re.I)
        if not hit:
            continue
        if re.search(r"redact|mask|scrub|sanitiz|\*{3,}|omit|\.length\b|Boolean\(|"
                     r"!!|\?\s*['\"]", chunk, re.I):
            continue
        out.append(finding("S-SECRET-LOG", f, _line(f.text, m.start()), chunk[:80],
                           f"`{hit.group(1)}` is going into a log or analytics sink. Redact it "
                           "at the call site -- once it is in an aggregator you cannot take it "
                           "back, and it will outlive the incident (TRUST-005, FORM-012).",
                           "high"))
    return out


@check("S-PASSWORD-HANDLING", exts=SRC)
def password_handling(f, p):
    """Passwords must arrive at the server exactly as typed. Every
    convenience transform is a silent authentication failure for someone."""
    out = []
    for m in re.finditer(r"\b(\w*password\w*)\s*\.\s*(toLowerCase|toUpperCase|trim|replace|"
                         r"normalize|slice|substring)\s*\(\s*\)?[^\n]{0,24}", f.text, re.I):
        # `pw.trim() === ""` and `pw.trim().length` are emptiness checks, not
        # transforms that reach the server. Only a stored/sent result matters.
        if re.search(r"^\s*\)?\s*(?:===?|!==?|\.length|\?|\)\s*(?:\||&))",
                     m.group(0)[len(m.group(1)) + len(m.group(2)) + 2:]):
            continue
        out.append(finding("S-PASSWORD-HANDLING", f, _line(f.text, m.start()), m.group(0),
                           f"`.{m.group(2)}()` applied to a password. Transforming it silently "
                           "locks out anyone whose password relies on that character, and it "
                           "weakens the credential space (FORM-012).", "high"))
    for m in re.finditer(r"(?:localStorage|sessionStorage)\.setItem\(\s*[\"'`][^\"'`]*"
                         rf"(?:{SECRET})[^\"'`]*[\"'`]", f.text, re.I):
        out.append(finding("S-PASSWORD-HANDLING", f, _line(f.text, m.start()), m.group(0)[:70],
                           "A credential is being written to web storage, which is readable by "
                           "any script on the origin and survives until explicitly cleared. Use "
                           "an httpOnly cookie or keep it in memory (FORM-012, TRUST-005).",
                           "high"))
    for t in f.tags:
        if t.name.lower() != "input":
            continue
        name = " ".join(str(t.attr(a) or "") for a in ("name", "id", "autocomplete")).lower()
        if "password" in name and (t.attr("type") or "").lower() not in ("password",):
            out.append(finding("S-PASSWORD-HANDLING", f, t.line, t.raw,
                               'A password field without type="password" renders in plain text '
                               "and is offered to the wrong autofill entry (FORM-012).", "high"))
    return out


# ------------------------------------------------------------------ TRUST-003
@check("S-PERM-ONMOUNT", exts=SRC)
def permission_on_mount(f, p):
    """A permission prompt with no preceding user action has no explanation
    attached, so people deny it reflexively -- and browsers increasingly
    penalise origins that ask this way."""
    out = []
    api = (r"Notification\.requestPermission|navigator\.geolocation\.\w+|"
           r"navigator\.mediaDevices\.getUserMedia|navigator\.\w*[Pp]ermissions?\.request|"
           r"requestPermission\s*\(")
    for m in re.finditer(api, f.text):
        win = f.text[max(0, m.start() - 500):m.start()]
        in_effect = re.search(r"useEffect\s*\(|onMount\s*\(|componentDidMount|"
                              r"\$effect\s*\(|created\s*\(\)|mounted\s*\(\)", win)
        in_handler = re.search(r"on(?:Click|Submit|Press|Change)\s*[=:]|"
                               r"addEventListener\s*\(\s*[\"'`](?:click|submit)", win)
        if in_handler and not in_effect:
            continue
        if not in_effect:
            continue
        out.append(finding("S-PERM-ONMOUNT", f, _line(f.text, m.start()), m.group(0),
                           "Permission requested on mount rather than at the point of need. "
                           "Ask when the user does the thing that requires it, explain why "
                           "first, and keep working when they decline (TRUST-003).", "medium"))
    return out


# ------------------------------------------------------------------ TRUST-002
@check("S-DARK-PATTERN", exts=SRC)
def dark_patterns(f, p):
    """Manufactured urgency and pre-granted consent are not growth tactics,
    they are the things regulators name in enforcement actions."""
    out = []
    # a countdown that resets or is seeded from a constant is not a real deadline
    for m in re.finditer(r"(?:setInterval|setTimeout)\s*\([^)]{0,160}", f.text):
        chunk = m.group(0)
        if not re.search(r"countdown|timeLeft|secondsLeft|expiresIn|urgency|offerEnds", chunk, re.I):
            continue
        win = f.text[max(0, m.start() - 400):m.start() + 400]
        if re.search(r"serverTime|expiresAt|deadline|endsAt|new Date\([^)]+\)", win):
            continue
        out.append(finding("S-DARK-PATTERN", f, _line(f.text, m.start()), chunk[:70],
                           "A countdown with no server-provided deadline is manufactured "
                           "urgency. If the offer really ends, drive it from the real end "
                           "time (TRUST-002).", "medium"))
    # consent that is pre-granted is not consent
    for t in f.tags:
        if t.name.lower() != "input" or (t.attr("type") or "").lower() != "checkbox":
            continue
        # In JSX `checked={expr}` is a controlled binding, which is required
        # syntax and says nothing about the initial value. Only a literal
        # pre-tick counts: bare `checked`, `checked={true}`, `defaultChecked`.
        chk = t.attr("checked")
        dflt = t.attr("defaultChecked")
        literal_on = (chk is not None and str(chk).strip().strip("{}\"' ").lower()
                      in ("", "true", "checked")) or \
                     (dflt is not None and str(dflt).strip().strip("{}\"' ").lower()
                      in ("", "true"))
        if not literal_on:
            continue
        ctx = (t.raw + " " + (f.text[t.end:t.end + 200])).lower()
        if re.search(r"consent|marketing|newsletter|subscribe|share|opt.?in|terms|agree|"
                     r"third.?part|tracking|analytics", ctx):
            out.append(finding("S-DARK-PATTERN", f, t.line, t.raw[:80],
                               "A consent or marketing checkbox is pre-checked. Opt-in must be "
                               "an action the user takes, and in several jurisdictions a "
                               "pre-ticked box is not valid consent (TRUST-002).", "high"))
    for m in re.finditer(r"[\"'`](?:only\s+\d+\s+left|\d+\s+people are viewing|"
                         r"selling fast|almost gone|last chance)[^\"'`]*[\"'`]", f.text, re.I):
        win = f.text[max(0, m.start() - 300):m.start() + 300]
        if re.search(r"\bstock\b|inventory|quantity|count\s*[=:]|fetch|await", win, re.I):
            continue
        out.append(finding("S-DARK-PATTERN", f, _line(f.text, m.start()), m.group(0)[:60],
                           "Scarcity copy not backed by a real quantity. If the number is real, "
                           "read it from inventory; if it is not, remove it (TRUST-002).",
                           "medium"))
    return out


# ------------------------------------------------------------------ CONTENT-010
@check("S-FAKE-STATS", exts=SRC)
def invented_numbers(f, p):
    """An invented statistic is a claim the company cannot support, sitting in
    the product where a regulator or a customer will eventually read it."""
    out = []
    # These land as JSX text at least as often as string literals, so match the
    # claim itself rather than requiring quotes around it.
    pats = [
        (r"\b(?:\d{1,3}(?:,\d{3})+|\d+k|\d+\s*million)\+?\s*"
         r"(?:customers|users|companies|teams|developers|downloads)\b",
         "a customer or user count"),
        (r"\b\d{2,3}(?:\.\d+)?%\s*(?:faster|more|increase|improvement|"
         r"uptime|satisfaction|accuracy)\b", "a performance claim"),
        (r"\b(?:Jane|John)\s+(?:Doe|Smith)\b[^\n]{0,60}(?:CEO|CTO|Founder|Director)",
         "a placeholder testimonial"),
    ]
    for pat, what in pats:
        for m in re.finditer(pat, f.text, re.I):
            out.append(finding("S-FAKE-STATS", f, _line(f.text, m.start()), m.group(0)[:70],
                               f"Hardcoded {what} in the source. If it is real it belongs in "
                               "content with a source; if it is placeholder it must not ship "
                               "(CONTENT-010, TRUST-002).", "medium"))
    return out


# ------------------------------------------------------------------ STATE-002
@check("S-STATE-PREMATURE", exts=SRC)
def premature_success(f, p):
    """Announcing success before the server confirms it means the user walks
    away believing something happened that did not."""
    out = []
    success = (r"toast\.success|notify\.success|showSuccess|"
               r"set(?:Success|Ok|Done|Saved|Sent|Complete[d]?|Submitted)\s*\(\s*true|"
               r"setStatus\s*\(\s*[\"'`](?:success|done|saved)|"
               r"[\"'`][^\"'`]*(?:saved|sent|deleted|updated|created|published)"
               r"[^\"'`]*[\"'`]\s*\)")
    for m in re.finditer(success, f.text, re.I):
        # look backwards within the same handler for an awaited call
        start = max(0, m.start() - 600)
        win = f.text[start:m.start()]
        if re.search(r"\bawait\b|\.then\s*\(|onSuccess|isSuccess|\bres(?:ponse)?\.ok\b", win):
            continue
        if not re.search(r"fetch\s*\(|axios|mutate|supabase|\.post\s*\(|\.put\s*\(|"
                         r"\.patch\s*\(|\.delete\s*\(|useMutation", win, re.I):
            continue
        out.append(finding("S-STATE-PREMATURE", f, _line(f.text, m.start()), m.group(0)[:70],
                           "Success is announced in the same breath as the request, with "
                           "nothing awaited between them. Confirm the durable acknowledgement "
                           "first -- an unconfirmed success is a lie the user acts on "
                           "(STATE-002).", "medium"))
    return out


# ------------------------------------------------------------------ STATE-009
@check("S-DRAFT-BOUNDARY", exts=SRC)
def draft_boundaries(f, p):
    """A draft keyed without the account is another user's draft on a shared
    device, and one that is never cleared outlives the session that made it."""
    out = []
    for m in re.finditer(r"(?:localStorage|sessionStorage)\.setItem\(\s*([^,]{2,80}),", f.text):
        key = m.group(1)
        if not re.search(r"draft|form|unsaved|autosave|compose|editor|wip", key, re.I):
            continue
        if re.search(r"user|account|tenant|org|workspace|\bid\b|session", key, re.I):
            continue
        out.append(finding("S-DRAFT-BOUNDARY", f, _line(f.text, m.start()), m.group(0)[:70],
                           "A draft stored under a key with no account or user in it. On a "
                           "shared device or after an account switch, the next person opens "
                           "someone else's unsent work (STATE-009).", "medium"))
    # Only meaningful when this file actually writes a draft to web storage --
    # otherwise it fires on any module that merely mentions both words.
    writes_draft = re.search(r"(?:localStorage|sessionStorage)\.setItem\([^,]{0,80}"
                             r"(?:draft|autosave|unsaved|compose)", f.text, re.I)
    if writes_draft and re.search(r"\b(?:logout|signOut)\s*\(", f.text, re.I):
        if not re.search(r"(?:localStorage|sessionStorage)\.(?:removeItem|clear)", f.text):
            m = re.search(r"\b(?:logout|signOut)\s*\(", f.text, re.I)
            out.append(finding("S-DRAFT-BOUNDARY", f, _line(f.text, m.start()), m.group(0),
                               "This file stores a draft and handles sign-out but never "
                               "clears it. The next account on this browser inherits the "
                               "previous one's unsent work (STATE-009).", "medium"))
    return out


# ------------------------------------------------------------------ STATE-010 / STATE-011
@check("S-CONFLICT-OVERWRITE", exts=SRC)
def silent_overwrite(f, p):
    """Two people editing one record without a version check means the second
    save silently destroys the first, and nobody is told."""
    out = []
    for m in re.finditer(r"(?:method\s*:\s*[\"'`](?:PUT|PATCH)[\"'`]|\.put\s*\(|\.patch\s*\()",
                         f.text, re.I):
        win = f.text[max(0, m.start() - 500):m.start() + 700]
        if re.search(r"version|etag|If-Match|updated_?at|revision|_rev|lastModified|"
                     r"concurrency|optimisticLock", win, re.I):
            continue
        out.append(finding("S-CONFLICT-OVERWRITE", f, _line(f.text, m.start()), m.group(0),
                           "A full-record update with no version or ETag check. Whoever saves "
                           "second overwrites the first edit silently. Send the version you "
                           "read and let the server reject a stale write (STATE-010).",
                           "low"))
        break        # one per file: the pattern is a project-wide convention,
                     # not a per-call-site mistake
    return out


@check("S-RETRY-SAFETY", exts=SRC)
def unsafe_retry(f, p):
    """Retrying a request whose outcome is unknown is how one payment becomes
    two. The fix is an idempotency key, not a shorter timeout."""
    out = []
    for m in re.finditer(r"\b(retry|onRetry|handleRetry|retryCount|maxRetries|retries)\b",
                         f.text, re.I):
        # `retry: {...}` inside a client/query config applies to reads, where
        # retrying is correct. Only a retry wrapped around a write is a hazard.
        after = f.text[m.end():m.end() + 24]
        if re.match(r"\s*:\s*[\{\d]", after):
            continue
        win = f.text[max(0, m.start() - 500):m.start() + 700]
        if not re.search(r"method\s*:\s*[\"'`]POST|\.post\s*\(|useMutation|mutationFn|"
                         r"charge|payment|checkout|transfer", win, re.I):
            continue
        if re.search(r"idempotenc|Idempotency-Key|dedupe|deduplicat|requestId|"
                     r"reconcil|already\w*(?:Processed|Exists)", win, re.I):
            continue
        out.append(finding("S-RETRY-SAFETY", f, _line(f.text, m.start()), m.group(0),
                           "Retry on a non-idempotent operation with no idempotency key or "
                           "reconciliation. If the first attempt actually succeeded and only "
                           "the response was lost, this commits it twice (STATE-011, "
                           "NUM-020).", "low"))
        break
    return out
