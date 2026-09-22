#!/usr/bin/env python3
"""Turn a reference image into a measurable spec: region bands, a sampled palette,
and which regions are photographic rather than flat.

  comp_spec.py shot.png
  comp_spec.py shot.png --json
  comp_spec.py shot.png --contract      # the colour block, from the real pixels
  comp_spec.py shot.png --provenance "prompt or origin"   # record it IN the file
  comp_spec.py shot.png --read-provenance

Derived from impeccable's `comp-spec` (Apache-2.0) and its rule that the medium of
a region follows from what the pixels ARE, never from what feels buildable -- see
NOTICE.md. Writing CSS for a sculpted panel, or a many-vertex clip-path for a torn
edge, is the quiet deletion of the design somebody approved.

Why this is worth having with no image model at all. `visualize` needs a reference
to spec against; a screenshot of the existing product is one, and that is the
brownfield case. Point this at a screenshot and it tells you the palette the
product actually uses, where its horizontal rhythm changes, and which bands carry
photographic material. All three are things people otherwise eyeball and then
disagree about.

PNG only, 8-bit, non-interlaced -- what agent-browser writes. Another format is
reported as such rather than guessed at.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pngread                                                # noqa: E402


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def hexof(rgb):
    return "#%02x%02x%02x" % rgb


def analyse(img, bands=24, quant=4):
    w, h, ch, buf = img
    step = max(1, w // 320)                 # ~320 columns is plenty for a palette
    rowstep = max(1, h // 900)

    # ---------------------------------------------------------------- palette
    hist = {}
    for y in range(0, h, rowstep):
        base = y * w * ch
        for x in range(0, w, step):
            o = base + x * ch
            key = (buf[o] >> quant, buf[o + 1] >> quant, buf[o + 2] >> quant)
            hist[key] = hist.get(key, 0) + 1
    total = sum(hist.values()) or 1
    mul = 1 << quant
    palette = [{"hex": hexof(tuple(min(255, v * mul + mul // 2) for v in k)),
                "rgb": [min(255, v * mul + mul // 2) for v in k],
                "coverage_pct": round(100.0 * n / total, 2)}
               for k, n in sorted(hist.items(), key=lambda kv: -kv[1])[:12]]

    # ------------------------------------------------------------ region bands
    # Horizontal bands, each described by its dominant colour, its colour spread
    # and its edge density. The interesting output is the CLASSIFICATION: a band
    # with many distinct colours and high edge density is photographic and ships
    # as a raster; a flat band with few colours is semantic and ships as code.
    band_h = max(8, h // bands)
    out_bands = []
    for bi in range(0, h, band_h):
        y0, y1 = bi, min(h, bi + band_h)
        bh = {}
        edges = 0
        samples = 0
        for y in range(y0, y1, max(1, rowstep)):
            base = y * w * ch
            prev = None
            for x in range(0, w, step):
                o = base + x * ch
                px = (buf[o], buf[o + 1], buf[o + 2])
                key = (px[0] >> quant, px[1] >> quant, px[2] >> quant)
                bh[key] = bh.get(key, 0) + 1
                samples += 1
                if prev is not None:
                    d = abs(px[0] - prev[0]) + abs(px[1] - prev[1]) + abs(px[2] - prev[2])
                    if d > 48:
                        edges += 1
                prev = px
        if not samples:
            continue
        distinct = len(bh)
        dom_key, dom_n = max(bh.items(), key=lambda kv: kv[1])
        dom = tuple(min(255, v * mul + mul // 2) for v in dom_key)
        dom_share = dom_n / samples
        edge_density = edges / samples
        # The thresholds are stated, not tuned into invisibility: a band that is
        # more than 60% one colour and has few distinct colours is flat; many
        # colours plus many edges is photographic; the middle is mixed, and mixed
        # is the honest answer rather than a coin toss.
        if distinct <= 8 and dom_share > 0.6:
            kind = "flat"
        elif distinct >= 48 and edge_density > 0.10:
            kind = "plate"
        elif distinct >= 24 or edge_density > 0.06:
            kind = "mixed"
        else:
            kind = "flat"
        out_bands.append({
            "y": y0, "h": y1 - y0,
            "dominant": hexof(dom), "dominant_share_pct": round(100 * dom_share, 1),
            "distinct_colours": distinct,
            "edge_density": round(edge_density, 3),
            "kind": kind,
        })

    # Merge adjacent bands with the same kind and a similar dominant colour: the
    # useful unit is a section, not a 40px slice.
    regions = []
    for b in out_bands:
        if regions and regions[-1]["kind"] == b["kind"] \
                and regions[-1]["dominant"] == b["dominant"]:
            regions[-1]["h"] += b["h"]
            regions[-1]["bands"] += 1
            continue
        r = dict(b)
        r["bands"] = 1
        regions.append(r)

    # ------------------------------------------------------- surfaces and ink
    # The two highest-coverage colours are almost always the canvas and its
    # primary surface; the highest-contrast colour against the canvas is the ink.
    canvas = tuple(palette[0]["rgb"]) if palette else (255, 255, 255)
    ink, best = None, 0.0
    for p in palette[1:]:
        r = ratio(tuple(p["rgb"]), canvas)
        if r > best and p["coverage_pct"] >= 0.3:
            ink, best = tuple(p["rgb"]), r
    return {
        "size": [w, h], "channels": ch,
        "palette": palette,
        "canvas": hexof(canvas),
        "ink": hexof(ink) if ink else None,
        "ink_on_canvas": best if ink else None,
        "regions": regions,
        "counts": {"regions": len(regions),
                   "plate": sum(1 for r in regions if r["kind"] == "plate"),
                   "mixed": sum(1 for r in regions if r["kind"] == "mixed"),
                   "flat": sum(1 for r in regions if r["kind"] == "flat")},
    }


def as_contract(spec) -> str:
    lines = ["# Sampled from a reference image, not declared. Check each role before",
             "# committing it: a pixel read tells you what IS there, not what was meant.",
             "color:", "  space: hex", "  roles:",
             f"    canvas: \"{spec['canvas']}\"",
             f"    ink: \"{spec['ink'] or 'UNKNOWN'}\""]
    for p in spec["palette"][1:7]:
        lines.append(f"    # {p['hex']}  {p['coverage_pct']}% of the image")
    return "\n".join(lines)


def human(spec, path):
    w = sys.stdout.write
    w(f"\ncomp spec -- {path}  {spec['size'][0]}x{spec['size'][1]}\n" + "=" * 74 + "\n")
    w(f"\npalette (quantised, by coverage)\n")
    for p in spec["palette"][:8]:
        bar = "#" * max(1, int(p["coverage_pct"] / 2))
        w(f"  {p['hex']}  {p['coverage_pct']:>6.2f}%  {bar}\n")
    w(f"\n  canvas {spec['canvas']}   ink {spec['ink']}"
      f"   ink on canvas {spec['ink_on_canvas']}:1\n")
    if spec["ink_on_canvas"] and spec["ink_on_canvas"] < 4.5:
        w("  NOTE the most contrasting colour in this image is under 4.5:1 against its\n"
          "       own canvas. Either the reference has no body text in it, or its body\n"
          "       text does not meet the floor.\n")
    w(f"\nregions, top to bottom  ({spec['counts']})\n")
    w(f"  {'y':>6}{'h':>6}  {'kind':<7}{'dominant':<10}{'share':>7}{'colours':>9}{'edges':>8}\n")
    for r in spec["regions"]:
        w(f"  {r['y']:>6}{r['h']:>6}  {r['kind']:<7}{r['dominant']:<10}"
          f"{r['dominant_share_pct']:>6.1f}%{r['distinct_colours']:>9}"
          f"{r['edge_density']:>8.3f}\n")
    w("\nWhat the kinds mean, and why it matters at build time:\n"
      "  flat   few colours, one dominant. Ships as semantic code -- text, controls,\n"
      "         chrome, flat shape systems. Anything that must move, scale or respond.\n"
      "  plate  many colours and many edges. Photographic or illustrated: a figure, a\n"
      "         product, machinery, a named texture. Ships as a raster. Writing CSS for\n"
      "         one of these is not an optimisation, it is a quiet deletion of the\n"
      "         design somebody approved.\n"
      "  mixed  both, in one band. Split it before deciding, or say which half wins.\n"
      "\nThis reads pixels. It cannot tell you what the regions MEAN, which of them is\n"
      "the focal moment, or whether the composition is any good.\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--contract", action="store_true")
    ap.add_argument("--bands", type=int, default=24)
    ap.add_argument("--provenance", metavar="TEXT",
                    help="record where this image came from, inside the file")
    ap.add_argument("--read-provenance", action="store_true")
    a = ap.parse_args(argv)
    p = Path(a.image)

    if a.read_provenance:
        got = pngread.text_chunks(p)
        if not got:
            sys.stderr.write(f"{p} carries no recorded provenance. A generated image with "
                             f"no origin in it is an asset nobody can account for.\n")
            return 1
        print(json.dumps(got, indent=1))
        return 0
    if a.provenance:
        ok = pngread.add_text(p, "deuxui:provenance", a.provenance)
        sys.stderr.write(("recorded in " + str(p)) if ok else
                         f"could not write a text chunk into {p}\n")
        return 0 if ok else 1

    img = pngread.rows(p)
    if img is None:
        sys.stderr.write(
            f"{p} is not an 8-bit non-interlaced PNG, which is the only form this reads "
            f"(it is what agent-browser writes). Convert it and try again -- nothing is "
            f"claimed about an image that was not decoded.\n")
        return 1
    spec = analyse(img, bands=a.bands)
    if a.json:
        print(json.dumps(spec, indent=1))
    elif a.contract:
        print(as_contract(spec))
    else:
        human(spec, p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
