#!/usr/bin/env bash
# deuxui live iteration -- change something, see what moved.
#
#   ux_live.sh [base-url] [--routes /,/settings] [--reset] [--out DIR]
#
# Runs the static and runtime tiers, then prints the DELTA against the previous
# run: which detectors were fixed, which regressed, and which are still failing.
# Nothing else in this tool answers "did that edit help", and without an answer
# the loop is: change something, re-read a 200-row matrix, guess.
#
# The first run records a baseline and says so. Every run after it is a comparison.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT=".deuxui/reports"; BASE=""; ROUTES=""; RESET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --routes) ROUTES="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --reset) RESET=1; shift;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) BASE="$1"; shift;;
  esac
done
SNAP="$OUT/live-snapshot.json"
mkdir -p "$OUT"
[ "$RESET" = 1 ] && rm -f "$SNAP"

python3 "$HERE/ux_check.py" . --json > "$OUT/static.json" 2>/dev/null
STATIC_RC=$?
[ "$STATIC_RC" -gt 2 ] && { echo "static tier failed" >&2; exit 1; }

if [ -n "$BASE" ] || python3 "$HERE/uxconfig.py" --get app.dev_url >/dev/null 2>&1; then
  bash "$HERE/ux_browser.sh" ${BASE:+"$BASE"} ${ROUTES:+--routes "$ROUTES"} \
       --out "$OUT/runtime" >/dev/null 2>&1
fi

python3 - "$OUT" "$SNAP" <<'PY'
import json, sys
from pathlib import Path

out, snap = Path(sys.argv[1]), Path(sys.argv[2])


def load(p, d):
    try:
        return json.loads(p.read_text())
    except Exception:
        return d


now = {}
for f, tier in ((out / "static.json", "static"),
                (out / "runtime" / "runtime.json", "runtime")):
    for did, v in (load(f, {}).get("detectors") or {}).items():
        now[did] = v["status"]

if not snap.exists():
    snap.write_text(json.dumps(now, indent=1))
    fails = sorted(d for d, s in now.items() if s == "FAIL")
    nr = sum(1 for s in now.values() if s == "NOT_RUN")
    print(f"\nbaseline recorded: {len(now)} detectors, {len(fails)} failing, "
          f"{nr} not run")
    print("Change something and run this again to see what moved.\n")
    for d in fails[:20]:
        print(f"  FAIL   {d}")
    if len(fails) > 20:
        print(f"  ... and {len(fails) - 20} more")
    raise SystemExit(0)

was = load(snap, {})
fixed = sorted(d for d, s in now.items() if s == "PASS" and was.get(d) == "FAIL")
broke = sorted(d for d, s in now.items() if s == "FAIL" and was.get(d) == "PASS")
# NOT_APPLICABLE counts as stopped too. Deleting the only Kotlin file in a
# project moved fifteen Android detectors out of scope, and an earlier version
# of this delta reported them as fifteen fixes.
lost = sorted(d for d, s in now.items()
              if s in ("NOT_RUN", "NOT_APPLICABLE") and was.get(d) in ("PASS", "FAIL"))
still = sorted(d for d, s in now.items() if s == "FAIL" and was.get(d) == "FAIL")
new = sorted(d for d in now if d not in was)

print(f"\nsince the last run  --  {len(fixed)} fixed, {len(broke)} regressed, "
      f"{len(still)} still failing")
print("-" * 68)
for d in broke:
    print(f"  REGRESSED  {d}")
for d in lost:
    # A check that stopped running is not a check that started passing. This is
    # the row that makes a green delta trustworthy: without it, deleting the
    # file a detector read would look like a fix.
    print(f"  STOPPED    {d}  (was {was[d]}, now {now[d]} -- it examined "
          f"nothing, so nothing was proved)")
for d in fixed:
    print(f"  fixed      {d}")
for d in still[:12]:
    print(f"  still      {d}")
if len(still) > 12:
    print(f"  ... and {len(still) - 12} more still failing")
for d in new:
    print(f"  new        {d}  {now[d]}")
print("-" * 68)
if broke or lost:
    print("Regressions and stopped checks are listed first on purpose: an edit "
          "that\nfixes two things and breaks one has not made the interface "
          "better yet.")
snap.write_text(json.dumps(now, indent=1))
PY
