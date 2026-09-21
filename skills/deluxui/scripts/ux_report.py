#!/usr/bin/env python3
"""deluxui verdict -- merge the static, runtime and manual tiers into one report.

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

import yaml

HERE = Path(__file__).resolve().parent
RULES = HERE.parent / "references" / "rules"
TH = yaml.safe_load((RULES / "thresholds.yaml").read_text())


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
        vp = int(name.rsplit("_", 1)[-1].removesuffix(".json"))
        if d.get("page_overflows"):
            worst = min(worst or vp, vp)
            for o in d["offenders"][:5]:
                hits.append(f"{vp}px: <{o['tag']} class=\"{o['cls']}\"> extends to "
                            f"{o['right']}px ({o.get('text','')[:30]})")
    if not hits:
        return ("PASS", f"No horizontal overflow at any tested viewport (floor {floor}px).", [])
    return ("FAIL", f"Page scrolls sideways from {worst}px down.", hits)


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
    hits, imaged = [], 0
    for name, d in raws.items():
        if not name.endswith("__contrast.json") or "failures" not in d:
            continue
        for fl in d["failures"]:
            if fl.get("backdrop_has_image"):
                imaged += 1
                continue
            hits.append(f"{fl['ratio']}:1 (needs {fl['need']}:1) {fl['color']} "
                        f"at {fl['fontPx']}px -- \"{fl['text']}\"")
    note = (f" {imaged} further candidates sit on a background image and were not "
            "judged -- only a pixel read can settle those." if imaged else "")
    if not hits:
        return ("PASS", "All resolvable rendered text meets its contrast floor." + note, [])
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


def _console(raws, texts, out):
    hits = [f"{k}: {v.strip()[:160]}" for k, v in texts.items()
            if k.endswith("__errors.txt") and v.strip()]
    if not hits:
        return ("PASS", "No uncaught page errors during the run.", [])
    return ("FAIL", "The page threw during a normal visit.", hits[:10])


def _state(mode, label, rules_hint):
    def fn(raws, out):
        found = False
        hits = []
        for name, d in raws.items():
            if f"__state_{mode}.json" not in name or "probe" not in d:
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


# Declared runtime detectors. None means "declared but not implemented yet" --
# it reports NOT_RUN with that reason rather than quietly vanishing.
RUNTIME = {
    "R-REFLOW": _reflow,
    "R-TARGET": _targets,
    "R-TARGET-COARSE": _target_coarse,
    "R-CONTRAST": _contrast,
    "R-FOCUS-WALK": _focus,
    "R-MOTION": _motion,
    "R-VITALS": _vitals,
    "R-MEASURE": _measure,
    "R-CONSOLE": None,
    "R-STATE-ERROR": _state("abort", "An aborted request", None),
    "R-STATE-EMPTY": _state("empty", "An empty result set", None),
    "R-STATE-OFFLINE": _state("offline", "Going offline", None),
    "R-STATE-SLOW": None,
    "R-AXE": None,
    "R-ZOOM": _override("zoom", "200% text size", "NUM-008 / SC 1.4.4"),
    "R-TEXTSPACING": _override("spacing", "The text-spacing override",
                               "NUM-010 / SC 1.4.12"),
    "R-PIXEL-CONTRAST": None,
    "R-BASELINE-DIFF": None,
    "R-FORCED-COLORS": None,
}
UNIMPLEMENTED = {
    "R-STATE-SLOW": "Response throttling is not wired into the driver yet.",
    "R-AXE": "axe-core was not loaded. Install it in the project (npm i -D axe-core) "
             "to add rule-level coverage this probe set does not reproduce.",
    "R-PIXEL-CONTRAST": "Pixel sampling is not implemented. Text over images is "
                        "reported by R-CONTRAST as unjudged rather than guessed.",
    "R-BASELINE-DIFF": "No baseline screenshot was recorded before the change.",
    "R-FORCED-COLORS": "Forced-colors emulation is not available through the driver yet.",
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

def self_audit(results, dstat, static, runtime, config, release, manual=None):
    """Returns {detector_id: (status, note)} for the A-* family."""
    out = {}

    # --- GOV-006: no PASS without a detector that reported PASS
    passes = [r for r in results if r["status"] == "PASS"]
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
    else:
        out["A-EVIDENCE-BACKED"] = ("PASS",
            f"All {len(passes)} PASS rules name the detector that produced them.")

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
    disabled = set(config.get("disabled_checks") or [])
    overrides = (config.get("thresholds") or {})
    violations = []
    if disabled:
        violations.append(f"{len(disabled)} checks disabled in project config "
                          f"({', '.join(sorted(disabled)[:5])}) -- the rules they "
                          "cover now report NOT_RUN, not PASS")
    for group, vals in overrides.items():
        block = TH.get(group, {})
        allowed = block.get("overridable")
        if allowed is False:
            violations.append(f"thresholds.{group} is marked non-overridable "
                              "(it comes from a standard) but the project overrides it")
        elif isinstance(allowed, list):
            bad = [k for k in vals if k not in allowed]
            if bad:
                violations.append(f"thresholds.{group}: {', '.join(bad)} "
                                  "is not in the overridable list")
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
def merge(static_json: Path, runtime_json: Path, manual_yaml: Path,
          features: list, release: bool, config_path: Path | None = None):
    reg = yaml.safe_load((RULES / "registry.yaml").read_text())
    det = yaml.safe_load((RULES / "detectors.yaml").read_text())["detectors"]
    static = load(static_json, {}) or {}
    runtime = load(runtime_json, {}) or {}
    manual = {}
    if manual_yaml and manual_yaml.exists():
        manual = yaml.safe_load(manual_yaml.read_text()) or {}

    dstat = {}
    for k, v in (static.get("detectors") or {}).items():
        dstat[k] = (v["status"], v.get("note", ""))
    for k, v in (runtime.get("detectors") or {}).items():
        dstat[k] = (v["status"], v.get("note", ""))
    for k, v in (manual.get("attestations") or {}).items():
        dstat[k] = (v.get("status", "NOT_RUN"), v.get("evidence", ""))

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

    config = {}
    if config_path and config_path.exists():
        config = yaml.safe_load(config_path.read_text()) or {}
    audit = self_audit(results, dstat, static, runtime, config, release, manual)
    # fold the A-* results back in as rule statuses for the GOV rules they cover
    A_RULES = {"A-EVIDENCE-BACKED": ["GOV-006"], "A-UNKNOWN-DECLARED": ["GOV-005"],
               "A-CONFIG-AUTHORITY": ["GOV-008"],
               "A-EVIDENCE-MAP": ["QA-001", "QA-005", "GOV-002"],
               "A-SCOPE-STATED": ["QA-002", "QA-003", "GOV-009", "A11Y-013"],
               "A-NO-INVENTED-METRICS": ["MEASURE-002", "MEASURE-005", "MEASURE-007"]}
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
        "generated_by": "deluxui/scripts/ux_report.py",
        "tiers_present": {"static": bool(static), "runtime": bool(runtime),
                          "manual": bool(manual)},
        "declared_features": features,
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
    sys.stderr.write(
        f"\nNOT_RUN {counts['NOT_RUN']}   FAIL {counts['FAIL']}   PASS {counts['PASS']}"
        f"   NOT_APPLICABLE {counts['NOT_APPLICABLE']}\n"
        f"release_decision: {decision} -- {why}\n")
    return 2 if decision == "BLOCKED" else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--collect", metavar="DIR", help="interpret raw runtime probe output")
    ap.add_argument("--base"); ap.add_argument("--api"); ap.add_argument("--routes")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--static", default=".deluxui/reports/static.json")
    ap.add_argument("--runtime", default=".deluxui/reports/runtime/runtime.json")
    ap.add_argument("--manual", default=".deluxui/reports/manual.yaml")
    ap.add_argument("--feature", action="append", default=[],
                    help="declare a feature the product has (repeatable)")
    ap.add_argument("--config", default=".deluxui/ux.config.yaml",
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
