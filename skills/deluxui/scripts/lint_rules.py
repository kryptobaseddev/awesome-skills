#!/usr/bin/env python3
"""Keep the rule registry and the checks that claim to test it in sync.

The failure this prevents is the quiet one: prose citing a rule ID that does not
exist, or a detector advertising coverage nobody implemented. Both make a report
look more rigorous than it is, which is worse than having no report.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
RULES = SKILL / "references" / "rules"

RULE_RE = re.compile(r"\b((?:GOV|CTX|UX|NUM|VIS|LAY|NAV|FORM|COMP|STATE|A11Y|PERF|"
                     r"CONTENT|TRUST|AI|MEASURE|QA|TEST|LAW)-\d{2,3})\b")


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

    unimplemented = [k for k, v in ux_report.RUNTIME.items()
                     if v is None and k != "R-CONSOLE"]
    for did in unimplemented:
        if did not in ux_report.UNIMPLEMENTED:
            errors.append(f"{did} is unimplemented but gives no reason to report")

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

    # --- every check must tell the reader what to do about a hit. The fix text
    # is the user-facing explanation, so a thin one is a real defect.
    for did, chk in IMPLEMENTED.items():
        src = (chk.fn.__doc__ or "") + (chk.fn.__code__.co_consts and
                                        " ".join(str(c) for c in chk.fn.__code__.co_consts
                                                 if isinstance(c, str)) or "")
        if len(src) < 120:
            warnings.append(f"{did} gives the reader almost no guidance on a hit")

    covered = {r for d in det["detectors"].values() for r in d["rules"]}
    print(f"rules {len(rule_ids)}  laws {len(law_ids)}  tests {len(test_ids)}  "
          f"sources {len(sources)}")
    print(f"detectors {len(det['detectors'])}  static {len(declared_static)}  "
          f"runtime {len(declared_runtime)}  manual "
          f"{len(det['detectors']) - len(declared_static) - len(declared_runtime)}")
    print(f"rules with a detector {len(covered)}  without {len(rule_ids - covered)}")
    print(f"runtime detectors declared but not yet implemented: "
          f"{len(unimplemented)} ({', '.join(unimplemented) or 'none'})")
    print(f"distinct rule IDs cited in prose: {len(cited)}")

    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    print("\nLINT", "PASS" if not errors else f"FAIL ({len(errors)} errors)")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
