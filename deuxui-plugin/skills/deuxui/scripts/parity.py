#!/usr/bin/env python3
"""Check the parity matrix against this skill, so coverage is a fact and not a claim.

`references/parity/impeccable.yaml` records, one row at a time, what impeccable does
and what this skill does about it. The file is worth nothing on its own: prose about
coverage is exactly the thing every other part of this skill refuses to accept about
an interface, and "we have everything they have" is unfalsifiable in the same way
"looks good" is.

So this resolves every piece of evidence in it. A row claiming `mapped` must point at
an operation reference, a workflow, a script, a subcommand, a flag or a detector that
actually exists here; a row claiming `partial` or `absent` must say what is missing in
a `gap`. Both directions are enforced, because the two ways this file rots are a
`mapped` whose evidence was deleted, and a `partial` whose gap was quietly removed
until the row read like a match.

    parity.py                 the report
    parity.py --json
    parity.py --check         exit 2 if any claim cannot be resolved

Exit: 0 every claim resolves, 2 at least one does not.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import yaml                                                          # noqa: E402

MATRIX = SKILL / "references" / "parity" / "impeccable.yaml"
SECTIONS = ("commands", "cli", "live", "agents", "additional")
STATUSES = ("mapped", "partial", "absent")


def detector_ids() -> set:
    """Every detector ID this skill declares."""
    out = set()
    p = SKILL / "references" / "rules" / "detectors.yaml"
    try:
        doc = yaml.safe_load(p.read_text())
    except (OSError, yaml.YAMLError):
        return out

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(k, str) and re.fullmatch(r"[SRAM]-[A-Z0-9][A-Z0-9-]*", k):
                    out.add(k)
                if k == "id" and isinstance(v, str):
                    out.add(v)
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(doc)
    return out


_SUBS: dict[str, set] = {}


def subcommands(script: str) -> set:
    """The subcommands `scripts/<script>` really has, asked of the script itself.

    This started as a regex over `add_parser("name")` and was wrong on the first two
    rows it was pointed at: `ux_image.py` and `ux_select.py` both build some of their
    subparsers in a loop, so the names are never literals in the source. The check
    reported two real capabilities as missing -- a false negative in a tool whose
    entire job is to not make claims it cannot support.

    So it asks argparse, by reading the usage line's `{a,b,c}` group out of `--help`.
    One subprocess per script, cached, and the answer is what the script would
    actually accept rather than what its source looks like."""
    if script in _SUBS:
        return _SUBS[script]
    q = SKILL / "scripts" / script
    out: set = set()
    if q.exists():
        try:
            r = subprocess.run([sys.executable, str(q), "--help"],
                               capture_output=True, text=True, timeout=40)
            m = re.search(r"\{([a-z0-9_,-]+)\}", (r.stdout or "") + (r.stderr or ""))
            if m:
                out = {x for x in m.group(1).split(",") if x}
        except (OSError, subprocess.SubprocessError):
            out = set()
    _SUBS[script] = out
    return out


def _declares(script: str, kind: str, name: str) -> bool:
    """Whether `scripts/<script>` declares that subcommand or that option."""
    if kind == "sub":
        return name in subcommands(script)
    # Options are literal in `add_argument("--x")` in every script here, and a flag
    # can live on a subparser that `--help` never lists, so this one stays textual.
    q = SKILL / "scripts" / script
    try:
        body = q.read_text(errors="replace")
    except OSError:
        return False
    return bool(re.search(r'add_argument\(\s*["\']' + re.escape(name) + r'["\']', body))


def resolve(ev: str, dets: set) -> tuple[bool, str]:
    """One piece of evidence: does it exist, and if not, what was looked for."""
    if ":" not in ev:
        return False, f"{ev!r} has no kind prefix (op:, script:, detector:, ...)"
    kind, rest = ev.split(":", 1)

    if kind == "op":
        p = SKILL / "references" / "ops" / f"{rest}.md"
    elif kind == "workflow":
        p = SKILL / "references" / "workflows" / f"{rest}.md"
    elif kind == "script":
        p = SKILL / "scripts" / rest
    elif kind == "ref":
        p = SKILL / rest
    elif kind in ("sub", "flag"):
        if ":" not in rest:
            return False, f"{ev!r} needs <script>:<name>"
        script, name = rest.split(":", 1)
        if not (SKILL / "scripts" / script).exists():
            return False, f"scripts/{script} does not exist"
        if not _declares(script, kind, name):
            what = "subcommand" if kind == "sub" else "option"
            return False, f"scripts/{script} declares no {what} {name!r}"
        return True, ""
    elif kind == "detector":
        if rest not in dets:
            return False, f"detector {rest} is not in references/rules/detectors.yaml"
        return True, ""
    elif kind == "hook":
        p = SKILL / "references" / "ops" / "hooks.md"
    else:
        return False, f"unknown evidence kind {kind!r} in {ev!r}"

    if not p.exists():
        return False, f"{p.relative_to(SKILL)} does not exist"
    return True, ""


def audit() -> dict:
    try:
        doc = yaml.safe_load(MATRIX.read_text())
    except OSError:
        return {"ok": False, "fatal": f"{MATRIX} is missing", "rows": [],
                "counts": {}, "problems": [f"{MATRIX} is missing"]}
    except yaml.YAMLError as e:
        return {"ok": False, "fatal": f"{MATRIX} is not valid YAML: {e}", "rows": [],
                "counts": {}, "problems": [str(e)]}

    dets = detector_ids()
    rows, problems = [], []
    counts = {s: 0 for s in STATUSES}

    for section in SECTIONS:
        for row in doc.get(section) or []:
            name = row.get("name", "?")
            where = f"{section}/{name}"
            st = row.get("status")
            if section == "additional":
                st = st or "mapped"
            if st not in STATUSES:
                problems.append(f"{where}: status {st!r} is not one of "
                                f"{', '.join(STATUSES)}")
                st = "absent"
            counts[st] = counts.get(st, 0) + 1

            # The rule that keeps this file honest in the other direction.
            if st in ("partial", "absent") and not str(row.get("gap") or "").strip():
                problems.append(
                    f"{where}: status is {st!r} with no `gap`. A gap with no "
                    f"description is how this file stops describing reality -- the "
                    f"row reads as accounted for while nothing says what is missing.")
            if st == "mapped" and row.get("gap"):
                problems.append(f"{where}: status is 'mapped' but a `gap` is recorded. "
                                f"Say 'partial'.")

            ev = row.get("evidence") or []
            if st in ("mapped", "partial") and not ev:
                problems.append(f"{where}: claims {st!r} with no evidence at all")
            unresolved = []
            for e in ev:
                ok, why = resolve(str(e), dets)
                if not ok:
                    unresolved.append((str(e), why))
                    problems.append(f"{where}: {why}")
            rows.append({"section": section, "name": name, "status": st,
                         "evidence": len(ev), "unresolved": unresolved,
                         "gap": row.get("gap")})

    return {"ok": not problems, "rows": rows, "counts": counts, "problems": problems,
            "source": doc.get("source", {}), "detectors_known": len(dets)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 2 if any claim cannot be resolved")
    ap.add_argument("--status", choices=STATUSES, help="only rows with this status")
    a = ap.parse_args(argv)
    r = audit()

    if a.json:
        print(json.dumps(r, indent=1))
        return 0 if r["ok"] else 2

    w = sys.stdout.write
    src = r.get("source", {})
    w(f"\nparity against {src.get('project', '?')} "
      f"CLI {src.get('cli_version', '?')}, read {src.get('read_on', '?')}\n")
    c = r["counts"]
    total = sum(c.values())
    w(f"  {total} row(s): {c.get('mapped', 0)} mapped, {c.get('partial', 0)} partial, "
      f"{c.get('absent', 0)} absent\n")
    w(f"  {r.get('detectors_known', 0)} detector ID(s) available as evidence\n\n")

    for section in SECTIONS:
        rows = [x for x in r["rows"] if x["section"] == section
                and (not a.status or x["status"] == a.status)]
        if not rows:
            continue
        w(f"{section}\n")
        for x in rows:
            mark = {"mapped": "ok ", "partial": "part", "absent": "GAP"}[x["status"]]
            bad = "  <- UNRESOLVED" if x["unresolved"] else ""
            w(f"  {mark:<4} {x['name']:<28} {x['evidence']} evidence{bad}\n")
            if x["status"] != "mapped" and x["gap"]:
                first = " ".join(str(x["gap"]).split())
                w(f"         {first[:150]}\n")
            for e, why in x["unresolved"]:
                w(f"         {e}: {why}\n")
        w("\n")

    if r["problems"]:
        w(f"{len(r['problems'])} unresolvable claim(s):\n")
        for p in r["problems"]:
            w(f"  {p}\n")
        w("\nPARITY FAIL — a claim that cannot be resolved is not a claim.\n\n")
        return 2
    w("PARITY OK — every claim in the matrix resolves to something that exists here.\n"
      "  Read the `part` and `GAP` rows: they are the answer to \"do you have "
      "everything\",\n  and they are the rows this file exists to keep visible.\n\n")
    return 0 if not a.check else (0 if r["ok"] else 2)


if __name__ == "__main__":
    sys.exit(main())
