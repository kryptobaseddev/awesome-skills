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
        row("project config", WARN, "no .deluxui/ux.config.yaml",
            "Thresholds, excluded paths, declared features and the dev URL all "
            "fall back to defaults. `deluxui init` writes one.")

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
        row("visual contract", GONE, "no .deluxui/design.contract.yaml",
            "Every S-CONTRACT-* rule reports NOT_RUN. `deluxui design` writes one "
            "for new work; scripts/derive_contract.py --write derives one from code.")

    manual = root / ".deluxui/reports/manual.yaml"
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
        row("manual tier", GONE, "no .deluxui/reports/manual.yaml",
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
                dev = _v("adb", "devices")
                row("Android device", OK, dev or "adb present")
            else:
                row("Android device", GONE, "adb not on PATH",
                    "AND-016 and AND-017 stay NOT_RUN. Install platform-tools and "
                    "attach an emulator or device.")
    else:
        row("platforms detected", OK, "web only",
            "The 40 iOS and Android rules report NOT_APPLICABLE, which is correct "
            "for a project that does not ship to a phone.")

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
    w(f"\ndeluxui doctor -- {root}\n" + "=" * 74 + "\n")
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
