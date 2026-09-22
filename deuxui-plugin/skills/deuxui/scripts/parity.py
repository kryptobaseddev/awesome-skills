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


_RUNS: dict[str, tuple] = {}


def runs(script: str) -> tuple[bool, str]:
    """Does `scripts/<script>` actually start, or is it a file that satisfies a claim?

    The rest of this checker proves a piece of evidence EXISTS. That is the weaker
    half: a row can cite a script that is present and broken, and the claim resolves
    while the capability does not. A `mapped` row backed by a module that raises on
    import is exactly the shape of overstatement this file was written to prevent, and
    nothing here could see it.

    So `--deep` runs each cited script's `--help`. Chosen because it is the one
    invocation every script here supports, it touches no project files, and it forces
    the whole import graph -- which is where rot actually shows up. Exit status is
    read, and stderr is quoted when it fails, so the report says what broke rather
    than that something did."""
    if script in _RUNS:
        return _RUNS[script]
    q = SKILL / "scripts" / script
    if not q.exists():
        _RUNS[script] = (False, "the file does not exist")
        return _RUNS[script]
    try:
        r = subprocess.run([sys.executable, str(q), "--help"],
                           capture_output=True, text=True, timeout=60)
    except subprocess.SubprocessError as e:
        _RUNS[script] = (False, f"{type(e).__name__}: {e}")
        return _RUNS[script]
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "").strip().splitlines()
        _RUNS[script] = (False, f"exits {r.returncode}: "
                                + (tail[-1][:160] if tail else "no output"))
    else:
        _RUNS[script] = (True, "")
    return _RUNS[script]


# Files that assert behaviour rather than describe it. A capability named by one of
# these is exercised; a capability named nowhere in them is only known to START.
CONTROLS = ("selftest.py", "browsertest.py", "native_conformance.py",
            "lint_rules.py", "checks/fixtures")


def _control_text() -> str:
    """Everything the automated controls contain, as one blob to search."""
    out = []
    for name in CONTROLS:
        q = SKILL / "scripts" / name
        if q.is_dir():
            for f in sorted(q.rglob("*")):
                if f.is_file():
                    try:
                        out.append(f.read_text(errors="replace"))
                    except OSError:
                        pass
        elif q.exists():
            try:
                out.append(q.read_text(errors="replace"))
            except OSError:
                pass
    return "\n".join(out)


def executable(ev: list) -> bool:
    """Does this row cite anything that can be RUN?

    A row backed only by an operation reference or a workflow is prose an agent
    follows. There is nothing to smoke-test: `lint_rules.py` already proves every rule
    and detector ID it cites exists, and whether the guidance is good is a judgement no
    control can make. Counting those as "unexercised" buries the rows that matter in a
    number nobody can act on."""
    return any(str(e).split(":", 1)[0] in ("script", "sub", "flag") for e in ev)


def exercised(ev: list, blob: str) -> bool:
    """Is any of this row's evidence named by a control?

    A deliberately weak test, and it is labelled as one. It asks whether a control
    MENTIONS the capability, not whether it asserts the right thing about it -- no
    static check can tell the difference between a control that would catch a
    regression and one that imports a module and moves on.

    It is still worth printing, because the number it produces is the honest answer to
    "wired and working": a row whose evidence no control mentions at all is known to
    start and nothing more, and that set should be small and named rather than
    averaged into a pass."""
    for e in ev:
        e = str(e)
        if ":" not in e:
            continue
        kind, rest = e.split(":", 1)
        if kind == "detector":
            if rest in blob:
                return True
        elif kind in ("script", "sub", "flag"):
            name = rest.split(":", 1)[0]
            # A row citing a CONTROL is exercised by construction -- `lint_rules.py`
            # does not import itself, so the mention test could never see it and
            # reported "the rule registry" as unexercised while the linter that proves
            # every one of its IDs runs on every commit.
            if name in CONTROLS:
                return True
            stem = name.rsplit(".", 1)[0]
            if stem and (f"import {stem}" in blob or f"{stem}." in blob):
                return True
    return False


def audit(deep: bool = False, matrix=None) -> dict:
    """Resolve every claim in the matrix. `matrix` overrides which file that is.

    The override exists so the two refusals below can be TESTED. The rule that a
    `mapped` row may not carry a gap is the one that caught a too-generous claim in
    v5.10.0, and it was itself unexercised: with only one matrix in the tree, the
    only way to prove the rule fires is to hand it a file that breaks it."""
    src = Path(matrix) if matrix else MATRIX
    try:
        doc = yaml.safe_load(src.read_text())
    except OSError:
        return {"ok": False, "fatal": f"{src} is missing", "rows": [],
                "counts": {}, "problems": [f"{src} is missing"]}
    except yaml.YAMLError as e:
        return {"ok": False, "fatal": f"{src} is not valid YAML: {e}", "rows": [],
                "counts": {}, "problems": [str(e)]}

    dets = detector_ids()
    blob = _control_text()
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
                elif deep:
                    # Existing is not working. A row can cite a script that is present
                    # and broken, and the claim resolves while the capability does not.
                    kind, rest = str(e).split(":", 1)
                    # NOT `name`: that is the row's name, three lines up, and shadowing
                    # it here set every row's name to None in the report.
                    cited = (rest if kind == "script" else
                             rest.split(":", 1)[0] if kind in ("sub", "flag") else None)
                    if cited and cited.endswith(".py"):
                        good, told = runs(cited)
                        if not good:
                            unresolved.append((str(e), f"cited but does not run -- {told}"))
                            problems.append(f"{where}: scripts/{cited} is cited as "
                                            f"evidence and does not run: {told}")
            rows.append({"section": section, "name": name, "status": st,
                         "evidence": len(ev), "unresolved": unresolved,
                         "gap": row.get("gap"),
                         "exercised": exercised(ev, blob) if ev else False,
                         "executable": executable(ev)})

    return {"ok": not problems, "rows": rows, "counts": counts, "problems": problems,
            "source": doc.get("source", {}), "detectors_known": len(dets),
            "unexercised": sorted(r["name"] for r in rows
                                  if r["status"] == "mapped" and not r["exercised"]
                                  and r["executable"]),
            "prose_only": sorted(r["name"] for r in rows
                                 if r["status"] == "mapped" and not r["executable"]),
            "deep": deep, "scripts_run": len(_RUNS),
            "scripts_broken": sorted(k for k, (g, _w) in _RUNS.items() if not g)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 2 if any claim cannot be resolved")
    ap.add_argument("--status", choices=STATUSES, help="only rows with this status")
    ap.add_argument("--deep", action="store_true",
                    help="also RUN every cited script, because a present-but-broken "
                         "script satisfies a claim it cannot support")
    ap.add_argument("--matrix", metavar="PATH",
                    help="check this file instead of the shipped matrix")
    a = ap.parse_args(argv)
    r = audit(a.deep, a.matrix)

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
    w(f"  {r.get('detectors_known', 0)} detector ID(s) available as evidence\n")
    ux = r.get("unexercised") or []
    prose = r.get("prose_only") or []
    mapped = r["counts"].get("mapped", 0)
    runnable = mapped - len(prose)
    w(f"  {runnable - len(ux)}/{runnable} runnable mapped row(s) exercised by a "
      f"control; {len(ux)} known only to start\n")
    if ux:
        w(f"    only start: {', '.join(ux)}\n"
          f"    (\"only start\" means --deep proved the script runs and no control "
          f"asserts what it\n     produces. It is a gap in TESTING, not a claim that "
          f"the capability is absent.)\n")
    w(f"  {len(prose)} mapped row(s) are guidance with nothing to run; lint_rules "
      f"proves the IDs they cite exist\n")
    if r.get("deep"):
        bad = r.get("scripts_broken") or []
        w(f"  {r.get('scripts_run', 0)} cited script(s) run: "
          + ("all start" if not bad else f"{len(bad)} BROKEN — {', '.join(bad)}") + "\n")
    w("\n")

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
