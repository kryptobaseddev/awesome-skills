#!/usr/bin/env bash
# preflight.sh — check the parametric-3D-printing toolchain and explain what's missing.
#
# Two engines power this skill; you need at least one, ideally both:
#   1. OpenSCAD          — generate parametric geometry from .scad code (the core)
#   2. Python mesh stack — inspect / repair / convert / boolean existing meshes
# A slicer (Bambu Studio / OrcaSlicer) is needed only to turn a mesh into G-code.
#
# Exit 0 if OpenSCAD OR the Python mesh stack is usable; 1 if neither is.
set -uo pipefail

ok=0; warn=0
green()  { printf '  \033[32mok\033[0m   %s\n' "$1"; }
yellow() { printf '  \033[33mmiss\033[0m %s\n' "$1"; warn=$((warn+1)); }
hdr()    { printf '\n\033[1m%s\033[0m\n' "$1"; }

OS="$(uname -s)"
case "$OS" in
  Linux) PKG="apt install / dnf install / pacman -S";;
  Darwin) PKG="brew install";;
  *) PKG="your package manager";;
esac

# ---- 1. OpenSCAD --------------------------------------------------------------
hdr "OpenSCAD (parametric geometry engine)"
OSCAD=""
if [[ -n "${OPENSCAD:-}" ]] && { command -v "$OPENSCAD" >/dev/null 2>&1 || [[ -x "$OPENSCAD" ]]; }; then OSCAD="$OPENSCAD";
elif command -v openscad >/dev/null 2>&1; then OSCAD="openscad";
elif command -v openscad-nightly >/dev/null 2>&1; then OSCAD="openscad-nightly"; fi

if [[ -n "$OSCAD" ]]; then
  ver="$("$OSCAD" --version 2>&1 | head -1)"
  green "$OSCAD — $ver"
  if "$OSCAD" --help 2>&1 | grep -q -- '--backend'; then
    green "Manifold backend available (--backend=manifold) — fast, robust booleans"
  else
    yellow "no --backend flag (older build): booleans use CGAL (slower). A 2023+ snapshot enables Manifold."
  fi
  ok=$((ok+1))
else
  yellow "OpenSCAD not found"
  echo "       Linux:  $PKG openscad   (or the nightly AppImage from https://openscad.org/downloads.html)"
  echo "               headless PNG previews also want: $PKG xvfb  (run: xvfb-run -a render.sh ... --png)"
  echo "       macOS:  brew install --cask openscad"
  echo "       Win:    winget install OpenSCAD.OpenSCAD"
  echo "       Newer 'nightly' snapshots ship the Manifold engine (much faster booleans)."
fi

# ---- 2. Python mesh stack -----------------------------------------------------
hdr "Python mesh stack (inspect / repair / convert / boolean meshes)"
PYBIN=""
for c in python3 python; do command -v "$c" >/dev/null 2>&1 && { PYBIN="$c"; break; }; done
if [[ -z "$PYBIN" ]]; then
  yellow "no python3 found — install Python 3.8+"
else
  green "$("$PYBIN" --version 2>&1)"
  have_tri=$("$PYBIN" - <<'PY' 2>/dev/null
try:
    import trimesh; print(trimesh.__version__)
except Exception: print("")
PY
)
  if [[ -n "$have_tri" ]]; then
    green "trimesh $have_tri"
    "$PYBIN" -c "import manifold3d" 2>/dev/null && green "manifold3d (robust boolean engine)" || yellow "manifold3d missing — boolean ops will fail. pip install manifold3d"
    "$PYBIN" -c "import scipy"      2>/dev/null && green "scipy (body-count / adjacency)" || yellow "scipy missing — some mesh stats degrade. pip install scipy"
    "$PYBIN" -c "import stl"        2>/dev/null && green "numpy-stl (lightweight STL fallback)" || true
    ok=$((ok+1))
  else
    yellow "trimesh not installed"
    echo "       pip install \"trimesh[easy]\" manifold3d numpy-stl"
    echo "       (trimesh[easy] pulls scipy/networkx/shapely; manifold3d powers boolean ops)"
  fi
fi

# ---- 3. Slicer (optional) -----------------------------------------------------
hdr "Slicer (mesh -> G-code; needed only to actually print)"
found_slicer=0
for s in bambu-studio BambuStudio bambustudio orca-slicer OrcaSlicer orcaslicer prusa-slicer PrusaSlicer; do
  if command -v "$s" >/dev/null 2>&1; then green "$s on PATH"; found_slicer=1; fi
done
# common flatpak ids
if command -v flatpak >/dev/null 2>&1; then
  flatpak info com.bambulab.BambuStudio >/dev/null 2>&1 && { green "BambuStudio (flatpak)"; found_slicer=1; }
  flatpak info io.github.softfever.OrcaSlicer >/dev/null 2>&1 && { green "OrcaSlicer (flatpak)"; found_slicer=1; }
fi
if [[ $found_slicer -eq 0 ]]; then
  yellow "no slicer detected (fine for design; install one to slice/print)"
  echo "       Bambu Studio: https://bambulab.com/en/download/studio  (official, for Bambu printers)"
  echo "       OrcaSlicer:   https://github.com/SoftFever/OrcaSlicer/releases  (community fork; great Bambu profiles)"
  echo "       Slicing is mostly a GUI step. Headless CLI slicing exists but is limited — see references/bambu-lab.md."
fi

# ---- verdict ------------------------------------------------------------------
hdr "Verdict"
if [[ $ok -ge 1 ]]; then
  echo "  Ready to work ($ok/2 engines present). Missing pieces above are optional but recommended."
  exit 0
else
  echo "  Neither engine is usable yet. Install OpenSCAD and/or the Python mesh stack (see above), then re-run."
  exit 1
fi
