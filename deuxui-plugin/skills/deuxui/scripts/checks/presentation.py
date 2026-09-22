"""Localisation, data honesty, generated-output behaviour, and component state
coverage -- the rules about what the interface shows and how truthfully.
"""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")

AI_DEPS = re.compile(r"^(?:ai|openai|@?anthropic(?:-ai)?/?\w*|@ai-sdk/.+|langchain|"
                     r"@langchain/.+|ollama|mistralai|cohere-ai|@google/generative-ai|"
                     r"@google/genai|groq-sdk|replicate)$", re.I)
CHART_DEPS = re.compile(r"recharts|chart\.js|react-chartjs|victory|nivo|visx|d3|"
                        r"echarts|highcharts|plotly", re.I)


def _ln(t, pos):
    return t[:pos].count("\n") + 1


@check("S-CONTENT-RTL", requires=lambda p: p.has_i18n)
def physical_properties(f, p):
    """Physical properties do not flip. In Arabic or Hebrew a `margin-left`
    stays on the left and the layout comes apart (CONTENT-007)."""
    out = []
    seen = set()
    css_pat = (r"\b(margin|padding)-(left|right)\s*:|\b(left|right)\s*:\s*\d|"
               r"\btext-align\s*:\s*(left|right)\b|\bborder-(left|right)\b")
    tw_pat = r"(?<![\w-])(?:ml|mr|pl|pr|left|right|border-l|border-r|text-left|text-right)-"
    for m in re.finditer(css_pat, f.css or ""):
        key = m.group(0)[:20]
        if key in seen:
            continue
        seen.add(key)
        out.append(finding("S-CONTENT-RTL", f, _ln(f.css, m.start()), m.group(0),
                           "A physical direction property in a project that ships more than "
                           "one locale. Use the logical form (margin-inline-start, "
                           "inset-inline-start, text-align: start) so it mirrors in RTL "
                           "(CONTENT-007).", "low"))
    if not out:
        for m in re.finditer(tw_pat, f.text):
            out.append(finding("S-CONTENT-RTL", f, _ln(f.text, m.start()), m.group(0),
                               "A physical direction utility in a multi-locale project. "
                               "Tailwind's logical equivalents (ms-, me-, ps-, pe-, "
                               "text-start) mirror in RTL; these do not (CONTENT-007).",
                               "low"))
            break
    return out


@check("S-CHART-TRUTH", exts=SRC,
       requires=lambda p: any(CHART_DEPS.search(d) for d in p.deps))
def chart_honesty(f, p):
    """A y-axis that does not start at zero magnifies every difference. Done
    without saying so, the chart argues rather than reports (CONTENT-009)."""
    out = []
    for m in re.finditer(r"domain\s*=?\s*\{?\s*\[\s*(?:'|\")?(\d+)", f.text):
        if m.group(1) == "0":
            continue
        win = f.text[max(0, m.start() - 400):m.start() + 400]
        if re.search(r"truncat|not to scale|baseline|zoom", win, re.I):
            continue
        out.append(finding("S-CHART-TRUTH", f, _ln(f.text, m.start()), m.group(0)[:50],
                           f"A value axis starting at {m.group(1)} rather than zero, with "
                           "nothing saying so. It multiplies the apparent size of small "
                           "differences (CONTENT-009).", "medium"))
    has_axis = re.search(r"<(?:XAxis|YAxis|Axis)\b|scales\s*:", f.text)
    if has_axis and not re.search(r"\b(?:unit|label|name|title)\s*=|aria-label|"
                                  r"<figcaption|summary", f.text, re.I):
        m = has_axis
        out.append(finding("S-CHART-TRUTH", f, _ln(f.text, m.start()), m.group(0),
                           "A chart with axes but no unit, axis label or text summary. The "
                           "numbers are unreadable without seeing the picture, and unusable "
                           "with a screen reader (CONTENT-009, COMP-015).", "medium"))
    return out


@check("S-AI-UNCERTAINTY", exts=SRC,
       requires=lambda p: any(AI_DEPS.match(d) for d in p.deps))
def ai_uncertainty_and_control(f, p):
    """Generated output that cannot be stopped, is never marked uncertain, and
    arrives without its sources invites the user to act on all of it equally
    (AI-002, AI-004, AI-006)."""
    out = []
    if not f.tags:
        return out
    streams = re.search(r"\b(?:useChat|useCompletion|streamText|streamObject|"
                        r"createStreamableValue)\b", f.text)
    if not streams:
        return out
    if not re.search(r"\bstop\b|abort|cancel|\.stop\(|isLoading\s*&&", f.text, re.I):
        out.append(finding("S-AI-UNCERTAINTY", f, _ln(f.text, streams.start()),
                           streams.group(0),
                           "A streaming generation with no stop control. Once it starts the "
                           "user can only wait, including when it is obviously going wrong "
                           "(AI-004).", "medium"))
    if not re.search(r"regenerate|retry|try again|edit|correct", f.text, re.I):
        out.append(finding("S-AI-UNCERTAINTY", f, _ln(f.text, streams.start()),
                           streams.group(0),
                           "No retry or correction path for generated output. Regeneration "
                           "and editing are the whole recovery story for a model that got it "
                           "wrong (AI-004).", "low"))
    if re.search(r"\b(?:citation|source|reference|retriev|rag|context)\b", f.text, re.I) and \
            not re.search(r"href=|<a\b|sourceUrl|\[\d+\]|footnote", f.text):
        out.append(finding("S-AI-UNCERTAINTY", f, _ln(f.text, streams.start()),
                           streams.group(0),
                           "Source-backed output rendered with no link back to the source. "
                           "A summary the reader cannot check is indistinguishable from one "
                           "that was invented (AI-006).", "low"))
    return out


@check("S-AI-STREAM-A11Y", exts=SRC,
       requires=lambda p: any(AI_DEPS.match(d) for d in p.deps))
def streamed_output_accessibility(f, p):
    """A token-by-token live region reads every fragment aloud. The right
    setting announces the result, not the typing (AI-005)."""
    out = []
    if not f.tags:
        return out
    if not re.search(r"\b(?:useChat|useCompletion|streamText|isStreaming)\b", f.text):
        return out
    live = re.search(r"aria-live\s*=\s*[\"'{]?\s*(assertive|polite)", f.text)
    if live and live.group(1) == "assertive":
        out.append(finding("S-AI-STREAM-A11Y", f, _ln(f.text, live.start()), live.group(0),
                           'aria-live="assertive" on streamed output interrupts the user on '
                           "every token. Use polite, and announce the completed message "
                           "rather than the stream (AI-005, A11Y-006).", "medium"))
    elif not live:
        m = re.search(r"\b(?:useChat|useCompletion|streamText)\b", f.text)
        out.append(finding("S-AI-STREAM-A11Y", f, _ln(f.text, m.start()), m.group(0),
                           "Streamed output with no live region at all. A screen-reader user "
                           "gets no indication that a reply arrived (AI-005, A11Y-006).",
                           "low"))
    return out


@check("S-VIS-STATE-COVERAGE", exts=SRC)
def component_state_coverage(f, p):
    """An interactive component needs more than a resting appearance. Hover,
    focus-visible, active and disabled each answer a question the user is
    asking (VIS-004)."""
    out = []
    rel = f.rel.replace("\\", "/")
    if not re.search(r"/(?:ui|components?)/[\w-]*(?:button|input|select|checkbox|"
                     r"radio|switch|toggle|tab)[\w-]*\.[jt]sx$", rel, re.I):
        return out
    cls = f.text
    missing = []
    if not re.search(r"hover:|:hover", cls):
        missing.append("hover")
    if not re.search(r"focus-visible|:focus", cls):
        missing.append("focus-visible")
    if not re.search(r"disabled:|:disabled|\[disabled\]|aria-disabled", cls):
        missing.append("disabled")
    if len(missing) < 2:
        return out
    out.append(finding("S-VIS-STATE-COVERAGE", f, 1, rel,
                       "A shared control component with no " + " and no ".join(missing)
                       + " treatment. Every instance in the product inherits the gap, which "
                       "is why primitives are where state coverage pays (VIS-004).",
                       "medium"))
    return out


@check("S-UX-PREFERENCE-CONTROL", exts=SRC)
def remembered_preferences(f, p):
    """Anything the interface remembers about someone, they should be able to
    see and change. Silent personalisation is the interface deciding for them
    (UX-014)."""
    out = []
    for m in re.finditer(r"(?:localStorage|sessionStorage)\.setItem\(\s*([^,]{2,60}),",
                         f.text):
        key = m.group(1)
        if not re.search(r"pref|theme|density|layout|sidebar|collaps|sort|view|"
                         r"dismiss|onboard|tour|seen", key, re.I):
            continue
        if re.search(r"reset|clear|removeItem|settings|preferences", f.text, re.I):
            continue
        out.append(finding("S-UX-PREFERENCE-CONTROL", f, _ln(f.text, m.start()),
                           m.group(0)[:60],
                           "A remembered preference with no visible way to inspect or reset "
                           "it. The interface keeps deciding and the user cannot tell why "
                           "(UX-014).", "low"))
        break
    return out


@check("S-UX-CONTROL-ALIGNMENT", exts=SRC)
def control_direction_mismatch(f, p):
    """A control whose label points one way and whose effect goes the other is
    a small betrayal the user pays for every time (UX-013)."""
    out = []
    PAIRS = [(r"\bincrease\b|\bmore\b|\bup\b|\bnext\b", r"-\s*1|--|decrement|prev"),
             (r"\bdecrease\b|\bless\b|\bdown\b|\bprev\b", r"\+\s*1|\+\+|increment|next")]
    for t in f.tags:
        if not t.is_interactive():
            continue
        label = (re.sub(r"<[^>]*>", " ", t.inner or "") + " "
                 + str(t.attr("aria-label") or "")).lower()
        handler = str(t.attr("onClick") or t.attr("on:click") or t.attr("@click") or "")
        if not label.strip() or not handler:
            continue
        for lab_pat, bad_pat in PAIRS:
            if re.search(lab_pat, label) and re.search(bad_pat, handler):
                out.append(finding("S-UX-CONTROL-ALIGNMENT", f, t.line,
                                   f'"{label.strip()[:30]}" -> {handler[:40]}',
                                   "The control's label and its effect point in opposite "
                                   "directions (UX-013).", "low"))
                break
    return out
