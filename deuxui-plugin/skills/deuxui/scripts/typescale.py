#!/usr/bin/env python3
"""Build a type system: a role ladder whose steps are far enough apart to carry
different jobs, with leading tuned to the measure rather than to a habit.

  typescale.py                             # the default operate-mode ladder
  typescale.py --mode persuade --ratio 1.333
  typescale.py --body 17 --measure 68 --mode read
  typescale.py --contract                  # the block to paste into the contract
  typescale.py --css                       # custom properties + role classes
  typescale.py --check .deuxui/design.contract.yaml

Why a tool. The craft floor can tell you that two adjacent roles are within 1.1x
of each other and therefore cannot carry different jobs (S-CRAFT-TYPE-FLAT), and
that a clamp() topping out at 9rem is shouting (S-CRAFT-HERO-SCALE). It could
never tell you what to write instead, so the ladder was invented per project by
whatever felt right and then measured for self-consistency. This produces a
ladder that satisfies those detectors by construction, and states the constraints
it used.

Three things it does that a modular-scale generator does not:

  Leading falls as the measure narrows. A 38ch heading and a 70ch paragraph do
  not want the same line height; one ratio for the whole ladder is the single
  most common typographic tell in generated interfaces.

  Roles, not sizes. A ladder of numbers is not a system -- the system is which
  job each rung does, and the contract records that so a component using
  `text-[19px]` is measurably off it.

  Large roles get tighter tracking, small roles get looser. Optical sizing by
  hand, because the tracking a face needs at 64px is not what it needs at 12px,
  and most variable fonts are not wired to do it for you.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ratio per visitor mode. Persuade and experience surfaces can afford a wide
# jump between display and body because there is little else on the page;
# operate and read surfaces need many distinguishable rungs in a small range, so
# the ratio is smaller and the roles do the work instead.
MODE_RATIO = {"persuade": 1.414, "experience": 1.5, "operate": 1.25,
              "read": 1.25, "native": 1.25}
# The rungs, as multiples of the ratio from the body role. Negative steps down.
ROLES = [("display", 4), ("h1", 3), ("h2", 2), ("h3", 1), ("body", 0),
         ("small", -1), ("caption", -2)]
FLOOR_PX = 12.0          # thresholds.yaml type_craft.ui_text_min_px
DISPLAY_MAX_REM = 6.0    # thresholds.yaml type_craft.display_max_rem
MIN_STEP = 1.25          # thresholds.yaml type_craft.scale_step_ratio_min


def leading(size_px: float, measure_ch: float) -> float:
    """Line height for this size at this measure.

    Two forces, both real. Larger type needs proportionally less leading, because
    the gap is already wide in absolute terms. Wider measures need more, because
    the eye has further to travel back to the start of the next line and a tight
    gap makes it land on the wrong one. A single ratio for the whole ladder gets
    both wrong in opposite directions.
    """
    base = 1.65 - 0.30 * min(1.0, (size_px - 12) / 52)     # 1.65 small -> 1.35 large
    base += (measure_ch - 60) * 0.0035                     # wider measure, more air
    return round(min(1.75, max(1.05, base)), 2)


def tracking(size_px: float) -> float:
    """Tracking in em. Tight at display sizes, open at caption sizes -- what
    optical sizing does automatically in the few faces wired for it, and what
    nothing does in the rest."""
    if size_px >= 48:
        return -0.02
    if size_px >= 32:
        return -0.015
    if size_px >= 20:
        return -0.01
    if size_px <= 13:
        return 0.01
    return 0.0


def build(body=16.0, ratio=None, mode="operate", measure=(45, 75), mono=False):
    ratio = MODE_RATIO.get(mode, 1.25) if ratio is None else ratio
    mid = sum(measure) / 2
    rungs, notes = [], []
    # The big end of a ladder can be dramatic; the small end cannot. A 1.414
    # ratio applied downward from a 16px body puts the caption rung at 8px --
    # not a size choice, a mistake. Descending steps therefore use the calm
    # ratio whatever the mode, which is a real typographic constraint and not a
    # workaround: display contrast is a decision about the top of the scale.
    down = min(ratio, 1.25)
    for name, step in ROLES:
        px = body * (ratio ** step) if step > 0 else body * (down ** step)
        if name == "display":
            cap = DISPLAY_MAX_REM * 16
            if px > cap:
                notes.append(f"display wanted {px:.0f}px at ratio {ratio}; clamped to "
                             f"the {DISPLAY_MAX_REM:g}rem ceiling. Past this a heading "
                             f"reads as loud rather than leading -- take the emphasis "
                             f"from weight, space and colour instead (S-CRAFT-HERO-SCALE).")
                px = cap
        px = round(px, 1)
        if px < FLOOR_PX:
            # Drop the rung rather than emit it. A ladder with six usable roles
            # is a system; a seventh at 10px is a role nobody can read, and
            # keeping it only so the scale looks complete is how the floor gets
            # crossed on purpose.
            notes.append(f"no {name} rung: it would land at {px:g}px, below the "
                         f"{FLOOR_PX:g}px floor. This ladder has "
                         f"{len(rungs)} roles, which is the number it can carry at a "
                         f"{body:g}px body. Raise the body size if you need another "
                         f"(NUM-015).")
            continue
        m = measure[1] if step <= 0 else max(28, round(measure[1] * (0.72 ** step)))
        rungs.append({
            "role": name, "px": px, "rem": round(px / 16, 3),
            "line_height": leading(px, m if step <= 0 else mid),
            "tracking_em": tracking(px),
            "weight": 700 if step >= 3 else (600 if step >= 1 else 400),
            "measure_ch": m,
        })
    for a, b in zip(rungs, rungs[1:]):
        step = a["px"] / b["px"] if b["px"] else 0
        # Compare with a tolerance: the rungs are rounded to 0.1px for the
        # stylesheet, and 20.0/16.0 comes back as 1.2499999 often enough that a
        # bare `<` reported every correctly built ladder as flat.
        if step < MIN_STEP - 0.005:
            notes.append(f"{a['role']} and {b['role']} differ by {step:.2f}x, under the "
                         f"{MIN_STEP}x minimum. Two roles the reader cannot tell apart "
                         f"cannot carry two different jobs (S-CRAFT-TYPE-FLAT).")
    families = {"display": "UNKNOWN", "body": "UNKNOWN", "mono": "UNKNOWN" if mono else None}
    return {"mode": mode, "ratio": round(ratio, 4), "body_px": body,
            "measure_ch": list(measure), "rungs": rungs, "families": families,
            "notes": notes}


def as_contract(t) -> str:
    fam = t["families"]
    lines = ["type:",
             "  families:",
             f"    display: {fam['display']}       # name it; at most three families total",
             f"    body: {fam['body']}",
             f"    mono: {fam['mono'] if fam['mono'] else 'null'}",
             "  scale_px: [" + ", ".join(str(r["px"]) for r in
                                         sorted(t["rungs"], key=lambda r: r["px"])) + "]",
             f"  measure_ch: [{t['measure_ch'][0]}, {t['measure_ch'][1]}]",
             f"  display_max_rem: {DISPLAY_MAX_REM}"]
    return "\n".join(lines)


def as_css(t) -> str:
    out = [":root {"]
    for r in t["rungs"]:
        out.append(f"  --text-{r['role']}: {r['rem']}rem;")
        out.append(f"  --leading-{r['role']}: {r['line_height']};")
        out.append(f"  --tracking-{r['role']}: {r['tracking_em']}em;")
    out.append("}")
    out.append("")
    for r in t["rungs"]:
        out.append(f".text-{r['role']} {{ font-size: var(--text-{r['role']}); "
                   f"line-height: var(--leading-{r['role']}); "
                   f"letter-spacing: var(--tracking-{r['role']}); "
                   f"font-weight: {r['weight']}; }}")
    return "\n".join(out)


def human(t):
    w = sys.stderr.write
    w(f"\ntype system  mode {t['mode']}  ratio {t['ratio']}  body {t['body_px']:g}px\n")
    w("-" * 76 + "\n")
    w(f"  {'role':<10}{'px':>7}{'rem':>8}{'leading':>9}{'tracking':>10}"
      f"{'weight':>8}{'measure':>9}\n")
    prev = None
    for r in t["rungs"]:
        jump = f"  {prev / r['px']:.2f}x" if prev else ""
        w(f"  {r['role']:<10}{r['px']:>7}{r['rem']:>8}{r['line_height']:>9}"
          f"{r['tracking_em']:>10}{r['weight']:>8}{r['measure_ch']:>9}{jump}\n")
        prev = r["px"]
    for n in t["notes"]:
        w(f"  note  {n}\n")
    w("\n" + ("Every step clears the 1.25x minimum, so S-CRAFT-TYPE-FLAT cannot fire\n"
               "on this ladder. " if not t["notes"] else
               "Read the notes above before using this ladder.\n")
      + "What this does NOT establish: whether the face\n"
      "suits the product, whether the hierarchy matches the content's actual\n"
      "structure, or how any of it survives a German compound noun. Put the real\n"
      "copy in and look.\n")


def check(contract_path: Path) -> int:
    import yaml
    if not contract_path.exists():
        sys.stderr.write(f"no contract at {contract_path}\n")
        return 1
    doc = yaml.safe_load(contract_path.read_text()) or {}
    ty = doc.get("type") or {}
    sizes = sorted(float(s) for s in (ty.get("scale_px") or [])
                   if isinstance(s, (int, float)))
    fams = {k: v for k, v in (ty.get("families") or {}).items()
            if v and str(v).upper() != "UNKNOWN"}
    w, bad = sys.stdout.write, 0
    w(f"declared type system: {contract_path}\n" + "-" * 70 + "\n")
    if not sizes:
        w("  NOT_RUN   no scale_px declared, so nothing was checked\n")
    for a, b in zip(sizes, sizes[1:]):
        step = b / a
        ok = step >= MIN_STEP
        bad += 0 if ok else 1
        w(f"  {'PASS' if ok else 'FAIL':<9} {a:g} -> {b:g}px   {step:.2f}x   "
          f"needs {MIN_STEP}x\n")
    for s in sizes:
        if s < FLOOR_PX:
            bad += 1
            w(f"  FAIL      {s:g}px is below the {FLOOR_PX:g}px floor\n")
        if s > DISPLAY_MAX_REM * 16:
            bad += 1
            w(f"  FAIL      {s:g}px is past the {DISPLAY_MAX_REM:g}rem display ceiling\n")
    if len(fams) > 3:
        bad += 1
        w(f"  FAIL      {len(fams)} families declared ({', '.join(fams)}); three is "
          f"the ceiling and more reads as indecision\n")
    w("-" * 70 + f"\n  {bad} problem(s) in the declared ladder\n")
    return 2 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--body", type=float, default=16.0)
    ap.add_argument("--ratio", type=float)
    ap.add_argument("--mode", default="operate", choices=sorted(MODE_RATIO))
    ap.add_argument("--measure", default="45,75")
    ap.add_argument("--mono", action="store_true", help="the system includes a mono face")
    ap.add_argument("--contract", action="store_true")
    ap.add_argument("--css", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", metavar="CONTRACT")
    a = ap.parse_args(argv)
    if a.check:
        return check(Path(a.check))
    lo, _, hi = a.measure.partition(",")
    t = build(a.body, a.ratio, a.mode, (int(lo), int(hi or lo)), a.mono)
    if a.json:
        print(json.dumps(t, indent=1))
    elif a.contract:
        print(as_contract(t))
    elif a.css:
        print(as_css(t))
    else:
        human(t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
