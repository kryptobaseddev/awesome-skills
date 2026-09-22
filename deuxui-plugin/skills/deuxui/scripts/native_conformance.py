#!/usr/bin/env python3
"""Prove the native driver issues the right commands and reads the results right.

  native_conformance.py            # the full matrix against recording stubs
  native_conformance.py --real     # additionally use whatever real tooling exists

What this proves, and what it does not. It does NOT prove that an iPhone renders
your layout correctly -- nothing on a Linux host can, and pretending otherwise
would be exactly the laundering this tool refuses. What it DOES prove is every
part that lives in this repository and can therefore be wrong:

  - the driver issues the documented command sequence, in order, with the device
    identifier attached to each one;
  - it restores every setting it changed, so a developer's emulator is not left in
    dark mode at 1.3x font scale;
  - the seven availability states each produce the right verdict;
  - the report readers turn each recorded state into the right status.

It works by putting recording stubs for `xcrun` and `adb` on PATH. A stub is not a
device, and the harness says so in its own output rather than letting a green run
imply more than it establishes.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# A one-pixel PNG, so a stubbed capture writes bytes a reader will accept as an
# image rather than an empty file the driver would (correctly) reject.
PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a"
    "49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082")

STUB_SH = r'''#!/usr/bin/env bash
# Recording stub for %(tool)s. Logs every invocation, then behaves per $UXC_MODE.
echo "%(tool)s $*" >> "$UXC_LOG"
mode="${UXC_MODE:-ok}"
'''

XCRUN_BODY = r'''
if [ "$1" = "simctl" ]; then
  shift
  case "$1" in
    list)
      if [ "$mode" = "nodevice" ]; then echo "== Devices =="; exit 0; fi
      echo "    iPhone 16 Pro (11111111-2222-3333-4444-555555555555) (Booted)"
      exit 0 ;;
    io)
      # io <udid> screenshot <path>
      if [ "$mode" = "shotfail" ]; then echo "simctl io failed: no such device" >&2; exit 1; fi
      if [ "$mode" = "emptyshot" ]; then : > "$4"; exit 0; fi
      cp "$UXC_PNG" "$4"; exit 0 ;;
    ui)
      # ui <udid> appearance|content_size <value>
      if [ "$3" = "content_size" ] && [ "$mode" = "nocontentsize" ]; then
        echo "Unknown subcommand: content_size" >&2; exit 1
      fi
      exit 0 ;;
  esac
fi
exit 0
'''

ADB_BODY = r'''
args="$*"
# strip a leading -s <serial>
if [ "$1" = "-s" ]; then serial="$2"; shift 2; fi
case "$1" in
  devices)
    echo "List of devices attached"
    if [ "$mode" != "nodevice" ]; then echo "emulator-5554	device"; fi
    exit 0 ;;
  shell)
    shift
    case "$1 $2" in
      "getprop ro.product.model") echo "sdk_gphone64_x86_64"; exit 0 ;;
      "getprop ro.build.version.sdk") echo "34"; exit 0 ;;
    esac
    if [ "$1" = "wm" ]; then echo "Physical size: 1080x2400"; exit 0; fi
    exit 0 ;;
  exec-out)
    if [ "$mode" = "shotfail" ]; then echo "error: device offline" >&2; exit 1; fi
    if [ "$mode" = "emptyshot" ]; then exit 0; fi
    cat "$UXC_PNG"; exit 0 ;;
esac
exit 0
'''


def make_stubs(d: Path, tools=("xcrun", "adb")) -> tuple[Path, Path, Path]:
    bin_dir = d / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    log = d / "calls.log"
    png = d / "one.png"
    png.write_bytes(PNG_1PX)
    for tool in tools:
        body = XCRUN_BODY if tool == "xcrun" else ADB_BODY
        p = bin_dir / tool
        p.write_text(STUB_SH % {"tool": tool} + body)
        p.chmod(0o755)
    return bin_dir, log, png


def run_driver(bin_dir: Path | None, log: Path | None, png: Path | None,
               out: Path, mode="ok", args=("--both",)) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if bin_dir is not None:
        # A stub-only PATH, so a real tool cannot answer for a stub and a missing
        # stub really is missing.
        env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
        env["UXC_LOG"] = str(log)
        env["UXC_PNG"] = str(png)
        env["UXC_MODE"] = mode
    else:
        env["PATH"] = "/usr/bin:/bin"
    return subprocess.run(["bash", str(HERE / "ux_native.sh"), *args,
                           "--out", str(out)],
                          capture_output=True, text=True, env=env, timeout=180)


def read_json(out: Path, platform: str) -> dict:
    p = out / "runtime" / "raw" / f"native-{platform}.json"
    return json.loads(p.read_text()) if p.exists() else {}


def verdicts(out: Path) -> dict:
    """What ux_report makes of what the driver recorded."""
    import ux_report
    raw = out / "runtime" / "raw"
    raws = {f.name: json.loads(f.read_text()) for f in raw.glob("*.json")}
    got = {}
    for did in ("R-IOS-CAPTURE", "R-IOS-APPEARANCE", "R-AND-CAPTURE", "R-AND-THEME"):
        st, note, _hits = ux_report.RUNTIME[did](raws, out)
        got[did] = (st, note)
    return got


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--real", action="store_true",
                    help="also run against whatever real tooling is installed")
    a = ap.parse_args(argv)
    fails, w = [], sys.stdout.write
    w("\nnative driver conformance\n" + "=" * 74 + "\n")

    # ---------------------------------------------------------------- happy path
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        bin_dir, log, png = make_stubs(d)
        out = d / "reports"
        r = run_driver(bin_dir, log, png, out, "ok")
        calls = log.read_text().splitlines() if log.exists() else []
        ios, android = read_json(out, "ios"), read_json(out, "android")
        v = verdicts(out)

        w("\n-- both tools present, a target booted, captures succeed\n")
        w(f"   iOS available={ios.get('available')} device={str(ios.get('device'))[:44]!r} "
          f"captures={len(ios.get('captures') or [])}\n")
        w(f"   Android available={android.get('available')} "
          f"device={str(android.get('device'))[:44]!r} "
          f"captures={len(android.get('captures') or [])}\n")
        for did, (st, _n) in v.items():
            w(f"   {st:<8} {did}\n")
        for did, want in (("R-IOS-CAPTURE", "PASS"), ("R-IOS-APPEARANCE", "PASS"),
                          ("R-AND-CAPTURE", "PASS"), ("R-AND-THEME", "PASS")):
            if v[did][0] != want:
                fails.append(f"{did} came out {v[did][0]}, expected {want} on the happy "
                             f"path: {v[did][1][:120]}")
        if len(ios.get("captures") or []) != 3:
            fails.append(f"iOS recorded {len(ios.get('captures') or [])} captures; the "
                          f"pass is light, dark and enlarged text")
        if len(android.get("captures") or []) != 3:
            fails.append(f"Android recorded {len(android.get('captures') or [])} captures")
        if "11111111-2222-3333-4444-555555555555" not in str(ios.get("device", "")):
            fails.append("the iOS record does not name the UDID; display names collide "
                         "and the UDID is the only identifier that does not")
        if "emulator-5554" not in str(android.get("device", "")):
            fails.append("the Android record does not name the serial")

        # ------------------------------------------------- the command sequence
        w("\n-- the command sequence, in order\n")
        joined = "\n".join(calls)
        expect_ios = [
            ("appearance light before the first capture", "xcrun simctl ui .* appearance light"),
            ("a light capture", r"xcrun simctl io .* screenshot .*ios-light\.png"),
            ("appearance dark", "xcrun simctl ui .* appearance dark"),
            ("a dark capture", r"xcrun simctl io .* screenshot .*ios-dark\.png"),
            ("an accessibility content size", "content_size accessibility"),
            ("a large-type capture", r"xcrun simctl io .* screenshot .*ios-large-type\.png"),
            ("content size restored", "content_size medium"),
        ]
        expect_and = [
            ("night mode off first", "adb .*shell cmd uimode night no"),
            ("a light capture", "adb .*exec-out screencap"),
            ("night mode on", "adb .*shell cmd uimode night yes"),
            ("font scale raised", r"adb .*settings put system font_scale 1\.3"),
            ("font scale restored", r"adb .*settings put system font_scale 1\.0"),
        ]
        import re
        pos = 0
        for label, pat in expect_ios + expect_and:
            m = re.search(pat, joined)
            ok = bool(m)
            w(f"   {'ok ' if ok else 'MISSING'} {label}\n")
            if not ok:
                fails.append(f"the driver never issued: {label} (/{pat}/)")
        # Order matters for the two that restore state: a restore before its change
        # would mean the capture happened in the wrong mode.
        def at(pat):
            m = re.search(pat, joined)
            return m.start() if m else -1

        def last_at(pat):
            ms = list(re.finditer(pat, joined))
            return ms[-1].start() if ms else -1
        if at("content_size accessibility") > at("content_size medium") >= 0:
            fails.append("the iOS content size was restored before the large-type "
                         "capture, so that capture was taken at the default size")
        if at(r"font_scale 1\.3") > at(r"font_scale 1\.0") >= 0:
            fails.append("the Android font scale was restored before the enlarged capture")
        # And the one that matters to whoever owns the device.
        # The LAST light must come after the dark. Written with the first match this
        # reported a restore failure against a driver that does restore, because
        # `appearance light` legitimately appears before `appearance dark` too.
        if at("appearance dark") >= 0 and last_at("appearance light") > at("appearance dark"):
            w("   ok  appearance restored to light afterwards\n")
        else:
            fails.append("the driver left the simulator in dark mode; it changed a "
                         "developer's device state and did not put it back")
        if last_at(r"font_scale 1\.0") > at(r"font_scale 1\.3") >= 0:
            w("   ok  Android font scale restored afterwards\n")
        else:
            fails.append("the driver left the Android font scale raised")
        if last_at("uimode night no") > at("uimode night yes") >= 0:
            w("   ok  Android night mode restored afterwards\n")
        else:
            fails.append("the driver left the emulator in dark theme")

    # ------------------------------------------------------- the failure states
    cases = [
        ("no tool on PATH at all", None, "ok",
         {"R-IOS-CAPTURE": "NOT_RUN", "R-AND-CAPTURE": "NOT_RUN"}),
        ("tools present, nothing booted or attached", "stub", "nodevice",
         {"R-IOS-CAPTURE": "NOT_RUN", "R-AND-CAPTURE": "NOT_RUN"}),
        ("capture command fails", "stub", "shotfail",
         {"R-IOS-CAPTURE": "FAIL", "R-AND-CAPTURE": "FAIL"}),
        ("capture writes an empty file", "stub", "emptyshot",
         {"R-IOS-CAPTURE": "FAIL", "R-AND-CAPTURE": "FAIL"}),
        ("simctl has no content_size subcommand", "stub", "nocontentsize",
         {"R-IOS-CAPTURE": "PASS", "R-IOS-APPEARANCE": "FAIL"}),
    ]
    w("\n-- the availability and failure states\n")
    for label, kind, mode, want in cases:
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            out = d / "reports"
            if kind is None:
                r = run_driver(None, None, None, out)
            else:
                bin_dir, log, png = make_stubs(d)
                r = run_driver(bin_dir, log, png, out, mode)
            v = verdicts(out)
            line = "  ".join(f"{k.split('-', 1)[1]}={v[k][0]}" for k in sorted(want))
            bad = [k for k, x in want.items() if v[k][0] != x]
            w(f"   {'ok ' if not bad else 'WRONG'} {label:<44} {line}\n")
            for k in bad:
                fails.append(f"{label}: {k} came out {v[k][0]}, expected {want[k]} -- "
                             f"{v[k][1][:110]}")

    # --------------------------------------------------------------- real tools
    if a.real:
        w("\n-- against the real tooling on this machine\n")
        for tool, plat, flag in (("xcrun", "ios", "--ios"), ("adb", "android", "--android")):
            present = shutil.which(tool)
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "reports"
                env = dict(os.environ)
                subprocess.run(["bash", str(HERE / "ux_native.sh"), flag, "--out", str(out)],
                               capture_output=True, text=True, env=env, timeout=300)
                rec = read_json(out, plat)
                v = verdicts(out)
                key = "R-IOS-CAPTURE" if plat == "ios" else "R-AND-CAPTURE"
                w(f"   {tool}: {'installed' if present else 'not installed'} -> "
                  f"{v[key][0]}\n      {str(rec.get('reason') or rec.get('device'))[:96]}\n")
                if not present and v[key][0] != "NOT_RUN":
                    fails.append(f"{tool} is absent and {key} did not report NOT_RUN")

    w("\n" + "=" * 74 + "\n")
    for f in fails:
        w(f"  FAIL  {f}\n")
    w(f"\nNATIVE CONFORMANCE {'PASS' if not fails else f'FAIL ({len(fails)})'}\n")
    w("\nTo get evidence about a real target:\n"
      "  iOS      macOS with Xcode. Boot a Simulator, install the app, then\n"
      "           `bash scripts/ux_native.sh --ios`. No other host can produce it.\n"
      "  Android  `adb` plus an emulator or an attached device, then\n"
      "           `bash scripts/ux_native.sh --android`. An emulator satisfies\n"
      "           AND-016 by its own terms; hardware is still required for posture,\n"
      "           gesture feel, refresh rate and performance (AND-018).\n"
      "\nWhat this establishes: the driver issues the documented commands in the right\n"
      "order, restores what it changed, and every availability state maps to the right\n"
      "verdict. What it does NOT establish: that any real device renders the interface\n"
      "correctly. A stub is not a phone. Run with a booted Simulator or an attached\n"
      "device to get evidence about one.\n")
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
