---
name: 3d-parametric-models
description: "Model parametric 3D geometry as code and edit mesh files programmatically. OpenSCAD (.scad) is the core for scripting solid models with named parameters; pair it with a Python mesh toolkit (trimesh/manifold3d) to inspect, repair, measure, scale, boolean, convert, and batch-generate STL/3MF — then optionally slice and print (Bambu Lab / OrcaSlicer). Use whenever the user wants to create, generate, design, model, script, parametrize, modify, repair, convert, or batch-produce a 3D model, part, or mesh: write or improve OpenSCAD/.scad code, turn a description into an STL or 3MF, make a part with adjustable/customizable dimensions, fix a non-watertight or non-manifold STL, scale/cut/boolean/convert an existing STL, render many variants, or design something to 3D print. Trigger even if they only say 'OpenSCAD', '.scad', 'STL', '3MF', 'edit/repair this STL', 'parametric model', 'CAD', 'make me a bracket/box/holder/knob', 'design for 3D printing', 'Bambu', 'Fusion 360', or 'Blender'. Bridges Fusion 360 and Blender."
license: MIT
compatibility: >-
  OpenSCAD 2021.01+ (a 2023+/nightly build gets the fast Manifold backend) for
  generating geometry, and Python 3.8+ with trimesh + manifold3d + numpy-stl for
  mesh inspect/repair/convert/boolean. A slicer (Bambu Studio or OrcaSlicer) is
  needed only to produce G-code and print. Bundled scripts use bash + Python 3.
  Run scripts/preflight.sh to check the toolchain and get install commands.
metadata:
  author: github.com/kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-06-15 21:30:00"
  category: 3d-modeling
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# 3D Parametric Models — script OpenSCAD, edit STL/3MF, then (optionally) print

Build and edit 3D models the way you write software: as **parametric code** you can
read, diff, version, and regenerate — not hand-pushed vertices. Two capabilities sit
at the core, and each stands on its own:

1. **Model by scripting OpenSCAD** — describe a solid with primitives + boolean ops +
   named parameters; OpenSCAD is text-first and fully declarative, which is exactly
   what an LLM is good at, and one command renders a watertight mesh.
2. **Edit meshes programmatically** — a small Python toolkit (trimesh/manifold3d)
   inspects, validates, repairs, measures, scales, booleans, arranges, and converts
   any STL/3MF/OBJ that already exists — including files you downloaded, which carry
   no parametric history.

3D **printing is a common destination, not the point**: when you want a physical
object, a slicer (Bambu Studio / OrcaSlicer) turns the model into a print — and this
skill documents that path well — but the modeling and mesh-editing work is just as
useful for visualization, asset pipelines, conversion, measurement, and CAD interop.

```
            ┌──────────── model ────────────┐        ┌──────── (optional) make ───────┐
 idea ──► parametric .scad ──► render.sh ──► .stl / .3mf ──► mesh_tool.py (validate/edit) ──► slice ──► print
          (OpenSCAD code)      (OpenSCAD CLI)                (trimesh/manifold3d)            (Bambu / Orca)
   ▲                                                              │
   └────── tune named parameters / scad_params.py batch ◄────────┘   edit ANY existing mesh, print or not
```

## Pick the right engine (don't fight the tool)

| The request… | Use | Why |
|---|---|---|
| Mechanical / functional part — bracket, box, enclosure, mount, holder, knob, gear, jig, adapter, spacer | **OpenSCAD** (`render.sh`) | Exact dimensions, named parameters, reproducible, manifold output, LLM-writable |
| "Make it adjustable / customizable / in several sizes" | **OpenSCAD + `scad_params.py batch`** | One file → many STLs from a parameter grid |
| Edit a mesh that already exists (a downloaded STL/3MF): scale, cut a hole, boolean, repair, measure, convert | **`mesh_tool.py`** (trimesh/manifold3d) | Mesh editing without a GUI; STL has no parametric history to recover |
| Organic / sculpted / artistic shape (figurine, character, terrain) | **Blender** (or a generative tool), then validate | OpenSCAD is poor at freeform; see `references/blender.md` |
| User already has it in Fusion 360 / wants assemblies, fillets, drawings | **Fusion 360**, export STEP/3MF | See `references/fusion360.md` for the bridge |

Default to **OpenSCAD** for anything dimensional. Reach for mesh tools to *modify*
existing files, and the Fusion/Blender references to *translate* a user's existing
workflow into this one.

## Facts that prevent broken work

- **Everything is millimeters. Z is up. The build plate is XY at z = 0.** STL/OpenSCAD
  are unitless and slicers assume mm — a model authored in "inches" prints 25.4× too
  small. Sit the finished part on the bed (min z = 0) so the slicer doesn't have to.
- **A printable solid must be watertight + 2-manifold with outward normals.** OpenSCAD
  CSG (union/difference/intersection) produces this *by construction*; downloaded or
  mesh-edited models may not — always run `mesh_tool.py info FILE` before slicing.
- **The OpenSCAD CLI defaults `.stl` to ASCII**, not binary (a real, long-standing quirk:
  the GUI defaults to binary, the command line to ASCII). ASCII STL is ~3× larger. The
  bundled `render.sh` forces **binary** (`--export-format binstl`); if you call `openscad`
  directly and want small files, pass `--export-format binstl` yourself.
- **Prefer 3MF over STL for Bambu.** 3MF carries mm units, color, materials, and per-object
  settings, is smaller, and is *required* for AMS multicolor. Emit STL only for legacy tools.
- **The Manifold backend is now default** in OpenSCAD nightlies (since 2025-08-17) and is
  dramatically faster for booleans; older builds (incl. 2021.01) use CGAL. `render.sh`
  auto-passes `--backend=manifold` when the build supports it. (The old `--enable=manifold`
  was removed; the selector is `--backend=manifold|cgal`.)
- **Print-fit clearances are printer-specific — never hardcode blindly.** Good FDM starting
  points: ~0.1 mm tight/press, ~0.2 mm snug, ~0.3–0.4 mm sliding/loose. Drive every mating
  gap from ONE `clearance` variable and tell the user to print a tolerance test once.
- **Design against gravity:** unsupported overhangs ≤ ~45° from vertical (modern printers
  reach ~50–70°), unsupported bridges ≤ ~10 mm, walls ≥ 0.8 mm (2× a 0.4 mm nozzle),
  horizontal holes as teardrops or ≥ 2 mm, chamfer build-plate edges to fight elephant's
  foot. Full numbers in `references/design-for-printing.md`.
- **FDM parts are anisotropic:** the Z (layer-to-layer) bond is only ~30–55% as strong as
  in-plane. Orient so loads run *along* layers, like wood grain — this often competes with
  minimizing supports, so surface the tradeoff instead of choosing silently.
- **Add `eps` overlap (≈0.01 mm) to boolean cuts/joins** so coincident faces don't create
  zero-thickness walls or z-fighting. Idiomatic OpenSCAD; see the templates.

## Preflight

Check the toolchain and get exact install commands for whatever is missing:

```bash
bash scripts/preflight.sh
```

It verifies OpenSCAD (+ Manifold backend), the Python mesh stack, and any slicer,
then prints per-OS install lines. You need OpenSCAD *or* the Python stack to start;
both for the full loop.

## Make a part in one command (scaffold)

Stand up a runnable parametric project — a Customizer-annotated `.scad`, a Makefile,
a parameter set, a batch grid, helper scripts, and a README:

```bash
python3 scripts/scaffold.py my-box           # -> ./my-box/
cd my-box && make                            # -> my-box.stl (needs openscad on PATH or $OPENSCAD)
python3 mesh_tool.py info my-box.stl         # confirm watertight + manifold + size
make 3mf            # my-box.3mf (preferred for Bambu)
make variants       # render every combo in variants.json into ./build/
make png            # preview (headless server: xvfb-run -a make png)
```

`scaffold.py my-thing --starter blank` gives a minimal stub instead of the box+lid example.

## Quick start — author, render, validate, iterate

The core inner loop without scaffolding:

**1. Write parametric `.scad`** (parameters at the top, geometry from small modules):

```scad
// shelf-bracket.scad — units mm, Z up, sits on bed
/* [Size] */
length = 60;      // [20:200]
height = 50;      // [20:200]
thick  = 4;       // [2:0.5:10]   plate thickness (>= 2x nozzle)
hole_d = 4.5;     // [3:0.5:8]    M4 clearance hole
/* [Quality] */
fn = 48;          // [16:8:128]
$fn = fn;
eps = 0.01;

module bracket() {
  difference() {
    union() {                          // two plates + a gusset
      cube([thick, height, length]);
      cube([height, thick, length]);
      // 45-degree gusset = self-supporting, no supports needed
      translate([thick, thick, 0]) rotate([0,0,45])
        cube([1, (height-thick)*1.41, length]);
    }
    // mounting holes through each plate
    for (z = [length*0.25, length*0.75])
      translate([-eps, height/2, z]) rotate([0,90,0])
        cylinder(h = thick+2*eps, d = hole_d);
  }
}
bracket();
```

**2. Render** (binary STL by default; any format by extension):

```bash
scripts/render.sh shelf-bracket.scad -o bracket.stl
scripts/render.sh shelf-bracket.scad -o bracket.3mf -D 'length=120' -D 'thick=6'   # override params
scripts/render.sh shelf-bracket.scad -o preview.png --png --view-all               # look at it
```

**3. Validate before you ever slice:**

```bash
python3 scripts/mesh_tool.py info bracket.stl
#   size (mm)   4.0 x 50.0 x 60.0   watertight True   manifold True  => PRINTABLE
```

**4. Iterate.** Change a parameter, re-render, re-validate. To explore a design
space, list the knobs and batch-render a grid (see next section).

> Always *look at the render* (`--png`) before declaring a part done — geometry that
> validates can still be the wrong shape. Read the PNG back and check it matches intent.

## Writing good parametric OpenSCAD

This is the heart of the skill. The difference between throwaway and reusable code:

- **All tunables are named top-level variables, grouped with Customizer comments**
  (`/* [Group] */`, `value; // [min:max]` slider, `// [a,b,c]` dropdown). This makes the
  model adjustable in the OpenSCAD Customizer, on MakerWorld/Thingiverse, and via `-D` /
  parameter sets. List them with `scad_params.py list FILE.scad`.
- **Build from small modules**, not one giant nested expression. Name sub-shapes.
- **One `clearance` variable** drives every mating fit; one `wall`/`floor`; one `$fn`/`fn`.
- **Watch the immutable-variable gotcha:** OpenSCAD variables are set at compile time and
  *last assignment wins for the whole scope* — they are not reassignable step-by-step. Use
  `let()` and parameters, not "x = x + 1".
- **Keep `$fn` sane:** 32 draft, 64 good, 128 smooth. High `$fn` on every circle explodes
  triangle count and render time; raise it only where curvature shows.
- **Reach for BOSL2** (the big community library) for threads, gears, rounding, attachments,
  and distributors instead of reinventing them — `include <BOSL2/std.scad>`. Note BOSL2 needs
  `include`, so it works on MakerWorld but **not** in the Thingiverse Customizer.

Refactoring/improving an existing `.scad`: pull magic numbers up into named, annotated
parameters; replace copy-pasted geometry with a module + a `for` loop; add `eps` to cuts;
switch a slow `minkowski()` rounding for `offset()`/BOSL2 rounding; verify the result still
renders and stays watertight. Deep language reference (every primitive, transform, loop,
list comprehension, special variable, and the library ecosystem) is in
**`references/openscad-language.md`**; the full command line (export formats, parameter
sets, animation, headless PNG, Makefiles, batch) is in **`references/openscad-cli.md`**.

## Generate and modify meshes programmatically

**Many variants from one file** — define a grid or explicit list and batch-render:

```bash
python3 scripts/scad_params.py list shelf-bracket.scad           # see the knobs
echo '{"format":"stl","grid":{"length":[60,90,120],"thick":[4,6]}}' > matrix.json
python3 scripts/scad_params.py batch shelf-bracket.scad matrix.json -d out/   # 6 STLs
```

**Edit a mesh that already exists** (downloaded STL/3MF, or another tool's output) —
`mesh_tool.py` is the no-GUI workhorse (trimesh + manifold3d):

```bash
python3 scripts/mesh_tool.py info thing.stl                       # watertight? size? volume?
python3 scripts/mesh_tool.py repair thing.stl -o fixed.stl        # fill holes, fix normals
python3 scripts/mesh_tool.py scale thing.stl -o big.stl --to-x 120     # resize so X = 120 mm
python3 scripts/mesh_tool.py scale thing.stl -o fit.stl --fit 256x256x256   # fit a build plate
python3 scripts/mesh_tool.py boolean difference base.stl cutter.stl -o cut.stl  # CSG on meshes
python3 scripts/mesh_tool.py convert thing.stl thing.3mf          # STL -> 3MF (mm units kept)
python3 scripts/mesh_tool.py arrange a.stl b.stl c.stl -o plate.stl     # lay out on the bed
```

When you *can*, regenerate from parametric source instead of editing the mesh — mesh edits
are destructive and can't recover lost intent. Format choice, repair strategy, and the
trimesh/manifold3d/numpy-stl APIs are detailed in **`references/mesh-and-stl.md`**.

## Design so it prints the first time

Apply these while *authoring*, not as an afterthought (numbers for FDM, 0.4 mm nozzle):

- **Walls ≥ 0.8 mm** (ideally multiples of 0.4: 0.8/1.2/1.6). **Overhangs ≤ ~45°** or add
  supports / reorient. **Bridges ≤ ~10 mm.** **Min feature ≈ 0.4 mm.**
- **Horizontal holes:** teardrop profile or ≥ 2 mm (a bare horizontal cylinder sags at the
  top). **Vertical holes print undersized** — add ~0.1–0.25 mm or model oversize.
- **Chamfer build-plate edges ~0.4–0.6 mm** (or use slicer elephant-foot compensation ~0.2 mm).
- **Text:** embossed ≥ 1.0 mm wide × ≥ 0.5 mm tall, bold sans-serif; engraved ≥ 0.5 mm wide.
- **Fits:** ~0.1 press / ~0.2 snug / ~0.3–0.4 sliding — *tune per printer*.
- **Threads:** model only ≥ M5 (or use BOSL2 threads, tuned via `$slop`); below that prefer
  heat-set inserts (CNC Kitchen pilot holes: M3≈4.0, M4≈5.6, M5≈6.4, M6≈8.0 mm) or tapped holes.

The complete, sourced rule set (with tolerances, supports strategy, anisotropy, shrinkage by
material, living hinges, print-in-place clearances) is in **`references/design-for-printing.md`**.

## Slice and print on Bambu Lab

Slicing is mostly a **GUI** step — there is no robust headless "STL→print" pipeline; treat
that as the expected workflow:

1. Export **3MF** (`render.sh model.scad -o model.3mf`) and open it in **Bambu Studio**
   (official) or **OrcaSlicer** (community fork with excellent Bambu profiles).
2. Pick the **printer** (X1C / P1S / A1 / A1 mini / H2D), a **filament** profile (PLA 0.20 mm
   is the safe default; PETG tougher; ABS/ASA need an enclosure; TPU flexible/slow), and a
   **process/quality** profile (layer height 0.08–0.28 mm for a 0.4 nozzle).
3. Orient for strength + minimal supports; use **tree/organic supports** with a support
   interface for easier removal; paint supports manually where auto over/under-does it.
4. For multicolor, assign filaments per object/face and use the **AMS** — this needs 3MF.
5. Slice → preview layers → send over LAN or cloud.

A limited command line exists (`OrcaSlicer --slice --export-3mf` → `output.gcode.3mf`;
BambuStudio CLI with hyphenated `--load-settings`), with caveats. Profiles, filament temps,
calibration (flow rate vs pressure-advance), the printer lineup, and the exact CLI flags are
in **`references/bambu-lab.md`**.

## Coming from Fusion 360 or Blender

- **Fusion 360 user?** Your *User Parameters* (Modify → Change Parameters) are exactly
  OpenSCAD's top-level variables; sketch+extrude maps to 2D `square/circle/polygon` +
  `linear_extrude`/`rotate_extrude`; the timeline maps to reading the script top-to-bottom.
  Export **STEP** to keep editability, **3MF/STL** to print. Mapping + the Fusion Python API
  in **`references/fusion360.md`**.
- **Blender user?** Set units to mm (1 BU = 1 mm), enable the **3D-Print Toolbox** add-on to
  check manifold/wall/overhang and *Make Manifold*, apply Modifiers (Boolean/Mirror/Array/
  Solidify) before export, and use **Geometry Nodes** for true procedural/parametric work.
  Blender wins for organic shapes; OpenSCAD wins for exact, reproducible engineering parts.
  Bridge + a headless `bpy` export example in **`references/blender.md`**.

## Scripts

| Script | Does |
|---|---|
| `scripts/preflight.sh` | Check OpenSCAD + Python mesh stack + slicer; print install commands |
| `scripts/render.sh` | Headless OpenSCAD render: `.scad` → STL/3MF/PNG/… with `-D` overrides, `-p`/`-P` sets, Manifold auto-detect, binary-STL default |
| `scripts/mesh_tool.py` | Inspect / validate / repair / measure / convert / scale / transform / boolean / arrange existing meshes (trimesh + manifold3d) |
| `scripts/scad_params.py` | `list` Customizer params, emit a parameter-set `json`, and `batch`-render a grid/list of variants |
| `scripts/scaffold.py` | Generate a runnable parametric project (`.scad` + Makefile + params + variants + README) |

All scripts print usage with `-h`. The Python tools need `pip install "trimesh[easy]"
manifold3d numpy-stl`; `render.sh`/scaffold need OpenSCAD on PATH or `$OPENSCAD`.

## References

Load the deep dive you need — each is self-contained:

| File | Read when you need… |
|---|---|
| `references/openscad-language.md` | The full language: primitives, transforms, CSG, modules/functions, loops, list comprehensions, special variables, refactoring, and the library ecosystem (BOSL2, etc.) |
| `references/openscad-cli.md` | Command-line mastery: export formats, parameter sets, animation, headless PNG/xvfb, dependency files, Makefiles, batch generation |
| `references/mesh-and-stl.md` | Programmatic mesh work in Python (trimesh / manifold3d / numpy-stl / pymeshlab), STL vs 3MF vs STEP, repair, conversion, and CadQuery/build123d code-CAD |
| `references/design-for-printing.md` | The sourced, numeric DFAM rule set: walls, overhangs, bridges, holes, tolerances, threads, supports, orientation/anisotropy, shrinkage |
| `references/bambu-lab.md` | Bambu Studio / OrcaSlicer workflow, printer lineup, filament profiles & temps, supports, AMS multicolor, calibration, and CLI slicing |
| `references/fusion360.md` | Fusion 360 → code-first mapping, export settings, mesh↔BRep limits, and the Fusion Python API |
| `references/blender.md` | Blender for 3D printing: units, 3D-Print Toolbox, modifiers, Geometry Nodes, headless `bpy` export, and when to use it vs OpenSCAD |
| `references/openscad-for-llms.md` | How an LLM writes print-ready OpenSCAD well (the mistakes models make + fixes), and how this code-first path compares to text-to-CAD / CadQuery / Zoo — read before generating to avoid naive output |

Templates live in `assets/templates/` (`parametric-box.scad` is a fully-worked, print-ready
example with a friction-fit lid; `Makefile.tmpl` is the build file the scaffolder uses).
