# Blender for 3D Printing & as a Bridge to OpenSCAD

**Covers:** how to use Blender (4.x / current) to produce printable STL/3MF meshes —
scene units, the 3D-Print Toolbox, modifiers-as-quasi-parametric, Geometry Nodes,
mesh hygiene, the 4.x STL exporter, and headless `bpy` scripting — plus when to stay
in Blender vs. move a part to OpenSCAD (and how to move geometry between them).
**Read this when:** the user already knows Blender and wants a printing workflow, or
is deciding between sculpt/visual modeling (Blender) and code-first parametric CAD
(OpenSCAD). For the code-first path itself, see the main skill + OpenSCAD references.

## Contents
1. [Setup: scene units and the 1-unit-=-1-mm gotcha](#1-setup-scene-units-and-the-1-unit--1-mm-gotcha)
2. [The 3D-Print Toolbox add-on](#2-the-3d-print-toolbox-add-on)
3. [Destructive vs non-destructive: the modifier stack](#3-destructive-vs-non-destructive-the-modifier-stack)
4. [Geometry Nodes: Blender's real parametric system](#4-geometry-nodes-blenders-real-parametric-system)
5. [Making a mesh printable (manifold hygiene)](#5-making-a-mesh-printable-manifold-hygiene)
6. [Export: STL & 3MF, getting units right](#6-export-stl--3mf-getting-units-right)
7. [Headless bpy scripting](#7-headless-bpy-scripting)
8. [Decision: Blender vs OpenSCAD, and moving between them](#8-decision-blender-vs-openscad-and-moving-between-them)
9. [Sources](#sources)

---

## 1. Setup: scene units and the 1-unit-=-1-mm gotcha

Blender is dimensionless internally; "Blender Units" (BU) become millimeters only by
convention plus correct export. Set up first in **Properties ▸ Scene ▸ Units**:

- **Unit System** — `Metric` (or `None`). Default is Metric.
- **Length** — `Millimeters` so the UI reads in mm (default `Adaptive` shows
  `m`/`cm`/`mm` by magnitude). Display-only; does not rescale geometry.
- **Unit Scale** — leave at `1.0` for printing. Manual caveat: it "only influences the
  values displayed in the user interface and **not** how things behave internally." It
  is a UI multiplier, not a geometry scale.

**The classic gotcha.** Blender's internal length unit is the **meter**: one BU = 1 m.
A `2 mm` cube is `0.002` BU on the axes. STL stores raw numbers with no units. If you
model "2" thinking millimeters but export without applying scene units, the slicer reads
`2 meters` = **2000 mm** — a 1000× error. Two correct ways to land at real millimeters:

1. **Model in meters, export with Scene Unit on.** Keep Length = `Millimeters` so the
   UI shows mm; the STL exporter's **Scene Unit** option applies the scene's unit scale
   so a `2 mm`-labeled edge writes `2.0` to the file. This is the clean path.
2. **Model at 1 BU = 1 mm and export with Scene Unit off, Scale = 1.** Treat numbers
   as millimeters directly; the STL exporter writes them verbatim. Simple, but the
   viewport's metric readouts will be wrong (it thinks meters).

Pick one convention and never mix them. Most printing errors that are "off by 1000×"
(or 0.001×) are a Scene-Unit / Unit-Scale mismatch between modeling and export.

---

## 2. The 3D-Print Toolbox add-on

Blender's official mesh-validation tool for printing. Author: Campbell Barton;
internal name `object_print3d_utils` (panel label "3D-Print").

**Enable it (changed by version):**
- **Blender ≤ 4.1** — bundled add-on. `Edit ▸ Preferences ▸ Add-ons`, search
  `3D Print Toolbox` (category Mesh), tick to enable.
- **Blender 4.2+** — shipped as a **bundled extension**. If it is not already in the
  Add-ons list, go to `Edit ▸ Preferences ▸ Get Extensions`, search
  `3D Print Toolbox`, Install, then it appears under Add-ons. Same panel afterward.

**Where it lives:** `3D Viewport ▸ Sidebar` (press `N`) ▸ **3D-Print** tab, shown when
a mesh object is selected. Run individual checks or **Check All**; in Edit Mode the
**Result** field's bad geometry is auto-selected so you can `View Selected` (`/` on
numpad, or `\`) to zoom to it.

**Analyze ▸ Statistics** — `Volume` and `Area` buttons compute and display mesh volume
/ surface area (volume is also the basis for Scale-to-Volume below).

**Analyze ▸ Checks** (official meanings):
- **Solid** — checks for **non-manifold edges** (an edge must border exactly 2 faces;
  1 = hole, >2 = non-manifold) and **bad-contiguous edges** (a face whose normal points
  opposite its neighbors). The single most important check for printing.
- **Intersections** — self-intersecting / overlapping faces (e.g. two cubes poked
  together). Often fixable with a Boolean. Some slicers tolerate this.
- **Degenerate** — faces/edges with **zero area or length** (e.g. a face scaled to a
  point but not merged). Fix with `Merge ▸ By Distance`.
- **Distorted** — non-flat quads/ngons that may triangulate unpredictably on export.
- **Thickness** — faces forming geometry thinner than a threshold ("Thin") that a
  slicer might drop. Threshold is set in the panel.
- **Edge Sharp** — sharp edges bounding thin slivers a slicer may miss.
- **Overhang** — faces steeper than a threshold angle that need support to print.
- **Check All** — runs all of the above at once.

**Clean Up:**
- **Distorted** — triangulates faces flagged Distorted.
- **Make Manifold** — best-effort auto-repair: fixes bad normals, fills holes, removes
  stray/empty edges and faces. Run it, then re-run **Solid** — it is not guaranteed to
  produce a perfect manifold, so verify.

**Transform ▸ Scale To** — `Volume` scales the object to an exact target volume;
`Bounds` scales so the largest bounding-box axis equals a target size. Handy for hitting
a real-world mm dimension before export.

**Export** — shortcut buttons to Blender's standard `File ▸ Export` operators
(STL/PLY/OBJ). The toolbox itself does **not** implement a 3MF exporter — use a
separate 3MF extension (see §6).

---

## 3. Destructive vs non-destructive: the modifier stack

Blender has two layers of editing. Direct edits in Edit Mode (extrude, bevel, merge)
are **destructive** — they bake into the mesh immediately. **Modifiers** are
**non-destructive**: an ordered stack evaluated on top of the base mesh that you can
re-order, tweak, or remove at any time. The stack is the closest thing vanilla Blender
modeling has to a parameter history — but the parameters are not named or scriptable
the way OpenSCAD variables are; they are sliders on each modifier.

Modifiers most relevant to printing (Properties ▸ Modifiers, wrench icon):
- **Boolean** — union / difference / intersect against another object or collection.
  **Solver matters:** `Exact` is robust and can clean self-intersections (with an empty
  source it just removes interior self-intersecting geometry); the `Manifold` solver is
  fastest but only works on already-manifold inputs. Prefer **Exact** for print parts.
- **Mirror** — symmetry across an axis; halves your modeling work, stays live.
- **Array** — repeat copies along an offset (linear/radial-with-empty); parametric
  counts.
- **Bevel** — round/chamfer edges (set by edge selection or angle); print-friendly fillets.
- **Solidify** — give a surface real wall thickness (turn a non-manifold shell into a
  printable solid).
- **Subdivision Surface** — smooth, denser organic geometry.
- **Screw** — lathe a profile around an axis (threads, bottles, knobs).
- **Remesh** — rebuild topology into a uniform, usually watertight manifold (great for
  cleaning up booleaned or sculpted meshes before printing).

**You must apply modifiers as part of export.** A modifier is live preview geometry;
the raw mesh data still has none of it. Either bake the stack first
(`Ctrl+A ▸ Visual Geometry to Mesh`, or `Object ▸ Apply ▸ Visual Geometry to Mesh`, or
per-modifier `Ctrl+A` in the dropdown — note applying Boolean etc. may require Object
Mode and a single user), **or** rely on the STL exporter's **Apply Modifiers** option
(on by default; see §6), which exports the evaluated mesh. If you neither apply nor
enable Apply Modifiers, you export the un-modified base mesh.

---

## 4. Geometry Nodes: Blender's real parametric system

**Geometry Nodes (GN)** is Blender's genuine procedural/parametric system and the
closest analog to parametric CAD. It is a node graph applied as a modifier; geometry
flows through nodes that create, transform, instance, boolean, and rewrite it. Crucially
you can **expose inputs** on the node group (sizes, counts, angles, toggles) that then
appear as editable fields on the modifier panel and are **driveable / scriptable** —
this is the named-parameter behavior OpenSCAD users expect, inside Blender.

When GN is the right tool for printing:
- **Arrays / scatter** — grids, radial patterns, distribute-on-surface (vents, perfs,
  lattices) controlled by numeric inputs.
- **Parametric detailing** — fillets, insets, repeated features driven by exposed values.
- **Procedural solids** — build a whole part from node math so changing one input
  regenerates it, like a `.scad` recompile.

Caveats for print output: GN can easily emit instanced or non-manifold geometry. Use
**Realize Instances** before export, and validate with the 3D-Print Toolbox — a
beautiful GN preview is not automatically watertight. GN is powerful but the graph is
visual, not text — it does not version-diff or read in a code review the way `.scad`
does (see §8).

---

## 5. Making a mesh printable (manifold hygiene)

A printable mesh is **watertight** (closed surface, every edge shared by exactly 2
faces) with **consistent outward normals** and no zero-area junk. Cleanup pass in Edit
Mode (`Tab`), all selected (`A`):

- **Recalculate Normals Outside** — `Shift+N` (`Mesh ▸ Normals ▸ Recalculate Outside`).
  Flipped faces read inside-out to slicers; the face-orientation overlay shows blue =
  outward, red = inward.
- **Merge by Distance** ("remove doubles") — `Mesh ▸ Merge ▸ By Distance` (`M`). Welds
  coincident verts that leave split edges = holes. Fixes most Degenerate / non-manifold
  cases from duplicated or imported geometry.
- **Fill holes** — select non-manifold boundary (`Select ▸ All by Trait ▸ Non Manifold`,
  `Shift+Ctrl+Alt+M`), then `Mesh ▸ Clean Up ▸ Fill Holes` (or `F` / grid-fill).
- **Avoid non-manifold geometry** — no internal faces, no faces shared by >2 faces, no
  loose verts/edges (`Mesh ▸ Clean Up ▸ Delete Loose`). Give zero-thickness shells real
  thickness with **Solidify** before export.
- **Remesh / Make Manifold** — for stubborn cases, a Remesh modifier (Voxel mode) or the
  toolbox's **Make Manifold** rebuilds a solid; expect some detail loss.

Final step: run **3D-Print Toolbox ▸ Check All** and drive non-manifold edges to 0
before exporting.

---

## 6. Export: STL & 3MF, getting units right

**STL** — `File ▸ Export ▸ Stl (.stl)`. The built-in 4.x exporter options:
- **Format: ASCII** — ASCII if on, binary if off (binary is smaller/faster; default).
- **Batch** — export each object to its own STL file.
- **Include ▸ Selection Only** — export only selected objects (instancer-selected
  instances count as selected).
- **Transform ▸ Scale** — uniform scale factor on export.
- **Transform ▸ Scene Unit** — "Apply current scene's unit (as defined by unit scale)
  to exported data." This is the switch that makes mm-labeled geometry export as mm
  (see §1). Turn **on** when you modeled in real meters/mm via scene units; leave **off**
  if you modeled at literal 1 BU = 1 mm.
- **Transform ▸ Forward / Up** — axis conversion. Blender is **Y Forward, Z Up**. Most
  slicers accept Blender's default; only change if the target app needs a different axis.
- **Geometry ▸ Apply Modifiers** — exports the **evaluated** mesh (after the modifier
  stack). On by default; this is what bakes your Boolean/Mirror/Array etc. into the STL.

> **Version note (STL is built-in again):** In Blender **3.x** the legacy Python STL
> add-on was being phased out and STL moved to a **C++ built-in / extension**; in
> **4.x it is a built-in importer/exporter** at the menu path above. Old tutorials that
> say "enable the STL add-on" are stale on 4.x.

**3MF** — there is **no** built-in 3MF exporter in vanilla Blender. Install a **3MF
add-on/extension** (the community `io_mesh_3mf` / "3MF format" add-on, available via
`Get Extensions`), then export via `File ▸ Export ▸ 3MF`. 3MF is preferred for modern
slicers (Bambu Studio / OrcaSlicer) because it carries units, multiple objects,
transforms, and metadata — STL carries none of that. The 3D-Print Toolbox does not add
3MF export.

**Always verify after export:** open the STL/3MF in the slicer (or `mesh_tool.py info`
from this skill) and confirm the bounding box is the size you intended in **mm**. A box
that should be 20 mm reading as 20000 mm or 0.02 mm means a Scene-Unit/Scale mistake.

---

## 7. Headless bpy scripting

Run Blender with no GUI to generate/process meshes in CI or batch:

```bash
blender --background --python script.py
# short flags: blender -b -P script.py
# pass args to the script after a bare --:
blender -b -P script.py -- --size 20 --out part.stl
```

`--background` (`-b`) runs GUI-less; `--python` (`-P`) runs the given file. Inside the
script read args after `--` via `sys.argv[sys.argv.index("--") + 1:]`. Flag **order
matters** on the CLI — arguments execute left to right.

**Operator name — the high-risk fact.** Blender **4.x** uses the new C++ STL I/O
operators. The Python 3.x operators were **removed**:

| Action | Blender 3.x (legacy, gone in 4.x) | Blender 4.x / current (use this) |
| ------ | --------------------------------- | -------------------------------- |
| Export STL | `bpy.ops.export_mesh.stl(...)` | `bpy.ops.wm.stl_export(filepath=...)` |
| Import STL | `bpy.ops.import_mesh.stl(...)` | `bpy.ops.wm.stl_import(filepath=...)` |

Current `bpy.ops.wm.stl_export` signature (key params; all keyword-only):
`filepath`, `ascii_format=False`, `use_batch=False`, `export_selected_objects=False`,
`collection=''`, `global_scale=1.0`, `use_scene_unit=False`, `forward_axis='Y'`,
`up_axis='Z'`, `apply_modifiers=True`. Note it is **`export_selected_objects`**, not
`use_selection`, and **`use_scene_unit`** mirrors the UI Scene-Unit toggle (default
`False`).

Minimal, correct, runnable example — make a cube sized in mm, apply a modifier, export:

```python
# blender --background --python make_cube.py
import bpy

# Start clean (also: bpy.ops.wm.read_factory_settings(use_empty=True))
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Scene units: metric, mm, unit scale 1.0  (model in meters, export with scene unit)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene.unit_settings.length_unit = 'MILLIMETERS'

# 20 mm cube  ->  size in meters = 0.020
bpy.ops.mesh.primitive_cube_add(size=0.020, location=(0, 0, 0.010))
cube = bpy.context.active_object

# Non-destructive bevel modifier (named on the object, applied at export)
bev = cube.modifiers.new(name="Bevel", type='BEVEL')
bev.width = 0.001          # 1 mm
bev.segments = 3

# Export STL (4.x operator). Scene Unit ON so 0.020 BU -> 20 mm in the file.
bpy.ops.wm.stl_export(
    filepath="/tmp/cube.stl",
    apply_modifiers=True,          # bakes the bevel
    use_scene_unit=True,
    export_selected_objects=False, # export everything
    ascii_format=False,            # binary
)
print("exported /tmp/cube.stl")
```

**bmesh for procedural mesh building.** For mesh construction beyond `bpy.ops`
primitives, use the `bmesh` module: build/modify topology in memory, then write to a
mesh datablock. Sketch:

```python
import bpy, bmesh
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=0.020)
# bmesh.ops.* for inset, bevel, spin, extrude, recalc_face_normals, remove_doubles ...
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)   # normals outside
me = bpy.data.meshes.new("Part")
bm.to_mesh(me); bm.free()
obj = bpy.data.objects.new("Part", me)
bpy.context.collection.objects.link(obj)
```

`bmesh` gives explicit, scriptable control over verts/edges/faces (and operators like
`remove_doubles`, `recalc_face_normals`, `triangulate`) — the right layer for
generating printable geometry headlessly.

---

## 8. Decision: Blender vs OpenSCAD, and moving between them

Both make printable meshes; they are good at opposite things. Use the request shape to
pick — do not force one tool to be the other.

**Reach for Blender when the part is shape-led / visual:**
- Organic, sculpted, or artistic forms (figurines, terrain, jewelry, ergonomic grips) —
  Sculpt Mode + dyntopo + Multires have no OpenSCAD equivalent.
- Complex deformation (lattice, warp, cloth/soft-body sim baked to mesh).
- Retopology / cleanup of scanned or imported meshes.
- Fast visual iteration judged by eye, not by dimension; subdivision-surface smoothness.

**Reach for OpenSCAD / code when the part is dimension-led / engineering:**
- Exact dimensions and tolerances (bolt holes, snap-fits, mating parts) — type the
  number, get the number; no drift from a stray vertex move.
- **Named, reproducible parameters** and `Customizer` ranges; regenerate N variants
  deterministically (`scad_params.py` in this skill).
- **Version control** — `.scad` is plain text that diffs and code-reviews cleanly; a
  `.blend` is opaque binary and a Geometry-Nodes graph does not diff meaningfully.
- Guaranteed clean CSG — OpenSCAD's boolean tree (esp. the Manifold backend) avoids the
  accidental non-manifold geometry hand-modeling and Blender booleans can introduce.

Rule of thumb: **shape you feel → Blender; dimensions you specify → OpenSCAD.** Many
real parts are a hybrid: sculpt the organic body in Blender, define the precise
mounting/interface features in OpenSCAD, and boolean them.

**Moving geometry between them:**
- **Blender → OpenSCAD.** Export STL or OBJ from Blender (§6), then in OpenSCAD bring it
  in with `import("part.stl");` (handles STL/OFF/OBJ/3MF/AMF; `surface()` is for
  heightmap DAT/PNG, not solids). Imported meshes are dumb triangle soups, **not**
  parametric — you can only translate/rotate/scale them and boolean against generated
  solids. **The mesh must be clean (manifold) first** or booleans against it fail or
  produce holes — run the 3D-Print Toolbox in Blender before exporting. Keep the
  parametric logic native in `.scad`; treat the import as a fixed sub-part.
- **OpenSCAD → Blender.** Render/export STL (or 3MF) from OpenSCAD, then
  `bpy.ops.wm.stl_import(filepath=...)` or `File ▸ Import ▸ Stl`. Use this to sculpt,
  add organic detail, or render/marketing-shot a precise part. Once in Blender it is a
  plain mesh — the OpenSCAD parameters do not survive the round trip, so keep `.scad`
  as the source of truth and re-import after parameter changes.

Net: keep the **parametric source** in whichever tool owns the part's intent, export
clean STL/OBJ/3MF as the interchange, and validate manifold-ness on every hop.

---

## Sources

- Blender Manual — Scene Properties (Units, Unit System, Unit Scale, metric length table):
  https://docs.blender.org/manual/en/latest/scene_layout/scene/properties.html
- Blender Manual — 3D Print Toolbox (checks, Clean Up, Make Manifold, Scale To):
  https://docs.blender.org/manual/en/4.1/addons/mesh/3d_print_toolbox.html
- 3D Print Toolbox extension (4.2+ install via Get Extensions; Analyze/Edit/Export):
  https://extensions.blender.org/add-ons/print3d-toolbox/
- Blender Manual — STL import/export (menu path, options: ASCII, Batch, Selection Only,
  Scale, Scene Unit, Forward/Up, Apply Modifiers):
  https://docs.blender.org/manual/en/latest/files/import_export/stl.html
- Blender Manual — Boolean Modifier (Exact vs Manifold solver):
  https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/booleans.html
- Blender Python API — `bpy.ops.wm.stl_export` / `stl_import` (exact 4.x signatures):
  https://docs.blender.org/api/current/bpy.ops.wm.html
- Blender Manual — Command Line Arguments (`--background`, `--python`):
  https://docs.blender.org/manual/en/latest/advanced/command_line/arguments.html
- Blender `bmesh` module reference:
  https://docs.blender.org/api/current/bmesh.html
- Blender Manual — Geometry Nodes (procedural geometry, exposed group inputs):
  https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html
- OpenSCAD User Manual — Import/Export (`import()`, `surface()`, clean STL requirement):
  https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/STL_Import_and_Export
