#!/usr/bin/env python3
"""Keep the rule registry and the checks that claim to test it in sync.

The failure this prevents is the quiet one: prose citing a rule ID that does not
exist, or a detector advertising coverage nobody implemented. Both make a report
look more rigorous than it is, which is worse than having no report.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

# Do not leave .pyc files beside the checks. A directory-source plugin install
# copies the working tree verbatim, so stray bytecode ships to the consumer
# despite being gitignored. Costs ~15ms per run, which nothing here notices.
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
RULES = SKILL / "references" / "rules"

# Detector IDs cited in prose. A doc that names `S-CRAFT-HALOO` reads exactly as
# authoritative as one that names the real detector, and the reader who tries to
# run it finds nothing. A trailing hyphen or asterisk marks a family reference
# (`S-CRAFT-*`, `S-IOS-`), which is allowed.
DET_RE = re.compile(r"\b((?:S|R|M|A)-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b(?![-*])")

RULE_RE = re.compile(r"\b((?:GOV|CTX|UX|NUM|VIS|LAY|NAV|FORM|COMP|STATE|A11Y|PERF|"
                     r"CONTENT|TRUST|AI|MEASURE|QA|IOS|AND|TEST|LAW)-\d{2,3})\b")


def main() -> int:
    errors, warnings = [], []
    reg = yaml.safe_load((RULES / "registry.yaml").read_text())
    det = yaml.safe_load((RULES / "detectors.yaml").read_text())
    yaml.safe_load((RULES / "thresholds.yaml").read_text())   # must parse

    rule_ids = {r["id"] for r in reg["rules"]}
    test_ids = {t["id"] for t in reg["tests"]}
    law_ids = {l["id"] for l in reg["laws"]}
    known = rule_ids | test_ids | law_ids
    sources = set(reg["sources"])

    if len(rule_ids) != len(reg["rules"]):
        errors.append("duplicate rule IDs in registry.yaml")
    for r in reg["rules"]:
        if not re.fullmatch(r"[A-Z0-9]+-\d{3}", r["id"]):
            errors.append(f"malformed rule id {r['id']}")
        if r["severity"] not in ("P0", "P1", "P2"):
            errors.append(f"{r['id']}: bad severity {r['severity']}")
        for b in r["basis"]:
            if b not in sources:
                errors.append(f"{r['id']} cites unknown source {b}")

    # --- detectors must name real rules, and real engines
    engines = set(det["engines"])
    for did, d in det["detectors"].items():
        if d["engine"] not in engines:
            errors.append(f"{did}: unknown engine {d['engine']}")
        for rid in d["rules"]:
            if rid not in rule_ids:
                errors.append(f"{did} claims unknown rule {rid}")

    # --- declared coverage must actually exist
    from checks import ALL as IMPLEMENTED
    import ux_report

    declared_static = {k for k, v in det["detectors"].items()
                       if det["engines"][v["engine"]]["tier"] == "static"}
    declared_runtime = {k for k, v in det["detectors"].items()
                        if det["engines"][v["engine"]]["tier"] == "runtime"}

    for did in sorted(declared_static - set(IMPLEMENTED)):
        errors.append(f"{did} is declared but no static check implements it")
    for did in sorted(set(IMPLEMENTED) - declared_static):
        errors.append(f"{did} is implemented but not declared in detectors.yaml")
    for did in sorted(declared_runtime - set(ux_report.RUNTIME)):
        errors.append(f"{did} is declared but ux_report.RUNTIME does not handle it")
    for did in sorted(set(ux_report.RUNTIME) - declared_runtime):
        errors.append(f"{did} is handled in ux_report but not declared in detectors.yaml")

    # the report tier must be produced by the self-audit, or it is a claim with
    # nothing behind it -- exactly what A-EVIDENCE-BACKED exists to catch
    declared_report = {k for k, v in det["detectors"].items()
                       if det["engines"][v["engine"]]["tier"] == "report"}
    audit_src = (HERE / "ux_report.py").read_text()
    for did in sorted(declared_report):
        if f'"{did}"' not in audit_src:
            errors.append(f"{did} is declared as a report check but ux_report.py "
                          "never emits it")

    unimplemented = [k for k, v in ux_report.RUNTIME.items()
                     if v is None and k != "R-CONSOLE"]
    for did in unimplemented:
        if did not in ux_report.UNIMPLEMENTED:
            errors.append(f"{did} is unimplemented but gives no reason to report")

    # --- a manual detector without a question is an invitation to sign something
    # nobody performed. "Design review: PASS" certified eleven rules once; the
    # question is what makes a manual result a result rather than a mood.
    for did, d in det["detectors"].items():
        if d["engine"] != "manual":
            continue
        q = (d.get("question") or "").strip()
        if len(q) < 60:
            errors.append(f"{did} is a manual detector with no usable question. State "
                          f"what the person has to DO, specifically enough that another "
                          f"person could tell whether they did it.")
        if len(d["rules"]) > 4:
            errors.append(f"{did} puts {len(d['rules'])} rules behind one signature "
                          f"({', '.join(d['rules'])}). Split it: one attestation "
                          f"certifying many separate judgements is the laundering "
                          f"GOV-006 exists to prevent.")

    # --- prose may not invent rule IDs
    cited = {}
    for md in sorted(SKILL.rglob("*.md")):
        if "docs/" in md.as_posix():
            continue                      # the source rulebook defines them
        for m in RULE_RE.finditer(md.read_text(errors="replace")):
            cited.setdefault(m.group(1), set()).add(md.relative_to(SKILL).as_posix())
    for rid, where in sorted(cited.items()):
        if rid not in known:
            errors.append(f"{rid} cited in {', '.join(sorted(where))} but not in the registry")

    # --- prose may not invent detector IDs either
    cited_det = {}
    for md in sorted(SKILL.rglob("*.md")):
        if "docs/" in md.as_posix():
            continue
        for m in DET_RE.finditer(md.read_text(errors="replace")):
            cited_det.setdefault(m.group(1), set()).add(md.relative_to(SKILL).as_posix())
    for did, where in sorted(cited_det.items()):
        if did not in det["detectors"]:
            errors.append(f"{did} cited in {', '.join(sorted(where))} but no such "
                          f"detector exists. A doc that names a detector nobody can "
                          f"run is worse than one that names none.")

    # --- every check must tell the reader what to do about a hit. The fix text
    # is the user-facing explanation, so a thin one is a real defect.
    for did, chk in IMPLEMENTED.items():
        src = (chk.fn.__doc__ or "") + (chk.fn.__code__.co_consts and
                                        " ".join(str(c) for c in chk.fn.__code__.co_consts
                                                 if isinstance(c, str)) or "")
        if len(src) < 120:
            warnings.append(f"{did} gives the reader almost no guidance on a hit")

    # A declared-but-unimplemented detector cannot produce a verdict, so a rule
    # whose ONLY detectors are inert is not covered -- it is orphaned, and can
    # never report anything but NOT_RUN no matter what anyone does. Counting it as
    # covered is how "rules with a detector 190, without 0" concealed three P1
    # rules that were unreachable.
    covered = {r for d in det["detectors"].values() for r in d["rules"]}
    inert = set(unimplemented)

    # --- law reachability. The laws were carried as data and consumed by nothing,
    # while index.md advertised "19 enforceable laws" and lint used their IDs only
    # to spell-check prose. A law now has to name a detector that can produce a
    # verdict, or be published as unreachable -- the three fates stated apart,
    # because a live check and somebody's signature are not the same evidence.
    law_live, law_manual = set(), set()
    for did, d in det["detectors"].items():
        if did in inert:
            continue
        for lid in d.get("laws", []):
            if lid not in law_ids:
                errors.append(f"{did} claims unknown law {lid}")
                continue
            (law_manual if d.get("engine") == "manual" else law_live).add(lid)
    enforceable = {l["id"] for l in reg["laws"] if l.get("enforceable") is not False}
    law_manual -= law_live
    law_unreachable = sorted(enforceable - law_live - law_manual)

    reachable = {r for did, d in det["detectors"].items() if did not in inert
                 for r in d["rules"]}
    orphaned = sorted(rule_ids - reachable)
    for rid in orphaned:
        sev = next(r["severity"] for r in reg["rules"] if r["id"] == rid)
        errors.append(f"{rid} ({sev}) is orphaned: every detector naming it is "
                      f"declared but unimplemented, so it can only ever report "
                      f"NOT_RUN. Implement one, or give it a manual detector.")
    print(f"rules {len(rule_ids)}  laws {len(law_ids)}  tests {len(test_ids)}  "
          f"sources {len(sources)}")
    print(f"detectors {len(det['detectors'])}  static {len(declared_static)}  "
          f"runtime {len(declared_runtime)}  report {len(declared_report)}  manual "
          f"{len(det['detectors']) - len(declared_static) - len(declared_runtime) - len(declared_report)}")
    print(f"rules with a detector {len(covered)}  without {len(rule_ids - covered)}  "
          f"orphaned onto inert detectors {len(orphaned)}")
    print(f"laws {len(enforceable)} enforceable: live detector {len(law_live)}  "
          f"manual only {len(law_manual)}  unreachable {len(law_unreachable)}"
          + (f" ({', '.join(law_unreachable)})" if law_unreachable else ""))
    print(f"runtime detectors declared but not yet implemented: "
          f"{len(unimplemented)} ({', '.join(unimplemented) or 'none'})")
    print(f"distinct rule IDs cited in prose: {len(cited)}  "
          f"detector IDs cited: {len(cited_det)}")

    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    print("\nLINT", "PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
