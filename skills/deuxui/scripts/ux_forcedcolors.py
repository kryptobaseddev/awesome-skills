#!/usr/bin/env python3
"""R-FORCED-COLORS -- run the page normally and again with forced-colors emulated,
and record what it lost.

  ux_forcedcolors.py --out .deuxui/reports/runtime --route /

Requires a page already open in agent-browser. It reaches the browser's own CDP
endpoint (scripts/cdp.py) because `Emulation.setEmulatedMedia` with a
`forced-colors` feature is the only honest way to enter this mode, and
agent-browser's `set media` does not expose it. The detector reported NOT_RUN for
a long time with the reason "the driver cannot emulate forced-colors" -- true of
the driver, false of the browser behind it.

Two passes, diffed. A forced-colors defect is by definition something that
carried meaning before and does not after, so a single-pass inspection cannot see
one. The second pass samples exactly the elements the first selected; letting it
re-select dropped eleven of fourteen, including every element whose boundary was
painted as a background.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cdp                                                    # noqa: E402

PROBE = HERE / "checks" / "browser" / "forcedcolors.js"


def _visible_ring(f: dict) -> bool:
    """Does this focused element show anything at all?"""
    return (f.get("outlineStyle") not in ("none", "hidden", None)
            and float(f.get("outlineWidth") or 0) > 0) or f.get("shadow") == "yes"


# Which elements are REGIONS. A tint on a region is a boundary; a tint on a text
# element is emphasis, and emphasis survives forced-colors because the text does.
# Without this split the probe flagged every coloured paragraph on the fixture as
# having lost a boundary -- eight findings about nothing, which is how a checker
# gets ignored.
REGION_TAGS = {"div", "section", "aside", "article", "header", "footer", "nav",
               "form", "fieldset", "table", "thead", "tbody", "tr", "td", "th",
               "ul", "ol", "li", "dl", "main", "dialog", "details", "figure",
               "blockquote", "menu", "output"}


def analyse(normal: dict, forced: dict) -> dict:
    findings = []

    # 1. Focus indicators. box-shadow is dropped in forced-colors, so a ring built
    #    from one simply is not there -- Tailwind's `ring-*` utilities are
    #    box-shadow, which makes this the most common modern instance.
    for k, fn in (normal.get("focus") or {}).items():
        ff = (forced.get("focus") or {}).get(k)
        if not ff:
            continue
        if _visible_ring(fn) and not _visible_ring(ff):
            how = "a box-shadow" if fn.get("shadow") == "yes" else "an outline"
            findings.append({
                "kind": "focus-lost", "label": fn.get("label", k),
                "detail": f"focus is shown with {how} normally and with nothing at all "
                          f"in forced-colors mode. box-shadow does not exist in this "
                          f"mode; use `outline` with a non-zero width, which is "
                          f"preserved, and keep `outline-offset` for the gap.",
            })

    # 2. Distinctions encoded as background. One element tinted differently from
    #    its siblings -- a selected row, a status chip, a highlighted cell -- is
    #    colour carrying information, and forced-colors collapses every background
    #    to one value. This is SC 1.4.1 measured at runtime rather than inferred.
    for k, a in (normal.get("elements") or {}).items():
        b = (forced.get("elements") or {}).get(k)
        if not b or a.get("bImg") == "yes":
            continue
        sibs = [s for s in (a.get("sibBg") or []) if s]
        differed = bool(sibs) and any(s != a.get("bg") for s in sibs)
        now_same = all(s == b.get("bg") for s in (b.get("sibBg") or []) if s)
        # A border, an underline or a heavier weight all survive the mode and all
        # carry the same distinction the background was carrying. Only a
        # distinction with none of them is actually lost.
        deco = str(b.get("deco") or "")
        mine = deco + "|" + str(b.get("bWidth") or "")
        group_marks = {str(x) for x in (b.get("sibDeco") or [])}
        kept = (float(a.get("bWidth") or 0) > 0
                or any(m in deco for m in ("underline", "overline", "line-through"))
                # or somebody in the group carries a mark this one does not, which
                # is the same distinction expressed a way the mode preserves
                or any(g and g.split("|")[0] not in ("none", "") for g in group_marks)
                or (group_marks and any(g != mine for g in group_marks)
                    and any("underline" in g or "overline" in g for g in group_marks)))
        if differed and now_same and not kept:
            findings.append({
                "kind": "distinction-lost", "label": a.get("label", k),
                "detail": f"<{a.get('tag')}> is distinguished from its siblings by "
                          f"background colour alone ({a.get('bg')} against "
                          f"{sorted(set(sibs))[:3]}), and in forced-colors every "
                          f"background becomes one system colour, so the distinction "
                          f"disappears. Whatever this colour meant -- selected, "
                          f"succeeded, current -- needs a second cue: a border, an icon, "
                          f"text, or a position (VIS-004, SC 1.4.1).",
            })
            continue

    # 3. Region boundaries painted as backgrounds. A tint on a region is a
    #    boundary; a tint on a paragraph is emphasis, and emphasis survives because
    #    the text does. Only regions are judged here.
    for k, a in (normal.get("elements") or {}).items():
        b = (forced.get("elements") or {}).get(k)
        if not b or a.get("tag") not in REGION_TAGS or a.get("bImg") == "yes":
            continue
        had_bg_boundary = (a.get("bg") and a.get("pBg") and a["bg"] != a["pBg"]
                           and float(a.get("bWidth") or 0) == 0)
        if not had_bg_boundary:
            continue
        if b.get("bg") == b.get("pBg"):
            findings.append({
                "kind": "boundary-lost", "label": a.get("label", k),
                "detail": f"<{a.get('tag')}> is separated from its surroundings by "
                          f"background colour alone ({a.get('bg')} on {a.get('pBg')}), "
                          f"and in forced-colors both become the same system colour, so "
                          f"the boundary disappears. Add a border -- 1px is enough, and "
                          f"border-color IS forced, so it survives.",
            })

    # 4. Explicit opt-outs. Sometimes right -- a colour swatch has to keep its
    #    colour -- and usually somebody silencing the mode rather than supporting it.
    for o in (forced.get("optouts") or [])[:10]:
        findings.append({
            "kind": "opt-out", "label": o.get("label") or o.get("tag"),
            "detail": f"<{o.get('tag')}> sets `forced-color-adjust: none`, which opts it "
                      f"out of the mode entirely. Legitimate for a colour sample the user "
                      f"needs to see; for anything else it defeats the accommodation.",
        })

    # 5. Icons coloured by `fill` rather than `currentColor`. fill is NOT forced, so
    #    a fixed fill can land on a forced background of similar lightness.
    for k, a in (normal.get("elements") or {}).items():
        if a.get("tag") != "svg":
            continue
        fill = str(a.get("fill") or "")
        if not fill or fill in ("none", "currentcolor", "currentColor"):
            continue
        b = (forced.get("elements") or {}).get(k) or {}
        if b.get("adjust") == "none":
            continue
        findings.append({
            "kind": "icon-fill", "label": a.get("label", k),
            "detail": f"an svg painted with a fixed fill ({fill}). `fill` is not "
                      f"overridden in forced-colors, so this colour lands on whatever "
                      f"the system chose for the background. Use `currentColor` so the "
                      f"icon follows the forced text colour.",
            "confidence": "low",
        })

    return {
        "probe": "forcedcolors",
        "emulated": bool(forced.get("mode") == "forced"),
        "paired": len(set((normal.get("elements") or {}))
                      & set((forced.get("elements") or {}))),
        "selected": len(normal.get("elements") or {}),
        "focus_pairs": len(set((normal.get("focus") or {}))
                           & set((forced.get("focus") or {}))),
        "findings": findings,
    }


def run(out_dir: Path, route: str, url: str | None = None) -> int:
    js = PROBE.read_text()
    ws, info = cdp.connect_page(url)
    if ws is None:
        payload = {"probe": "forcedcolors", "emulated": False, "reason": str(info),
                   "findings": []}
        _write(out_dir, route, payload)
        sys.stderr.write(f"forced-colors: {info}\n")
        return 0
    try:
        cdp.set_media(ws, [])
        cdp.evaluate(ws, "window.__uxFcPaths = null; 1")
        normal = cdp.evaluate(ws, js)
        paths = list((normal or {}).get("elements") or {})
        cdp.evaluate(ws, f"window.__uxFcPaths = {json.dumps(paths)}; 1")
        cdp.set_media(ws, [("forced-colors", "active")])
        forced = cdp.evaluate(ws, js)
        if not forced or forced.get("mode") != "forced":
            payload = {"probe": "forcedcolors", "emulated": False,
                       "reason": "Emulation.setEmulatedMedia was accepted but the page "
                                 "still reports (forced-colors: active) as false, so "
                                 "nothing was measured in this mode.",
                       "findings": []}
        else:
            payload = analyse(normal, forced)
    except Exception as e:
        payload = {"probe": "forcedcolors", "emulated": False,
                   "reason": f"{type(e).__name__}: {e}", "findings": []}
    finally:
        try:
            cdp.set_media(ws, [])          # never leave the page emulated
            cdp.evaluate(ws, "window.__uxFcPaths = null; 1")
        except Exception:
            pass
        ws.close()
    _write(out_dir, route, payload)
    n = len(payload.get("findings") or [])
    sys.stderr.write(f"forced-colors: {'emulated' if payload.get('emulated') else 'NOT emulated'}"
                     f", {n} finding(s)\n")
    return 0


def _write(out_dir: Path, route: str, payload: dict):
    slug = (route.strip("/").replace("/", "_") or "root")
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{slug}__forcedcolors.json").write_text(json.dumps(payload, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".deuxui/reports/runtime")
    ap.add_argument("--url", help="the page under test; without it the probe attaches to whichever tab is first, which is wrong the moment two are open")
    ap.add_argument("--route", default="/")
    a = ap.parse_args(argv)
    return run(Path(a.out), a.route, a.url)


if __name__ == "__main__":
    sys.exit(main())
