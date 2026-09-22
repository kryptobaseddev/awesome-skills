#!/usr/bin/env python3
"""Every defect this skill has shipped, and the control that would catch it again.

    python3 defects.py [--check] [--json] [--id DEF-07] [--unguarded]

A defect list is the easiest document in a repository to write and the easiest to
stop believing. Prose saying "fixed" is exactly the shape of sentence this skill
exists to refuse -- unfalsifiable, self-reported, and true right up until somebody
edits the line it describes. So `references/defects.yaml` is data and this resolves
it, the same way `parity.py` resolves the coverage claim.

Each row carries two kinds of citation, and they answer different questions:

  guard    the fix, still present in the tree. Delete it and this goes red, so the
           row cannot quietly become a description of code that no longer exists.
  control  the assertion that fails when the fix is reverted. This is what makes
           "fixed" mean something: a fix with no control is one refactor away from
           being undone by somebody who never knew it was load-bearing.

A row may honestly have no control, and then it must say so in `no_control` and is
reported as UNGUARDED -- counted, named, and printed in the summary. That is the
NOT_RUN rule turned on this file: an unguarded fix is not the same as a guarded one
and averaging them into a single "24 fixed" is the laundering this whole skill
argues against.

Three integrity rules, because the ways a file like this rots are known:

  * a `control` may only cite a file that actually runs as a control. A row
    "guarded" by a reference document is guarded by nothing.
  * `fixed_in` may not be ahead of the shipped version in SKILL.md. A ledger that
    claims a fix in a release nobody has is a claim about the future.
  * every `guard` and `control` pattern must resolve. A citation that no longer
    matches is the failure mode this file exists to prevent, not a formatting nit.

Exit 0 when every row resolves, 2 when any does not (with `--check`).
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LEDGER = ROOT / "references" / "defects.yaml"
SKILL = ROOT / "SKILL.md"

# A control is a file that RUNS and can fail. A reference document cannot catch a
# regression, so citing one as a control is the error this list refuses.
CONTROLS = ("scripts/selftest.py", "scripts/browsertest.py", "scripts/lint_rules.py",
            "scripts/native_conformance.py", "scripts/parity.py", "scripts/checks/")

REQUIRED = ("id", "title", "surface", "symptom", "consequence", "fix",
            "found_in", "fixed_in", "class")

# What kind of wrong it was. Not decoration: a wrong result and a check that could
# not fail need different kinds of control, and counting them together hides which
# of the two this tool keeps producing.
CLASSES = ("wrong-result", "never-worked", "undetectable", "dead-end", "latent",
           "drift")
ID_RE = re.compile(r"^DEF-\d{2}$")


def shipped_version() -> tuple:
    """The version SKILL.md says this is, as a tuple. () when it cannot be read."""
    try:
        head = SKILL.read_text().split("---")[1]
        m = re.search(r'^\s*version:\s*"?([\d.]+)"?\s*$', head, re.M)
        return tuple(int(x) for x in m.group(1).split(".")) if m else ()
    except Exception:
        return ()


def _as_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except ValueError:
        return ()


def present(cit: dict) -> tuple[bool, str]:
    """Does `cit["text"]` appear in `cit["file"]`? The whole check is this literal."""
    f = cit.get("file") or ""
    t = cit.get("text") or ""
    if not f or not t:
        return False, "a citation needs both `file` and `text`"
    p = ROOT / f
    if not p.exists():
        return False, f"{f} does not exist"
    try:
        body = p.read_text(errors="replace")
    except OSError as e:
        return False, f"{f} could not be read ({e})"
    if t not in body:
        return False, f"{f} no longer contains {t[:58]!r}"
    return True, "present"


def audit(ledger=None) -> dict:
    """Resolve every row. `ledger` overrides which file that is.

    The override exists so the refusals below can be TESTED. `parity.py` learned the
    same lesson: with one file in the tree, the only way to prove a rule fires is to
    hand it a file that breaks it, and a rule nothing exercises is indistinguishable
    from a rule that passes everything."""
    src = Path(ledger) if ledger else LEDGER
    doc = yaml.safe_load(src.read_text()) if src.exists() else None
    if not isinstance(doc, dict) or not isinstance(doc.get("defects"), list):
        return {"ok": False, "rows": [], "counts": {}, "by_class": {},
                "problems": [f"{src} is missing or has no `defects:` list"]}

    shipped, problems, rows, seen = shipped_version(), [], [], set()
    for i, row in enumerate(doc["defects"]):
        where = f"defects[{i}]"
        if not isinstance(row, dict):
            problems.append(f"{where}: not a mapping")
            continue
        rid = str(row.get("id") or "")
        where = rid or where
        for k in REQUIRED:
            if not str(row.get(k) or "").strip():
                problems.append(f"{where}: `{k}` is missing or empty")
        if not ID_RE.match(rid):
            problems.append(f"{where}: id must look like DEF-01")
        if rid in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(rid)

        kind = str(row.get("class") or "")
        if kind and kind not in CLASSES:
            problems.append(f"{where}: class {kind!r} is not one of {', '.join(CLASSES)}")

        surface = str(row.get("surface") or "")
        if surface and not (ROOT / surface).exists():
            problems.append(f"{where}: surface {surface} does not exist")

        fixed = str(row.get("fixed_in") or "")
        ft = _as_tuple(fixed)
        if fixed and fixed != "unrecorded" and not ft:
            problems.append(f"{where}: fixed_in {fixed!r} is not a version")
        elif ft and shipped and ft > shipped:
            problems.append(f"{where}: fixed_in {fixed} is ahead of the shipped "
                            f"{'.'.join(map(str, shipped))} -- a ledger cannot claim a "
                            f"fix in a release that does not exist")

        guards = row.get("guard") or []
        if not guards:
            problems.append(f"{where}: no `guard`, so nothing proves the fix is still "
                            f"in the tree")
        for g in guards:
            ok, why = present(g if isinstance(g, dict) else {})
            if not ok:
                problems.append(f"{where}: guard {why}")

        controls = row.get("control") or []
        excuse = str(row.get("no_control") or "").strip()
        if controls and excuse:
            problems.append(f"{where}: has a control AND an excuse for having none")
        if not controls and not excuse:
            problems.append(f"{where}: no `control` and no `no_control` saying why. An "
                            f"unguarded fix has to be declared, not omitted")
        for c in controls:
            c = c if isinstance(c, dict) else {}
            cf = str(c.get("file") or "")
            if cf and not cf.startswith(CONTROLS):
                problems.append(f"{where}: {cf} is not a control -- a document cannot "
                                f"catch a regression")
            ok, why = present(c)
            if not ok:
                problems.append(f"{where}: control {why}")

        rows.append({"id": rid, "title": row.get("title"), "surface": surface,
                     "class": kind, "found_in": row.get("found_in"), "fixed_in": fixed,
                     "guards": len(guards), "controls": len(controls),
                     "guarded": bool(controls),
                     "reverted": bool(row.get("verified_by_revert")),
                     "no_control": excuse or None})

    return {"ok": not problems, "rows": rows, "problems": problems,
            "scope": doc.get("scope"),
            "counts": {"defects": len(rows),
                       "guarded": sum(1 for r in rows if r["guarded"]),
                       "unguarded": sum(1 for r in rows if not r["guarded"]),
                       "revert_verified": sum(1 for r in rows if r["reverted"])},
            "by_class": {k: sum(1 for r in rows if r["class"] == k)
                         for k in CLASSES if any(r["class"] == k for r in rows)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 2 if any row fails")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--id", help="one row, in full")
    ap.add_argument("--ledger", metavar="PATH",
                    help="check this file instead of the shipped ledger")
    ap.add_argument("--unguarded", action="store_true",
                    help="only the rows whose fix no control would catch")
    a = ap.parse_args(argv)

    r = audit(a.ledger)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0 if r["ok"] or not a.check else 2

    doc = yaml.safe_load(LEDGER.read_text()) if LEDGER.exists() else {}
    if a.id:
        for row in (doc.get("defects") or []):
            if str(row.get("id")) == a.id:
                print(yaml.safe_dump(row, sort_keys=False, allow_unicode=True, width=88))
                return 0
        sys.stderr.write(f"no such defect: {a.id}\n")
        return 2

    w = sys.stderr.write
    c = r["counts"]
    w("\n")
    for row in r["rows"]:
        if a.unguarded and row["guarded"]:
            continue
        mark = "ok  " if row["guarded"] else "GAP "
        w(f"  {mark} {row['id']}  fixed {row['fixed_in']:<8} "
          f"{str(row['class']):<13} {str(row['title'])[:52]}\n")
        if not row["guarded"]:
            w(f"        UNGUARDED: {row['no_control']}\n")
    w(f"\n  {c['defects']} defect(s): {c['guarded']} guarded by a control, "
      f"{c['unguarded']} not.\n")
    w("  by kind:   " + " · ".join(f"{k} {n}" for k, n in r["by_class"].items()) + "\n")
    w(f"  {c['revert_verified']} of them had the control verified by deleting the "
      f"mechanism it guards.\n")
    if c["unguarded"]:
        w("  An unguarded fix is one refactor from being undone. The rows above say so\n"
          "  rather than reading as though every fix were equally safe.\n")
    for p in r["problems"]:
        w(f"  FAIL {p}\n")
    w("\n" + ("  DEFECTS OK — every fix is still in the tree and every control resolves.\n"
              if r["ok"] else
              "  DEFECTS FAILING — a citation above no longer resolves. Either the fix "
              "was undone\n  or the ledger describes code that is gone; both make this "
              "file a liability.\n") + "\n")
    return 0 if r["ok"] or not a.check else 2


if __name__ == "__main__":
    sys.exit(main())
