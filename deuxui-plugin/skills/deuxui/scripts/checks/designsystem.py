"""Design-system drift: inventing what the project already has."""
from __future__ import annotations
import re
from . import check, finding
from ._util import document_kind, strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro")
CSS = (".css", ".scss", ".sass", ".less")

# Headless primitive libraries. If one is installed, hand-rolling the same
# component is a COMP-001 violation, not a style preference.
PRIMITIVES = {
    "@radix-ui": "Radix UI",
    "@base-ui/react": "Base UI",
    "@base-ui-components/react": "Base UI",
    "@headlessui": "Headless UI",
    "@ark-ui": "Ark UI",
    "react-aria-components": "React Aria",
    "@mantine/core": "Mantine",
    "bits-ui": "Bits UI",
    "melt": "Melt UI",
    "radix-vue": "Radix Vue",
    "reka-ui": "Reka UI",
}
# Components these libraries already solve, with the accessibility work done.
SOLVED = ("dialog", "modal", "dropdown", "popover", "tooltip", "select", "combobox",
          "accordion", "tabs", "slider", "switch", "checkbox", "radiogroup",
          "menu", "toast", "collapsible", "navigationmenu", "contextmenu",
          "hovercard", "progress", "scrollarea", "toggle", "avatar", "alertdialog")


# Only 3, 4, 6 and 8 hex digits are colours; {3,8} admitted 5 and 7, which no
# colour has. `(?<!&)` keeps HTML entities (`&#8212;`) out.
_HEX = re.compile(r"(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{4}|[0-9a-fA-F]{3})"
                  r"\b(?![\w-])|rgba?\([^)]*\)|oklch\([^)]*\)|hsla?\([^)]*\)")
# Where a colour literal is written: a CSS value, a prop, an arbitrary Tailwind
# value, an argument, a string. An all-digit hex anywhere else is a PR number,
# an issue, an invoice -- "Fixed in #856", "mailbox #4784".
_COLOUR_POS = re.compile(r"[:=(\[,'\"`]\s*$")
# QR builders keep literal colours or scanners fail. Email and PDF come from the
# shared document_kind(): neither has a cascade, so a literal is not an escaped token.
_QR = re.compile(r"""from\s+['"](?:qrcode(?:\.react)?|react-qr-code|qr-code-styling)['"]""")


@check("S-TOKEN-HEX", requires=lambda p: bool(p.cssvars))
def raw_colors(f, p):
    """A literal colour in a component is a token that escaped. It will not
    follow the theme, will not flip in dark mode, and nobody will find it.

    A field report found this rule firing on 26 pull-request numbers in comments
    and prose, and on a file with no colour in it at all. Comments are blanked
    before matching, and an all-digit hex has to sit where a colour is written."""
    out = []
    if f.ext in CSS and re.search(r"@theme|:root", f.text):
        return out                      # this file is where colours are allowed to live
    if _QR.search(f.text) or document_kind(f.path, f.text) in ("email", "pdf"):
        return out
    text = strip_comments(f.text)
    seen = set()
    for m in _HEX.finditer(text):
        val = m.group(0)
        if val.lower() in ("#fff", "#ffffff", "#000", "#000000") or val in seen:
            continue
        if val.startswith("#") and val[1:].isdigit() and not _COLOUR_POS.search(
                text[max(0, m.start() - 24):m.start()]):
            continue
        ctx = text[max(0, m.start() - 60):m.start()]
        if "--" in ctx or "stopColor" in ctx or "currentColor" in ctx:
            continue
        seen.add(val)
        line = text[:m.start()].count("\n") + 1
        out.append(finding("S-TOKEN-HEX", f, line, val,
                           "Hardcoded colour in a project that defines theme variables. Use "
                           "the semantic token so it follows the theme and dark mode "
                           "(VIS-001).", "high"))
    return out


@check("S-TOKEN-ARBITRARY", exts=SRC, requires=lambda p: p.has_tailwind)
def arbitrary_values(f, p):
    out = []
    seen = set()
    for m in re.finditer(r"(?<![\w-])((?:p|m|gap|space|w|h|rounded|top|left|right|"
                         r"bottom|inset)[a-z-]*)-\[([^\]]+)\]", f.text):
        val = m.group(2)
        if val.startswith(("var(", "--", "calc(")) or "%" in val or val.endswith(("vw", "dvh", "svh", "cqi", "cqw")):
            continue
        num = re.match(r"^(\d+(?:\.\d+)?)px$", val)
        if not num:
            continue
        px = float(num.group(1))
        unit = p.num("spacing", "base_unit_px", 4)
        if (unit and px % unit == 0) or m.group(0) in seen:
            continue
        seen.add(m.group(0))
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-TOKEN-ARBITRARY", f, line, m.group(0),
                           f"{px:g}px is off the {unit:g}px spacing scale. One-off values are how a "
                           "system turns back into a pile of magic numbers -- snap to the "
                           "scale, or add a named step if the scale is genuinely missing one "
                           "(VIS-001, NUM-017).", "high"))
    return out


@check("S-DS-REINVENT", exts=SRC,
       requires=lambda p: any(k in d for d in p.deps for k in PRIMITIVES))
def reinventing_primitives(f, p):
    lib = next((name for k, name in PRIMITIVES.items()
                for d in p.deps if k in d), "your primitive library")
    out = []
    for m in re.finditer(r"(?:export\s+)?(?:function|const)\s+([A-Z]\w+)", f.text):
        name = m.group(1)
        base = re.sub(r"(?:Root|Trigger|Content|Portal|Provider)$", "", name).lower()
        if base not in SOLVED:
            continue
        head = f.text[:4000]
        if re.search(r"@radix-ui|@base-ui|@headlessui|@ark-ui|react-aria|bits-ui|"
                     r"reka-ui|radix-vue|melt|from\s+[\"']@/components/ui/", head):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-DS-REINVENT", f, line, m.group(0),
                           f"`{name}` reimplements a component {lib} already ships with focus "
                           "management, keyboard support and ARIA solved. Compose the "
                           "existing primitive before writing a new one (COMP-001, CTX-001).",
                           "medium"))
    return out


@check("S-DS-NEWDEP", exts=SRC, requires=lambda p: bool(p.deps))
def undeclared_ui_dep(f, p):
    out = []
    KNOWN_UI = re.compile(r"^(@?[\w.-]+(?:/[\w.-]+)?)")
    for m in re.finditer(r"from\s+[\"']([^\"'.][^\"']*)[\"']", f.text):
        spec = m.group(1)
        if spec.startswith(("@/", "~/", "#")):
            continue
        pkg = KNOWN_UI.match(spec).group(1)
        if spec.startswith("@") and spec.count("/") >= 1:
            pkg = "/".join(spec.split("/")[:2])
        else:
            pkg = spec.split("/")[0]
        if pkg in p.deps:
            continue
        if not re.search(r"ui|icon|chart|motion|animat|form|table|toast|modal|dialog|"
                         r"carousel|picker|editor|three|drei", pkg, re.I):
            continue
        line = f.text[:m.start()].count("\n") + 1
        out.append(finding("S-DS-NEWDEP", f, line, spec,
                           f"`{pkg}` is imported but not in the project manifest. Adding a UI "
                           "dependency for something the existing stack already covers is how "
                           "an interface ends up with three button components (CTX-001).",
                           "high"))
    return out
