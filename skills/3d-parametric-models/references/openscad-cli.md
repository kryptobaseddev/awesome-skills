# OpenSCAD Command-Line Interface — Reference

*Headless/batch use of the `openscad` binary to turn `.scad` source into STL/3MF/PNG/etc. Read when building/printing a parametric model from the CLI, scripting batch renders, wiring OpenSCAD into CI, or debugging a render that won't run headless. The bundled `scripts/render.sh` and `scripts/scad_params.py` implement every pattern here.*

## Contents

- [TL;DR](#tldr) · [Binaries & invocation](#binaries--invocation) · [Output & export formats](#output--export-formats) · [Parameter override -D](#parameter-override--d) · [Customizer sets -p / -P](#customizer-sets--p---p) · [Preview/render & backend](#previewrender--the-geometry-backend) · [PNG export](#png-export) · [Warnings & diagnostics](#warnings--diagnostics) · [Dependency output -d / -m](#dependency-output--d---m) · [Animation](#animation) · [Headless GL context for PNG](#headless-gl-context-for-png) · [Batch patterns](#batch-patterns) · [WASM / browser](#wasm--browser) · [Install](#install) · [Capability probe](#capability-probe) · [Sources](#sources)

Verified 2026-06-15 against `openscad --help` for stable **2021.01** and the **2025.08.17** nightly, the openscad(1) man page, and the OpenSCAD discuss list. Stable is 2021.01; active development ships dated nightlies.

## TL;DR

```bash
openscad -o out.stl in.scad                              # STL — but CLI default is ASCII (see below)
openscad --export-format binstl -o out.stl in.scad       # force BINARY STL (what slicers want)
openscad --export-format binstl -o out.stl -D 'w=40' -D 'label="A1"' in.scad   # param overrides
openscad -o out.3mf in.scad                              # 3MF: units/metadata, multi-material
xvfb-run -a openscad --imgsize=1024,768 -o preview.png in.scad   # PNG needs a GL context
openscad --hardwarnings --check-parameters=true --export-format binstl -o out.stl in.scad   # CI strict
```

With `-o`/`--o` the **GUI is not started** (headless mode). The output extension selects the export type unless `--export-format` overrides it. `render.sh` wraps all this and injects `--export-format binstl` for `.stl` by default.

## Binaries & invocation

```
openscad [options] file.scad
```

| Platform | CLI binary |
|---|---|
| Linux apt/AppImage | `openscad` (stable) / `openscad-nightly` (nightly) |
| macOS | `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` — symlink it to `/usr/local/bin/openscad` |
| Windows | **`openscad.com`** (console wrapper), *not* `openscad.exe` (GUI build; no console stdout/stderr) |

- Exactly one input `.scad` (or `.csg`) positional arg. Flags accept `--flag value` and `--flag=value`; short forms `-o -D -p -P -d -m -q`.
- No `-o` ⇒ GUI launches and fails on a headless box without X11.
- `render.sh` resolves the binary from `$OPENSCAD`, then `openscad`, then `openscad-nightly`.

## Output & export formats

The output extension picks the type: `stl off wrl amf 3mf csg dxf svg pdf png echo ast term nef3 nefdbg param pov`.

| Ext | Kind | Notes |
|---|---|---|
| `stl` | 3D mesh | **CLI default is ASCII** — pass `--export-format binstl` for binary |
| `3mf` | 3D mesh | units/metadata, multi-material; preferred over STL for slicers |
| `off` `amf` `wrl` | 3D mesh | CGAL OFF / AMF / VRML |
| `dxf` `svg` `pdf` | 2D | only valid for 2D geometry (`projection()` / 2D primitives) |
| `png` | image | **requires a GL context** (see headless section) |
| `csg` | source | OpenSCAD-language dump, calculations resolved & module calls applied |
| `echo` `ast` `term` | text | echo output / AST / CSG term dump |
| `nef3` `nefdbg` `param` `pov` | misc | CGAL Nef / Customizer params / POV-Ray (nightly) |

A 2D model exported to a 3D format (or vice-versa) errors out — match format to geometry dimensionality.

### CLI STL default is ASCII, not binary

The CLI defaults `.stl` to **ASCII STL**, *not* binary. Only the **GUI** (F6/F7) defaults to binary. The `--help` text says: *"Ascii export is the current stl default, but binary stl is planned as the future default so asciistl should be explicitly specified in scripts when needed."* To get binary you **must pass `--export-format binstl`** — never assume `.stl` is binary. `render.sh` and `scad_params.py batch` do this automatically; pass `--ascii` to opt into ASCII.

### `--export-format ARG` — override format independent of extension

The only ASCII/binary STL toggle (no separate `--asciistl`/`--binstl` flag).

| Value | Effect |
|---|---|
| `binstl` | Binary STL — required to get binary; CLI will NOT pick it for you |
| `asciistl` | ASCII STL (human-readable, larger) |
| `stl 3mf off amf wrl dxf svg pdf png csg` … | same as the matching extension |

```bash
openscad --export-format binstl  -o model.stl model.scad     # binary (do this for slicers)
openscad --export-format asciistl -o model.stl model.scad    # ascii
openscad --export-format 3mf -o part.bin model.scad          # decouple name from format
```

## Parameter override -D

`-D ARG` / `--D ARG` — `var=val`, pre-define a variable as a constant. Value is an **arbitrary OpenSCAD expression** (numbers, strings, vectors, bools, ranges, math). `-D` overrides top-level assignments and may be repeated. Quoting is two-layer: shell parses first, then OpenSCAD.

| Type | `-D` argument | OpenSCAD sees |
|---|---|---|
| Number / float / bool | `-D 'n=42'` `-D 'r=2.5'` `-D 'solid=true'` | `n = 42;` etc. |
| **String** | `-D 'label="A1"'` | `label = "A1";` — inner `"` required by OpenSCAD; single quotes stop the shell |
| Vector / point list | `-D 'sz=[10,20,30]'` `-D 'pts=[[0,0],[1,0]]'` | vector / nested vector |
| Expression / range | `-D 'a=360/8'` `-D 'rng=[0:5:100]'` | `a = 45;` / range |

**Rule:** wrap the whole `name=value` token in single quotes; put double quotes inside for strings.

```bash
openscad --export-format binstl -o out.stl -D width=40 -D 'size=[40,20,10]' in.scad
openscad --export-format binstl -o tag.stl -D 'text="SN-0042"' in.scad
openscad --export-format binstl -o gear.stl -D 'teeth=24' -D 'angle=360/teeth' in.scad
```

**Windows `cmd.exe`:** no single quotes; double the inner quotes; use `openscad.com`:
```bat
openscad.com -o out.stl -D "quality=""production""" file.scad
```

**Programmatic (argv array, no shell):** pass each arg separately with OpenSCAD-level quoting only:
```python
subprocess.run(["openscad", "--export-format", "binstl", "-o", "out.stl",
    "-D", 'label="A1"',          # OpenSCAD sees: label = "A1";
    "-D", "size=[40,20,10]", "in.scad"])
```
`scad_params.py` (`_fmt_define`) does exactly this: numbers/bools/vectors pass through, bare strings get wrapped in `"…"`.

## Customizer sets -p / -P

Keep named presets in one JSON file, select one at render time.

- `-p ARG` / `--p ARG` — Customizer parameter file (`.json`)
- `-P ARG` / `--P ARG` — parameter-set name to apply

```json
{ "parameterSets": {
    "small": { "width": "20", "label": "S" },
    "large": { "width": "80", "label": "L" } },
  "fileFormatVersion": "1" }
```
```bash
openscad --export-format binstl -o widget_large.stl -p widget.json -P large widget.scad
# preset + ad-hoc -D override (-D wins for that var):
openscad --export-format binstl -o widget.stl -p widget.json -P large -D 'label="custom"' widget.scad
```
`scad_params.py json` emits this file shape; `scad_params.py list` prints tunable top-level params. `--check-parameters` / `--check-parameter-ranges` control whether mismatched / out-of-range values are warnings or hard errors.

## Preview/render & the geometry backend

### `--render` / `--preview` (affect PNG export only)

- `--render` — full geometry render (CGAL/Manifold) before PNG export. **Bare flag** — `--render=` is rejected.
- `--preview[=throwntogether]` — fast OpenCSG preview; default for PNG.

**Mesh exports always do a full render** — preview/render only changes what a `.png` looks like. `$preview` is `true` in preview, `false` in full render. `render.sh` passes the bare `--render` for PNG.

No standalone `--csg` flag; use the `.csg` extension: `openscad -o model.csg model.scad`.

### Geometry backend — Manifold

`--backend ARG` = `cgal` (old/slow) or `manifold` (new/fast, often 10–100× on boolean-heavy CSG). Value case-insensitive.

**Manifold is the DEFAULT backend in current nightlies.** As of the **2025-08-17** announcement it became the default for development snapshots ("starting with the next nightly build"); pass `--backend=cgal` to force the old engine.

> The stale `--help` string in 2025.08.17 still prints `'CGAL' … [default]`, but the maintainer's announcement supersedes it. For a 2026-era nightly assume Manifold is default — verify with `--backend` either way.

```bash
openscad --backend=manifold -o out.stl in.scad   # explicit Manifold (default in nightlies)
openscad --backend=cgal     -o out.stl in.scad   # opt OUT, force legacy CGAL
```

| Build era | Manifold | Status |
|---|---|---|
| Pre-2024.09 | `--enable=manifold` | legacy toggle, **REMOVED** — no longer works |
| 2024.09.28+ nightly | `--backend=manifold` | promoted out of experimental |
| 2025-08-17+ nightly | (default) | Manifold default; `--backend=cgal` to opt out |
| Stable 2021.01 | none | CGAL only; use a nightly for Manifold |

**Gotcha:** legacy `--enable=manifold` is gone (`manifold` no longer in the `--enable` list) — migrate to `--backend=manifold`. `render.sh` auto-detects `--backend` from `--help` and selects `manifold`/`cgal`, falling back to CGAL on pre-`--backend` builds.

## PNG export

These apply **only when exporting `.png`** (ignored for mesh/2D exports).

| Flag | Syntax / values |
|---|---|
| `--imgsize ARG` | `=width,height` e.g. `--imgsize=1920,1080` |
| `--camera ARG` | Two forms only: `=eye_x,y,z,center_x,y,z` (**6 numbers**) or `=trans_x,y,z,rot_x,y,z,dist` (**7 numbers**) |
| `--projection ARG` | `=ortho` / `=perspective` (or `o`/`p`) |
| `--viewall` / `--autocenter` | fit object in frame / look at object center |
| `--colorscheme ARG` | render color scheme (below) |
| `--view ARG` | overlays: `axes \| crosshairs \| edges \| scales` (comma-separated) |
| `--csglimit ARG` | stop preview after N CSG elements |

`--view` in current nightlies accepts only `axes`, `crosshairs`, `edges`, `scales` — **there is no `wireframe`** (valid in 2021.01 and the old man page, removed from the nightly this skill targets). `--camera` has **no 5-number form**: only the 6-number vector (eye+center) and 7-number gimbal (trans+rot+distance) forms exist.

`--colorscheme` values (`*` = default): `*Cornfield | Metallic | Sunset | Starnight | BeforeDawn | Nature | Daylight Gem | Nocturnal Gem | DeepOcean | Solarized | Tomorrow | Tomorrow Night | ClearSky | Monotone`. Quote multi-word names: `--colorscheme="Tomorrow Night"`.

```bash
# fit, orthographic, axes+edges, 1600×1200:
xvfb-run -a openscad -o shot.png --imgsize=1600,1200 --projection=ortho \
  --viewall --autocenter --view=axes,edges --colorscheme=Cornfield --render model.scad
# vector camera — 6 numbers: eye(50,-60,40) + center(0,0,0):
xvfb-run -a openscad -o iso.png --imgsize=1024,768 --camera=50,-60,40,0,0,0 model.scad
# gimbal camera — 7 numbers: trans(0,0,0) + rot(55,0,25) + distance 140:
xvfb-run -a openscad -o iso.png --camera=0,0,0,55,0,25,140 --imgsize=800,600 model.scad
```

## Warnings & diagnostics

| Flag | Meaning |
|---|---|
| `--hardwarnings` | stop on first warning (non-zero exit) — CI fail-fast on deprecations / `undef` |
| `--check-parameters ARG` | `=true/false` — check params to **user** modules/functions |
| `--check-parameter-ranges ARG` | `=true/false` — range-check **builtin** module params |
| `--trace-depth ARG` / `--debug ARG` | max trace messages / `'all'` or source-file set |
| `-q` / `--quiet` | print nothing except errors |
| `--summary ARG` | `all \| cache \| time \| camera \| geometry \| bounding-box \| area` |
| `--summary-file ARG` | write summary as **JSON** to file; `-` ⇒ stdout (programmatic bbox/geometry) |
| `--info` / `-v` / `-h` | build/feature info / version / help |

```bash
openscad --hardwarnings --check-parameters=true --check-parameter-ranges=true \
  --summary=all --summary-file=stats.json --export-format binstl -o out.stl in.scad
```

**Exit codes:** `0` success, non-zero on failure (parse/geometry error, missing file, or — with `--hardwarnings` — first warning). Check `$?`; do not parse stderr text.

## Dependency output -d / -m

For incremental builds, OpenSCAD emits the files a render depends on (imported STLs, `include`/`use` libs, fonts, `import()` data):

- `-d ARG` / `--d ARG` — `deps_file`, Make-format dependency file
- `-m ARG` / `--m ARG` — `make_cmd` to (re)create a missing referenced dependency

```bash
openscad --export-format binstl -o part.stl -d part.deps part.scad
# part.deps:  part.stl: part.scad lib/util.scad fonts/...
```

## Animation

`--animate N` — export N frames; OpenSCAD sweeps `$t` from 0 up to (not including) 1, writing one file per frame (index auto-suffixed). PNG output ⇒ N numbered PNGs for GIF/MP4. `--animate_sharding =<shard>/<num>` splits the set across parallel jobs (nightly only).

```bash
xvfb-run -a openscad --animate 36 --imgsize=640,480 -o frame.png spinner.scad  # frame00000..00035.png
xvfb-run -a openscad --animate 36 --animate_sharding 1/4 -o frame.png spinner.scad  # job 1 of 4
```
In `spinner.scad`: `rotate([0,0,360*$t]) model();`. Assemble: `ffmpeg -framerate 24 -i frame%05d.png -pix_fmt yuv420p out.mp4`.

## Headless GL context for PNG

**Mesh and 2D exports (STL, 3MF, OFF, AMF, DXF, SVG, PDF, CSG) do NOT need a display** — they run on a bare headless box. **Only PNG export requires an OpenGL context** (via GLX, which needs an X server).

```bash
xvfb-run -a openscad --imgsize=1024,768 -o preview.png model.scad
# if "couldn't find RGB GLX visual / fbconfig", set screen depth:
xvfb-run -a -s "-screen 0 1280x1024x24" openscad --imgsize=1280,1024 -o preview.png model.scad
```
```bash
sudo apt-get install -y openscad xvfb libgl1-mesa-dri   # mesa software GL (llvmpipe), no GPU needed
```
Gotchas: `unset LIBGL_ALWAYS_INDIRECT` if set; ensure `libgl1-mesa-dri` (llvmpipe) is present. An **EGL/OSMesa build** (`Dockerfile.egl`) creates an offscreen context with no X server, but is not the default binary (GLEW is GLX *or* EGL).

**Decision rule:** STL/3MF/etc. → run `openscad` directly, no Xvfb. PNG on CI with a normal binary → wrap in `xvfb-run -a`. Zero X11 → EGL build image. `render.sh` emits the xvfb hint only when a **PNG** export fails.

## Batch patterns

```bash
# one BINARY STL per size:
for w in 10 20 30 40 50; do
  openscad --backend=manifold --export-format binstl -o "bracket_${w}mm.stl" -D "width=${w}" bracket.scad
done
# string parameter (labels) — inner double quotes:
for sn in A1 A2 B7; do
  openscad --export-format binstl -o "tag_${sn}.stl" -D "label=\"${sn}\"" tag.scad
done
# parallelize:
printf '%s\n' 10 20 30 40 50 | xargs -P "$(nproc)" -I{} \
  openscad --backend=manifold --export-format binstl -o "bracket_{}.stl" -D "width={}" bracket.scad
# drive every Customizer preset:
for s in small medium large; do openscad -o "widget_${s}.3mf" -p widget.json -P "$s" widget.scad; done
```

`scad_params.py batch FILE.scad matrix.json -d OUT` renders from a `matrix.json` (`{"variants":[{name,params}]}` or `{"grid":{p:[..]}}`), binary STL per variant unless `--ascii`.

**Makefile (with dependency tracking):**
```make
OPENSCAD ?= openscad
SCAD = $(wildcard *.scad)
STL  = $(SCAD:.scad=.stl)
FLAGS = --backend=manifold --export-format binstl --hardwarnings

all: $(STL)
%.stl: %.scad
	$(OPENSCAD) $(FLAGS) -o $@ -d $*.deps $<
-include $(SCAD:.scad=.deps)
clean:
	rm -f $(STL) *.deps
.PHONY: all clean
```
Parameterized variant:
```make
WIDTHS = 10 20 30 40
PARTS  = $(foreach w,$(WIDTHS),bracket_$(w).stl)
all: $(PARTS)
bracket_%.stl: bracket.scad
	openscad --backend=manifold --export-format binstl -o $@ -D "width=$*" $<
```

## WASM / browser

No-install option (browser, locked-down CI, serverless):

- **openscad-wasm** — headless WASM module: write a `.scad` into its virtual FS, call with an args array (`["/in.scad","-o","/out.stl"]`), read output bytes. Historically uses the legacy `--enable=manifold` form internally.
- **openscad-playground** (live at `ochafik.com/openscad`) — browser IDE wrapping that module; **defaults to Manifold**. F5 preview, Ctrl+Enter/F6 full render → STL. PWA-installable.
- Official downloads ZIP ships an experimental WASM build (no preview shading, limited fonts, slower).

**Use for:** quick param exploration, embedding `.scad`→STL in a web app, sandboxed execution. **Not for:** heavy production batch (native + Manifold is faster, all formats/fonts).

## Install

| Channel | Command / source | Gives you |
|---|---|---|
| Official | https://openscad.org/downloads.html | canonical, all platforms |
| apt | `sudo apt install openscad` | **stable 2021.01** (no Manifold) — still 2021.01 through Ubuntu 26.04 |
| Homebrew | `brew install --cask openscad` / `openscad@snapshot` | stable / nightly |
| snap | `sudo snap install openscad-nightly` | dated nightly w/ Manifold |
| AppImage | `files.openscad.org/snapshots/` → `chmod +x` | portable nightly |
| winget / AUR | `OpenSCAD.OpenSCAD.Nightly` / `openscad-snapshot-appimage` | nightly |

**Nightly vs stable:** 2021.01 predates Manifold and many CLI niceties (`--backend`, `--summary-file`, `--animate_sharding`). For those, **use a nightly**. Probe with `--version`/`--help`; do not assume a flag exists.

## Capability probe

```bash
help=$(openscad --help 2>&1)
grep -qi -- '--backend' <<<"$help" && BACKEND="--backend=manifold" || BACKEND=""
# always force binary STL explicitly — CLI default is ASCII:
openscad $BACKEND --export-format binstl -o out.stl in.scad
```

## Sources

- OpenSCAD User Manual — *Using OpenSCAD in a command line environment* (Wikibooks): https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment · official mirror: https://files.openscad.org/documentation/manual/Using_OpenSCAD_in_a_command_line_environment.html
- "stl export defaults to asciistl from the command line but binary from the gui" (openscad/openscad#3850): https://github.com/openscad/openscad/issues/3850
- "Manifold backend is now the default" — M. Kintel, discuss list, 2025-08-17: https://lists.openscad.org/empathy/thread/TMJEJCZINIJNYJX2YF7IDNBAPQY66KIF
- "Manifold backend is no longer experimental" (2024.09.28): https://lists.openscad.org/empathy/thread/D6KV3ZLXHLBHSITSQ5GPUZUKHURU4ABE
- Experimental Features wiki (`--enable`): https://github.com/openscad/openscad/wiki/Experimental-Features
- openscad(1) man page (`--view`, `--colorscheme`, `--camera`): https://man.archlinux.org/man/openscad.1.en · https://manpages.opensuse.org/Tumbleweed/openscad/openscad.1.en.html
- EGL headless context (issues #3857, #4613): https://github.com/openscad/openscad/issues/3857 · https://github.com/openscad/openscad/issues/4613
- openscad-playground: https://github.com/openscad/openscad-playground · openscad-wasm: https://github.com/openscad/openscad-wasm
- Downloads: https://openscad.org/downloads.html · nightly snap: https://snapcraft.io/openscad-nightly · AppImages: https://appimage.github.io/OpenSCAD/
- Debian package tracker (apt ships 2021.01): https://tracker.debian.org/openscad
