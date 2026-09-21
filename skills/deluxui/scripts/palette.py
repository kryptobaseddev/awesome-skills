#!/usr/bin/env python3
"""Seed a colour system in OKLCH, with every pair contrast-checked before it is
written down.

  palette.py --hue 25                      # pick a hue, get a system
  palette.py --seed '#1f6feb'              # keep a brand colour, build around it
  palette.py --seed '#1f6feb' --mode operate --dark
  palette.py --seed '#1f6feb' --contract   # the block to paste into the contract
  palette.py --seed '#1f6feb' --css        # :root custom properties
  palette.py --check .deluxui/design.contract.yaml   # audit a declared palette

Why a tool. `deluxui design` told the agent to "commit to a world" and handed it
nothing to commit with, so the colour decision was made by whatever the model
felt like -- and then checked, afterwards, by detectors that could only measure
consistency with that whim. This makes the first decision as checkable as the
conformance to it: every text role is verified against the surface it will sit
on, and a pair that cannot reach its ratio is reported as such rather than
emitted and hoped for.

Lightness is in OKLCH because OKLCH lightness is perceptually even, so a ramp
step means the same thing at every hue. Chroma is reduced near white and black on
purpose: holding chroma constant to make the numbers tidy produces the muddy
dark step and the neon light step that give generated palettes away.

Roles, not swatches. A colour with no role is decoration, and decoration is not a
colour system.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from checks._util import _oklch_to_rgb, contrast_ratio, hex_to_rgb   # noqa: E402


# --------------------------------------------------------------- sRGB -> OKLCH
def _srgb_to_linear(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_oklch(rgb):
    r, g, b = (_srgb_to_linear(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return (round(L, 4), round(C, 4), round(H, 1))


def oklch(L, C, H):
    return f"oklch({L:.3f} {C:.3f} {H:.1f})"


def rgb_of(L, C, H):
    return _oklch_to_rgb(L, C, H)


def ratio(a, b):
    return round(contrast_ratio(rgb_of(*a), rgb_of(*b)), 2)


# Chroma has to fall off near the ends of the lightness range or the ramp goes
# neon at the top and muddy at the bottom. This is the single most visible
# difference between a palette somebody built and one a loop emitted.
def taper(C, L):
    edge = min(L, 1 - L)                       # 0 at the extremes, 0.5 in the middle
    return round(C * min(1.0, edge / 0.28), 4)


def solve_lightness(target_ratio, against, hue, chroma, darker=True, margin=0.15):
    """The lightness that just clears `target_ratio` against a fixed colour.

    Contrast against a fixed background is monotonic in lightness, so this is a
    clean boundary search: for dark-on-light, the LIGHTEST value that still
    clears the bar; for light-on-dark, the darkest. Written first as a
    maximise-the-ratio loop, it returned L=0.500 for every role regardless of
    what each role needed -- five different requirements producing one colour,
    which is the sort of result that looks like a system and is not one.

    `margin` lands the value slightly past the requirement rather than exactly on
    it. A pair that computes to 4.50 in Python can render at 4.49 after the
    browser rounds the same colour, and a contrast rule is not a place to sit on
    the boundary.

    Returns (L, achieved_ratio, reached). `reached` False means this hue cannot
    make the ratio at this chroma -- a fact worth printing rather than rounding
    away, because the alternative is shipping a pair nobody can read.
    """
    need = target_ratio + margin
    lo, hi = (0.0, against[0]) if darker else (against[0], 1.0)
    best, best_r, found = None, 0.0, False
    for _ in range(48):
        mid = (lo + hi) / 2
        r = ratio((mid, taper(chroma, mid), hue), against)
        if r >= need:
            best, best_r, found = mid, r, True
            # Feasible: push back toward the background for the least extreme
            # colour that still works.
            if darker:
                lo = mid
            else:
                hi = mid
        else:
            if darker:
                hi = mid
            else:
                lo = mid
        if hi - lo < 0.0015:
            break
    if not found:
        # Nothing in range clears it. Report the most extreme end and its real
        # ratio, so the caller can say by how much the hue falls short.
        end = 0.0 if darker else 1.0
        return end, ratio((end, taper(chroma, end), hue), against), False
    return round(best, 3), best_r, True


# ------------------------------------------------------------------- the system
# Per visitor mode, how much of the page colour is allowed to own. Operate and
# read surfaces earn their accent by rarity; persuade and experience surfaces may
# let it carry whole regions. See references/design/visitor-modes.md.
MODES = {
    "persuade":   {"canvas_L": 0.16, "chroma": 0.14, "tint_neutrals": 0.012},
    "experience": {"canvas_L": 0.14, "chroma": 0.16, "tint_neutrals": 0.014},
    "operate":    {"canvas_L": 0.985, "chroma": 0.10, "tint_neutrals": 0.004},
    "read":       {"canvas_L": 0.985, "chroma": 0.08, "tint_neutrals": 0.003},
    "native":     {"canvas_L": 0.985, "chroma": 0.10, "tint_neutrals": 0.0},
}
# Semantic hues. Deliberately not "green = success" as a law: these are the
# conventional readings in the locales this tool is used in, and a product whose
# domain reverses one of them should say so in the contract rather than here.
SEMANTIC = {"success": 150.0, "warning": 75.0, "danger": 27.0}


def build(hue, mode="operate", dark=False, chroma=None):
    cfg = MODES.get(mode, MODES["operate"])
    C = cfg["chroma"] if chroma is None else chroma
    tint = cfg["tint_neutrals"]

    if dark:
        canvas_L, surface_L = 0.155, 0.205
    else:
        canvas_L, surface_L = 0.985, 1.0
    canvas = (canvas_L, taper(tint, canvas_L), hue)
    surface = (surface_L, taper(tint * 0.7, surface_L), hue)

    roles, notes = {}, []

    def place(name, target, against, darker, c=None, hue_=None):
        L, r, ok = solve_lightness(target, against, hue_ if hue_ is not None else hue,
                                   C if c is None else c, darker=darker)
        col = (L, taper(C if c is None else c, L), hue_ if hue_ is not None else hue)
        roles[name] = {"oklch": oklch(*col), "on": "canvas",
                       "contrast": r, "needs": target, "meets": ok}
        if not ok:
            notes.append(f"{name}: the best this hue reaches at chroma "
                         f"{(C if c is None else c):.2f} is {r}:1, short of {target}:1. "
                         f"Lower the chroma or move the hue -- do not ship the pair.")
        return col

    roles["canvas"] = {"oklch": oklch(*canvas), "on": None, "contrast": None,
                       "needs": None, "meets": True}
    roles["surface"] = {"oklch": oklch(*surface), "on": "canvas",
                        "contrast": ratio(surface, canvas), "needs": None, "meets": True}

    # Text first: it has the hardest requirement, so everything else is placed
    # around what the reading colours need rather than the other way round.
    place("ink", 7.0, canvas, darker=not dark, c=tint * 1.5)
    place("muted", 4.5, canvas, darker=not dark, c=tint * 2.0)
    place("interactive", 4.5, canvas, darker=not dark)
    # Focus is judged as a non-text indicator: 3:1 against BOTH the canvas it sits
    # on and the control it outlines, which is the pair everyone forgets.
    place("focus", 3.0, canvas, darker=not dark)
    for name, h in SEMANTIC.items():
        place(name, 4.5, canvas, darker=not dark, hue_=h)

    # The ramp. Nine even lightness steps, chroma tapered, so a value in the code
    # that is not one of these is measurably an escape.
    ramp = []
    for i in range(9):
        L = round(0.97 - i * 0.105, 3)
        ramp.append({"step": i * 100 + 100, "oklch": oklch(L, taper(C, L), hue),
                     "on_canvas": ratio((L, taper(C, L), hue), canvas)})

    pairs = {
        "ink on canvas": roles["ink"]["contrast"],
        "muted on canvas": roles["muted"]["contrast"],
        "interactive on canvas": roles["interactive"]["contrast"],
        "focus on canvas": roles["focus"]["contrast"],
        "surface on canvas": roles["surface"]["contrast"],
    }
    return {"hue": hue, "mode": mode, "dark": dark, "chroma": C,
            "roles": roles, "ramp": ramp, "pairs": pairs, "notes": notes}


# ----------------------------------------------------------------------- output
def as_contract(p) -> str:
    r = p["roles"]
    lines = ["color:",
             "  space: oklch",
             "  roles:"]
    for k in ("canvas", "surface", "ink", "muted", "interactive", "focus",
              "success", "warning", "danger"):
        lines.append(f"    {k}: \"{r[k]['oklch']}\"")
    lines.append("  ramp_steps: [" + ", ".join(f"{s['oklch'].split()[0][6:]}"
                                               for s in p["ramp"]) + "]")
    lines.append(f"  dark_mode: {'composed' if p['dark'] else 'UNKNOWN'}"
                 f"        # run again with --dark and compose it, never invert")
    return "\n".join(lines)


def as_css(p) -> str:
    r = p["roles"]
    out = [":root {"]
    for k, v in r.items():
        out.append(f"  --color-{k}: {v['oklch']};")
    for s in p["ramp"]:
        out.append(f"  --color-brand-{s['step']}: {s['oklch']};")
    out.append("}")
    return "\n".join(out)


def human(p):
    w = sys.stderr.write
    w(f"\ncolour system  hue {p['hue']}  chroma {p['chroma']:.2f}  "
      f"mode {p['mode']}{'  dark' if p['dark'] else ''}\n")
    w("-" * 72 + "\n")
    w(f"  {'role':<13}{'value':<28}{'on canvas':>10}  {'needs':>6}\n")
    for k, v in p["roles"].items():
        need = f"{v['needs']}:1" if v["needs"] else "-"
        got = f"{v['contrast']}:1" if v["contrast"] else "-"
        flag = "" if v["meets"] else "   <-- SHORT"
        w(f"  {k:<13}{v['oklch']:<28}{got:>10}  {need:>6}{flag}\n")
    w(f"\n  ramp: " + "  ".join(f"{s['step']}" for s in p["ramp"]) + "\n")
    for n in p["notes"]:
        w(f"  note  {n}\n")
    w("\nEvery text pair above was measured, not estimated. What this does NOT\n"
      "establish: whether the hue is right for the product, whether the accent is\n"
      "spent on the primary action, or how the palette behaves over an image. Those\n"
      "are decisions; run `ux_check.py` after you apply it and read the result.\n")


def check(contract_path: Path) -> int:
    """Audit a palette that is already declared, pair by pair."""
    import yaml
    if not contract_path.exists():
        sys.stderr.write(f"no contract at {contract_path}. Run `deluxui design` for new "
                         f"work, or scripts/derive_contract.py --write for existing "
                         f"code.\n")
        return 1
    doc = yaml.safe_load(contract_path.read_text()) or {}
    roles = ((doc.get("color") or {}).get("roles") or {})
    def parse(v):
        v = str(v).strip()
        if v.upper() == "UNKNOWN" or not v:
            return None
        if v.startswith("#"):
            return hex_to_rgb(v)
        if v.startswith("oklch("):
            n = [float(x.rstrip("%")) for x in v[6:-1].replace("/", " ").split()[:3]]
            if n[0] > 1:
                n[0] /= 100
            return _oklch_to_rgb(*n)
        return None
    canvas, surface = parse(roles.get("canvas")), parse(roles.get("surface"))
    w = sys.stdout.write
    w(f"declared palette: {contract_path}\n" + "-" * 68 + "\n")
    bad = 0
    checks = [("ink", 4.5), ("muted", 4.5), ("interactive", 4.5), ("focus", 3.0),
              ("success", 4.5), ("warning", 4.5), ("danger", 4.5)]
    for name, need in checks:
        fg = parse(roles.get(name))
        if fg is None:
            w(f"  NOT_RUN   {name:<13} not declared, so nothing was checked\n")
            continue
        for gname, bg in (("canvas", canvas), ("surface", surface)):
            if bg is None:
                continue
            r = round(contrast_ratio(fg, bg), 2)
            ok = r >= need
            bad += 0 if ok else 1
            w(f"  {'PASS' if ok else 'FAIL':<9} {name:<13} on {gname:<8} "
              f"{r:>6}:1  needs {need}:1\n")
    w("-" * 68 + f"\n  {bad} failing pair(s)\n")
    if bad:
        w("\nThese are declared values failing their own requirement, so every screen\n"
          "that conforms to the contract inherits the failure. Fix the palette, not\n"
          "the components.\n")
    return 2 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hue", type=float)
    ap.add_argument("--seed", help="a brand colour to keep, as hex")
    ap.add_argument("--mode", default="operate", choices=sorted(MODES))
    ap.add_argument("--chroma", type=float)
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--contract", action="store_true", help="contract block on stdout")
    ap.add_argument("--css", action="store_true", help="custom properties on stdout")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", metavar="CONTRACT",
                    help="audit an already-declared palette")
    a = ap.parse_args(argv)

    if a.check:
        return check(Path(a.check))

    hue, chroma = a.hue, a.chroma
    if a.seed:
        rgb = hex_to_rgb(a.seed)
        if not rgb:
            sys.stderr.write(f"could not read {a.seed!r} as a hex colour\n")
            return 1
        L, C, H = rgb_to_oklch(rgb)
        hue = H if hue is None else hue
        chroma = C if chroma is None else chroma
        sys.stderr.write(f"seed {a.seed} is {oklch(L, C, H)} -- keeping hue {H} "
                         f"and chroma {C:.3f}\n")
    if hue is None:
        sys.stderr.write("give a --hue (0-360) or a --seed colour to build around\n")
        return 1

    p = build(hue, a.mode, a.dark, chroma)
    if a.json:
        print(json.dumps(p, indent=1))
    elif a.contract:
        print(as_contract(p))
    elif a.css:
        print(as_css(p))
    else:
        human(p)
    return 2 if p["notes"] else 0


if __name__ == "__main__":
    sys.exit(main())
