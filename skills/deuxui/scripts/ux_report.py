#!/usr/bin/env python3
"""deuxui verdict -- merge the static, runtime and manual tiers into one report.

Two modes:
  --collect DIR        interpret raw runtime probe output into DIR/runtime.json
  --merge              combine static + runtime + manual into agent_report.yaml

The gate is deliberately hard to satisfy by accident. A rule nobody checked is
NOT_RUN, NOT_RUN is not a pass, and a release audit with unchecked P0 rules is
BLOCKED. If that feels obstructive, the answer is to run the missing check --
not to reinterpret the status.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# Do not leave .pyc files beside the checks. A directory-source plugin install
# copies the working tree verbatim, so stray bytecode ships to the consumer
# despite being gitignored. Costs ~15ms per run, which nothing here notices.
sys.dont_write_bytecode = True

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uxconfig

RULES = HERE.parent / "references" / "rules"
# Defaults. merge() and collect() rebind this to the project-merged thresholds so
# an overridable value set in .deuxui/ux.config.yaml actually reaches the probes
# that read it -- previously the file was validated and then never consulted.
import rulepack
TH = rulepack.load()[2]


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


# ------------------------------------------------------------ runtime interpretation
def _reflow(raws, out):
    hits, worst = [], None
    floor = TH["reflow"]["min_width_px"]
    for name, d in raws.items():
        if "__layout_" not in name or "offenders" not in d:
            continue
        suffix = name.rsplit("_", 1)[-1].removesuffix(".json")
        if not suffix.isdigit():
            continue        # the landscape capture is read by _orientation
        vp = int(suffix)
        if d.get("page_overflows"):
            worst = min(worst or vp, vp)
            for o in d["offenders"][:5]:
                hits.append(f"{vp}px: <{o['tag']} class=\"{o['cls']}\"> extends to "
                            f"{o['right']}px ({o.get('text','')[:30]})")
    if not hits:
        return ("PASS", f"No horizontal overflow at any tested viewport (floor {floor}px).", [])
    return ("FAIL", f"Page scrolls sideways from {worst}px down.", hits)


def _table_hidden(raws, out):
    """LAY-006 at runtime. R-REFLOW asks whether the page scrolls sideways, and a
    table in its own scroll box never makes it: the offenders were measured and
    then discarded because page_overflows was false. This reads the scroll boxes
    layout.js now records and fails the data tables among them -- the ones whose
    hidden right edge holds row actions or more columns than fit."""
    hits, seen, measured = [], set(), False
    for name, d in raws.items():
        if "__layout_" not in name or "containers" not in d:
            continue
        measured = True
        suffix = name.rsplit("_", 1)[-1].removesuffix(".json")
        route = name.split("__layout_")[0]
        for c in d["containers"]:
            if not c.get("dataTable") or c.get("pinned"):
                continue
            key = (route, c.get("cls"), c.get("lastColumn"))
            if key in seen:
                continue
            seen.add(key)
            last = f', last column "{c["lastColumn"]}"' if c.get("lastColumn") else ""
            hits.append(f"{route} @ {suffix}: {c['columns']}-column table in "
                        f"<{c['tag']} class=\"{c['cls']}\"> -- {c['hiddenPx']}px of "
                        f"{c['contentPx']}px hidden sideways{last}")
    if not measured:
        return ("NOT_RUN", "No layout capture recorded scroll boxes (layout.js predates "
                           "this check, or the layout probe did not run).", [])
    if not hits:
        return ("PASS", "No data table hides columns inside a horizontal scroll box at "
                        "any tested viewport.", [])
    return ("FAIL", f"{len(hits)} data table(s) hide their right edge inside a scroll "
                    "box. Rightmost is where row actions live; a card layout or a "
                    "pinned last column keeps them in view (LAY-006).", hits)


def _table_squeeze(raws, out):
    """LAY-006, the commoner failure. A width:100% table does not overflow if it
    can avoid it; it wraps cell text until the columns fit. R-TABLE-HIDDEN reads
    scrollWidth against clientWidth, which on the field report's eleven-column
    queue was 1118 against 1118 -- a clean fit -- while every row was five lines
    tall. This reads median row height against the cell's own line height."""
    hits, seen, measured = [], set(), False
    for name, d in raws.items():
        if "__layout_" not in name or "tables" not in d:
            continue
        measured = True
        suffix = name.rsplit("_", 1)[-1].removesuffix(".json")
        route = name.split("__layout_")[0]
        for t in d["tables"]:
            if not (t.get("dataTable") and t.get("squeezed")):
                continue
            key = (route, t.get("cls"), t.get("columns"), t.get("lastColumn"))
            if key in seen:
                continue
            seen.add(key)
            wrap = f'; "{t["wrapColumn"]}" wraps most' if t.get("wrapColumn") else ""
            hits.append(f"{route} @ {suffix}: {t['columns']}-column table {t['widthPx']}px "
                        f"wide -- median row {t['rowHeight']}px, about {t['lines']} lines, "
                        f"against a cap of {t['capPx']}px{wrap}")
    if not measured:
        return ("NOT_RUN", "No layout capture recorded table row heights (layout.js "
                           "predates this check, or the layout probe did not run).", [])
    if not hits:
        return ("PASS", "No data table fits its width by wrapping its rows past the "
                        "line cap at any tested viewport.", [])
    return ("FAIL", f"{len(hits)} data table(s) 'fit' by wrapping every row tall. No "
                    "overflow, and unusable: drop or merge columns at this width, or "
                    "switch to a card layout (LAY-006).", hits)


def _targets(raws, out):
    hits = []
    for name, d in raws.items():
        if not name.endswith("__targets.json") or "under_24" not in d:
            continue
        for t in d["under_24"]:
            if not t["spacing_exception_met"]:
                hits.append(f"{t['tag']} \"{t['label']}\" {t['w']}x{t['h']}px, "
                            "and a neighbouring target sits inside its 24px circle")
    if not hits:
        return ("PASS", "Every measured target meets 24px or the SC 2.5.8 spacing "
                        "exception.", [])
    return ("FAIL", f"{len(hits)} targets under 24px with no spacing exception.", hits[:20])


def _target_coarse(raws, out):
    for name, d in raws.items():
        if name.endswith("__targets.json") and "under_44" in d:
            n = len(d["under_44"])
            if n:
                return ("FAIL", f"{n} targets between 24px and the 44px coarse-pointer "
                                "default (NUM-005, a PROJECT default -- not a WCAG "
                                "failure). Fine on a dense desktop view; check a phone.",
                        [f"{t['tag']} \"{t['label']}\" {t['w']}x{t['h']}px"
                         for t in d["under_44"][:15]])
            return ("PASS", "All measured targets reach 44px.", [])
    return ("NOT_RUN", "Target probe produced no output.", [])


def _contrast(raws, out):
    hits, unjudged, unparsed, examined = [], 0, 0, 0
    for name, d in raws.items():
        if not name.endswith("__contrast.json") or "failures" not in d:
            continue
        examined += int(d.get("examined") or 0)
        unparsed += int(d.get("unparsed") or 0)
        # The probe no longer computes a ratio it cannot establish. A backdrop
        # painted by a gradient, an image, or an absolutely positioned sibling is
        # counted here instead -- neither passing nor failing, which is what
        # "nobody could measure it" actually means.
        unjudged += int(d.get("unjudged_count") or 0)
        for fl in d["failures"]:
            if fl.get("backdrop_has_image"):
                unjudged += 1
                continue
            hits.append(f"{fl['ratio']}:1 (needs {fl['need']}:1) {fl['color']} "
                        f"at {fl['fontPx']}px -- \"{fl['text']}\"")
    note = ""
    if unjudged:
        note += (f" {unjudged} of {examined} text runs sit on a backdrop CSS cannot "
                 f"resolve -- an image, a gradient, or a sibling layer -- and were "
                 f"not judged. Only a pixel read settles those, and R-PIXEL-CONTRAST "
                 f"is not implemented, so they are unmeasured rather than passing.")
    if unparsed:
        note += f" {unparsed} colour value(s) were in a format this probe cannot convert."
    if not hits:
        return ("PASS", "Every text run whose backdrop could be resolved meets its "
                        "contrast floor." + note, [])
    return ("FAIL", f"{len(hits)} text runs below their contrast floor." + note, hits[:25])


def _focus(raws, out):
    hits = []
    for name, d in raws.items():
        if not name.endswith("__focus.json") or "focusable" not in d:
            continue
        for e in d["no_visible_focus_style"]:
            hits.append(f"{e['tag']} \"{e['label']}\" looks identical focused and unfocused")
        if d.get("positive_tabindex"):
            hits.append(f"{d['positive_tabindex']} elements carry a positive tabindex")
        if d.get("focus_order_backjumps", 0) > 2:
            hits.append(f"focus jumps back up the page {d['focus_order_backjumps']} times")
    if not hits:
        return ("PASS", "Every focusable control changes appearance when focused.", [])
    return ("FAIL", f"{len(hits)} focus problems measured on the live page.", hits[:20])


def _motion(raws, out):
    for name, d in raws.items():
        if not name.endswith("__motion.json") or "still_moving" not in d:
            continue
        if not d.get("honours_reduced_motion"):
            return ("NOT_RUN", "The reduced-motion preference was not applied to the "
                               "page, so nothing was proven.", [])
        moving = d["still_moving"]
        if not moving:
            return ("PASS", "Nothing animates once reduced motion is requested.", [])
        return ("FAIL", f"{len(moving)} elements still animate under reduced motion.",
                [f"<{m['tag']} class=\"{m['cls']}\"> {m['animation']} {m['duration']}"
                 for m in moving[:15]])
    return ("NOT_RUN", "Motion probe produced no output.", [])


def _vitals(raws, out):
    p = TH["performance"]
    hits, seen = [], False
    for name, d in raws.items():
        if not name.endswith("__vitals.json"):
            continue
        data = (d or {}).get("data") or {}
        seen = True
        lcp = (data.get("lcp") or {}).get("startTime")
        cls = (data.get("cls") or {}).get("score")
        if lcp is not None and lcp / 1000.0 > p["lcp_seconds_p75"]:
            hits.append(f"LCP {lcp/1000:.2f}s exceeds {p['lcp_seconds_p75']}s")
        if cls is not None and cls > p["cls_p75"]:
            hits.append(f"CLS {cls:.3f} exceeds {p['cls_p75']}")
    if not seen:
        return ("NOT_RUN", "No vitals captured.", [])
    return ("NOT_RUN",
            "Lab measurement only" + (f": {'; '.join(hits)}. " if hits else ". ")
            + "NUM-012 is a field metric at the 75th percentile across real users and "
              "devices; one run on this machine cannot establish it either way.", hits)


def _measure(raws, out):
    hits = []
    for name, d in raws.items():
        if not name.endswith("__measure.json") or "too_wide" not in d:
            continue
        for x in d["too_wide"]:
            hits.append(f"{x['ch']} characters per line in <{x['tag']}> at "
                        f"{x['fontPx']}px -- \"{x['text']}\"")
    if not hits:
        return ("PASS", "Reading content stays within a workable measure.", [])
    return ("FAIL", f"{len(hits)} text blocks run past ~80 characters per line. The eye "
                    "loses the return sweep and people re-read lines (NUM-016).", hits[:12])


def _obstruction(raws, out):
    hits = []
    seen = False
    for name, d in raws.items():
        if not name.endswith("__obstruction.json") or "probe" not in d:
            continue
        seen = True
        for h in d.get("viewport_hogs", []):
            hits.append(f"a sticky bar takes {h['pct']}% of the viewport height "
                        f"and {h.get('widthPct', 100)}% of its width "
                        f"(class \"{h['cls']}\")")
        for o in d.get("focus_obscured", []):
            hits.append(f"focused {o['tag']} \"{o['label']}\" is painted over by "
                        f"\"{o['behind']}\"")
    if not seen:
        return ("NOT_RUN", "Obstruction probe produced no output.", [])
    if not hits:
        return ("PASS", "No sticky layer hides a focused control or dominates the "
                        "viewport.", [])
    return ("FAIL", f"{len(hits)} sticky-layer problems. A focused control hidden "
                    "behind a header fails SC 2.4.11, and a bar taking a quarter of a "
                    "phone screen leaves very little to read in.", hits[:10])


def _orientation(raws, out):
    for name, d in raws.items():
        if "__layout_landscape.json" not in name or "offenders" not in d:
            continue
        if d.get("page_overflows"):
            return ("FAIL", "The layout scrolls sideways in landscape at 844x390 -- "
                            "a common phone orientation, and one fixed-height layouts "
                            "usually fail (LAY-004).",
                    [f"<{o['tag']} class=\"{o['cls']}\"> reaches {o['right']}px"
                     for o in d["offenders"][:6]])
        return ("PASS", "Landscape phone orientation reflows without horizontal "
                        "scrolling.", [])
    return ("NOT_RUN", "Landscape orientation was not captured.", [])


# agent-browser prints a bare status glyph per checked surface, so `errors` emits
# lines like "\u2717 " with nothing after them even with no page open. Treating any
# non-blank output as "the page threw" made R-CONSOLE unable to pass on a clean
# page -- a check that cannot return PASS is not a check, it is a permanent alarm.
_ERR_NOISE = re.compile(r"^[\s\u2713\u2717\u2718\u00d7x\u2022\-\u2500\u2014|]*$")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _console_lines(text: str) -> list[str]:
    """Real error lines only: marker glyphs and framing stripped, empties dropped."""
    out = []
    for raw in _ANSI.sub("", text).splitlines():
        line = raw.strip()
        if not line or _ERR_NOISE.match(line):
            continue
        # drop a leading marker so the message is what gets compared and reported
        line = re.sub(r"^[\u2713\u2717\u2718\u00d7x\u2022]\s*", "", line).strip()
        if len(line) < 4:
            continue
        out.append(line)
    return out


def _console(raws, texts, out):
    files = {k: v for k, v in texts.items() if k.endswith("__errors.txt")}
    if not files:
        return ("NOT_RUN", "The driver captured no console output, so nothing was "
                           "examined for uncaught errors.", [])
    hits = []
    for k, v in sorted(files.items()):
        for line in _console_lines(v)[:6]:
            hits.append(f"{k.replace('__errors.txt', '')}: {line[:160]}")
    if not hits:
        return ("PASS", f"No uncaught page errors across {len(files)} route(s).", [])
    return ("FAIL", f"The page threw during a normal visit ({len(hits)} error line(s)).",
            hits[:10])


def _routes_without_client_fetch(raws) -> list:
    """Routes where the intercepted pattern was never requested on a healthy load.

    Forcing a condition on a request the page never makes forces nothing. The probe
    then describes an ordinary page, and every clause below reads that as a defect:
    a server-rendered route reported "request failed but the page says nothing about
    it" when no request had failed. Neither PASS nor FAIL is available here -- the
    condition was not established, which is what NOT_RUN means."""
    out = []
    for name, d in raws.items():
        if "__apiseen.json" not in name or d.get("probe") != "apiseen":
            continue
        if not d.get("api_seen"):
            out.append(name.split("__apiseen")[0])
    return out


def _state(mode, label, rules_hint):
    def fn(raws, out):
        found = False
        hits = []
        inert = set(_routes_without_client_fetch(raws))
        for name, d in raws.items():
            if f"__state_{mode}.json" not in name or "probe" not in d:
                continue
            if name.split(f"__state_{mode}")[0] in inert:
                continue
            found = True
            if d.get("stuck_spinner"):
                hits.append(f"{name}: spinner still visible, no failure message "
                            "-- this is the spinner that never stops")
            elif d.get("looks_blank"):
                hits.append(f"{name}: the region went blank with no explanation")
            elif mode == "empty" and not d.get("mentions_empty"):
                hits.append(f"{name}: empty payload rendered nothing that says so "
                            f"(excerpt: {d.get('excerpt','')[:80]})")
            elif mode in ("abort", "offline") and not d.get("mentions_failure"):
                hits.append(f"{name}: request failed but the page says nothing about it")
            elif mode in ("abort", "offline") and not d.get("recovery_actions"):
                hits.append(f"{name}: failure is shown but offers no way to recover")
        if not found:
            if inert:
                return ("NOT_RUN",
                        f"The intercepted pattern was never requested on "
                        f"{len(inert)} route(s), so this state was not forced on any "
                        f"of them. These probes need a route that fetches on the "
                        f"client; on a server-rendered route there is nothing to "
                        f"intercept, and reporting the unchanged page as a result "
                        f"would be a verdict about a condition that never happened.",
                        [f"{r}: no client request matched the --api pattern"
                         for r in sorted(inert)])
            return ("NOT_RUN", "No API route pattern was given, so this state was never "
                               "forced. Pass --api to ux_browser.sh.", [])
        if not hits:
            return ("PASS", f"{label} is handled: the interface says what happened "
                            "and offers a way on.", [])
        return ("FAIL", f"{label} is not handled.", hits)
    return fn


def _override(mode, label, criterion):
    def fn(raws, out):
        for name, d in raws.items():
            if f"__override_{mode}.json" not in name or "probe" not in d:
                continue
            hits = [f"clipped: <{c['tag']} class=\"{c['cls']}\"> {c['text']}"
                    for c in d.get("clipped", [])]
            hits += [f"pushed off screen: <{o['tag']} class=\"{o['cls']}\">"
                     for o in d.get("overflowing", [])]
            if not hits:
                return ("PASS", f"{label} loses no content or function.", [])
            return ("FAIL", f"{label} clips or displaces content ({criterion}).", hits[:15])
        return ("NOT_RUN", f"The {label.lower()} override was not applied.", [])
    return fn


def _baseline(raws, out):
    """GOV-004 -- did anything move that nobody asked to move?

    The driver already screenshots every route at every viewport; until now it
    never called `agent-browser diff screenshot --baseline`, so this detector was
    hardcoded NOT_RUN and its reason blamed the user for not recording a baseline
    the code could not have read. The output shape of the diff is not documented,
    so read it defensively: any of a percentage, a changed-pixel count or a plain
    "identical" verdict is enough to decide, and anything unrecognised reports
    NOT_RUN rather than guessing at a pass."""
    seen = False
    for name, d in raws.items():
        if not name.endswith("__baseline.json"):
            continue
        seen = True
        if d.get("absent"):
            return ("NOT_RUN", f"No baseline image at {d.get('looked_for')}. Capture one "
                               "before the change and pass --baseline, or this cannot be "
                               "measured.", [])
        if d.get("error"):
            return ("NOT_RUN", f"The baseline diff did not run: {d['error']}.", [])
        pct = None
        for k in ("diffPercent", "diff_percent", "percentChanged", "percent",
                  "differencePercent"):
            if isinstance(d.get(k), (int, float)):
                pct = float(d[k])
                break
        px = None
        for k in ("diffPixels", "diff_pixels", "changedPixels", "pixelsChanged"):
            if isinstance(d.get(k), (int, float)):
                px = int(d[k])
                break
        same = d.get("identical")
        if same is True or pct == 0 or px == 0:
            return ("PASS", "The render is pixel-identical to the baseline, so nothing "
                            "outside the change moved.", [])
        if pct is not None:
            # A threshold here would be a taste call dressed as a measurement. The
            # number is the evidence; a human decides whether that much movement was
            # the change they asked for.
            return ("FAIL", f"{pct:.2f}% of pixels differ from the baseline. Confirm "
                            f"every difference is one you intended.",
                    [f"pixel difference {pct:.2f}%"])
        if px is not None:
            return ("FAIL", f"{px} pixels differ from the baseline. Confirm every "
                            f"difference is one you intended.", [f"{px} pixels changed"])
        return ("NOT_RUN", "The baseline diff ran but returned nothing this reader "
                           "recognises, so no verdict is claimed.", [])
    if not seen:
        return ("NOT_RUN", "The driver produced no baseline comparison.", [])
    return ("NOT_RUN", "No baseline comparison was interpretable.", [])


# ------------------------------------------------------- R-PIXEL-CONTRAST
# Ground truth from the pixels the browser painted, for the text runs CSS cannot
# resolve: over an image, over a gradient, or over a positioned sibling layer.
# R-CONTRAST reports those as unmeasured rather than guessing, which is honest and
# useless -- on one real marketing page it was 61 of 95 runs. This is the route
# from "nobody could measure it" to a number.
#
# PNG decoding is stdlib only (zlib + struct). agent-browser writes 8-bit
# non-interlaced RGB or RGBA, which is what this reads; anything else reports
# NOT_RUN with the format it found rather than guessing at the bytes. The skill's
# dependency floor is python3 + pyyaml and this does not raise it.
def _png_rows(path: Path):
    """Delegates to scripts/pngread.py -- one filter loop, not two."""
    import pngread
    return pngread.rows(path)


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lum(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _pair_in_box(img, box, dpr=1.0):
    """The text colour and the background colour actually painted in this box.

    Separating glyph pixels from background pixels is the whole problem, and the
    obvious method fails. Taking the modal colour as background and "the most
    frequent colour furthest from it" as text picks a noise band: 12px text
    anti-aliased over a gradient spreads its pixels across dozens of values, none
    of which clears a frequency floor, while the background's own dithering
    supplies several bands that do. On a real page that reported 1.12:1 for
    white-at-60%-opacity on navy, which renders at about 5:1 -- a fabricated
    failure, the same defect as reading lab() as rgb().

    So separate on luminance instead of on frequency:

      background = the MEDIAN luminance. The background dominates the box by area,
      and a median is unmoved by however the glyphs are distributed.

      text = the mean RGB of the furthest 2% tail. The core glyph pixels are the
      extreme, and averaging the tail lands near the authored colour instead of on
      one dithered sample.

    This reads slightly conservative on thin text, because a partially covered
    pixel is closer to the background than the authored colour is. It errs toward
    reporting less contrast than was authored, which is the safe direction for a
    check, and it is stated here rather than left for someone to discover.
    """
    w, h, ch, buf = img
    x0 = max(0, int(box["x"] * dpr)); y0 = max(0, int(box["y"] * dpr))
    x1 = min(w, x0 + max(1, int(box["w"] * dpr)))
    y1 = min(h, y0 + max(1, int(box["h"] * dpr)))
    if x1 <= x0 or y1 <= y0:
        return None
    step = 1 if (x1 - x0) * (y1 - y0) < 90000 else 2
    px = []
    for y in range(y0, y1, step):
        row = y * w * ch
        for x in range(x0, x1, step):
            o = row + x * ch
            c = (buf[o], buf[o + 1], buf[o + 2])
            px.append((_lum(c), c))
    if len(px) < 40:
        return None
    px.sort(key=lambda t: t[0])
    n = len(px)
    med_l, med_c = px[n // 2]
    # Which end is the text on? Whichever extreme sits further from the median.
    lo_gap = med_l - px[0][0]
    hi_gap = px[-1][0] - med_l
    tail = max(8, int(n * 0.02))
    chunk = px[:tail] if lo_gap >= hi_gap else px[-tail:]
    fg = tuple(round(sum(c[i] for _l, c in chunk) / len(chunk)) for i in range(3))
    # A box with no glyphs in it -- a padding-only rect, a decorative strip -- has
    # no separation to find, and inventing one would produce exactly the fictional
    # verdicts this rewrite exists to remove.
    if abs(_lum(fg) - med_l) < 0.01:
        return None
    # Background: the median COLOUR, not a reconstruction from its luminance.
    bg = med_c
    return (fg, bg, round(_ratio(fg, bg), 2))


def _pixel_contrast(raws, out_dir):
    shots, runs = {}, []
    for name, d in raws.items():
        if name.endswith("__fullpage.json") and d.get("path"):
            shots[name[:-len("__fullpage.json")]] = Path(d["path"])
        elif name.endswith("__contrast.json"):
            for u in (d.get("unjudged") or []):
                if u.get("box"):
                    runs.append((name[:-len("__contrast.json")], u))
    if not runs:
        return ("NOT_RUN", "R-CONTRAST resolved every text run from CSS, so there was "
                           "nothing left for a pixel read to settle.", [])
    if not shots:
        return ("NOT_RUN", f"{len(runs)} text runs need a pixel read and no full-page "
                           f"screenshot was captured. Re-run ux_browser.sh; it takes one "
                           f"after the contrast probe.", [])
    hits, judged, unreadable = [], 0, 0
    cache = {}
    for key, u in runs:
        path = shots.get(key)
        if not path or not path.exists():
            unreadable += 1
            continue
        if key not in cache:
            cache[key] = _png_rows(path)
        img = cache[key]
        if img is None:
            unreadable += 1
            continue
        pair = _pair_in_box(img, u["box"], float(u.get("dpr") or 1.0))
        if pair is None:
            unreadable += 1
            continue
        fg, bg, r = pair
        judged += 1
        need = float(u.get("need") or 4.5)
        if r + 0.005 < need:
            hits.append(f"{r}:1 (needs {need}:1) painted fg rgb{fg} on rgb{bg} "
                        f"at {u.get('fontPx')}px -- \"{u.get('text', '')[:44]}\"")
    note = f"{judged} of {len(runs)} unresolvable runs read from the painted pixels"
    if unreadable:
        note += (f"; {unreadable} could not be read (region off the capture, too small, "
                 f"or an unsupported PNG form) and stay unmeasured")
    if not judged:
        return ("NOT_RUN", note + ". Nothing was established.", [])
    if not hits:
        return ("PASS", note + ", all meeting their floor.", [])
    near = [h for h in hits if _near_boundary(h)]
    tail = (f" {len(near)} of these are within 0.4 of their floor; the pixel read is "
            f"deliberately conservative on thin anti-aliased text, so confirm those "
            f"against the authored colour before treating them as defects."
            if near else "")
    return ("FAIL", f"{len(hits)} text runs fail on the pixels the browser painted. "
                    + note + "." + tail, hits[:25])


def _near_boundary(line: str) -> bool:
    m = re.match(r"([\d.]+):1 \(needs ([\d.]+):1\)", line)
    return bool(m) and float(m.group(2)) - float(m.group(1)) <= 0.4


def _slow(raws, out_dir):
    """What the interface says while it is waiting (NUM-014, STATE-006)."""
    seen, hits, ran, routes_skipped, reasons = 0, [], False, [], []
    for name, d in raws.items():
        if not name.endswith("__slow.json"):
            continue
        seen += 1
        if not d.get("ran"):
            (routes_skipped if "final content" in str(d.get("reason", ""))
             else reasons).append(str(d.get("reason") or "no reason recorded"))
            continue
        ran = True
        for f in (d.get("findings") or []):
            hits.append(str(f))
    if not seen:
        return ("NOT_RUN", "The slow-response pass was not run.", [])
    if not ran:
        why = ("; ".join(routes_skipped)[:300] if routes_skipped
               else "; ".join(reasons)[:300] or "no reason recorded")
        return ("NOT_RUN", f"No route held a waiting state open long enough to judge: "
                           f"{why}", [])
    tail = (f" {len(routes_skipped)} route(s) settled too fast to judge and are not "
            f"counted either way." if routes_skipped else "")
    if not hits:
        return ("PASS", "On a throttled link, every route that was caught loading said so "
                        "while it worked and stopped saying so when it finished." + tail,
                [])
    return ("FAIL", f"{len(hits)} problem(s) in how the interface behaves while waiting."
                    + tail, hits[:12])


def _forced_colors(raws, out_dir):
    """What the interface loses when the OS takes the palette away (VIS-008)."""
    seen, hits, emulated, paired, reasons = 0, [], False, 0, []
    for name, d in raws.items():
        if not name.endswith("__forcedcolors.json"):
            continue
        seen += 1
        if d.get("emulated"):
            emulated = True
            paired += int(d.get("paired") or 0)
        elif d.get("reason"):
            reasons.append(str(d["reason"]))
        for f in (d.get("findings") or []):
            hits.append(f"{f.get('kind')}: {f.get('label', '')[:44]} -- "
                        f"{f.get('detail', '')[:200]}")
    if not seen:
        return ("NOT_RUN", "The forced-colors pass was not run. It needs a page open in "
                           "agent-browser; ux_browser.sh runs it after the contrast probe.",
                [])
    if not emulated:
        return ("NOT_RUN", "forced-colors could not be emulated: "
                + ("; ".join(reasons)[:280] or "no reason recorded")
                + " Nothing was measured, so this is unrun, not passing.", [])
    if not hits:
        return ("PASS", f"{paired} element(s) compared normally and with forced-colors "
                        f"active; nothing lost a focus indicator, a boundary or a "
                        f"colour-encoded distinction.", [])
    return ("FAIL", f"{len(hits)} thing(s) lose meaning in forced-colors mode, measured "
                    f"across {paired} paired element(s).", hits[:20])


def _axe(raws, out_dir):
    """axe-core over the live page. Coverage this probe set does not reproduce --
    and still a minority of the WCAG criteria, which the note says out loud."""
    seen, hits, ran, counts, reasons = 0, [], False, {}, []
    for name, d in raws.items():
        if not name.endswith("__axe.json"):
            continue
        seen += 1
        if not d.get("ran"):
            reasons.append(str(d.get("reason") or "no reason recorded"))
            continue
        ran = True
        counts["passes"] = counts.get("passes", 0) + int(d.get("passes") or 0)
        counts["incomplete"] = counts.get("incomplete", 0) + int(d.get("incomplete") or 0)
        for v in (d.get("violations") or []):
            hits.append(f"[{v.get('impact', '?')}] {v.get('id')}: {v.get('help', '')} "
                        f"({v.get('nodes', 0)} node(s)) -- {v.get('target', '')[:70]}")
    if not seen:
        return ("NOT_RUN", "The axe pass was not run.", [])
    if not ran:
        return ("NOT_RUN", "axe-core could not be obtained: "
                + ("; ".join(reasons)[:260] or "no reason recorded")
                + " Install it in the project (npm i -D axe-core) or allow the fetch.",
                [])
    tail = (f" It also reported {counts.get('incomplete', 0)} incomplete check(s), which "
            f"are items axe could not decide and a person has to." 
            if counts.get("incomplete") else "")
    if not hits:
        return ("PASS", f"axe-core reported no violations across {counts.get('passes', 0)} "
                        f"passing checks. Automated rules reach a minority of the WCAG "
                        f"criteria, so this is a floor, not conformance." + tail, [])
    return ("FAIL", f"axe-core reported {len(hits)} violation(s)." + tail, hits[:25])


# ----------------------------------------------------------------- native tier
# scripts/ux_native.sh writes raw/native-ios.json and raw/native-android.json.
# A missing file, or one reporting the tool absent, is NOT_RUN -- never PASS.
# This is the one place in the whole tool where the temptation to fudge is
# strongest, because on a Linux machine `xcrun` will never exist and it would be
# convenient to call that "not applicable". It is not: the iPhone build is still
# unverified, and only a Mac can change that.
def _native(platform: str, want_pairs: bool):
    label = "iOS" if platform == "ios" else "Android"
    tool = "xcrun simctl" if platform == "ios" else "adb"
    appearance = "Dark Mode and a large Dynamic Type size" if platform == "ios" \
        else "the dark theme and an enlarged font scale"

    def probe(raws, out_dir):
        d = raws.get(f"native-{platform}.json")
        if not d:
            return ("NOT_RUN", f"No {label} capture recorded. Run scripts/ux_native.sh "
                               f"--{platform} against a booted target.", [])
        if not d.get("available"):
            return ("NOT_RUN", f"{tool} unavailable: "
                               f"{d.get('reason', 'reason not recorded')}. The {label} "
                               f"build is unverified -- this is not a pass and not a "
                               f"not-applicable.", [])
        caps = [c for c in (d.get("captures") or []) if (c.get("bytes") or 0) > 0]
        device = d.get("device") or "an unnamed target"
        if not caps:
            return ("FAIL", f"{tool} ran on {device} and produced no usable capture. "
                            f"Errors: {'; '.join(d.get('errors') or ['none reported'])}",
                    [f"no {label} screenshot produced"])
        kinds = {c.get("kind") for c in caps}
        if not want_pairs:
            classes = sorted({c.get("device_class") for c in caps if c.get("device_class")})
            return ("PASS", f"{len(caps)} capture(s) from {device}"
                            + (f", device classes: {', '.join(classes)}" if classes else ""),
                    [])
        missing = []
        if not {"light"} & kinds:
            missing.append("a light-appearance capture")
        if not {"dark"} & kinds:
            missing.append("a dark-appearance capture")
        if not {"large-type"} & kinds:
            missing.append("an enlarged-text capture")
        if missing:
            return ("FAIL", f"{tool} ran on {device} but the pass is incomplete: "
                            f"missing {', '.join(missing)}. {appearance} belong in the "
                            f"pass, because that is where a fixed layout truncates.",
                    [f"missing: {m}" for m in missing])
        return ("PASS", f"{label} verified in both appearances and at an enlarged text "
                        f"size on {device} ({len(caps)} captures).", [])
    return probe


# Declared runtime detectors. None means "declared but not implemented yet" --
# it reports NOT_RUN with that reason rather than quietly vanishing.
RUNTIME = {
    "R-REFLOW": _reflow,
    "R-TABLE-HIDDEN": _table_hidden,
    "R-TABLE-SQUEEZE": _table_squeeze,
    "R-TARGET": _targets,
    "R-TARGET-COARSE": _target_coarse,
    "R-CONTRAST": _contrast,
    "R-FOCUS-WALK": _focus,
    "R-MOTION": _motion,
    "R-VITALS": _vitals,
    "R-MEASURE": _measure,
    "R-STICKY-OBSTRUCTION": _obstruction,
    "R-ORIENTATION": _orientation,
    "R-CONSOLE": None,
    "R-STATE-ERROR": _state("abort", "An aborted request", None),
    "R-STATE-EMPTY": _state("empty", "An empty result set", None),
    "R-STATE-OFFLINE": _state("offline", "Going offline", None),
    "R-STATE-SLOW": _slow,
    "R-AXE": _axe,
    "R-ZOOM": _override("zoom", "200% text size", "NUM-008 / SC 1.4.4"),
    "R-TEXTSPACING": _override("spacing", "The text-spacing override",
                               "NUM-010 / SC 1.4.12"),
    "R-PIXEL-CONTRAST": _pixel_contrast,
    "R-BASELINE-DIFF": _baseline,
    "R-FORCED-COLORS": _forced_colors,
    "R-IOS-CAPTURE": _native("ios", want_pairs=False),
    "R-IOS-APPEARANCE": _native("ios", want_pairs=True),
    "R-AND-CAPTURE": _native("android", want_pairs=False),
    "R-AND-THEME": _native("android", want_pairs=True),
}
UNIMPLEMENTED = {
    "R-CONSOLE": "",
}


def collect(out_dir: Path, meta: dict):
    raw = out_dir / "raw"
    raws, texts = {}, {}
    for f in sorted(raw.glob("*.json")):
        raws[f.name] = load(f, {}) or {}
    for f in sorted(raw.glob("*.txt")):
        texts[f.name] = f.read_text(errors="replace")

    detectors = {}
    for did, fn in RUNTIME.items():
        if did == "R-CONSOLE":
            st, note, hits = _console(raws, texts, out_dir)
        elif fn is None:
            st, note, hits = "NOT_RUN", UNIMPLEMENTED.get(did, "Not implemented."), []
        else:
            st, note, hits = fn(raws, out_dir)
        detectors[did] = {"status": st, "note": note, "findings": hits}

    report = {"tier": "runtime", "available": True, "meta": meta, "detectors": detectors}
    (out_dir / "runtime.json").write_text(json.dumps(report, indent=1))

    w = sys.stderr.write
    w("\nruntime tier\n" + "-" * 70 + "\n")
    for did, d in detectors.items():
        w(f"  {d['status']:<16} {did:<18} {d['note'][:90]}\n")
        for h in d["findings"][:4]:
            w(f"       - {h[:110]}\n")
    n_fail = sum(1 for d in detectors.values() if d["status"] == "FAIL")
    n_nr = sum(1 for d in detectors.values() if d["status"] == "NOT_RUN")
    w(f"\n{n_fail} failing, {n_nr} not run. Written to {out_dir/'runtime.json'}\n")
    return 2 if n_fail else 0



# ------------------------------------------------------------ report self-audit
# GOV-005/006/008 are not properties of the product -- they are properties of the
# report. No scan of someone's app can tell you whether the agent writing about
# it invented a result. What CAN be checked is whether every PASS in this very
# document traces to a detector that actually ran, whether unknowns were declared
# rather than walked past, and whether project config was used to silence a
# standard. That is the only honest way to automate them, so it is what happens.

def _process_tier() -> dict:
    """The process detectors: how the work happened, not what it produced.

    Kept in its own function because it reads state nothing else in the report
    reads -- the phase record and the decision records -- and because when that
    state is absent the answer is NOT_RUN for all of them rather than silence.
    A report that simply omits the question reads as though nobody needed to ask
    it, which is how "the contract came first" stayed an assertion for so long."""
    out = {}
    try:
        import ux_phase
        st = ux_phase.load()
        out.update(ux_phase.process_checks(st))
    except Exception as e:                       # never let this break the report
        why = (f"The process tier could not run ({type(e).__name__}: {e}). Nothing "
               f"about the order of work is established.")
        st = {}
        for k in ("A-PHASE-ORDER", "A-COMP-APPROVED", "A-DECISION-VETTED"):
            out.setdefault(k, ("NOT_RUN", why))
    out["A-COMP-CONFORM"] = _comp_conform(st)
    try:
        import ux_ledger
        out.update(ux_ledger.process_checks())
    except Exception as e:
        out.setdefault("A-CONTRACT-ARCHIVED", (
            "NOT_RUN", f"The ledger could not be read ({type(e).__name__}: {e}), so "
                       f"whether the approvals resolve to a declaration is unknown."))
    return out


def _comp_conform(st: dict):
    """Does the approved comp match the contract it claims to express?

    A generator returns a beautiful image in a palette nobody declared, somebody
    approves it, and from then on the build is judged against a comp that was
    never the system. Measuring the approved artefact closes that, and it is the
    one check in this file that reads pixels rather than paperwork."""
    try:
        import ux_phase
        import ux_image
        ok, _bad, _sup = ux_phase.vetted_decisions()
    except Exception as e:
        return ("NOT_RUN", f"Could not read the decision records ({type(e).__name__}: "
                           f"{e}), so no approved comp was measured.")
    if not ok:
        return ("NOT_RUN", "No standing approval, so there is no approved comp to "
                           "measure against the contract.")
    # A live review of a working prototype has no comp raster to read, and does
    # not need one: the prototype is real code, so the S-CONTRACT-* checks measure
    # its conformance directly. Only a picture has to be measured as a picture.
    comps = [x for x in ok if "approves_a_build" not in x[1]]
    if not comps:
        return ("NOT_APPLICABLE",
                "The standing approval is a live review of a working prototype, not "
                "a comp. Its conformance to the contract is measured by the static "
                "tier against the prototype's own source, where it is a stronger "
                "claim than a pixel read.")
    f, d, _w = comps[-1]
    chosen = str(d.get("chosen") or "")
    shown = {str(s.get("id")): s for s in (d.get("shown") or [])}
    entry = shown.get(chosen)
    if not entry or not entry.get("image"):
        return ("NOT_RUN", f"{f.stem} records `{chosen}`, which names no single image "
                           f"(a combination or a rejection), so there is nothing to "
                           f"measure.")
    img = Path(entry["image"])
    if img.suffix.lower() != ".png":
        alt = img.with_suffix(".png")
        if not alt.exists():
            return ("NOT_RUN",
                    f"The approved comp {img} is a vector sheet. Reading a palette "
                    f"needs pixels, so nothing measured it -- and 'it was rendered "
                    f"from the contract' is an argument about the renderer rather "
                    f"than evidence about this file. Produce a raster "
                    f"(scripts/ux_image.py generate ...) to close this.")
        img = alt
    c = ux_image.load_contract(None)
    res = ux_image.verify(img, c)
    if not res.get("ok"):
        return ("NOT_RUN", res.get("error", "the comp could not be decoded"))
    if res["findings"]:
        return ("FAIL", f"{img.name}: " + " | ".join(res["findings"])[:400])
    return ("PASS", f"{img.name} carries every declared colour role at real coverage "
                    f"(canvas {res['canvas']}, ink {res['ink']}, "
                    f"{res['ink_on_canvas']}:1), and its provenance is in the file.")


def self_audit(results, dstat, static, runtime, config, release, manual=None,
               features=None, manual_detectors=frozenset()):
    """Returns {detector_id: (status, note)} for the A-* family."""
    out = {}
    out.update(_process_tier())

    # --- GOV-006: no PASS without a detector that reported PASS
    passes = [r for r in results if r["status"] == "PASS"]

    # A PASS whose every contributing detector is a human attestation is a
    # signature, not a measurement. It may be entirely legitimate -- somebody did
    # do the screen-reader pass -- but it must be counted apart, or the matrix
    # reads as though a machine checked it. This is the split that stops an
    # attestation being laundered into evidence by GOV-006's own sign-off.
    # `reason` on a PASS row is the joined list of detector IDs that passed, which
    # is the only per-rule provenance the row carries. A row whose every named
    # detector is a manual one is a signature, not a measurement.
    def _named(row):
        return [d.strip() for d in row["reason"].split(";") if d.strip()]
    signed = [r["rule_id"] for r in passes
              if _named(r) and all(d in manual_detectors for d in _named(r))]
    unbacked = [r["rule_id"] for r in passes if not r["reason"].strip()]
    tiers_ran = bool(static.get("detectors")) or bool(runtime.get("detectors"))
    if not tiers_ran:
        out["A-EVIDENCE-BACKED"] = ("FAIL",
            "The report contains rule statuses but no tier produced any detector "
            "output. Nothing here is evidence.")
    elif unbacked:
        out["A-EVIDENCE-BACKED"] = ("FAIL",
            f"{len(unbacked)} rules are marked PASS with no detector named: "
            + ", ".join(unbacked[:8]))
    elif signed:
        out["A-EVIDENCE-BACKED"] = ("PASS",
            f"All {len(passes)} PASS rules name a detector. {len(signed)} of them rest "
            f"only on a human attestation and nothing measured them: "
            f"{', '.join(signed[:8])}. That is admissible evidence and it is not a "
            f"measurement -- read those rows as somebody's signature.")
    else:
        out["A-EVIDENCE-BACKED"] = ("PASS",
            f"All {len(passes)} PASS rules name the detector that produced them, and "
            f"none rests only on an attestation.")

    # --- GOV-005: unknowns declared, not walked past
    unchecked_p0 = [r["rule_id"] for r in results
                    if r["status"] == "NOT_RUN" and r["severity"] == "P0"]
    decision = out.get("_decision")
    if unchecked_p0 and not release:
        out["A-UNKNOWN-DECLARED"] = ("PASS",
            f"{len(unchecked_p0)} P0 rules are unverified and reported as NOT_RUN "
            "rather than assumed.")
    elif unchecked_p0 and release:
        out["A-UNKNOWN-DECLARED"] = ("PASS",
            f"{len(unchecked_p0)} unverified P0 rules are blocking the release gate, "
            "which is the required behaviour.")
    else:
        out["A-UNKNOWN-DECLARED"] = ("PASS", "No P0 rule is unverified.")

    # --- GOV-008: project config may not silence a STANDARD
    disabled = uxconfig.disabled(config)
    violations = []
    if disabled:
        violations.append(f"{len(disabled)} checks disabled in project config "
                          f"({', '.join(sorted(disabled)[:5])}) -- the rules they "
                          "cover now report NOT_RUN, not PASS")
    # The refusals come from the same loader that applied the legal overrides, so
    # this reports what was actually rejected rather than re-deriving it and
    # risking the two disagreeing.
    violations.extend(uxconfig.thresholds(config)[1])
    # --- QA-001/QA-005: every assessed rule carries a status and a reason
    assessed = [r for r in results if r["status"] != "NOT_APPLICABLE"]
    silent = [r["rule_id"] for r in assessed if not r["reason"].strip()]
    if silent:
        out["A-EVIDENCE-MAP"] = ("FAIL",
            f"{len(silent)} assessed rules carry a status with no reason: "
            + ", ".join(silent[:8]))
    else:
        out["A-EVIDENCE-MAP"] = ("PASS",
            f"All {len(assessed)} assessed rules state how they were decided.")

    # --- QA-002/QA-003/GOV-009: the report must say what it looked at
    tiers = [k for k, v in {"static": static, "runtime": runtime}.items() if v]
    manual_present = bool(manual)
    parts = []
    if not manual_present:
        parts.append("no manual tier was recorded, so screen-reader, keyboard and "
                     "real-device coverage is absent")
    if "runtime" not in tiers:
        parts.append("the runtime tier did not run, so nothing was measured on a live page")
    out["A-SCOPE-STATED"] = ("PASS",
        ("Scope: " + ", ".join(tiers) + " tier(s). " + " ".join(parts)) if parts
        else f"Scope: {', '.join(tiers)} and manual. Full coverage of the declared scope.")

    # --- MEASURE-002/005/007: no numbers the report did not measure
    invented = []
    for r in results:
        if re.search(r"\b\d{1,3}%\s*(?:better|faster|improvement|increase|of users)",
                     r["reason"], re.I):
            invented.append(r["rule_id"])
        if re.search(r"\busers? (?:said|reported|found|preferred)\b", r["reason"], re.I):
            invented.append(r["rule_id"])
    if invented:
        out["A-NO-INVENTED-METRICS"] = ("FAIL",
            "Reasons contain percentage or user-research claims that no tier produced: "
            + ", ".join(sorted(set(invented))[:6]))
    else:
        out["A-NO-INVENTED-METRICS"] = ("PASS",
            "No percentage improvement or user-research claim appears that a tier did "
            "not produce. Lab vitals are reported as NOT_RUN for the same reason.")

    # --- GOV-003: every result must carry its class and its source
    unclassed = [r["rule_id"] for r in results
                 if r["status"] not in ("NOT_APPLICABLE",)
                 and (not r.get("class") or not r.get("basis"))]
    if unclassed:
        out["A-BASIS-CLASSED"] = ("FAIL",
            f"{len(unclassed)} results carry no class or no source: "
            + ", ".join(unclassed[:8]))
    else:
        out["A-BASIS-CLASSED"] = ("PASS",
            "Every result states whether it comes from a standard, a platform, "
            "research or a project default, and names its source.")

    # --- GOV-007: an exception may lower a PROJECT rule, never a STANDARD
    exc = config.get("_exceptions")
    if exc is None:
        exc = uxconfig.exceptions(config)
    bad_exc = []
    by_id = {r["rule_id"]: r for r in results}
    for e in exc:
        rec = by_id.get(e["rule_id"])
        if rec and rec.get("class") == "STANDARD":
            bad_exc.append(e["rule_id"])
    applied = sum(1 for r in results if r["status"] == "APPROVED_EXCEPTION")
    lapsed = [f"{e.get('exception_id') or e['rule_id']} ({e['inactive_reason']})"
              for e in exc if not e["active"]]
    if bad_exc:
        out["A-EXCEPTIONS-VALID"] = ("FAIL",
            "Exceptions claimed against STANDARD-class rules, which cannot be "
            "waived by project policy: " + ", ".join(bad_exc))
    else:
        out["A-EXCEPTIONS-VALID"] = ("PASS",
            (f"{len(exc)} recorded exception(s), none against a standard; "
             f"{applied} applied as APPROVED_EXCEPTION"
             + (f"; not applied: {', '.join(lapsed[:4])}" if lapsed else "") + ".")
            if exc else "No exceptions claimed.")

    # --- CTX-002/003/004: the product's own facts were declared, not assumed
    # The merged list (config + --feature), not the raw config, or the audit
    # reports a different set of features from the one that did the gating.
    feats = features if features is not None else uxconfig.features(config)
    gated = [r for r in results if r["status"] == "NOT_APPLICABLE"]
    if not feats and gated:
        out["A-CONTEXT-DECLARED"] = ("FAIL",
            f"{len(gated)} rules were ruled NOT_APPLICABLE but the project declares "
            "no features. Applicability was assumed rather than stated.")
    else:
        out["A-CONTEXT-DECLARED"] = ("PASS",
            f"Applicability derives from {len(feats)} declared feature(s); "
            f"{len(gated)} rules ruled out on that basis." if feats
            else "No feature gating applied; every rule treated as applicable.")

    # --- PERF-002/009/010: lab numbers are never reported as field evidence
    vit = (runtime.get("detectors") or {}).get("R-VITALS", {})
    if vit and vit.get("status") == "PASS":
        out["A-PERF-TIER"] = ("FAIL",
            "R-VITALS reported PASS. A single lab run cannot establish NUM-012, "
            "which is a 75th-percentile field metric across real users and devices.")
    else:
        out["A-PERF-TIER"] = ("PASS",
            "Performance is reported as lab measurement only; field evidence is "
            "marked NOT_RUN and needs real-user data.")

    if any("non-overridable" in v or "not in the overridable" in v for v in violations):
        out["A-CONFIG-AUTHORITY"] = ("FAIL", "; ".join(violations))
    elif violations:
        out["A-CONFIG-AUTHORITY"] = ("PASS",
            "Project config narrows scope but does not weaken a standard. " + violations[0])
    else:
        out["A-CONFIG-AUTHORITY"] = ("PASS",
            "No project override touches a standard-derived threshold.")
    return out


# ------------------------------------------------------------ merge + gate
# --- The attestation gate ----------------------------------------------------
# A manual attestation is the one place where a human sentence becomes a detector
# status. Left unguarded it is a laundry: an agent writes `status: PASS` for a
# rule nothing can check, merge ingests it, and the self-audit then certifies
# "All N PASS rules name the detector that produced them" -- because a manual
# attestation IS a named detector that reported PASS. That is the same shape as
# the single-file-116-PASS bug, and it is the reason a craft rule must never be
# allowed to enter through this door.
#
# So an attestation earns PASS only by carrying the marks of someone actually
# having done it. Anything less is NOT_RUN with the reason said out loud.

# Words that mean the claimant and the checker are the same party.
_SELF = re.compile(r"\b(?:claude|chatgpt|gpt|copilot|cursor|codex|gemini|llm|ai|"
                   r"agent|assistant|model|bot|automated|self|me|myself|"
                   r"this session|the tool)\b", re.I)


def vet_attestation(did: str, rec: dict) -> tuple[str, str, bool]:
    """(status, reason, attested) for one recorded manual result.

    Returns `attested=True` only when a human-performed result is on the record.
    A FAIL is always honoured -- nobody launders a failure, and a reported defect
    is useful however thin its paperwork."""
    status = str(rec.get("status", "NOT_RUN")).upper()
    ev = str(rec.get("evidence", "") or "").strip()
    who = str(rec.get("who", "") or "").strip()
    date = str(rec.get("date", "") or "").strip()

    if status == "FAIL":
        return ("FAIL", ev or "Recorded as failing, with no detail given.", True)
    if status != "PASS":
        return ("NOT_RUN", ev or "Not attempted.", False)

    missing = []
    if not who:
        missing.append("no `who`")
    elif _SELF.search(who):
        missing.append(f"`who: {who}` names the party making the claim")
    if not date:
        missing.append("no `date`")
    if len(ev) < 40:
        missing.append("evidence too thin to check" if ev else "no evidence")
    if missing:
        return ("NOT_RUN",
                f"Recorded PASS is not admissible ({'; '.join(missing)}). A manual "
                f"check earns PASS by someone having done it and said who, when and "
                f"how -- otherwise it stays unrun, which is what it is.", False)
    return ("PASS", f"Attested by {who} on {date}: {ev[:200]}", True)


def _project_root(config: dict) -> Path:
    """The project a report is about: the directory holding .deuxui/, found from
    the config file when there is one, else the working directory."""
    if config.get("_path"):
        return Path(config["_path"]).resolve().parent.parent
    return Path.cwd()


def merge(static_json: Path, runtime_json: Path, manual_yaml: Path,
          features: list, release: bool, config_path: Path | None = None):
    global TH
    # The config is read FIRST. It used to load about twenty-five lines below the
    # applicability gate, which meant `features:` in the file could not possibly
    # affect gating -- only the --feature flag did, while the documentation
    # promised otherwise.
    config = uxconfig.load(Path.cwd(), str(config_path) if config_path else None)
    TH, refused_overrides = uxconfig.thresholds(config)
    features = uxconfig.features(config, features)
    off = uxconfig.disabled(config)

    reg, det_doc, _th = rulepack.load()
    det = det_doc["detectors"]
    static = load(static_json, {}) or {}
    runtime = load(runtime_json, {}) or {}
    # Platforms the static tier MEASURED, unioned in. The iOS and Android rule
    # families gate on `feature: ios` / `feature: android`, and requiring someone
    # to declare what the tree already states is how forty rules stay invisible
    # in the project that most needs them. A declared feature still works and
    # still wins where they disagree -- this only removes the need to remember.
    measured = ((static.get("project") or {}).get("platforms") or []) \
        if isinstance(static, dict) else []
    for plat in measured:
        if plat not in features:
            features = list(features) + [plat]
    manual = {}
    if manual_yaml and manual_yaml.exists():
        manual = yaml.safe_load(manual_yaml.read_text()) or {}

    dstat = {}
    for k, v in (static.get("detectors") or {}).items():
        dstat[k] = (v["status"], v.get("note", ""))
    for k, v in (runtime.get("detectors") or {}).items():
        dstat[k] = (v["status"], v.get("note", ""))
    attested = set()
    # Every manual detector, answered or not. Left out entirely they vanished
    # from the report, which read as though nothing needed a human -- so the
    # sheet's questions are seeded as NOT_RUN first and any recorded answer
    # overwrites its row. An unanswered question now says what to do about it.
    for k, d in det.items():
        if d.get("engine") == "manual" and k not in dstat:
            q = " ".join((d.get("question") or "").split())
            dstat[k] = ("NOT_RUN", "Nobody has answered this yet. " + (q or
                        "No question recorded for this check.")
                        + f"  Record it: scripts/manual_sheet.py --write, then "
                          f"fill in {k}.")
    for k, v in (manual.get("attestations") or {}).items():
        st, why, ok = vet_attestation(k, v if isinstance(v, dict) else {})
        if st == "NOT_RUN":
            q = " ".join((det.get(k, {}).get("question") or "").split())
            if q:
                why = f"{why}  The question is: {q}"
        dstat[k] = (st, why)
        if ok and st == "PASS":
            attested.add(k)
    # A disabled check cannot contribute a PASS, including from a report file
    # produced before it was disabled. Config narrows what was examined; it never
    # converts an unexamined rule into a passing one.
    for k in off:
        dstat[k] = ("NOT_RUN", "Disabled in .deuxui/ux.config.yaml (disabled_checks).")

    by_rule = {}
    for did, (st, note) in dstat.items():
        for rid in det.get(did, {}).get("rules", []):
            by_rule.setdefault(rid, []).append((did, st, note))

    results, counts = [], {"PASS": 0, "FAIL": 0, "NOT_RUN": 0,
                           "NOT_APPLICABLE": 0, "APPROVED_EXCEPTION": 0}
    for r in reg["rules"]:
        rid, aw = r["id"], r.get("applies_when")
        if isinstance(aw, dict) and aw.get("feature") and aw["feature"] not in features:
            status, reason = "NOT_APPLICABLE", f"Project declares no {aw['feature']}."
        else:
            entries = by_rule.get(rid, [])
            sts = [s for _d, s, _n in entries]
            if "FAIL" in sts:
                status, reason = "FAIL", "; ".join(
                    f"{d}: {n}" for d, s, n in entries if s == "FAIL")[:300]
            elif "PASS" in sts:
                status, reason = "PASS", "; ".join(
                    d for d, s, _n in entries if s == "PASS")
            elif "NOT_RUN" in sts:
                status, reason = "NOT_RUN", "; ".join(
                    f"{d}: {n}" for d, s, n in entries if s == "NOT_RUN")[:300]
            elif sts:
                # Every detector said NOT_APPLICABLE -- no file in scope was the
                # kind it examines. That is not a pass and it is not a decision
                # about the product; it means nothing established this rule.
                status = "NOT_RUN"
                reason = ("no detector had anything in scope to examine ("
                          + ", ".join(d for d, _s, _n in entries)[:160] + ")")
            else:
                status, reason = "NOT_RUN", ("No detector covers this rule. It needs a "
                                             "human to check it and record the result.")
        counts[status] += 1
        results.append({"rule_id": rid, "severity": r["severity"], "class": r["class"],
                        "basis": r["basis"], "status": status, "reason": reason})

    # --- owner rulings. A FAIL on a PROJECT-class rule with an approved, unexpired
    # exception becomes APPROVED_EXCEPTION: not a pass, not blocking, and carrying
    # who decided and until when. This bucket existed in `counts` and was never
    # filled, so a density decision the owner had made and written down still
    # blocked the release like a defect nobody had looked at.
    exc = uxconfig.exceptions(config, root=_project_root(config))
    config["_exceptions"] = exc
    by_rid = {}
    for e in exc:
        if e["active"]:
            by_rid.setdefault(e["rule_id"], e)
    for r in results:
        e = by_rid.get(r["rule_id"])
        if not e or r["status"] != "FAIL" or r["class"] not in uxconfig.EXCEPTABLE_CLASSES:
            continue
        counts["FAIL"] -= 1
        counts["APPROVED_EXCEPTION"] += 1
        r["status"] = "APPROVED_EXCEPTION"
        r["reason"] = (f"{e.get('exception_id') or 'exception'}: owner "
                       f"{e.get('owner') or '(unnamed)'}, approved by "
                       f"{e.get('approved_by') or '(unnamed)'}, review "
                       f"{e.get('expires_or_review_on') or '(no date)'}. Measured: "
                       + r["reason"])[:400]

    # --- the 20 UX laws, rolled up from the detectors indexed to them.
    # They were carried as data and consumed by nothing, so a report could cite
    # LAW-12 beside A11Y-005 as though the gate adjudicated both. It adjudicates
    # one. Now a law carries a status, and a law whose only evidence is a human
    # attestation says so rather than passing as measured.
    law_by = {}
    for did, (st, note) in dstat.items():
        for lid in (det.get(did, {}).get("laws") or []):
            law_by.setdefault(lid, []).append((did, st, det.get(did, {}).get("engine")))
    law_results = {}
    for law in reg.get("laws", []):
        lid = law["id"]
        if law.get("enforceable") is False:
            law_results[lid] = {"status": "NOT_APPLICABLE",
                                "reason": f"Alias of {law.get('alias_of')}; evaluated once."}
            continue
        entries = law_by.get(lid, [])
        sts = [st for _d, st, _e in entries]
        if not entries:
            law_results[lid] = {"status": "NOT_RUN",
                                "reason": "No detector adjudicates any of this law's "
                                          "verify clauses."}
        elif "FAIL" in sts:
            law_results[lid] = {"status": "FAIL", "reason": "; ".join(
                d for d, st, _e in entries if st == "FAIL")}
        elif "PASS" in sts:
            measured = [d for d, st, e in entries if st == "PASS" and e != "manual"]
            law_results[lid] = {
                "status": "PASS",
                "reason": ("; ".join(measured) if measured else
                           "attested only: " + "; ".join(
                               d for d, st, _e in entries if st == "PASS")),
                "measured": bool(measured)}
        else:
            law_results[lid] = {"status": "NOT_RUN", "reason": "; ".join(
                f"{d}: {st}" for d, st, _e in entries)[:200]}

    manual_dets = {k for k, v in det.items() if v.get("engine") == "manual"}
    audit = self_audit(results, dstat, static, runtime, config, release, manual,
                       features=features, manual_detectors=manual_dets)
    # fold the A-* results back in as rule statuses for the GOV rules they cover
    A_RULES = {"A-EVIDENCE-BACKED": ["GOV-006"], "A-UNKNOWN-DECLARED": ["GOV-005"],
               "A-CONFIG-AUTHORITY": ["GOV-008"],
               "A-EVIDENCE-MAP": ["QA-001", "QA-005", "GOV-002"],
               "A-SCOPE-STATED": ["QA-002", "QA-003", "GOV-009", "A11Y-013"],
               "A-NO-INVENTED-METRICS": ["MEASURE-002", "MEASURE-005", "MEASURE-007"],
               "A-BASIS-CLASSED": ["GOV-003", "GOV-001"],
               "A-EXCEPTIONS-VALID": ["GOV-007", "QA-006"],
               "A-CONTEXT-DECLARED": ["CTX-002", "CTX-003", "CTX-004", "MEASURE-006"],
               "A-PHASE-ORDER": ["GOV-010"], "A-COMP-APPROVED": ["GOV-011"],
               "A-DECISION-VETTED": ["GOV-012"], "A-PROTO-ACCEPTED": ["GOV-014"],
               "A-COMP-CONFORM": ["VIS-001", "GOV-013"],
               "A-PERF-TIER": ["PERF-002", "PERF-009", "PERF-010", "MEASURE-001",
                               "MEASURE-003", "MEASURE-004"]}
    for did, rids in A_RULES.items():
        st, note = audit[did]
        for r in results:
            if r["rule_id"] in rids:
                if r["status"] in ("NOT_RUN", "NOT_APPLICABLE"):
                    counts[r["status"]] -= 1
                    counts[st] += 1
                r["status"], r["reason"] = st, f"{did}: {note}"

    blocking = [x for x in results
                if x["status"] == "FAIL" and x["severity"] in ("P0", "P1")]
    unchecked_p0 = [x for x in results
                    if x["status"] == "NOT_RUN" and x["severity"] == "P0"]
    if blocking:
        decision = "BLOCKED"
        why = f"{len(blocking)} P0/P1 rules are failing."
    elif release and unchecked_p0:
        decision = "BLOCKED"
        why = (f"{len(unchecked_p0)} P0 rules have never been checked. For a release "
               "audit an unchecked safety rule blocks: not knowing is not the same "
               "as passing.")
    elif unchecked_p0:
        decision = "CONDITIONAL"
        why = (f"Nothing is failing, but {len(unchecked_p0)} P0 rules are unverified. "
               "Fine mid-change; not enough to ship on.")
    else:
        decision = "READY"
        why = "Every applicable rule has been checked and none are failing."

    report = {
        "document_version": "1.0.0",
        "generated_by": "deuxui/scripts/ux_report.py",
        "tiers_present": {"static": bool(static), "runtime": bool(runtime),
                          "manual": bool(manual)},
        "declared_features": features,
        "attested_not_measured": sorted(attested),
        "law_results": law_results,
        "counts": {"not_run": counts["NOT_RUN"], "fail": counts["FAIL"],
                   "pass": counts["PASS"], "not_applicable": counts["NOT_APPLICABLE"],
                   "approved_exception": counts["APPROVED_EXCEPTION"],
                   "rules_assessed": len(results)},
        "release_decision": decision,
        "decision_reason": why,
        "blocking_rules": [x["rule_id"] for x in blocking],
        "unverified_p0_rules": [x["rule_id"] for x in unchecked_p0],
        "report_self_audit": {k: {"status": v[0], "note": v[1]}
                              for k, v in audit.items()},
        "rule_results": results,
    }
    print(yaml.safe_dump(report, sort_keys=False, allow_unicode=True, width=100))
    by_class = {}
    for x in results:
        if x["status"] == "FAIL":
            by_class[x["class"]] = by_class.get(x["class"], 0) + 1
    sys.stderr.write(
        f"\nNOT_RUN {counts['NOT_RUN']}   FAIL {counts['FAIL']}   PASS {counts['PASS']}"
        f"   APPROVED_EXCEPTION {counts['APPROVED_EXCEPTION']}"
        f"   NOT_APPLICABLE {counts['NOT_APPLICABLE']}\n"
        + (f"failing by class: " + "   ".join(
            f"{c} {by_class[c]}" for c in ("STANDARD", "PLATFORM", "PROJECT", "HEURISTIC")
            if by_class.get(c)) + "\n" if by_class else "")
        + f"release_decision: {decision} -- {why}\n")
    return 2 if decision == "BLOCKED" else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collect", metavar="DIR", help="interpret raw runtime probe output")
    ap.add_argument("--base"); ap.add_argument("--api"); ap.add_argument("--routes")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--static", default=".deuxui/reports/static.json")
    ap.add_argument("--runtime", default=".deuxui/reports/runtime/runtime.json")
    ap.add_argument("--manual", default=".deuxui/reports/manual.yaml")
    ap.add_argument("--feature", action="append", default=[],
                    help="declare a feature the product has (repeatable)")
    ap.add_argument("--config", default=".deuxui/ux.config.yaml",
                    help="project config, audited for standard-weakening overrides")
    ap.add_argument("--release", action="store_true",
                    help="release audit: unchecked P0 rules block")
    a = ap.parse_args(argv)

    if a.collect:
        return collect(Path(a.collect),
                       {"base": a.base, "api": a.api, "routes": a.routes})
    if a.merge:
        return merge(Path(a.static), Path(a.runtime), Path(a.manual),
                     a.feature, a.release, Path(a.config) if a.config else None)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
