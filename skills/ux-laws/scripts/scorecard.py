#!/usr/bin/env python3
"""ux-laws scorecard: turn inventory.json (static) and probe JSON files (runtime, one per
route x viewport) into a guardrail scorecard - PASS / WARN / FAIL / NOT_MEASURED per metric,
each tied to the Law of UX or standard it protects.

NOT_MEASURED is never a pass. A metric with no evidence stays NOT_MEASURED in the output and
counts against "measured coverage", so a thin audit cannot look like a clean one.

Usage
  python3 scorecard.py [--inventory inventory.json] [--probes DIR_OR_FILES ...]
                       [--manual manual.json] [--baseline previous-scorecard.json]
                       [--out DIR] [--json]

  --probes     probe JSON files, or directories containing them (*.json). Name them
               <route>@<width>.json so rows read well (walk.mjs does this).
  --manual     JSON object of hand-measured values for metrics no script can see, e.g.
               {"inp_ms": 180, "feedback_ms": 250, "focus_visible": true, "keyboard_complete": true,
                "states_verified": 3, "states_total": 4}
  --baseline   a previous scorecard.json; adds a delta column so iterations show movement
  --out DIR    write scorecard.md + scorecard.json there (default: print markdown)

Thresholds live in THRESHOLDS below and are mirrored in references/metrics.md. Tune them in a
project-local copy if the product has a reason; record that reason in the audit report.
Exit code: 0 always for a produced scorecard (it is a report, not a gate); 2 on bad input.
Use --gate to exit 1 when any FAIL is present.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

LAW = "https://lawsofux.com/"

# id, label, law/standard, source url, kind, comparator, warn, fail
#   kind "max": value must be <= warn to PASS, <= fail-1... (see judge())
THRESHOLDS = [
    # ---- runtime, mobile-first (judged on the narrowest viewport measured, plus every viewport for reflow)
    ("viewport_meta", "Pages missing <meta name=viewport> (or blocking zoom)", "WCAG 1.4.4 · mobile-first baseline", "https://developer.mozilla.org/en-US/docs/Web/HTML/Viewport_meta_tag", "max", 0, 1),
    ("reflow", "No horizontal scroll at narrow widths", "WCAG 1.4.10 Reflow · Fitts", "https://www.w3.org/WAI/WCAG22/Understanding/reflow.html", "bool_false", None, None),
    ("targets_24", "Targets below 24×24 CSS px", "WCAG 2.5.8 · Fitts's Law", "https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html", "max", 0, 1),
    ("targets_44", "Touch targets below 44 px (coarse pointer)", "Fitts's Law · Apple HIG 44pt", LAW + "fittss-law/", "max", 0, 999999),
    ("input_zoom", "Inputs under 16px font on mobile (iOS focus zoom)", "Flow · Doherty", LAW + "flow/", "max", 0, 1),
    ("unlabeled_fields", "Fields without a programmatic label", "WCAG 1.3.1/3.3.2 · Working Memory", LAW + "working-memory/", "max", 0, 1),
    ("type_hints", "Email/phone/numeric fields without the matching type/inputmode", "Postel's Law", LAW + "postels-law/", "max", 0, 999999),
    ("form_wall", "Largest single form/step (visible fields)", "Chunking · Hick's Law", LAW + "chunking/", "max", 7, 13),
    ("primary_actions", "Filled/gradient CTAs competing in the first viewport", "Hick's Law · Von Restorff", LAW + "hicks-law/", "max", 1, 3),
    ("contrast", "Text below WCAG contrast (4.5:1, 3:1 large)", "WCAG 1.4.3 · Von Restorff", "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html", "max", 0, 1),
    ("tiny_text", "Text under 12px", "Cognitive Load", LAW + "cognitive-load/", "max", 0, 999999),
    ("images_alt", "Images without alt", "WCAG 1.1.1", "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html", "max", 0, 1),
    ("h1", "Pages without exactly one h1 / with skipped heading levels", "Chunking · Serial Position", LAW + "chunking/", "max", 0, 999999),
    ("nav_links", "Top-level nav links (review trigger, not a 7±2 rule)", "Hick's Law · Choice Overload", LAW + "hicks-law/", "max", 7, 999999),
    ("fixed_chrome", "Viewport share covered by fixed/sticky chrome (mobile)", "Selective Attention", LAW + "selective-attention/", "max_float", 0.2, 0.35),
    ("hover_only", "Hover-reveal CSS rules not guarded by @media (hover: hover)", "Jakob's Law · Fitts", LAW + "jakobs-law/", "max", 0, 999999),
    ("font_families", "Distinct font families rendered", "Law of Similarity", LAW + "law-of-similarity/", "max", 3, 5),
    ("font_sizes", "Distinct font sizes rendered (type-scale sprawl)", "Law of Similarity · Prägnanz", LAW + "law-of-similarity/", "max", 9, 14),
    ("radii", "Distinct border radii rendered", "Law of Similarity · Common Region", LAW + "law-of-common-region/", "max", 5, 8),
    ("shadows", "Distinct box shadows rendered", "Law of Common Region", LAW + "law-of-common-region/", "max", 4, 7),
    ("gradients", "Elements with gradient backgrounds", "Anti-generic · Von Restorff", LAW + "von-restorff-effect/", "max", 1, 999999),
    ("copy_tells", "Template copy (Welcome back, Get started, An error occurred…)", "Mental Model · Peak-End", LAW + "mental-model/", "max", 0, 999999),
    ("em_dashes", "Em/en dashes in visible UI copy", "Anti-generic (copy tell)", LAW + "mental-model/", "max", 0, 999999),
    ("emoji", "Emoji used as icons or decoration in UI text", "Cognitive Load · anti-generic", LAW + "cognitive-load/", "max", 0, 999999),
    ("eyebrows", "Small uppercase tracked labels (eyebrows) per page", "Selective Attention · anti-generic", LAW + "selective-attention/", "max", 2, 999999),
    ("accent_hues", "Distinct saturated hues on interactive elements (accent lock)", "Von Restorff · Similarity", LAW + "von-restorff-effect/", "max", 2, 4),
    ("lcp", "LCP of a lab load, ms (field target: p75 ≤ 2500)", "Doherty Threshold · Core Web Vitals", "https://web.dev/articles/lcp", "max", 2500, 4000),
    ("cls", "CLS of a lab load (field target: p75 ≤ 0.1)", "Core Web Vitals", "https://web.dev/articles/cls", "max_float", 0.1, 0.25),
    # ---- static (inventory)
    ("token_adoption", "Token adoption: var(--x) refs ÷ (refs + raw color/arbitrary literals)", "Law of Similarity", LAW + "law-of-similarity/", "min_float", 0.8, 0.5),
    ("families_split", "Component families with more than one member (consolidation candidates)", "Law of Similarity · Occam's Razor", LAW + "occams-razor/", "max", 0, 999999),
    ("dup_names", "Component names defined in more than one file", "Occam's Razor", LAW + "occams-razor/", "max", 0, 999999),
    ("bypass", "Raw native controls used where a primitive exists", "Law of Similarity · Jakob's Law", LAW + "law-of-similarity/", "max", 0, 10),
    ("data_states", "Data views missing loading, error or empty handling", "Doherty · Postel · Peak-End", LAW + "doherty-threshold/", "max", 0, 1),
    # ---- manual (no script sees these; supply via --manual)
    ("inp_ms", "INP, ms (field p75 ≤ 200)", "Doherty Threshold · Core Web Vitals", "https://web.dev/articles/inp", "max", 200, 500),
    ("feedback_ms", "Slowest visible feedback after an action, ms", "Doherty Threshold (<400ms)", LAW + "doherty-threshold/", "max", 400, 1000),
    ("focus_visible", "Keyboard focus visible on every control", "WCAG 2.4.7 · Fitts", "https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html", "bool_true", None, None),
    ("keyboard_complete", "Critical path completable by keyboard alone", "WCAG 2.1.1", "https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html", "bool_true", None, None),
    ("states_coverage", "Empty/loading/error/success verified in the running app (fraction)", "Doherty · Postel · Peak-End", LAW + "peak-end-rule/", "min_float", 1.0, 0.5),
]


def judge(kind, value, warn, fail):
    if value is None:
        return "NOT_MEASURED"
    if kind == "bool_false":
        return "FAIL" if value else "PASS"
    if kind == "bool_true":
        return "PASS" if value else "FAIL"
    if kind in ("max", "max_float"):
        if value <= warn:
            return "PASS"
        return "FAIL" if value >= fail else "WARN"
    if kind == "min_float":
        if value >= warn:
            return "PASS"
        return "FAIL" if value < fail else "WARN"
    return "NOT_MEASURED"


def load_probes(items):
    files = []
    for it in items or []:
        if os.path.isdir(it):
            files += sorted(glob.glob(os.path.join(it, "*.json")))
        else:
            files += glob.glob(it)
    probes = []
    for f in files:
        try:
            d = json.loads(Path(f).read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"skip {f}: {e}", file=sys.stderr)
            continue
        if isinstance(d, dict) and "viewport" in d:
            d["_file"] = Path(f).stem
            probes.append(d)
    return probes


def from_probes(probes):
    """Metric -> (value, evidence). Mobile metrics use the narrowest viewport per route."""
    if not probes:
        return {}
    v = {}
    width = lambda p: p.get("requestedWidth") or p["viewport"]["w"]
    narrow_w = min(width(p) for p in probes)
    narrow = [p for p in probes if width(p) <= max(480, narrow_w)]
    worst = lambda ps, f: max(((f(p), p["_file"]) for p in ps), key=lambda t: t[0], default=(None, None))

    def total(ps, f):
        # max per route across its viewports (same element is not counted twice), summed over routes
        per_route = {}
        for p in ps:
            route = p["_file"].split("@")[0]
            n = f(p)
            if n > per_route.get(route, (-1, ""))[0]:
                per_route[route] = (n, p["_file"])
        return (sum(n for n, _ in per_route.values()), ", ".join(fl for n, fl in per_route.values() if n))

    def bad_meta(p):
        m = (p["structure"].get("viewportMeta") or "").replace(" ", "").lower()
        return int(not m or "width=device-width" not in m or "user-scalable=no" in m or "maximum-scale=1" in m)
    v["viewport_meta"] = total(probes, bad_meta) if any("viewportMeta" in p["structure"] for p in probes) else (None, "")
    over = [p["_file"] for p in probes if p["reflow"]["horizontalOverflow"]]
    v["reflow"] = (bool(over), "overflow at " + ", ".join(over) if over else f"none across {len(probes)} captures")
    v["targets_24"] = total(probes, lambda p: p["targets"]["below24"])
    v["targets_44"] = total(narrow, lambda p: p["targets"]["below44"]) if narrow else (None, "")
    v["input_zoom"] = total(narrow, lambda p: p["fields"]["below16px"]) if narrow else (None, "")
    v["unlabeled_fields"] = total(probes, lambda p: p["fields"]["unlabeled"])
    v["type_hints"] = total(probes, lambda p: len(p["fields"]["typeHints"]))
    v["form_wall"] = worst(probes, lambda p: max([f["fields"] for f in p["fields"]["forms"]] or [0]))
    v["primary_actions"] = worst(probes, lambda p: p["primaryActions"]["firstViewportFilled"])
    v["contrast"] = total(probes, lambda p: p["text"]["lowContrast"])
    v["tiny_text"] = total(probes, lambda p: p["text"]["below12px"])
    v["images_alt"] = total(probes, lambda p: p["structure"]["imagesMissingAlt"])
    v["h1"] = total(probes, lambda p: int(p["structure"]["h1"] != 1) + int(p["structure"]["headingSkips"] > 0))
    v["nav_links"] = worst(probes, lambda p: p["structure"]["topNavLinks"])
    v["fixed_chrome"] = worst(narrow, lambda p: p["chrome"]["fixedViewportShare"]) if narrow else (None, "")
    v["hover_only"] = worst(probes, lambda p: p["hover"]["revealOnHoverRulesNotGuarded"])
    v["font_families"] = worst(probes, lambda p: len([f for f in p["system"]["fontFamilies"] if f]))
    v["font_sizes"] = worst(probes, lambda p: p["system"]["fontSizes"])
    v["radii"] = worst(probes, lambda p: p["system"]["radii"])
    v["shadows"] = worst(probes, lambda p: p["system"]["shadows"])
    v["gradients"] = worst(probes, lambda p: p["system"]["gradientElements"])
    tells = sorted({t for p in probes for t in p["copy"]["tells"]})
    v["copy_tells"] = (len(tells), ", ".join(f'"{t}"' for t in tells))
    if any("taste" in p for p in probes):
        tp = [p for p in probes if "taste" in p]
        v["em_dashes"] = worst(tp, lambda p: p["taste"]["emDashes"])
        v["emoji"] = worst(tp, lambda p: p["taste"]["emoji"])
        v["eyebrows"] = worst(tp, lambda p: p["taste"]["eyebrows"])
        v["accent_hues"] = worst(tp, lambda p: p["taste"]["accentHues"])
    lcps = [(p["perf"]["lcpMs"], p["_file"]) for p in probes if p.get("perf") and p["perf"].get("lcpMs") is not None]
    v["lcp"] = max(lcps) if lcps else (None, "no LCP entry (headless or no paint observed)")
    clss = [(p["perf"]["cls"], p["_file"]) for p in probes if p.get("perf") and p["perf"].get("cls") is not None]
    v["cls"] = max(clss) if clss else (None, "")
    return v


def from_inventory(inv):
    if not inv:
        return {}
    c = inv["counts"]
    comp = inv.get("composed", {})
    fam = {k: m for k, m in inv["families"].items() if len([x for x in m if x not in comp]) > 1}
    bypass_rows = [(el, sum(x["count"] for x in rows)) for el, rows in inv["raw_element_bypass"].items()
                   if inv["primitive_exists"].get({"button": "button", "input": "field", "select": "field", "textarea": "field",
                                                   "table": "table", "dialog": "overlay", "img": "media", "a": "link"}[el])]
    missing = [d["file"] for d in inv["data_views"] if not (d["loading"] and d["error"] and d["empty"])]
    return {
        "token_adoption": (inv["style"]["token_adoption"], f'{inv["style"]["totals"].get("token_refs", 0)} token refs'),
        "families_split": (len(fam), "; ".join(f"{k}: {', '.join(m[:6])}" for k, m in fam.items())),
        "dup_names": (c["duplicate_component_names"], ""),
        "bypass": (sum(n for _, n in bypass_rows), ", ".join(f"<{el}>×{n}" for el, n in bypass_rows)),
        "data_states": (len(missing), ", ".join(missing[:6])),
    }


def from_manual(m):
    if not m:
        return {}
    out = {}
    for k in ("inp_ms", "feedback_ms", "focus_visible", "keyboard_complete"):
        if k in m:
            out[k] = (m[k], "manual")
    if "states_verified" in m and m.get("states_total"):
        out["states_coverage"] = (round(m["states_verified"] / m["states_total"], 2), f'{m["states_verified"]}/{m["states_total"]} manual')
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory")
    ap.add_argument("--probes", nargs="*")
    ap.add_argument("--manual")
    ap.add_argument("--baseline")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--gate", action="store_true")
    a = ap.parse_args()

    def jload(p):
        if not p:
            return None
        try:
            return json.loads(Path(p).read_text())
        except (OSError, json.JSONDecodeError) as e:
            print(f"cannot read {p}: {e}", file=sys.stderr)
            sys.exit(2)

    probes = load_probes(a.probes)
    values = {}
    values.update(from_probes(probes))
    values.update(from_inventory(jload(a.inventory)))
    values.update(from_manual(jload(a.manual)))
    base = {r["id"]: r for r in (jload(a.baseline) or {}).get("rows", [])}

    rows = []
    for mid, label, law, url, kind, warn, fail in THRESHOLDS:
        val, ev = values.get(mid, (None, ""))
        status = judge(kind, val, warn, fail)
        target = {"bool_false": "false", "bool_true": "true"}.get(kind) or (f"≥ {warn}" if kind == "min_float" else f"≤ {warn}")
        row = {"id": mid, "metric": label, "law": law, "source": url, "value": val, "target": target, "status": status, "evidence": ev}
        if mid in base and isinstance(val, (int, float)) and isinstance(base[mid].get("value"), (int, float)) and not isinstance(val, bool):
            row["delta"] = round(val - base[mid]["value"], 3)
        rows.append(row)

    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("PASS", "WARN", "FAIL", "NOT_MEASURED")}
    measured = len(rows) - counts["NOT_MEASURED"]
    result = {
        "captures": [p["_file"] for p in probes],
        "viewports": sorted({p.get("requestedWidth") or p["viewport"]["w"] for p in probes}),
        "counts": counts,
        "measured_coverage": f"{measured}/{len(rows)}",
        "rows": rows,
    }
    md = render(result, bool(base))
    if a.out:
        Path(a.out).mkdir(parents=True, exist_ok=True)
        Path(a.out, "scorecard.json").write_text(json.dumps(result, indent=2))
        Path(a.out, "scorecard.md").write_text(md)
        print(f"wrote {a.out}/scorecard.md and scorecard.json", file=sys.stderr)
    if a.json:
        print(json.dumps(result, indent=2))
    elif not a.out:
        print(md)
    return 1 if (a.gate and counts["FAIL"]) else 0


def render(r, with_delta):
    icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "**FAIL**", "NOT_MEASURED": "NOT_MEASURED"}
    c = r["counts"]
    L = ["# UX guardrail scorecard", "",
         f"Captures: {', '.join(r['captures']) or 'none'} · viewports: {', '.join(map(str, r['viewports'])) or 'none'}",
         f"**{c['FAIL']} FAIL · {c['WARN']} WARN · {c['PASS']} PASS · {c['NOT_MEASURED']} NOT_MEASURED** - measured coverage {r['measured_coverage']}",
         "", "NOT_MEASURED is not a pass. Lab LCP/CLS are one load, not field p75.", "",
         "| status | metric | value | target | law / standard | evidence |" + (" Δ |" if with_delta else ""),
         "|---|---|---|---|---|---|" + ("---|" if with_delta else "")]
    order = {"FAIL": 0, "WARN": 1, "NOT_MEASURED": 2, "PASS": 3}
    for row in sorted(r["rows"], key=lambda x: order[x["status"]]):
        val = "-" if row["value"] is None else row["value"]
        d = f" {row.get('delta', '')} |" if with_delta else ""
        ev = (row["evidence"] or "")[:140].replace("|", "/")
        L.append(f"| {icon[row['status']]} | {row['metric']} | {val} | {row['target']} | [{row['law']}]({row['source']}) | {ev} |{d}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
