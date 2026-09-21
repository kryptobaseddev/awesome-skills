#!/usr/bin/env bash
# deluxui native runtime tier -- capture evidence from a Simulator, an emulator or
# a device, and record what was and was not available.
#
#   ux_native.sh --ios     [--out .deluxui/reports] [--udid UDID]   [--bundle ID]
#   ux_native.sh --android [--out .deluxui/reports] [--serial SER]  [--package ID]
#   ux_native.sh --both
#
# It writes raw/native-ios.json and raw/native-android.json for
# scripts/ux_report.py, plus the PNGs beside them. A capture from a browser is not
# evidence about a phone, so when the platform tooling is absent this records
# `available: false` with the reason and exits 0 -- the rule then reports NOT_RUN,
# which is the true answer, rather than disappearing from the report.
#
# Three passes per platform, because a single default-appearance screenshot is
# where fixed layouts hide:
#   light       the app as most people first see it
#   dark        a designed appearance, not an inversion
#   large-type  the accessibility text size that truncates a rigid layout
set -uo pipefail

OUT=".deluxui/reports"
UDID=""; SERIAL=""; BUNDLE=""; PACKAGE=""
DO_IOS=0; DO_AND=0

while [ $# -gt 0 ]; do
  case "$1" in
    --ios) DO_IOS=1 ;;
    --android) DO_AND=1 ;;
    --both) DO_IOS=1; DO_AND=1 ;;
    --out) OUT="$2"; shift ;;
    --udid) UDID="$2"; shift ;;
    --serial) SERIAL="$2"; shift ;;
    --bundle) BUNDLE="$2"; shift ;;
    --package) PACKAGE="$2"; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
  shift
done
if [ "$DO_IOS" = 0 ] && [ "$DO_AND" = 0 ]; then
  echo "pick a platform: --ios, --android or --both" >&2; exit 1
fi

# The runtime tier lives under reports/runtime/ and ux_report.py --collect reads
# raw/ from there, so the native captures land beside the browser ones and one
# collect pass interprets both.
RUNDIR="$OUT/runtime"
RAW="$RUNDIR/raw"; SHOTS="$RUNDIR/native"
mkdir -p "$RAW" "$SHOTS"

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/	/ /g' | tr -d '\n'; }

bytes_of() { [ -f "$1" ] && wc -c < "$1" | tr -d ' ' || echo 0; }

# ---------------------------------------------------------------------- iOS
capture_ios() {
  local target="$UDID" dev="" caps="" errs="" n=0

  if ! command -v xcrun >/dev/null 2>&1; then
    printf '{"platform":"ios","available":false,"reason":"xcrun is not on PATH. iOS capture needs macOS with Xcode installed; no other host can produce it."}\n' \
      > "$RAW/native-ios.json"
    echo "iOS:     xcrun unavailable -> NOT_RUN (recorded, not skipped)" >&2
    return 0
  fi

  # Several booted simulators can share a display name; the UDID never collides.
  if [ -z "$target" ]; then
    target=$(xcrun simctl list devices booted 2>/dev/null \
             | grep -oE '\(([0-9A-F-]{36})\)' | head -1 | tr -d '()')
  fi
  if [ -z "$target" ]; then
    printf '{"platform":"ios","available":false,"reason":"No booted Simulator. Boot one (xcrun simctl boot <udid>) and install the app before capturing."}\n' \
      > "$RAW/native-ios.json"
    echo "iOS:     no booted simulator -> NOT_RUN" >&2
    return 0
  fi
  dev=$(xcrun simctl list devices 2>/dev/null | grep "$target" | sed 's/^ *//' | head -1)
  dev="${dev:-$target}"

  shoot() {                         # shoot <kind> <device_class>
    # Declared separately on purpose. bash 5.3 makes every name in a `local`
    # statement a local BEFORE performing any of its assignments, so
    # `local kind="$1" path="...$kind..."` reads an unset local and, under
    # `set -u`, aborts the script. This whole function had never executed on a
    # machine without Xcode, so the bug shipped invisible until a conformance
    # harness put a stub `xcrun` on PATH and ran it.
    local kind="$1"
    local klass="$2"
    local path="$SHOTS/ios-$kind.png"
    if xcrun simctl io "$target" screenshot "$path" >/dev/null 2>"$SHOTS/.err"; then
      local b; b=$(bytes_of "$path")
      caps="$caps${caps:+,}{\"kind\":\"$kind\",\"device_class\":\"$klass\",\"path\":\"$(json_escape "$path")\",\"bytes\":$b}"
      n=$((n+1))
    else
      errs="$errs${errs:+,}\"$kind: $(json_escape "$(head -c 200 "$SHOTS/.err" 2>/dev/null)")\""
    fi
  }

  local klass="iphone"
  echo "$dev" | grep -qi ipad && klass="ipad"

  xcrun simctl ui "$target" appearance light >/dev/null 2>&1
  shoot light "$klass"
  xcrun simctl ui "$target" appearance dark >/dev/null 2>&1
  shoot dark "$klass"
  # Dynamic Type at an accessibility size. Available on Xcode 15+; when the
  # subcommand is missing the capture is simply not recorded, and the rule fails
  # on an incomplete pass rather than passing on a partial one.
  if xcrun simctl ui "$target" content_size accessibility-extra-extra-large >/dev/null 2>&1; then
    shoot large-type "$klass"
    xcrun simctl ui "$target" content_size medium >/dev/null 2>&1
  else
    errs="$errs${errs:+,}\"large-type: this Xcode's simctl has no content_size subcommand; set the text size in Settings and capture manually\""
  fi
  xcrun simctl ui "$target" appearance light >/dev/null 2>&1
  rm -f "$SHOTS/.err"

  printf '{"platform":"ios","available":true,"tool":"xcrun simctl","device":"%s","captures":[%s],"errors":[%s]}\n' \
    "$(json_escape "$dev")" "$caps" "$errs" > "$RAW/native-ios.json"
  echo "iOS:     $n capture(s) from $dev" >&2
}

# ------------------------------------------------------------------ Android
capture_android() {
  local target="$SERIAL" dev="" caps="" errs="" n=0

  if ! command -v adb >/dev/null 2>&1; then
    printf '{"platform":"android","available":false,"reason":"adb is not on PATH. Install platform-tools and attach an emulator or device."}\n' \
      > "$RAW/native-android.json"
    echo "Android: adb unavailable -> NOT_RUN (recorded, not skipped)" >&2
    return 0
  fi
  if [ -z "$target" ]; then
    target=$(adb devices 2>/dev/null | awk 'NR>1 && $2=="device" {print $1; exit}')
  fi
  if [ -z "$target" ]; then
    printf '{"platform":"android","available":false,"reason":"No attached device or running emulator. Start one and install the app before capturing."}\n' \
      > "$RAW/native-android.json"
    echo "Android: no device attached -> NOT_RUN" >&2
    return 0
  fi
  local model sdk
  model=$(adb -s "$target" shell getprop ro.product.model 2>/dev/null | tr -d '\r')
  sdk=$(adb -s "$target" shell getprop ro.build.version.sdk 2>/dev/null | tr -d '\r')
  dev="${model:-$target} (API ${sdk:-?}, $target)"

  # A tablet is a different device class, and a phone bottom bar shipped to one
  # is exactly what AND-001 is about -- so record which it was.
  local klass="phone" wpx
  wpx=$(adb -s "$target" shell wm size 2>/dev/null | grep -oE '[0-9]+x[0-9]+' | head -1 \
        | cut -dx -f1)
  [ -n "${wpx:-}" ] && [ "$wpx" -ge 1600 ] 2>/dev/null && klass="tablet"

  shoot_a() {                       # shoot_a <kind>
    local kind="$1"
    local path="$SHOTS/android-$kind.png"
    if adb -s "$target" exec-out screencap -p > "$path" 2>"$SHOTS/.err"; then
      local b; b=$(bytes_of "$path")
      if [ "$b" -gt 0 ]; then
        caps="$caps${caps:+,}{\"kind\":\"$kind\",\"device_class\":\"$klass\",\"path\":\"$(json_escape "$path")\",\"bytes\":$b}"
        n=$((n+1))
        return
      fi
    fi
    errs="$errs${errs:+,}\"$kind: $(json_escape "$(head -c 200 "$SHOTS/.err" 2>/dev/null)")\""
  }

  adb -s "$target" shell cmd uimode night no >/dev/null 2>&1
  shoot_a light
  adb -s "$target" shell cmd uimode night yes >/dev/null 2>&1
  shoot_a dark
  adb -s "$target" shell cmd uimode night no >/dev/null 2>&1
  adb -s "$target" shell settings put system font_scale 1.3 >/dev/null 2>&1
  shoot_a large-type
  adb -s "$target" shell settings put system font_scale 1.0 >/dev/null 2>&1
  rm -f "$SHOTS/.err"

  printf '{"platform":"android","available":true,"tool":"adb","device":"%s","captures":[%s],"errors":[%s]}\n' \
    "$(json_escape "$dev")" "$caps" "$errs" > "$RAW/native-android.json"
  echo "Android: $n capture(s) from $dev" >&2
}

[ "$DO_IOS" = 1 ] && capture_ios
[ "$DO_AND" = 1 ] && capture_android

# Interpret what was captured. This re-reads every raw probe in the directory,
# so running the browser driver first and this second leaves one runtime.json
# describing both, rather than whichever ran last.
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/ux_report.py" --collect "$RUNDIR" >/dev/null 2>&1 || true

cat >&2 <<'NOTE'

Captures and their availability record are in the report directory. Two things
these images cannot establish, however many you take:
  - posture, gesture feel, refresh rate and real performance. A Simulator and an
    emulator do not have them. IOS-020 / AND-018 ask which hardware produced any
    claim about them, and the honest answer here is "none".
  - whether the screen is any good. This tier proves the layout survives both
    appearances and a larger text size. Reading the result is still your job.
NOTE
exit 0
