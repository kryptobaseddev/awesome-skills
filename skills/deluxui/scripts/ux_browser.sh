#!/usr/bin/env bash
# deluxui runtime tier -- measures a running interface instead of reading about it.
#
#   ux_browser.sh <base-url> [--routes /,/settings] [--api '**/api/**']
#                            [--out DIR] [--viewports 320,390,768,1024,1440]
#
# Needs the agent-browser CLI. Without it every runtime rule stays NOT_RUN and
# says so -- an unmeasured rule is never reported as a pass.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBES="$HERE/checks/browser"
BASE=""; ROUTES="/"; API=""; OUT=".deluxui/reports/runtime"
VIEWPORTS="320,390,768,1024,1440"

while [ $# -gt 0 ]; do
  case "$1" in
    --routes) ROUTES="$2"; shift 2;;
    --api) API="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --viewports) VIEWPORTS="$2"; shift 2;;
    -h|--help) sed -n '2,12p' "$0"; exit 0;;
    *) BASE="$1"; shift;;
  esac
done
[ -n "$BASE" ] || { echo "usage: ux_browser.sh <base-url> [--routes ...] [--api ...]" >&2; exit 1; }

mkdir -p "$OUT/raw" "$OUT/screens"

if ! command -v agent-browser >/dev/null 2>&1; then
  python3 - "$OUT" <<'PY'
import json, sys, pathlib
reason = ("agent-browser is not installed, so nothing was measured. "
          "Install it (npm i -g agent-browser) and re-run; until then every "
          "runtime rule stays NOT_RUN.")
p = pathlib.Path(sys.argv[1]) / "runtime.json"
p.write_text(json.dumps({"tier": "runtime", "available": False,
                         "reason": reason, "probes": []}, indent=1))
print(reason, file=sys.stderr)
PY
  exit 3
fi

ab() { timeout 120 agent-browser "$@" 2>/dev/null; }
probe() { # probe <name> <outfile>
  local js; js="$(cat "$PROBES/$1.js")"
  ab eval "$js" > "$2" 2>/dev/null
  [ -s "$2" ] || echo '{"probe":"'"$1"'","error":"probe returned nothing"}' > "$2"
}

slug() { echo "$1" | sed 's#[^a-zA-Z0-9]#_#g; s#^_*##; s#_*$##' | sed 's#^$#root#'; }

IFS=',' read -ra ROUTE_LIST <<< "$ROUTES"
IFS=',' read -ra VP_LIST <<< "$VIEWPORTS"
LAST_VP="${VP_LIST[${#VP_LIST[@]}-1]}"

for route in "${ROUTE_LIST[@]}"; do
  R="$(slug "$route")"
  echo "route $route" >&2
  ab open "${BASE%/}${route}" >/dev/null
  ab wait --load networkidle >/dev/null

  # --- reflow across the viewport matrix (NUM-009, NUM-019)
  for vp in "${VP_LIST[@]}"; do
    ab set viewport "$vp" 900 >/dev/null
    ab wait 250 >/dev/null
    probe layout "$OUT/raw/${R}__layout_${vp}.json"
    ab screenshot "$OUT/screens/${R}_${vp}.png" >/dev/null
  done

  # --- everything else at the widest tested viewport
  ab set viewport "$LAST_VP" 900 >/dev/null
  ab wait 300 >/dev/null
  probe targets  "$OUT/raw/${R}__targets.json"
  probe contrast "$OUT/raw/${R}__contrast.json"
  probe focus    "$OUT/raw/${R}__focus.json"
  probe measure  "$OUT/raw/${R}__measure.json"
  ab snapshot    > "$OUT/raw/${R}__a11ytree.txt" 2>/dev/null
  ab vitals --json > "$OUT/raw/${R}__vitals.json" 2>/dev/null
  ab console     > "$OUT/raw/${R}__console.txt" 2>/dev/null
  ab errors      > "$OUT/raw/${R}__errors.txt" 2>/dev/null

  # --- user setting overrides: 200% text (NUM-008) and text spacing (NUM-010)
  for mode in zoom spacing; do
    ab eval "window.__uxMode='$mode'" >/dev/null
    probe zoom "$OUT/raw/${R}__override_${mode}.json"
  done

  # --- reduced motion (LAY-010, A11Y-010)
  ab set media reduced-motion >/dev/null
  ab reload >/dev/null; ab wait --load networkidle >/dev/null
  probe motion "$OUT/raw/${R}__motion.json"
  ab set media light >/dev/null

  # --- forced states. This is the part nobody tests by hand, which is exactly
  #     why it is where the defects live (STATE-001/006/008, UX-001, UX-009).
  if [ -n "$API" ]; then
    for mode in abort empty offline; do
      case "$mode" in
        abort)   ab network route "$API" --abort >/dev/null;;
        empty)   ab network unroute >/dev/null
                 ab network route "$API" --body '[]' >/dev/null;;
        offline) ab network unroute >/dev/null
                 ab set offline on >/dev/null;;
      esac
      ab reload >/dev/null
      ab wait --load networkidle >/dev/null
      ab wait 1200 >/dev/null
      probe statecheck "$OUT/raw/${R}__state_${mode}.json"
      ab screenshot "$OUT/screens/${R}_state_${mode}.png" >/dev/null
    done
    ab set offline off >/dev/null
    ab network unroute >/dev/null
  fi
done

python3 "$HERE/ux_report.py" --collect "$OUT" --base "$BASE" \
        ${API:+--api "$API"} --routes "$ROUTES"
