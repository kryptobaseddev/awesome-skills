#!/usr/bin/env python3
"""Compare what was built against the comp that was approved.

Every other check in this skill compares an artefact to the CONTRACT. That catches a
build that left the system, and it cannot catch a build that stayed inside the system
and is not the thing somebody said yes to. The comp round exists so a structural
decision is made against something visible; nothing until now went back and asked
whether the code did what the chosen picture did.

It is not a pixel diff, and it should not be. A comp is 1024 wide at some arbitrary
height; a screenshot is whatever the viewport is, at whatever scroll position, with
real copy of a different length and real data in place of placeholders. Aligning those
pixel-for-pixel produces a number that moves when nothing meaningful changed, which is
the fastest way to make a check ignored. So this compares what can honestly be
compared -- what each image is MADE OF:

  palette     which of the comp's colours reached the build, weighted by coverage
  ground      canvas and ink, and the contrast between them, measured on both
  structure   the sequence of region kinds (flat / mixed / photographic)

Each dimension reports its own verdict against a stated tolerance, and the ones it
cannot judge say so rather than averaging into a score. What it deliberately cannot
see is stated in the output every time: type, spacing, hierarchy and motion do not
survive this measurement, and a PASS here is not a statement about them.

    comp_diff.py COMP.png BUILT.png
    comp_diff.py COMP.png --url http://localhost:5173/pricing
    comp_diff.py COMP.png BUILT.png --json

Derived from impeccable's `comp-diff` (Apache-2.0) -- see NOTICE.md.

Exit: 0 every dimension it could judge agrees, 2 at least one disagrees, 3 it could
not obtain one of the two images.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pngread                                                       # noqa: E402
import comp_spec                                                     # noqa: E402
from checks._util import rgb_to_oklch                                # noqa: E402

# Stated, not tuned into invisibility. A colour is "the same colour" when it is within
# this distance in OKLab-ish terms -- lightness and chroma in 0-1, hue in degrees.
NEAR_L, NEAR_C, NEAR_H = 0.06, 0.05, 12.0
# A comp colour only has to be matched if it covers at least this much of the comp.
MIN_COVERAGE = 1.0
# Contrast between canvas and ink may drift by this much before it is a different
# ground. 0.5 is below what anyone can see and well inside PNG quantisation.
CONTRAST_TOL = 0.5


def _without_plates(img, spec):
    """The same image with its photographic bands removed, and how much was removed.

    A comp's plate region is a placeholder for a photograph -- in a rendered wireframe
    it is literally a hatched panel captioned "ships as a raster". Its colours are a
    stand-in, not a commitment, and measuring them as design intent is how this check
    produced a confident DIFFERS against a build that was faithful: seventeen per cent
    of the comp was a blue hatch standing in for an image that had not been chosen yet.

    So the palette and the ground are measured on the SEMANTIC area only -- the part
    the comp actually decides. The plate bands are not discarded from the comparison:
    they are what `structure_diff` is about, and a plate that became flat in the build
    is the single most important thing this tool can find."""
    w, h, ch, buf = img
    keep = [(r["y"], r["y"] + r["h"]) for r in spec["regions"] if r["kind"] != "plate"]
    if not keep:
        return img, 100.0
    rows = bytearray()
    kept = 0
    for y0, y1 in keep:
        y0, y1 = max(0, y0), min(h, y1)
        if y1 <= y0:
            continue
        rows += buf[y0 * w * ch: y1 * w * ch]
        kept += y1 - y0
    if kept == 0:
        return img, 100.0
    return (w, kept, ch, bytes(rows)), round(100.0 * (h - kept) / h, 1)


def _load(path: Path) -> dict:
    """The full spec, plus a second one measured with photographic bands removed."""
    img = pngread.rows(path)
    full = comp_spec.analyse(img)
    semantic_img, dropped = _without_plates(img, full)
    sem = comp_spec.analyse(semantic_img) if dropped else full
    full["semantic"] = sem
    full["plate_pct"] = dropped
    return full


def near(a: str, b: str) -> bool:
    """Are these two hex colours the same colour, to a person?"""
    def ok(hexs):
        v = hexs.lstrip("#")
        return rgb_to_oklch(tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)))
    la, ca, ha = ok(a)
    lb, cb, hb = ok(b)
    if abs(la - lb) > NEAR_L or abs(ca - cb) > NEAR_C:
        return False
    # Hue is meaningless on a grey, and comparing it there rejects matching greys.
    if max(ca, cb) < 0.03:
        return True
    d = abs(ha - hb) % 360
    return min(d, 360 - d) <= NEAR_H


def palette_diff(comp: dict, built: dict) -> dict:
    """Which of the comp's colours reached the build, and which of the build's are new."""
    comp, built = comp["semantic"], built["semantic"]
    want = [c for c in comp["palette"] if c["coverage_pct"] >= MIN_COVERAGE]
    got = built["palette"]
    missing, moved, seen_as = [], [], {}
    for c in want:
        m = next((g for g in got if near(c["hex"], g["hex"])), None)
        if m is None:
            missing.append({"hex": c["hex"], "coverage_pct": c["coverage_pct"]})
        elif abs(m["coverage_pct"] - c["coverage_pct"]) > 15:
            moved.append({"hex": c["hex"], "comp_pct": c["coverage_pct"],
                          "built_pct": m["coverage_pct"], "matched": m["hex"]})
        seen_as.setdefault(m["hex"] if m else None, []).append(c["hex"])
    added = [{"hex": g["hex"], "coverage_pct": g["coverage_pct"]} for g in got
             if g["coverage_pct"] >= 5.0
             and not any(near(g["hex"], c["hex"]) for c in comp["palette"])]
    # Two distinct comp colours matching the SAME built colour is a lost tonal step,
    # not two happy matches -- and reporting it as two rows with the same built
    # percentage, which is what this did, reads as a display bug rather than a finding.
    collapsed = [{"built": k, "comp": v} for k, v in seen_as.items()
                 if k is not None and len(v) > 1]
    return {"checked": len(want), "missing": missing, "coverage_shifted": moved,
            "introduced": added, "collapsed": collapsed,
            "verdict": "DIFFERS" if missing or added or collapsed else "AGREES",
            "why": ("every colour the comp commits to is present, and the build "
                    "introduces none of its own"
                    if not (missing or added) else
                    "; ".join(filter(None, [
                        f"{len(missing)} comp colour(s) absent from the build"
                        if missing else "",
                        f"{len(added)} colour(s) in the build that the comp does not "
                        f"have" if added else "",
                        f"{len(collapsed)} tonal step(s) in the comp collapsed to one "
                        f"colour in the build" if collapsed else ""])))}


def ground_diff(comp: dict, built: dict) -> dict:
    """Canvas, ink, and the contrast between them -- on both, measured the same way."""
    def contrast(spec):
        # comp_spec reports this as a bare ratio, not a record. Reading it as a dict
        # returned None for every image, which would have made this dimension report
        # NOT_RUN on input it could measure perfectly well -- the exact laundering this
        # skill exists to prevent, in the code that enforces it.
        if not spec.get("ink"):
            return None
        v = spec.get("ink_on_canvas")
        if isinstance(v, dict):
            v = v.get("ratio")
        return float(v) if isinstance(v, (int, float)) else None
    comp, built = comp["semantic"], built["semantic"]
    cc, bc = contrast(comp), contrast(built)
    rows = {"comp": {"canvas": comp["canvas"], "ink": comp["ink"], "contrast": cc},
            "built": {"canvas": built["canvas"], "ink": built["ink"], "contrast": bc}}
    if cc is None or bc is None:
        return {**rows, "verdict": "NOT_RUN",
                "why": ("one of the two images has no readable ink against its canvas, "
                        "so there is no contrast to compare. A comp that is mostly "
                        "imagery does this.")}
    same_canvas = near(comp["canvas"], built["canvas"])
    same_ink = near(comp["ink"], built["ink"])
    drift = abs(cc - bc)
    ok = same_canvas and same_ink and drift <= CONTRAST_TOL
    return {**rows, "contrast_drift": round(drift, 2), "verdict":
            "AGREES" if ok else "DIFFERS",
            "why": ("the ground is the same and the contrast between canvas and ink "
                    f"matches within {CONTRAST_TOL}"
                    if ok else "; ".join(filter(None, [
                        "" if same_canvas else
                        f"canvas {comp['canvas']} became {built['canvas']}",
                        "" if same_ink else
                        f"ink {comp['ink']} became {built['ink']}",
                        "" if drift <= CONTRAST_TOL else
                        f"contrast moved {drift:.2f} ({cc} to {bc})"])))}


def structure_diff(comp: dict, built: dict) -> dict:
    """The sequence of region kinds. A photographic band that became flat is a rewrite.

    Compared as a SEQUENCE of kinds rather than by count, because three flats and a
    plate in the wrong order is a different design from the same four in the right
    one -- and by count alone the two are identical."""
    cs = [r["kind"] for r in comp["regions"]]
    bs = [r["kind"] for r in built["regions"]]
    lost_plates = cs.count("plate") - bs.count("plate")
    same = cs == bs
    return {"comp": cs, "built": bs,
            "photographic_regions": {"comp": cs.count("plate"),
                                     "built": bs.count("plate")},
            "verdict": "AGREES" if same else
                       ("DIFFERS" if lost_plates > 0 or abs(len(cs) - len(bs)) > 1
                        else "NEAR"),
            "why": ("the same sequence of flat, mixed and photographic regions"
                    if same else
                    f"{lost_plates} photographic region(s) in the comp are not "
                    f"photographic in the build -- a sculpted or photographic panel "
                    f"rebuilt as CSS is the quiet deletion of the design somebody "
                    f"approved" if lost_plates > 0 else
                    f"the region sequence differs ({len(cs)} in the comp, {len(bs)} in "
                    f"the build), which real copy and real data can cause on their own")}


BLIND = ("Type, spacing, hierarchy, interaction and motion are NOT measured here. This "
         "compares what the two images are made of -- colour, ground and region "
         "structure. A build can agree on every dimension above and still be set in "
         "the wrong face at the wrong size: that is what the contract checks and the "
         "browser tier are for.")


WIREFRAME_WHY = (
    "the comp is a WIREFRAME. It settles structure -- what is on the screen, in what "
    "order, at what proportion -- and it settles nothing about colour: its plate bands "
    "are hatched stand-ins for images nobody has chosen yet, and its greys are there to "
    "be looked past. Measuring them against a finished build reports a faithful build "
    "as wrong. Compare colour against a generated or photographed comp, or against the "
    "contract directly with `ux_image.py verify`.")


def compare(comp_path: Path, built_path: Path, wireframe: bool = False) -> dict:
    comp, built = _load(comp_path), _load(built_path)
    out = {"comp": {"path": str(comp_path), "size": comp["size"],
                    "plate_pct": comp["plate_pct"]},
           "built": {"path": str(built_path), "size": built["size"],
                     "plate_pct": built["plate_pct"]},
           "comp_is_wireframe": wireframe,
           "palette": ({"verdict": "NOT_RUN", "why": WIREFRAME_WHY, "checked": 0,
                        "missing": [], "introduced": [], "coverage_shifted": [],
                        "collapsed": []} if wireframe
                       else palette_diff(comp, built)),
           "ground": ({"verdict": "NOT_RUN", "why": WIREFRAME_WHY} if wireframe
                      else ground_diff(comp, built)),
           "structure": structure_diff(comp, built),
           "not_measured": BLIND}
    judged = [out[k]["verdict"] for k in ("palette", "ground", "structure")]
    out["verdict"] = ("DIFFERS" if "DIFFERS" in judged else
                      "NOT_RUN" if all(v == "NOT_RUN" for v in judged) else
                      "AGREES")
    out["counts"] = {"agrees": judged.count("AGREES"), "differs": judged.count("DIFFERS"),
                     "near": judged.count("NEAR"), "not_run": judged.count("NOT_RUN")}
    return out


def capture(url: str, out: Path, width: int | None = None,
            navigate: bool = False) -> tuple[bool, str]:
    """A PNG of `url`, from the browser already running. Same path for a comp or a build.

    `navigate` is for rasterising a comp: the comp is a local file, so the tab has to be
    pointed at it rather than found already open. A BUILD is never navigated to -- the
    page under test is whatever the person has open, and moving it out from under them
    is how a tool loses the state that made the bug interesting."""
    import cdp
    ws, why = cdp.connect_page(None if navigate else url)
    if ws is None:
        return False, str(why)
    try:
        if navigate and not cdp.open_url(ws, url):
            return False, f"the browser would not navigate to {url}"
        if width:
            cdp.set_viewport(ws, width)
        if not cdp.screenshot(ws, out):
            return False, "the browser would not return a screenshot of that page"
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return True, ""


WIREFRAME_MARK = "deuxui:wireframe"


def is_wireframe(src: Path) -> bool:
    """Does this comp say it is a wireframe?

    `ux_image.py render` writes `<desc>deuxui:wireframe ...</desc>` into every sheet it
    draws. Asked of the file rather than derived from the pixels, because deriving it
    was wrong: a hatched plate placeholder has high edge density and FEW distinct
    colours, so `comp_spec` classifies it `mixed`, not `plate`, and an exclusion keyed
    on `plate` skipped exactly the band it existed for. The file knows; the pixels only
    hint."""
    if src.suffix.lower() not in (".svg", ".html", ".htm"):
        return False
    try:
        return WIREFRAME_MARK in src.read_text(errors="replace")[:4000]
    except OSError:
        return False


def as_png(src: Path, out: Path, width: int | None) -> tuple[Path | None, str]:
    """`src` as a PNG. An SVG or HTML comp is rasterised through the browser.

    `ux_image.py render` writes SVG, which is the right format for a comp -- it is
    drawn from declared values, so it has no pixels to be wrong about. But a comparison
    needs pixels on both sides, and rasterising it here means this can consume this
    skill's own comps instead of only rasters somebody produced elsewhere."""
    if src.suffix.lower() == ".png":
        return src, ""
    if src.suffix.lower() not in (".svg", ".html", ".htm"):
        return None, (f"{src.suffix} is not a format this can read. Give a PNG, or an "
                      f"SVG or HTML comp for it to rasterise.")
    ok, why = capture(src.resolve().as_uri(), out, width, navigate=True)
    if not ok:
        return None, (f"{src.name} is an {src.suffix.lstrip('.').upper()} and had to be "
                      f"rasterised through the browser, which failed: {why}")
    return out, ""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("comp", help="the approved comp, as a PNG")
    ap.add_argument("built", nargs="?", help="a PNG of what was built")
    ap.add_argument("--url", help="capture the built page from the open browser instead")
    ap.add_argument("--shot", default=".deuxui/reports/built.png",
                    help="where a captured screenshot is written")
    ap.add_argument("--width", type=int, default=1024,
                    help="viewport width for every capture, so the two are comparable "
                         "(default 1024)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    w = sys.stderr.write

    comp = Path(a.comp)
    if not comp.exists():
        w(f"\n{comp} does not exist. Nothing was compared.\n\n")
        return 3
    wireframe = is_wireframe(comp)
    comp, why = as_png(comp, Path(a.shot).with_name("comp.png"), a.width)
    if comp is None:
        w(f"\nNOT_RUN: {why}\n\n")
        return 3
    if a.url:
        shot = Path(a.shot)
        ok, why = capture(a.url, shot, a.width)
        if not ok:
            w(f"\nNOT_RUN: {why}\n  The comparison needs a picture of the built page. "
              f"Open it (`agent-browser open {a.url}`) or pass a PNG.\n\n")
            return 3
        built = shot
    elif a.built:
        built = Path(a.built)
        if not built.exists():
            w(f"\n{built} does not exist. Nothing was compared.\n\n")
            return 3
        # The build side is rasterised the same way as the comp. An HTML file IS a
        # build, and requiring somebody to screenshot it by hand first would make this
        # unusable on the one input it is most likely to be pointed at.
        built, why = as_png(built, Path(a.shot), a.width)
        if built is None:
            w(f"\nNOT_RUN: {why}\n\n")
            return 3
    else:
        w("\nGive a second PNG, or --url to capture the built page. Nothing was "
          "compared, which is not the same as agreeing.\n\n")
        return 3

    r = compare(comp, built, wireframe)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0 if r["verdict"] != "DIFFERS" else 2

    w(f"\n{comp.name}  {r['comp']['size'][0]}x{r['comp']['size'][1]}"
      f"   vs   {built.name}  {r['built']['size'][0]}x{r['built']['size'][1]}\n")
    if r["comp_is_wireframe"]:
        w("  the comp is a wireframe: colour and ground are NOT compared. Structure is.\n")
    if r["comp"]["plate_pct"] or r["built"]["plate_pct"]:
        w(f"  colour measured on the semantic area only: {r['comp']['plate_pct']}% of "
          f"the comp and {r['built']['plate_pct']}% of the build are photographic "
          f"bands,\n  which commit to no colour. They are compared under structure.\n")
    w("\n")
    for key in ("palette", "ground", "structure"):
        d = r[key]
        w(f"  {d['verdict']:<8} {key}\n           {d['why']}\n")
        if key == "palette":
            for m in d["missing"]:
                w(f"             absent   {m['hex']}  {m['coverage_pct']}% of the comp\n")
            for x in d["introduced"]:
                w(f"             new      {x['hex']}  {x['coverage_pct']}% of the build\n")
            for x in d["coverage_shifted"]:
                w(f"             shifted  {x['hex']}  {x['comp_pct']}% -> "
                  f"{x['built_pct']}% (as {x['matched']})\n")
            for x in d["collapsed"]:
                w(f"             merged   {', '.join(x['comp'])} are all {x['built']} "
                  f"in the build\n")
        if key == "structure" and d["verdict"] != "AGREES":
            w(f"             comp   {' '.join(d['comp']) or '(none)'}\n"
              f"             built  {' '.join(d['built']) or '(none)'}\n")
    w(f"\n  {r['verdict']}\n\n  {BLIND}\n\n")
    return 0 if r["verdict"] != "DIFFERS" else 2


if __name__ == "__main__":
    sys.exit(main())
