"""Forms, validation and authentication."""
from __future__ import annotations
import re
from . import check, finding

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")
CSS = (".css", ".scss", ".sass", ".less")

AUTOCOMPLETE_HINT = {
    "email": "email", "tel": "tel", "phone": "tel", "password": "current-password",
    "name": "name", "firstname": "given-name", "lastname": "family-name",
    "address": "street-address", "city": "address-level2", "zip": "postal-code",
    "postcode": "postal-code", "country": "country-name", "card": "cc-number",
    "cvc": "cc-csc", "otp": "one-time-code", "code": "one-time-code",
    "username": "username", "search": "off", "organization": "organization",
}
TYPE_HINT = {"email": "email", "tel": "tel", "phone": "tel", "url": "url",
             "password": "password", "search": "search", "date": "date", "number": "number"}


def _ident(t) -> str:
    return " ".join(str(t.attr(a) or "") for a in
                    ("name", "id", "placeholder", "aria-label", "autocomplete")).lower()


@check("S-FORM-AUTOCOMPLETE", exts=SRC)
def autocomplete(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() != "input":
            continue
        ty = (t.attr("type") or "text").lower()
        if ty in ("hidden", "submit", "button", "reset", "checkbox", "radio", "file", "range"):
            continue
        if t.has("autoComplete", "autocomplete"):
            continue
        ident = _ident(t)
        hit = next((v for k, v in AUTOCOMPLETE_HINT.items() if k in ident or k in ty), None)
        if not hit:
            continue
        out.append(finding("S-FORM-AUTOCOMPLETE", f, t.line, t.raw,
                           f'Add autocomplete="{hit}". Without it browsers and password '
                           "managers cannot fill the field, which is a real accessibility "
                           "barrier and not just a convenience (FORM-003, FORM-011).", "high"))
    return out


@check("S-FORM-INPUTTYPE", exts=SRC)
def input_type(f, p):
    out = []
    for t in f.tags:
        if t.name.lower() != "input":
            continue
        ty = (t.attr("type") or "text").lower()
        if ty not in ("text", ""):
            continue
        ident = _ident(t)
        hit = next((v for k, v in TYPE_HINT.items() if k in ident), None)
        if not hit:
            continue
        out.append(finding("S-FORM-INPUTTYPE", f, t.line, t.raw,
                           f'This looks like a {hit} field typed as text. type="{hit}" gives '
                           "the right mobile keyboard, native validation and autofill.", "high"))
    return out


@check("S-FORM-DISABLED", exts=SRC)
def disabled_submit(f, p):
    out = []
    for m in re.finditer(r"disabled\s*=\s*\{([^}]{0,120})\}", f.text):
        expr = m.group(1)
        if not re.search(r"!?\s*(isValid|valid|canSubmit|formValid|isComplete|dirty|"
                         r"errors?\b|isDirty)", expr):
            continue
        if re.search(r"isSubmitting|isPending|isLoading|loading|submitting|busy", expr):
            continue          # disabling during flight is correct -- that is STATE-003
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-FORM-DISABLED", f, line, m.group(0),
                           "A submit button disabled until the form is valid tells the user "
                           "nothing about what is wrong, and screen readers skip it. Let them "
                           "submit and show the errors instead (FORM-007).", "medium"))
    return out


@check("S-FORM-PASTE", exts=SRC)
def paste_blocked(f, p):
    out = []
    for m in re.finditer(r"on(?:Paste|paste|:paste)\s*=\s*\{?[^\n]{0,120}", f.text):
        if "preventDefault" not in m.group(0):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-FORM-PASTE", f, line, m.group(0),
                           "Blocking paste breaks password managers and anyone who cannot "
                           "type long strings reliably. It lowers security in practice "
                           "(FORM-010, WCAG 3.3.8).", "high"))
    return out


@check("S-FORM-VALIDATION")
def premature_validation(f, p):
    """`:invalid` matches before the user has touched the field, so an empty
    required input renders as an error on first paint. `:user-invalid` waits for
    interaction -- it is the modern answer to FORM-005."""
    out = []
    if f.ext in CSS:
        for m in re.finditer(r":invalid\b", f.text):
            line = f.text[:m.start()].count("\n") + 1
            ctx = f.text[max(0, m.start() - 200):m.start() + 200]
            if ":user-invalid" in ctx or ":not(:placeholder-shown)" in ctx or ":focus" in ctx:
                continue
            out.append(finding("S-FORM-VALIDATION", f, line, ":invalid",
                               "Use :user-invalid (and :user-valid). :invalid paints an error "
                               "on a field the user has not filled in yet, which is exactly "
                               "the premature error spam FORM-005 prohibits.", "high"))
        return out
    for m in re.finditer(r"\bvalidat\w*\s*[:=(]|\bmode\s*:\s*[\"']onChange[\"']", f.text):
        if "onChange" not in m.group(0):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-FORM-VALIDATION", f, line, m.group(0),
                           'Validating on every keystroke marks a half-typed value as wrong. '
                           'Validate on blur or submit, then switch to onChange for '
                           're-validation once a field has already errored (FORM-005).',
                           "medium"))
    return out
