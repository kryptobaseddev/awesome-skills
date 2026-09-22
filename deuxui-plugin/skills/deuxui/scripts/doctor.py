#!/usr/bin/env python3
"""What this installation can and cannot check, right now, on this machine.

  doctor.py [project-dir] [--json]

Run it before trusting a report. Every tier of this tool degrades quietly when
something is missing -- no browser means the runtime rules stay NOT_RUN, no
contract means the conformance rules stay NOT_RUN, no Xcode means the iOS
evidence rules stay NOT_RUN -- and a reader who does not know that reads a page
of NOT_RUN as pessimism rather than as a list of things nobody has set up.

It never says a tier is fine because it did not look. Each row is a check with a
result, and the summary counts what is genuinely unavailable rather than
averaging it away.
"""
from __future__ import annotations
import argparse, json, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SKILL = HERE.parent

OK, WARN, GONE = "ok", "degraded", "unavailable"


def _v(cmd, *args):
    try:
        r = subprocess.run([cmd, *args], capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0][:60]
    except Exception:
        return ""


def diagnose(root: Path) -> list[dict]:
    rows: list[dict] = []

    def row(name, state, detail, consequence=""):
        rows.append({"check": name, "state": state, "detail": detail,
                     "consequence": consequence})

    # ---------------------------------------------------------------- the skill
    try:
        import yaml                                            # noqa: F401
        row("pyyaml", OK, "importable")
    except ImportError:
        row("pyyaml", GONE, "not installed",
            "Nothing runs. `pip install pyyaml` -- it is the only dependency.")
        return rows
    import yaml
    try:
        reg = yaml.safe_load((SKILL / "references/rules/registry.yaml").read_text())
        det = yaml.safe_load((SKILL / "references/rules/detectors.yaml").read_text())
        row("rule registry", OK,
            f"{len(reg['rules'])} rules, {len(det['detectors'])} detectors, "
            f"{len(reg['laws'])} laws")
    except Exception as e:
        row("rule registry", GONE, f"{type(e).__name__}: {e}",
            "No rule can be reported. The install is broken, not the project.")
        return rows

    try:
        from checks import ALL
        row("static checks", OK, f"{len(ALL)} detectors implemented")
    except Exception as e:
        row("static checks", GONE, f"{type(e).__name__}: {e}",
            "The static tier cannot run at all.")

    strays = [str(p.relative_to(SKILL)) for p in SKILL.rglob("__pycache__")]
    if strays:
        row("shipped bytecode", WARN, ", ".join(strays[:3]),
            "A plugin install copies the tree verbatim, so this ships to the "
            "consumer. Remove it: find . -name __pycache__ -prune -exec rm -rf {} +")
    else:
        row("shipped bytecode", OK, "none")

    # ------------------------------------------------------------- the project
    import uxconfig
    cfg = uxconfig.load(root, None)
    if cfg.get("_path"):
        row("project config", OK, str(cfg["_path"]))
    else:
        row("project config", WARN, "no .deuxui/ux.config.yaml",
            "Thresholds, excluded paths, declared features and the dev URL all "
            "fall back to defaults. `deuxui init` writes one.")

    contract = uxconfig.contract(root)
    if contract:
        known = sum(1 for v in _flat(contract) if str(v).upper() != "UNKNOWN")
        total = len(list(_flat(contract)))
        row("visual contract", OK if known > total * 0.6 else WARN,
            f"{known}/{total} values declared",
            "" if known > total * 0.6 else
            "Most of the contract is UNKNOWN, so most conformance rules report "
            "NOT_RUN. Fill it in, or derive it: scripts/derive_contract.py --write")
    else:
        row("visual contract", GONE, "no .deuxui/design.contract.yaml",
            "Every S-CONTRACT-* rule reports NOT_RUN. `deuxui design` writes one "
            "for new work; scripts/derive_contract.py --write derives one from code.")

    manual = root / ".deuxui/reports/manual.yaml"
    if manual.exists():
        try:
            data = yaml.safe_load(manual.read_text()) or {}
            att = (data.get("attestations") or {})
            answered = sum(1 for v in att.values()
                           if isinstance(v, dict)
                           and str(v.get("status", "NOT_RUN")).upper() != "NOT_RUN")
            n_manual = sum(1 for d in det["detectors"].values()
                           if d.get("engine") == "manual")
            row("manual tier", OK if answered else WARN,
                f"{answered}/{n_manual} questions answered",
                "" if answered else
                "Nobody has answered any of them, so every judgement rule is "
                "NOT_RUN. scripts/manual_sheet.py --check lists them.")
        except Exception as e:
            row("manual tier", WARN, f"unreadable: {e}")
    else:
        row("manual tier", GONE, "no .deuxui/reports/manual.yaml",
            "Screen-reader, keyboard, device and judgement rules all stay "
            "NOT_RUN. scripts/manual_sheet.py --write starts the sheet.")

    # -------------------------------------------------------------- the runtime
    if shutil.which("agent-browser"):
        row("agent-browser", OK, _v("agent-browser", "--version") or "installed")
        url = uxconfig.get(cfg, "app.dev_url")
        if url:
            row("dev server URL", OK, str(url))
        else:
            row("dev server URL", WARN, "no app.dev_url in the config",
                "ux_browser.sh needs a URL on the command line every time.")
    else:
        row("agent-browser", GONE, "not on PATH",
            "The whole runtime tier stays NOT_RUN: real contrast, real hit areas, "
            "reflow, the focus walk, vitals, and every forced state. That is most "
            "of what a source scan cannot see.")

    # ------------------------------------------------------------- the platform
    import ux_check
    plats = ux_check.detect_platforms(root, _deps(root))
    if plats:
        row("platforms detected", OK, ", ".join(sorted(plats)))
        if "ios" in plats:
            if shutil.which("xcrun"):
                booted = _v("xcrun", "simctl", "list", "devices", "booted")
                row("iOS simulator", OK if booted else WARN,
                    booted or "xcrun present, nothing booted",
                    "" if booted else "Boot a Simulator and install the app, or "
                                      "IOS-018/019 stay NOT_RUN.")
            else:
                row("iOS simulator", GONE, "xcrun not on PATH",
                    "IOS-018 and IOS-019 stay NOT_RUN. Only macOS with Xcode can "
                    "produce iOS evidence -- a browser screenshot of a web build "
                    "is not it.")
        if "android" in plats:
            if shutil.which("adb"):
                dev = _v("adb", "devices", "-l")
                attached = [ln for ln in (subprocess.run(
                    ["adb", "devices"], capture_output=True, text=True,
                    timeout=20).stdout or "").splitlines()[1:] if ln.strip()]
                if attached:
                    row("Android device", OK, "; ".join(attached)[:44])
                else:
                    row("Android device", WARN, "adb present, nothing attached",
                        "AND-016 and AND-017 stay NOT_RUN until an emulator or device "
                        "is attached. An emulator satisfies the rule by its own terms; "
                        "hardware is still needed for posture, gestures and performance.")
            else:
                row("Android device", GONE, "adb not on PATH",
                    "AND-016 and AND-017 stay NOT_RUN. Install platform-tools and "
                    "attach an emulator or device.")
    else:
        row("platforms detected", OK, "web only",
            "The 40 iOS and Android rules report NOT_APPLICABLE, which is correct "
            "for a project that does not ship to a phone.")

    # --- the decision tier. These are the rules about how the work happened, and
    # they are the ones most easily mistaken for absent rather than unrun.
    phase = root / ".deuxui" / "phase.yaml"
    if phase.exists():
        try:
            st = yaml.safe_load(phase.read_text()) or {}
            row("phase gate", OK,
                f"{st.get('phase')} ({st.get('mode')})",
                "UI edits are refused before the `build` phase, and A-PHASE-ORDER "
                "reports whether the contract was declared before the code.")
        except Exception as e:
            row("phase gate", WARN, f"unreadable: {e}")
    else:
        row("phase gate", WARN, "no .deuxui/phase.yaml",
            "Nothing is gated and A-PHASE-ORDER, A-COMP-APPROVED and "
            "A-DECISION-VETTED all report NOT_RUN. An unrecorded order of work "
            "establishes nothing either way. scripts/ux_phase.py init starts it.")

    decisions = sorted((root / ".deuxui" / "decisions").glob("DEC-*.yaml"))
    if decisions:
        row("decisions", OK, f"{len(decisions)} record(s)",
            "scripts/ux_question.py check verifies each one still matches the "
            "comps it approved.")
    else:
        row("decisions", WARN, "none recorded",
            "No direction has been approved by anybody, so GOV-011 and GOV-012 "
            "report NOT_RUN. scripts/ux_question.py ask serves the choice.")

    try:
        import uxconfig as _uc
        legacy = _uc.legacy_state(root)
        if legacy:
            row("project state", GONE, f"{legacy.name}/ (pre-rename name)",
                f"This project's records are in {legacy.name}/ and every path in this "
                f"version points at {_uc.STATE}/, so the contract, decisions and notes "
                f"all read as absent. Rename it: mv {legacy.name} {_uc.STATE}")
    except Exception:
        pass

    try:
        import ux_ledger
        lin = ux_ledger.lineage()
        approvals = [d for _f, d in ux_ledger.decisions() if d.get("approves_a_build")]
        unresolved = [d.get("id") for d in approvals
                      if not d.get("contract_sha")
                      or ux_ledger.archived(d["contract_sha"]) is None]
        if unresolved:
            row("decision provenance", GONE,
                f"{len(unresolved)} of {len(approvals)} unresolvable",
                "A-CONTRACT-ARCHIVED FAILs: the approval exists and the declaration "
                "it approved does not. Nothing can reconstruct what was agreed. "
                "scripts/ux_ledger.py snapshot archives the contract in force.")
        elif approvals:
            row("decision provenance", OK,
                f"{len(approvals)} approval(s) resolve, {len(lin)} version(s)",
                "scripts/ux_ledger.py show DEC-001 prints what was declared at the "
                "time.")
        elif lin:
            row("decision provenance", OK, f"{len(lin)} contract version(s) archived",
                "Nothing approved yet, but the declaration's history is on record.")
        else:
            row("decision provenance", WARN, "no contract archived",
                "A-CONTRACT-ARCHIVED reports NOT_RUN. An approval recorded now could "
                "not be resolved back to what it approved. "
                "scripts/ux_ledger.py snapshot fixes it in one command.")
    except Exception as e:
        row("decision provenance", WARN, f"{type(e).__name__}: {e}")

    try:
        import ux_image
        provs = [p for p in ux_image.providers() if p["available"]]
        if provs:
            row("image generation", OK, ", ".join(p["id"] for p in provs),
                "ux_image.py generate can produce a raster comp, and verify will "
                "measure it back against the contract.")
        else:
            row("image generation", WARN, "no provider reachable",
                "ux_image.py render still works and needs nothing -- it draws the "
                "comp from the contract. Only the raster round is unavailable, and "
                "it reports NOT_RUN rather than producing nothing silently.")
    except Exception as e:
        row("image generation", WARN, f"{type(e).__name__}: {e}")

    return rows


def _flat(d, _p=""):
    for k, v in (d or {}).items():
        if isinstance(v, dict):
            yield from _flat(v, f"{_p}{k}.")
        elif isinstance(v, list):
            continue
        else:
            yield v


def _deps(root: Path) -> set:
    pkg = root / "package.json"
    if not pkg.exists():
        return set()
    try:
        d = json.loads(pkg.read_text())
        return set(d.get("dependencies", {})) | set(d.get("devDependencies", {}))
    except Exception:
        return set()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.path).resolve()
    rows = diagnose(root)

    if a.json:
        print(json.dumps({"root": str(root), "checks": rows}, indent=1))
        return 0 if not any(r["state"] == GONE for r in rows) else 2

    w = sys.stdout.write
    w(f"\ndeuxui doctor -- {root}\n" + "=" * 74 + "\n")
    for r in rows:
        mark = {OK: "  ok  ", WARN: " warn ", GONE: " GONE "}[r["state"]]
        w(f"{mark} {r['check']:<20} {r['detail'][:46]}\n")
        if r["consequence"]:
            for i, chunk in enumerate(_wrap(r["consequence"], 64)):
                w(f"       {'':<20} {chunk}\n")
    gone = [r for r in rows if r["state"] == GONE]
    warn = [r for r in rows if r["state"] == WARN]
    w("=" * 74 + f"\n  {len(gone)} unavailable, {len(warn)} degraded, "
                 f"{len(rows) - len(gone) - len(warn)} ok\n")
    if gone:
        w("\nEverything above marked GONE is a set of rules that will report NOT_RUN\n"
          "no matter how good the code is. Fix these before reading a report as a\n"
          "verdict -- NOT_RUN means nobody looked, and that is what it will keep\n"
          "meaning until one of these is installed.\n")
    return 2 if gone else 0


def _wrap(s, n):
    words, line, out = s.split(), "", []
    for word in words:
        if len(line) + len(word) + 1 > n:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
