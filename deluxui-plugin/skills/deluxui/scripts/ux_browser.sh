#!/usr/bin/env bash
# deluxui runtime tier -- measures a running interface instead of reading about it.
#
#   ux_browser.sh [base-url] [--routes /,/settings] [--api '**/api/**']
#                             [--out DIR] [--viewports 320,390,768,1024,1440]
#                             [--config PATH] [--baseline PNG]
#
# Every value defaults to app.* in .deluxui/ux.config.yaml; a flag overrides the
# file. The config used to be ignored entirely here, so `api_pattern` in it did
# nothing and the forced-state probes only ran when --api was passed by hand.
#
# Needs the agent-browser CLI. Without it every runtime rule stays NOT_RUN and
# says so -- an unmeasured rule is never reported as a pass.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROBES="$HERE/checks/browser"
BASE=""; ROUTES=""; API=""; OUT=".deluxui/reports/runtime"; VIEWPORTS=""; CONFIG=""
BASELINE=""; SLOW_ESCALATION=""

while [ $# -gt 0 ]; do
  case "$1" in
    --routes) ROUTES="$2"; shift 2;;
    --api) API="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    --viewports) VIEWPORTS="$2"; shift 2;;
    --config) CONFIG="$2"; shift 2;;
    --baseline) BASELINE="$2"; shift 2;;
    --slow-escalation) SLOW_ESCALATION=1; shift;;
    -h|--help) sed -n '2,16p' "$0"; exit 0;;
    *) BASE="$1"; shift;;
  esac
done

# Fill anything not given on the command line from the project config. One
# parser, shared with the Python tiers -- see scripts/uxconfig.py.
cfg() { python3 "$HERE/uxconfig.py" --get "$1" ${CONFIG:+--config "$CONFIG"} 2>/dev/null; }
[ -n "$BASE" ]      || BASE="$(cfg app.dev_url)"
[ -n "$ROUTES" ]    || ROUTES="$(cfg app.routes)"
[ -n "$API" ]       || API="$(cfg app.api_pattern)"
[ -n "$VIEWPORTS" ] || VIEWPORTS="$(cfg app.viewports)"
[ -n "$ROUTES" ]    || ROUTES="/"
# reflow.test_viewports_px is the overridable threshold behind app.viewports, so
# setting either one works and neither is silently ignored.
[ -n "$VIEWPORTS" ] || VIEWPORTS="$(python3 "$HERE/uxconfig.py" --json ${CONFIG:+--config "$CONFIG"} 2>/dev/null \
  | python3 -c 'import json,sys; print(",".join(str(v) for v in json.load(sys.stdin)["thresholds"]["reflow"]["test_viewports_px"]))' 2>/dev/null)"
[ -n "$VIEWPORTS" ] || VIEWPORTS="320,390,768,1024,1440"

# The merged thresholds, handed to every probe as window.__uxTh so a project
# override reaches the measurement instead of stopping at the config file.
TH_JSON="$(python3 "$HERE/uxconfig.py" --json ${CONFIG:+--config "$CONFIG"} 2>/dev/null \
  | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["thresholds"]))' 2>/dev/null)"
[ -n "$TH_JSON" ] || TH_JSON="{}"

if [ -z "$BASE" ]; then
  echo "usage: ux_browser.sh <base-url> [--routes ...] [--api ...]" >&2
  echo "  no base URL given and no app.dev_url in .deluxui/ux.config.yaml" >&2
  exit 1
fi
if [ -z "$API" ]; then
  echo "note: no --api and no app.api_pattern in config, so the aborted/empty/offline" >&2
  echo "      probes cannot run and the STATE-* rules will report NOT_RUN." >&2
fi

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
  local js; js="window.__uxTh=$TH_JSON;$(cat "$PROBES/$1.js")"
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
  # R-PIXEL-CONTRAST: the runs whose backdrop CSS cannot resolve -- text over an
  # image, a gradient, or a positioned sibling -- are settled from the pixels the
  # browser actually painted. The contrast probe records their page-absolute
  # boxes; this is the image they are read out of. It is captured unconditionally
  # because the probe has already scrolled through the page by this point, so the
  # scroll position the boxes were recorded at no longer matters.
  ab set viewport "$LAST_VP" 900 >/dev/null
  ab screenshot --full "$OUT/screens/${R}_fullpage.png" >/dev/null 2>&1 \
    && echo "{\"route\":\"$route\",\"path\":\"$OUT/screens/${R}_fullpage.png\"}" \
       > "$OUT/raw/${R}__fullpage.json"
  probe focus    "$OUT/raw/${R}__focus.json"
  probe measure  "$OUT/raw/${R}__measure.json"
  probe obstruction "$OUT/raw/${R}__obstruction.json"

  # R-FORCED-COLORS: two passes through the browser's own CDP endpoint, because
  # `Emulation.setEmulatedMedia` with a forced-colors feature is the only honest
  # way into the mode and agent-browser's `set media` does not expose it.
  python3 "$HERE/ux_forcedcolors.py" --url "${BASE%/}${route}" --out "$OUT" --route "$route" 2>&1 | sed 's/^/  /'

  # R-STATE-SLOW: make the request slow rather than absent. The other state probes
  # abort, empty or disconnect; none of them could answer "what does it say while
  # it waits", which is NUM-014's whole subject.
  python3 "$HERE/ux_slow.py" --url "${BASE%/}${route}" --out "$OUT" --route "$route" \
    ${SLOW_ESCALATION:+--escalation} 2>&1 | sed 's/^/  /'

  # R-AXE: axe-core over the live page, if it can be obtained. It covers rule
  # families this probe set does not reproduce, and it is NOT a substitute for the
  # rest -- automated checks reach a minority of the WCAG criteria either way.
  python3 "$HERE/ux_axe.py" --url "${BASE%/}${route}" --out "$OUT" --route "$route" 2>&1 | sed 's/^/  /'

  # --- GOV-004: prove the parts nobody asked you to change did not move.
  # The corpus was already being written and then thrown away: agent-browser has
  # `diff screenshot --baseline`, R-BASELINE-DIFF was declared, and nothing ever
  # called it -- so the instruction to capture a baseline was futile and the
  # detector's reason blamed the user for the code's omission.
  BL="$BASELINE"
  [ -n "$BL" ] || BL="$(dirname "$OUT")/baseline_${R}_${LAST_VP}.png"
  [ -n "$BASELINE" ] || [ -f "$BL" ] || BL="$(dirname "$OUT")/baseline.png"
  if [ -f "$BL" ]; then
    ab diff screenshot --baseline "$BL" > "$OUT/raw/${R}__baseline.json" 2>/dev/null \
      || echo '{"probe":"baseline","error":"diff failed"}' > "$OUT/raw/${R}__baseline.json"
  else
    printf '{"probe":"baseline","absent":true,"looked_for":"%s"}\n' "$BL" \
      > "$OUT/raw/${R}__baseline.json"
  fi
  ab snapshot    > "$OUT/raw/${R}__a11ytree.txt" 2>/dev/null
  ab vitals --json > "$OUT/raw/${R}__vitals.json" 2>/dev/null
  ab console     > "$OUT/raw/${R}__console.txt" 2>/dev/null
  ab errors      > "$OUT/raw/${R}__errors.txt" 2>/dev/null

  # --- landscape phone (LAY-004): where fixed heights and sticky bars collide
  ab set viewport 844 390 >/dev/null
  ab wait 250 >/dev/null
  probe layout "$OUT/raw/${R}__layout_landscape.json"
  ab set viewport "$LAST_VP" 900 >/dev/null

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
