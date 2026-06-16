#!/usr/bin/env bash
# render.sh — headless OpenSCAD render: .scad -> STL / 3MF / PNG / etc.
#
# This is the programmatic-generation core: turn parametric code into a printable
# mesh from the command line, with parameter overrides and (when available) the
# fast Manifold geometry backend. No GUI, CI-friendly.
#
# Usage:
#   render.sh INPUT.scad [-o OUT] [-D name=value ...] [-p file.json -P set]
#             [-f FORMAT] [--fn N] [--ascii] [--png [--size WxH] [--view-all]]
#             [--camera ARGS] [--color SCHEME] [--manifold|--no-manifold]
#             [--hardwarnings] [-q]
#
# Examples:
#   render.sh box.scad -o box.stl
#   render.sh box.scad -o box_big.stl -D 'width=120' -D 'height=40'
#   render.sh box.scad -o box.3mf -p params.json -P large
#   render.sh box.scad -o preview.png --png --view-all --size 1200x900
#
# The OpenSCAD binary is resolved from $OPENSCAD, then `openscad`, then
# `openscad-nightly`. Install: see ../references/openscad-cli.md or run preflight.sh.
set -euo pipefail

die() { echo "render.sh: $*" >&2; exit 2; }

# ---- resolve the OpenSCAD binary ---------------------------------------------
resolve_bin() {
  if [[ -n "${OPENSCAD:-}" ]] && command -v "$OPENSCAD" >/dev/null 2>&1; then echo "$OPENSCAD"; return; fi
  if [[ -n "${OPENSCAD:-}" ]] && [[ -x "$OPENSCAD" ]]; then echo "$OPENSCAD"; return; fi
  for c in openscad openscad-nightly; do
    if command -v "$c" >/dev/null 2>&1; then echo "$c"; return; fi
  done
  die "OpenSCAD not found. Set \$OPENSCAD or install it (see references/openscad-cli.md). \
Linux: apt/dnf install openscad, or the AppImage from https://openscad.org/downloads.html"
}

INPUT=""; OUT=""; FORMAT=""; ASCII=0; PNG=0; SIZE=""; VIEWALL=0; CAMERA=""; COLOR=""
MANIFOLD="auto"; HARDWARN=0; QUIET=0
declare -a DEFINES=()
PARAMFILE=""; PARAMSET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output) OUT="$2"; shift 2;;
    -f|--format) FORMAT="$2"; shift 2;;
    -D) DEFINES+=("$2"); shift 2;;
    -p) PARAMFILE="$2"; shift 2;;
    -P) PARAMSET="$2"; shift 2;;
    --fn) DEFINES+=("\$fn=$2"); shift 2;;
    --ascii) ASCII=1; shift;;
    --png) PNG=1; shift;;
    --size) SIZE="$2"; shift 2;;
    --view-all) VIEWALL=1; shift;;
    --camera) CAMERA="$2"; shift 2;;
    --color) COLOR="$2"; shift 2;;
    --manifold) MANIFOLD="on"; shift;;
    --no-manifold) MANIFOLD="off"; shift;;
    --hardwarnings) HARDWARN=1; shift;;
    -q|--quiet) QUIET=1; shift;;
    -h|--help) sed -n '2,30p' "$0"; exit 0;;
    -*) die "unknown option: $1";;
    *) [[ -z "$INPUT" ]] && INPUT="$1" || die "unexpected arg: $1"; shift;;
  esac
done

[[ -n "$INPUT" ]] || die "no input .scad given. Try: render.sh model.scad -o model.stl"
[[ -f "$INPUT" ]] || die "no such file: $INPUT"

BIN="$(resolve_bin)"

# default output / format
if [[ $PNG -eq 1 ]]; then
  [[ -n "$OUT" ]] || OUT="${INPUT%.scad}.png"
else
  [[ -n "$OUT" ]] || OUT="${INPUT%.scad}.stl"
fi

declare -a ARGS=()

# ---- manifold backend auto-detection ------------------------------------------
# The fast, robust Manifold engine is the DEFAULT backend in OpenSCAD nightlies
# since 2025-08-17; older builds (incl. 2021.01) only have CGAL. The selector flag
# is `--backend=manifold|cgal` (the legacy `--enable=manifold` was removed). We
# detect support from --help so this stays correct across versions.
HELP="$("$BIN" --help 2>&1 || true)"
HAS_BACKEND=0; grep -q -- '--backend' <<<"$HELP" && HAS_BACKEND=1
case "$MANIFOLD" in
  on)
    if [[ $HAS_BACKEND -eq 1 ]]; then ARGS+=(--backend=manifold)
    else echo "render.sh: this OpenSCAD has no --backend flag (pre-2023 build); using CGAL." >&2; fi;;
  auto) [[ $HAS_BACKEND -eq 1 ]] && ARGS+=(--backend=manifold) || true;;  # default-on where available
  off)  [[ $HAS_BACKEND -eq 1 ]] && ARGS+=(--backend=cgal) || true;;
esac

# ---- format -------------------------------------------------------------------
ext="${OUT##*.}"; ext="${ext,,}"
if [[ -n "$FORMAT" ]]; then
  ARGS+=(--export-format "$FORMAT")
elif [[ "$ext" == "stl" && $PNG -eq 0 ]]; then
  # default STL to binary (smaller, universally accepted); --ascii to override
  if [[ $ASCII -eq 1 ]]; then ARGS+=(--export-format asciistl); else ARGS+=(--export-format binstl); fi
fi

# ---- defines / customizer -----------------------------------------------------
for d in "${DEFINES[@]:-}"; do [[ -n "$d" ]] && ARGS+=(-D "$d"); done
[[ -n "$PARAMFILE" ]] && ARGS+=(-p "$PARAMFILE")
[[ -n "$PARAMSET"  ]] && ARGS+=(-P "$PARAMSET")

# ---- png-specific -------------------------------------------------------------
if [[ $PNG -eq 1 ]]; then
  ARGS+=(--render)                # bare flag: full geometry (not preview). '--render=' is rejected.
  [[ -n "$SIZE" ]]   && ARGS+=(--imgsize "${SIZE/x/,}")
  [[ $VIEWALL -eq 1 ]] && ARGS+=(--viewall --autocenter)
  [[ -n "$CAMERA" ]] && ARGS+=(--camera "$CAMERA")
  [[ -n "$COLOR" ]]  && ARGS+=(--colorscheme "$COLOR")
fi

[[ $HARDWARN -eq 1 ]] && ARGS+=(--hardwarnings)
[[ $QUIET -eq 1 ]] && ARGS+=(-q)

# ---- run ----------------------------------------------------------------------
[[ $QUIET -eq 1 ]] || echo "render.sh: $BIN -o $OUT ${ARGS[*]} $INPUT" >&2
set +e
"$BIN" -o "$OUT" "${ARGS[@]}" "$INPUT"
rc=$?
set -e

if [[ $rc -ne 0 || ! -s "$OUT" ]]; then
  if [[ $PNG -eq 1 ]]; then
    die "PNG export failed (exit $rc). PNG rasterization needs an OpenGL context. \
On a headless box, wrap the command: xvfb-run -a render.sh ... --png  (install: apt/dnf xvfb / xorg-x11-server-Xvfb). \
STL/3MF/OFF/AMF/CSG export do NOT need a display and work headless as-is."
  fi
  die "OpenSCAD exited $rc with no usable output at $OUT (empty geometry? check warnings above)"
fi

bytes=$(stat -c%s "$OUT" 2>/dev/null || stat -f%z "$OUT" 2>/dev/null || echo "?")
[[ $QUIET -eq 1 ]] || echo "render.sh: wrote $OUT ($bytes bytes)"
if [[ "$ext" == "stl" || "$ext" == "3mf" ]] && [[ $QUIET -eq 0 ]]; then
  echo "render.sh: validate it with -> python3 mesh_tool.py info $OUT" >&2
fi
