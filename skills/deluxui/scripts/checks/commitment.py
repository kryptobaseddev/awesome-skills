"""P0 checks around the moment of commitment: money, authorization, and
anything a model generated that a user is about to act on.

The shared failure these guard against is a user committing to something whose
cost, recipient, or reliability was never put in front of them.
"""
from __future__ import annotations
import re
from . import check, finding
from ._util import strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
SERVER = (".ts", ".js", ".mjs")

# Deliberately narrow. "Confirm" and "Submit" appear on every modal in every
# app; treating them as financial commitments buries the real ones.
COMMIT_VERB = (r"\bpay\b|\bpay now\b|purchase|checkout|check out|charge|subscribe|"
               r"place order|\bbuy\b|donate|upgrade plan|renew|transfer|send money|"
               r"start (?:trial|subscription)")
MONEY_CONTEXT = (r"currency|Intl\.NumberFormat|\bprice\b|\bamount\b|\btotal\b|"
                 r"subtotal|invoice|stripe|paypal|checkout|billing|\bplan\b|USD|EUR|GBP")


def _line(text, pos):
    return text[:pos].count("\n") + 1


def _submit_controls(f):
    """Controls whose label reads like a financial or legal commitment.

    Gated on the file having money context at all, because a "Confirm" in a
    settings dialog is not a purchase and reporting it as one is how a P0
    finding stops being read.
    """
    if not re.search(MONEY_CONTEXT, f.text, re.I):
        return
    for t in f.tags:
        if not t.is_interactive():
            continue
        if t.name.lower() in ("input", "select", "textarea") and \
                (t.attr("type") or "").lower() not in ("submit", "button"):
            continue
        label = (re.sub(r"<[^>]*>", " ", t.inner or "") + " "
                 + str(t.attr("aria-label") or "") + " " + str(t.attr("value") or ""))
        if re.search(COMMIT_VERB, label, re.I):
            yield t, " ".join(label.split())[:60]


# ------------------------------------------------------------------ TRUST-001 / FORM-013 / FORM-014
@check("S-COMMIT-DISCLOSURE", exts=SRC)
def commitment_disclosure(f, p):
    """Cost, recurrence and recipient have to be visible before the button,
    not on the receipt. After the commitment it is an apology, not a disclosure."""
    out = []
    for t, label in _submit_controls(f):
        win = f.text[max(0, t.start - 2500):t.start]
        has_amount = re.search(r"\b(?:total|amount|subtotal|price|cost)\b|"
                               r"Intl\.NumberFormat|currency", win, re.I)
        has_currency = re.search(r"currency|USD|EUR|GBP|[A-Z]{3}\b|currencyCode", win)
        has_terms = re.search(r"per month|per year|/mo\b|/yr\b|recurring|renews|"
                              r"cancel any ?time|billed", win, re.I)
        missing = []
        if not has_amount:
            missing.append("the amount being committed")
        if has_amount and not has_currency:
            missing.append("an explicit currency")
        if re.search(r"subscribe|renew|upgrade|plan", label, re.I) and not has_terms:
            missing.append("the recurring terms")
        if not missing:
            continue
        out.append(finding("S-COMMIT-DISCLOSURE", f, t.line, f'"{label}"',
                           "A commitment control with no " + " and no ".join(missing)
                           + " shown beforehand. Put the consequence in front of the "
                           "commitment, not on the confirmation screen "
                           "(TRUST-001, FORM-014).", "medium"))
    return out[:8]


@check("S-COMMIT-REVIEW", exts=SRC)
def commitment_review(f, p):
    """Legal, financial and protected-data submissions need a way back:
    review before, or correction after. SC 3.3.4 is explicit about it."""
    out = []
    for t, label in _submit_controls(f):
        win = f.text[max(0, t.start - 2000):t.start + 2000]
        if re.search(r"review|confirm|summary|are you sure|AlertDialog|verify|"
                     r"preview|step\s*[23]|checkout/confirm|undo|refund|cancel order",
                     win, re.I):
            continue
        out.append(finding("S-COMMIT-REVIEW", f, t.line, f'"{label}"',
                           "A financial or legal commitment with no review step, no "
                           "confirmation and no stated reversal path anywhere near it. "
                           "WCAG SC 3.3.4 asks for reversible, checked, or confirmed "
                           "(FORM-013).", "medium"))
    return out[:6]


# ------------------------------------------------------------------ FORM-009 / TRUST-004
@check("S-SERVER-VALIDATION")
def client_only_validation(f, p):
    """Client validation is a convenience. If the server does not repeat it,
    the rule does not exist -- anyone can post past it in one curl."""
    out = []
    is_server = bool(re.search(r"^\s*[\"']use server[\"']|export async function (?:POST|PUT|PATCH|DELETE)"
                               r"|createServerFn|defineEventHandler|app\.(?:post|put|patch)\s*\(",
                               f.text, re.M))
    if not is_server:
        return out
    handlers = list(re.finditer(r"export async function (?:POST|PUT|PATCH|DELETE)|"
                                r"app\.(?:post|put|patch|delete)\s*\(|"
                                r"defineEventHandler\s*\(|[\"']use server[\"']", f.text))
    for m in handlers:
        win = f.text[m.start():m.start() + 1800]
        validated = re.search(r"\bz\.|zod|yup|valibot|joi|ajv|superstruct|typebox|"
                              r"safeParse|\.parse\s*\(|validate\w*\s*\(|assert\w*\s*\(",
                              win, re.I)
        authorized = re.search(r"auth|session|getUser|currentUser|requireUser|"
                               r"permission|can\s*\(|ability|rbac|unauthorized|401|403",
                               win, re.I)
        missing = []
        if not validated:
            missing.append("input validation")
        if not authorized:
            missing.append("an authorization check")
        if not missing:
            continue
        out.append(finding("S-SERVER-VALIDATION", f, _line(f.text, m.start()),
                           m.group(0)[:60],
                           "A server mutation handler with no " + " and no ".join(missing)
                           + ". Whatever the form enforces, this endpoint accepts "
                           "(FORM-009, TRUST-004).", "medium"))
    return out[:6]


@check("S-AUTHZ-UI-ONLY", exts=SRC)
def ui_only_authorization(f, p):
    """Hiding a control is presentation. If the endpoint behind it is open,
    the control was the only thing stopping anyone."""
    out = []
    for m in re.finditer(r"\{\s*(?:is|has|can)(Admin|Owner|Staff|Manager|SuperUser|"
                         r"Permission|Role)\w*\s*&&", f.text):
        win = f.text[m.start():m.start() + 900]
        if not re.search(r"delete|remove|approve|publish|refund|payout|impersonate|"
                         r"promote|billing|settings|export", win, re.I):
            continue
        out.append(finding("S-AUTHZ-UI-ONLY", f, _line(f.text, m.start()), m.group(0)[:60],
                           "A privileged action gated only by a client-side role flag. That "
                           "hides the button; it does not stop the request. Confirm the "
                           "server enforces the same rule -- hidden UI is not access "
                           "control (TRUST-004).", "low"))
    return out[:6]


# ------------------------------------------------------------------ TRUST-008
@check("S-ACCOUNT-CONTEXT", exts=SRC)
def account_context(f, p):
    """Sending to the wrong workspace is a class of mistake people make
    constantly, and it is almost always because the UI never said which one."""
    out = []
    for t, label in _submit_controls(f):
        if not re.search(r"send|transfer|invite|share|publish|export", label, re.I):
            continue
        win = f.text[max(0, t.start - 1800):t.start]
        if re.search(r"workspace|organi[sz]ation|account|tenant|recipient|\bto\b\s*[:=]|"
                     r"currentOrg|activeAccount|sendingAs", win, re.I):
            continue
        out.append(finding("S-ACCOUNT-CONTEXT", f, t.line, f'"{label}"',
                           "A cross-account or outbound action with no visible account, "
                           "workspace or recipient context near it. State which account is "
                           "acting and who receives it, before the button (TRUST-008).",
                           "low"))
    return out[:6]


# ------------------------------------------------------------------ AI-001 / AI-003
# Vercel's SDK is published as plain `ai`, so a substring match would never find
# it and a loose one would match half of npm. Match the package name exactly.
_AI_DEPS = re.compile(r"^(?:ai|openai|@?anthropic(?:-ai)?/?\w*|@ai-sdk/.+|langchain|"
                      r"@langchain/.+|ollama|mistralai|cohere-ai|@google/generative-ai|"
                      r"@google/genai|groq-sdk|replicate)$", re.I)


@check("S-AI-PROVENANCE", exts=SRC,
       requires=lambda p: any(_AI_DEPS.match(d) for d in p.deps))
def ai_output_provenance(f, p):
    """Generated text that looks like a record gets treated as one. The label
    is the only thing separating a suggestion from a fact.

    Gated on the file rendering something: a model call in a service layer has
    no surface to label, and flagging every one of them buries the screens that
    genuinely show unlabelled output."""
    if not f.tags:
        return []
    out = []
    code = strip_comments(f.text)
    # Require a call shape, not the English word "generates" in a sentence.
    gen = re.search(r"\b(?:useChat|useCompletion|streamText|generateText|generateObject|"
                    r"createMessage|chat\.completions|messages\.create|"
                    r"generateContent)\s*[\(<]", code)
    if not gen:
        return out
    # A bare "Draft" or "Assistant" is a product noun, not a provenance marker.
    # Require something that actually tells the reader this was generated.
    labelled = re.search(r"AI[- ]generated|generated by (?:AI|the model)|AI suggestion|"
                         r"suggested by|may be inaccurate|can make mistakes|"
                         r"review before|not verified|double.?check|"
                         r"aria-label=[\"'][^\"']*\bAI\b", f.text, re.I)
    if not labelled:
        out.append(finding("S-AI-PROVENANCE", f, _line(f.text, gen.start()), gen.group(0),
                           "Model output rendered with nothing marking it as generated. A "
                           "suggestion shown like a record gets trusted like one -- label it "
                           "and say it needs checking (AI-001).", "medium"))
    for m in re.finditer(r"\b(?:toolCall|tool_call|functionCall|executeAction|runTool|"
                         r"onToolCall)\b", code):
        win = f.text[max(0, m.start() - 600):m.start() + 900]
        if re.search(r"confirm|approve|review|are you sure|AlertDialog|requireApproval|"
                     r"human.?in.?the.?loop|pending", win, re.I):
            continue
        out.append(finding("S-AI-PROVENANCE", f, _line(f.text, m.start()), m.group(0),
                           "A model-initiated action executed with no review step. Anything "
                           "consequential the model decides to do needs a human confirmation "
                           "before it happens, not an undo after (AI-003).", "medium"))
        break
    return out[:6]
