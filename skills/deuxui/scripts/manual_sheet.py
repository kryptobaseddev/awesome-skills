#!/usr/bin/env python3
"""Emit the manual tier as a sheet of questions, and report what is unanswered.

  manual_sheet.py                 # print the sheet
  manual_sheet.py --write         # write .deuxui/reports/manual.yaml if absent
  manual_sheet.py --check         # what is still unanswered, and what was refused
  manual_sheet.py --detector M-SCREENREADER   # one question, in full

Why this exists. A manual result is the one place in this tool where a sentence
becomes a status, so it is the one place worth making harder rather than easier.
Every manual detector carries the question the person has to answer -- a specific
act, phrased so a second person could tell whether it was performed. Writing
`status: PASS` beside "reviewed the design" is not an answer to any of them, and
ux_report refuses it: a PASS needs a `who` who is not the party making the claim,
a `date`, and evidence with something in it.

The sheet is the honest form of the work. Twenty questions mostly unanswered is a
better report than one signature covering all of them.
"""
from __future__ import annotations
import argparse, sys, textwrap
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import yaml
import rulepack

DEFAULT = Path(".deuxui/reports/manual.yaml")


def questions():
    _reg, det, _th = rulepack.load()
    out = []
    for did, d in sorted(det["detectors"].items()):
        if d.get("engine") != "manual":
            continue
        out.append((did, " ".join((d.get("question") or "").split()), d["rules"],
                    d.get("laws", [])))
    return out


def sheet_text(existing: dict | None = None) -> str:
    have = ((existing or {}).get("attestations") or {})
    lines = [
        "# deuxui manual tier -- the checks no machine settles.",
        "#",
        "# Answer the ones you performed. Leave the rest alone: an unanswered",
        "# question reports NOT_RUN, which is accurate, and a P0 or P1 rule left",
        "# NOT_RUN blocks a release gate. That is the design, not a defect.",
        "#",
        "# A PASS is admissible only with a `who` who is not the agent writing",
        "# this, a `date`, and evidence a reader could check. A FAIL is always",
        "# honoured, however thin -- nobody launders a failure.",
        "",
        "attestations:",
    ]
    for did, q, rules, laws in questions():
        rec = have.get(did) or {}
        lines.append("")
        for ln in textwrap.wrap(q, 74):
            lines.append(f"  # {ln}")
        lines.append(f"  # settles: {', '.join(rules)}"
                     + (f"   laws: {', '.join(laws)}" if laws else ""))
        lines.append(f"  {did}:")
        lines.append(f"    status: {rec.get('status', 'NOT_RUN')}   "
                     f"# PASS | FAIL | NOT_RUN")
        lines.append(f"    who: {rec.get('who', '')!s}".rstrip()
                     + ("" if rec.get("who") else "          # a person, not a tool"))
        lines.append(f"    date: {rec.get('date', '')!s}".rstrip()
                     + ("" if rec.get("date") else "         # YYYY-MM-DD"))
        ev = str(rec.get("evidence", "") or "")
        if ev:
            lines.append(f"    evidence: >-")
            for ln in textwrap.wrap(ev, 70):
                lines.append(f"      {ln}")
        else:
            # A placeholder written INSIDE the block scalar parses as evidence,
            # and "# What you did" is 40-odd characters of nothing that the
            # admissibility check would then weigh. Keep the prompt in a comment.
            lines.append("    # Say what you did and what happened -- answer the question")
            lines.append("    # above rather than restating the rule.")
            lines.append('    evidence: ""')
    return "\n".join(lines) + "\n"


def check(path: Path) -> int:
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    have = ((data or {}).get("attestations") or {})
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ux_report
    rows = []
    for did, q, rules, _laws in questions():
        rec = have.get(did)
        if not rec:
            rows.append(("NOT_RUN", did, "not in the sheet", rules, q))
            continue
        st, why, _att = ux_report.vet_attestation(did, rec)
        rows.append((st, did, why, rules, q))
    order = {"FAIL": 0, "NOT_RUN": 1, "PASS": 2}
    rows.sort(key=lambda r: (order.get(r[0], 3), r[1]))
    w = sys.stdout.write
    w(f"manual tier: {path}\n" + "-" * 74 + "\n")
    for st, did, why, rules, q in rows:
        w(f"  {st:<9} {did:<26} {', '.join(rules)}\n")
        if st != "PASS":
            w(f"            {why[:150]}\n")
            w(f"            ask: {q[:130]}\n")
    n = {k: sum(1 for r in rows if r[0] == k) for k in ("PASS", "FAIL", "NOT_RUN")}
    w("-" * 74 + f"\n  NOT_RUN {n['NOT_RUN']}   FAIL {n['FAIL']}   PASS {n['PASS']}"
      f"   of {len(rows)}\n")
    if n["NOT_RUN"]:
        w("\nNOT_RUN first, on purpose. These are the questions nobody has answered,\n"
          "and no amount of static or runtime checking will answer them.\n")
    return 2 if n["FAIL"] else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write the sheet to disk")
    ap.add_argument("--check", action="store_true", help="report what is unanswered")
    ap.add_argument("--detector", help="print one question in full")
    ap.add_argument("--path", default=str(DEFAULT))
    a = ap.parse_args(argv)
    path = Path(a.path)

    if a.detector:
        for did, q, rules, laws in questions():
            if did == a.detector:
                print(f"{did}   settles {', '.join(rules)}"
                      + (f"   laws {', '.join(laws)}" if laws else ""))
                print()
                print(textwrap.fill(q, 76))
                return 0
        sys.stderr.write(f"no manual detector named {a.detector}\n")
        return 1

    if a.check:
        return check(path)

    existing = yaml.safe_load(path.read_text()) if path.exists() else None
    text = sheet_text(existing)
    if a.write:
        if path.exists():
            # Never overwrite somebody's recorded work. Regenerating the sheet
            # preserves every answer already in it and only adds what is new.
            path.write_text(text)
            sys.stderr.write(f"updated {path}, preserving {len((existing or {}).get('attestations') or {})} "
                             f"existing answer(s)\n")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            sys.stderr.write(f"wrote {path}\n")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
