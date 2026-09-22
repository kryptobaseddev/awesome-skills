"""Conformance to the declared visual contract.

Every check here compares the artifact against `.deuxui/design.contract.yaml`
and never against a taste. That is what makes them admissible: the source of
truth is a declaration the project made, so no detector has to decide whether a
ramp is harmonious -- only whether this value is on the list.

Two consequences worth stating, because they are the whole design:

* With no contract, or with a field left UNKNOWN, these report NOT_RUN. A blank
  declaration is not a passing one, and a contract cannot launder its own gaps
  into evidence.
* They measure ESCAPES from the system, not the shape of the system. A probe over
  four real codebases found step counts identical everywhere (11-17 type steps in
  every project) while arbitrary escapes per file separated disciplined codebases
  from sprawling ones by roughly ten times. The escape is the signal; the shape is
  the project's business.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path as _Path
from . import check, finding

# fontindex lives beside the check package, not inside it: it is also a CLI the
# skill documents, and duplicating it here would be two answers to one question.
sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
from ._util import parse_color, rgb_to_oklch, strip_comments

SRC = (".tsx", ".jsx", ".js", ".ts", ".svelte", ".vue", ".astro", ".html", ".htm")


def _has(p, *path):
    """Walk the contract, returning the value only if every level is declared."""
    cur = p.contract or {}
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    if cur in (None, "", [], {}, "UNKNOWN"):
        return None
    return cur


def _needs(p, *path):
    return p.contract and _has(p, *path) is not None


def _line(t, pos):
    return t[:pos].count("\n") + 1


def _css_rules(text):
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
        yield m.start(), m.group(1).strip(), m.group(2)


_RM = re.compile(r"@media[^{]*prefers-reduced-motion\s*:\s*reduce[^{]*\{", re.I)


def _in_reduced_motion(css: str, pos: int) -> bool:
    """Whether `pos` falls inside a prefers-reduced-motion: reduce block."""
    for m in _RM.finditer(css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
            i += 1
        if m.end() <= pos < i:
            return True
    return False


# ------------------------------------------------------------------ type scale
@check("S-CONTRACT-TYPE-SCALE")
def type_scale(f, p):
    """A font size that is not a declared role. Every one is a role nobody named,
    which is how a scale becomes a list of nearby numbers."""
    out = []
    scale = _needs(p, "type", "scale_px") and _has(p, "type", "scale_px")
    if not scale:
        return out
    allowed = {float(x) for x in scale}
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    seen = set()
    for m in re.finditer(r"font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)", hay):
        v = float(m.group(1)) * (16.0 if m.group(2) == "rem" else 1.0)
        if v in allowed or v in seen or not (8 <= v <= 200):
            continue
        seen.add(v)
        near = min(allowed, key=lambda a: abs(a - v))
        out.append(finding("S-CONTRACT-TYPE-SCALE", f, _line(hay, m.start()),
                           m.group(0),
                           f"{v:g}px is not a declared type role. The contract lists "
                           f"{', '.join(f'{x:g}' for x in sorted(allowed))} -- the nearest "
                           f"is {near:g}px. Use the role, or add the step to the contract "
                           f"and say what job it does (VIS-002, VIS-001).", "high"))
    return out


@check("S-CONTRACT-FAMILY")
def type_family(f, p):
    """A font family the contract never declared. Three families is the ceiling
    and a fourth is always somebody's local decision."""
    out = []
    fams = _needs(p, "type", "families") and _has(p, "type", "families")
    if not fams:
        return out
    allowed = {str(v).lower() for v in fams.values() if v}
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    for m in re.finditer(r"font-family\s*:\s*([^;}\n]+)", hay):
        first = m.group(1).split(",")[0].strip().strip("'\"").lower()
        if not first or first in allowed:
            continue
        if re.match(r"^var\(", first) or re.fullmatch(
                r"(?:inherit|initial|unset|revert|sans-serif|serif|monospace|"
                r"cursive|fantasy|system-ui|ui-[\w-]+)", first):
            continue
        out.append(finding("S-CONTRACT-FAMILY", f, _line(hay, m.start()), m.group(0)[:60],
                           f"`{first}` is not a declared family. The contract names "
                           f"{', '.join(sorted(allowed))}. A fourth voice is a decision "
                           f"somebody made locally -- either it belongs to the system or "
                           f"it does not belong (VIS-002, VIS-001).", "high"))
    return out


# ---------------------------------------------------------------------- colour
@check("S-CONTRACT-COLOR")
def color_roles(f, p):
    """A literal colour where the contract declares a role. The role is the point:
    a raw value cannot be re-themed, and dark mode is where that bill arrives."""
    out = []
    if not _needs(p, "color", "roles"):
        return out
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    seen = set()
    for m in re.finditer(r"(?:color|background(?:-color)?|border-color|fill|stroke)"
                         r"\s*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))", hay):
        val = m.group(1).lower()
        if val in seen or re.match(r"^#(?:fff|ffffff|000|000000)$", val):
            continue          # pure black and white are rarely a theming mistake
        seen.add(val)
        out.append(finding("S-CONTRACT-COLOR", f, _line(hay, m.start()), m.group(0)[:50],
                           f"`{val}` is a literal where the contract declares colour "
                           f"roles. Name the role instead -- a literal cannot follow a "
                           f"theme, and it is dark mode that collects on that (VIS-001).",
                           "high"))
    return out


# ----------------------------------------------------------------------- depth
# A surface is a thing that is RAISED -- a card, a dialog, a popover. A form
# control's border, a table rule and a tab underline are structural hairlines:
# they draw a boundary, they claim no elevation, and an input without one fails
# SC 1.4.11. Reading them as depth was a proximity error -- the old check took a
# 400-character window around the declaration, so any border within a few rules of
# a `.card` selector was attributed to it.
_SURFACE_SEL = re.compile(r"card|panel|surface|dialog|modal|sheet|popover|tile|"
                          r"dropdown|menu|toast|drawer", re.I)
_STRUCTURAL_SEL = re.compile(r"\binput\b|\bselect\b|\btextarea\b|\bbutton\b|"
                             r"\bth\b|\btd\b|\btable\b|\bhr\b|\bfieldset\b|"
                             r"tab|field|::|:focus|:hover|:active|\bimg\b|\biframe\b",
                             re.I)


@check("S-CONTRACT-DEPTH-METAPHOR")
def depth_metaphor(f, p):
    """The contract commits to one way of saying 'surface'. Using the other one
    too is not richer, it is undecided."""
    out = []
    metaphor = _needs(p, "depth", "metaphor") and _has(p, "depth", "metaphor")
    if not metaphor:
        return out
    metaphor = str(metaphor).lower()
    other = "box-shadow" if metaphor == "border" else "border"
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    pat = (re.compile(r"box-shadow\s*:\s*(?!none)[^;}\n]+") if metaphor == "border"
           else re.compile(r"border(?:-(?:top|right|bottom|left))?\s*:\s*[1-9]\d*px\s+solid"))
    for pos, sel, body in _css_rules(hay):
        if not _SURFACE_SEL.search(sel) or _STRUCTURAL_SEL.search(sel):
            continue
        m = pat.search(body)
        if not m:
            continue
        out.append(finding("S-CONTRACT-DEPTH-METAPHOR", f, _line(hay, pos),
                           f"{sel[:30]} {{ {m.group(0)[:40]} }}",
                           f"The contract declares depth by `{metaphor}`, and this surface "
                           f"uses {other}. Two metaphors on one system means neither is "
                           f"carrying the elevation (VIS-006, VIS-001).", "medium"))
    return out


@check("S-CONTRACT-ELEVATION")
def elevation_set(f, p):
    """A shadow that is not one of the declared elevations. An elevation set is a
    vocabulary; a one-off shadow is a word nobody else can use."""
    out = []
    elevs = _needs(p, "depth", "elevations") and _has(p, "depth", "elevations")
    if not elevs:
        return out
    declared = {re.sub(r"\s+", " ", str(e)).strip().lower() for e in elevs}
    hay = strip_comments(f.css) if f.css else ""
    if not hay:
        return out
    for m in re.finditer(r"box-shadow\s*:\s*([^;}\n]+)", hay):
        val = re.sub(r"\s+", " ", m.group(1)).strip().lower().rstrip(";")
        if val in ("none", "inherit") or val in declared:
            continue
        if any(v in val or val in v for v in declared):
            continue
        if "var(" in val:
            continue          # a token reference is conformance by construction
        out.append(finding("S-CONTRACT-ELEVATION", f, _line(hay, m.start()),
                           m.group(0)[:64],
                           f"This shadow is not one of the {len(declared)} declared "
                           f"elevations. Use a declared step, or reference it as a token "
                           f"-- a one-off shadow cannot be re-tuned with the system "
                           f"(VIS-001, VIS-006).", "medium"))
    return out


@check("S-CONTRACT-RAMP")
def ramp_steps(f, p):
    """A colour whose lightness is not on the declared ramp.

    The contract template has always said an off-ramp value "is an escape, and
    escapes are the one design signal that discriminates" -- and until now nothing
    read `color.ramp_steps`. A field two scripts write, a template argues for, and
    no detector measures is the exact shape of an unrun check reported as fine, so
    the choice was to implement it or stop claiming it.

    Lightness only, deliberately. Hue and chroma are where a designer legitimately
    varies (a warning amber and a success green share a lightness step and nothing
    else); lightness is the axis a ramp actually fixes, and an off-step lightness is
    what makes two surfaces fail to read as the same tier."""
    out = []
    steps = _needs(p, "color", "ramp_steps") and _has(p, "color", "ramp_steps")
    if not steps:
        return out
    try:
        ladder = sorted(float(s) for s in steps)
    except (TypeError, ValueError):
        return out
    if not ladder:
        return out
    # The token source is where the ramp is DEFINED. Measuring it against itself
    # would report every step as an escape from itself.
    rel = str(getattr(f, "rel", "") or "")
    if any(rel == s or rel.endswith("/" + s) for s in (p.token_sources or [])):
        return out
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    if not hay:
        return out
    roles = _has(p, "color", "roles") or {}
    declared_vals = {str(v).strip().lower() for v in roles.values()
                     if isinstance(v, str)}
    seen = set()
    for m in re.finditer(r"#[0-9a-fA-F]{6}\b(?![\w-])|oklch\([^)]*\)", hay):
        raw = m.group(0)
        low = raw.strip().lower()
        if low in seen or low in declared_vals:
            continue
        rgb = parse_color(raw, p.cssvars)
        if not rgb:
            continue
        L = rgb_to_oklch(rgb)[0]
        # TOL is a perceptual judgement, not a rounding allowance: two surfaces
        # 0.02 apart in OKLCH lightness read as the same tier, and further apart
        # they read as two tiers that do not exist in the system.
        if any(abs(L - s) <= 0.02 for s in ladder):
            continue
        seen.add(low)
        near = min(ladder, key=lambda s: abs(L - s))
        out.append(finding("S-CONTRACT-RAMP", f, _line(hay, m.start()), raw[:40],
                           f"Lightness {L:.3f} is not on the declared ramp; the "
                           f"nearest step is {near:.3f}. A value between two steps "
                           f"reads as a tier the system does not have, and it cannot "
                           f"be re-tuned with the rest (VIS-001).", "medium"))
    return out


# --------------------------------------------------------------------- spacing
@check("S-CONTRACT-RADIUS")
def radius_set(f, p):
    """A radius outside the two the contract declares. Corner radius is one of the
    loudest signals of whether a system exists."""
    out = []
    card = _has(p, "radius", "card_px")
    ctrl = _has(p, "radius", "control_px")
    if card is None and ctrl is None:
        return out
    allowed = {float(v) for v in (card, ctrl) if isinstance(v, (int, float))}
    if not allowed:
        return out
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    seen = set()
    for m in re.finditer(r"border-radius\s*:\s*(\d+(?:\.\d+)?)px", hay):
        v = float(m.group(1))
        if v in allowed or v in seen or v == 0 or v > 200:
            continue
        if v >= 999:
            continue
        seen.add(v)
        out.append(finding("S-CONTRACT-RADIUS", f, _line(hay, m.start()), m.group(0),
                           f"{v:g}px radius; the contract declares "
                           f"{', '.join(f'{x:g}px' for x in sorted(allowed))}. Radius drift "
                           f"is the fastest way a set of components stops looking like one "
                           f"set (VIS-001).", "medium"))
    return out


# ---------------------------------------------------------------------- motion
@check("S-CONTRACT-MOTION")
def motion_budget(f, p):
    """A duration outside the declared band. Motion that varies per component was
    not designed, it accumulated."""
    out = []
    band = _needs(p, "motion", "duration_ms") and _has(p, "motion", "duration_ms")
    if not band or len(band) != 2:
        return out
    lo, hi = float(band[0]), float(band[1])
    hay = strip_comments(f.css) if f.css else strip_comments(f.text)
    seen = set()
    for m in re.finditer(r"(?:transition|animation)(?:-duration)?\s*:[^;}\n]*?"
                         r"(\d+(?:\.\d+)?)(ms|s)\b", hay):
        v = float(m.group(1)) * (1000.0 if m.group(2) == "s" else 1.0)
        if v in seen or v == 0:
            continue
        seen.add(v)
        if lo <= v <= hi:
            continue
        # A long duration on a deliberate, authored moment is legitimate.
        ctx = hay[max(0, m.start() - 200):m.start() + 120]
        if v > hi and re.search(r"hero|intro|onboard|celebrat|confetti|splash", ctx, re.I):
            continue
        # An indefinitely looping animation is not a transition: a spinner turning
        # once every 900ms is a rate, and judging it against a band meant for
        # entrances and state changes reports a defect that does not exist.
        if re.search(r"\binfinite\b", ctx):
            continue
        # Nor is anything inside a reduced-motion block. Its whole job is to leave
        # the band -- usually by making a duration negligible or a loop slow.
        if _in_reduced_motion(hay, m.start()):
            continue
        out.append(finding("S-CONTRACT-MOTION", f, _line(hay, m.start()), m.group(0)[:50],
                           f"{v:g}ms is outside the declared {lo:g}-{hi:g}ms band. "
                           f"{'Slower than this reads as lag' if v > hi else 'Faster than this is not perceived as motion'}"
                           f" -- and a band nobody keeps is not a motion system (NUM-018).",
                           "low"))
    return out


# ------------------------------------------------------------ face availability
@check("S-CONTRACT-FONT-AVAIL", scope="project")
def font_available(f, p):
    """A declared family that nothing provides.

    This is the quietest failure in the whole type layer. The contract names a
    face, the scale and leading are tuned for it, the CSS asks for it, and no file
    in the repository supplies it -- so the browser silently renders the next
    entry in the stack and every downstream judgement is about a typeface nobody
    chose. Nothing in the source looks wrong, which is exactly why it survives."""
    out = []
    fams = (p.contract.get("type") or {}).get("families") if p.contract else None
    if not isinstance(fams, dict) or not any(
            v not in (None, "", "UNKNOWN", "null") for v in fams.values()):
        return out
    try:
        import fontindex
    except ImportError:
        return out
    res = fontindex.analyse(p.root, p.contract)
    for hit in res["findings"]:
        if hit["severity"] == "low":
            continue                       # pairing is craft, not availability
        out.append(finding("S-CONTRACT-FONT-AVAIL", f, 1,
                           f"{hit['role']}: {hit['family']}", hit["detail"],
                           "high" if hit["severity"] == "high" else "medium"))
    return out
