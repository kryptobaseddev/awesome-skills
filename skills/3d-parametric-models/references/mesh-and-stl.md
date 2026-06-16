# Mesh & STL Manipulation in Python (No GUI)

*Programmatic create / inspect / repair / measure / transform / convert of 3D mesh & CAD files (STL, 3MF, OBJ, PLY, STEP) entirely in code. Read this when you are editing meshes or producing printable output and need the exact library, API call, or recipe — `scripts/mesh_tool.py` already wraps trimesh + manifold3d for the common tasks below; reach for it first, drop to raw API only when it can't.*

## Contents

- [0. Decision table](#0-decision-table)
- [1. Versions (pinned)](#1-versions-pinned)
- [2. Format reality check — STL vs 3MF vs STEP vs OBJ vs PLY](#2-format-reality-check--stl-vs-3mf-vs-step-vs-obj-vs-ply)
- [3. trimesh — the core library](#3-trimesh--the-core-library)
- [4. manifold3d — robust CSG / boolean engine](#4-manifold3d--robust-csg--boolean-engine)
- [5. numpy-stl — lightweight STL-only fallback](#5-numpy-stl--lightweight-stl-only-fallback)
- [6. pymeshlab — heavy repair / remesh / decimate](#6-pymeshlab--heavy-repair--remesh--decimate)
- [7. build123d / cadquery — when you need STEP](#7-build123d--cadquery--when-you-need-step)
- [8. Cookbook — copy-paste recipes](#8-cookbook--copy-paste-recipes)
- [9. Gotchas checklist](#9-gotchas-checklist)
- [Sources](#sources)

---

## 0. Decision table

| You want to... | Use | Why |
|---|---|---|
| Load/export/inspect/transform/measure/repair/convert a mesh | **trimesh** | Swiss-army knife. Reads STL/3MF/OBJ/PLY/GLB+. |
| Boolean union/diff/intersect, *guaranteed watertight* | **manifold3d** (direct, or trimesh's engine) | Robust, fast CSG with manifold guarantee. |
| Dead-simple STL read/write/translate/rotate, minimal deps | **numpy-stl** (`stl`) | Lightweight; STL-only; no repair/boolean. |
| Heavy repair / remesh / decimate / fill complex holes | **pymeshlab** | MeshLab's full filter suite. |
| Parametric *solid* CAD → **STEP** (B-rep) + STL | **build123d** or **cadquery** | True OpenCascade kernel, not triangles. |

```bash
pip install "trimesh[easy]" manifold3d numpy-stl     # core stack
pip install pymeshlab                                 # optional, heavy
pip install build123d                                 # or: pip install cadquery
```

`trimesh[easy]` pulls `networkx`, `scipy`, `shapely`, `lxml`, `manifold3d`, … Installing `manifold3d` makes `mesh.boolean` / `trimesh.boolean.*` work with **no Blender on PATH** (the recommended boolean backend).

**For routine tasks, use the bundled wrapper instead of writing API code:**

```bash
python scripts/mesh_tool.py info|validate|measure   part.stl     # validate: exit 1 if not printable
python scripts/mesh_tool.py repair|convert          in out       # repair -> watertight; convert -> by extension
python scripts/mesh_tool.py scale     in out --target-mm 100
python scripts/mesh_tool.py boolean   a.stl b.stl out.stl --op difference
python scripts/mesh_tool.py arrange   out.3mf a.stl b.stl c.stl  # lay parts on plate
```

---

## 1. Versions (pinned)

| Package | Import | Version | Notes |
|---|---|---|---|
| trimesh | `trimesh` | **4.12.2** | Pure-Python core; many optional deps. |
| manifold3d | `manifold3d` | **3.5.1** | Binary wheels. **Major API break after 2.x** (§4). |
| numpy-stl | `stl` | **3.2.0** | Python ≥3.9. STL only. |
| pymeshlab | `pymeshlab` | **2025.7** | Year.month versioning; large binary wheel. |
| cadquery | `cadquery` | **2.7.0** | Python ≥3.10. OpenCascade (OCP) kernel. |
| build123d | `build123d` | **0.10.0** | Same OCP kernel, Pythonic API. |

**Always pin.** trimesh's API is mostly stable; manifold3d's is not across majors. No py3.14 wheels for cadquery/build123d yet.

---

## 2. Format reality check — STL vs 3MF vs STEP vs OBJ vs PLY

Choosing the wrong target silently loses units, color, or solidity. The single most important conceptual section.

- **STL (.stl) — a bag of triangles.** Unordered triangles (3 verts + a normal each); geometry only. Encodings: **ASCII** (large, human-readable) and **binary** (default; 80-byte header + uint32 count + 50 bytes/triangle). **No units** — dimensionless; convention is **1 unit = 1 mm** but nothing states it (mm-vs-inch = 25.4× error is the #1 footgun). No color/materials/metadata/named-objects. Vertices arrive unwelded (repeated per triangle). Fine as a final printable artifact; lossy for interchange.
- **3MF (.3mf) — modern print format (Bambu/Prusa/Cura prefer it).** ZIP of XML (OPC); ISO/ASTM spec. **Has units** via `<model unit="millimeter">` (also micron/cm/inch/foot/meter). Carries color, materials, multiple named objects, transforms, metadata, vendor extensions. *Standard* 3MF opens everywhere; *vendor-extended* Bambu 3MF adds data other slicers ignore. trimesh writes **standard** 3MF → portable. Preferred modern target; keeps multiple bodies + units on one plate.
- **STEP (.step / .stp) — B-rep CAD exchange (ISO 10303).** Exact analytic surfaces (planes, cylinders, NURBS) + topology — NOT triangles. Real units, assemblies, colors, product structure. Editable in FreeCAD/Fusion/SolidWorks; no faceting error on round-trip. **You cannot produce STEP from a mesh library** — need a CAD kernel (build123d/cadquery). mesh→STEP is a hard lossy reconstruction; avoid. Use when the consumer is CAD or you want parametric solids.
- **OBJ (.obj)** — ASCII; verts/faces/normals/UVs + material via sidecar `.mtl`. No units. Textured/visual assets.
- **PLY (.ply)** — ASCII or binary; arbitrary per-vertex/per-face attributes (color, normals, quality). Scans/colored meshes. No units.

**Mental model:** STL = triangles · OBJ = +texture · PLY = +attributes · 3MF = +units +color +multi-object · STEP = exact solids + units.

---

## 3. trimesh — the core library

### 3.1 Load & export (conversion is "free")

trimesh infers format from extension; round-tripping `load`/`export` *is* conversion.

```python
import trimesh
mesh = trimesh.load("part.stl")            # -> Trimesh, or Scene if multi-body
mesh = trimesh.load_mesh("part.stl")       # always returns a single Trimesh-like geometry
mesh.export("part.3mf")                    # extension drives writer (.obj/.ply/.glb/.3mf...); 3MF -> unit="mm" (§3.8)
ply_bytes = mesh.export(file_type="ply")   # to bytes/string, no disk
```

**Gotcha:** `load()` on a multi-body/named file may return a `trimesh.Scene`, not `Trimesh`. Always branch:

```python
if isinstance(mesh, trimesh.Scene):
    mesh = mesh.to_geometry()              # == trimesh.util.concatenate(tuple(mesh.geometry.values()))
```

### 3.2 Inspect / measure

```python
m = trimesh.load_mesh("part.stl")
m.is_watertight          # closed: every edge shared by exactly 2 faces
m.is_winding_consistent  # face windings agree (needed for valid volume/normals)
m.euler_number           # topology: 2 for a simple closed solid (genus 0)
m.volume                 # mm^3 if STL in mm; ONLY meaningful if watertight
m.area                   # surface area
m.bounds                 # (2,3) [[minxyz],[maxxyz]];  m.extents -> (3,) bbox size
m.center_mass            # solid centroid (needs watertight);  m.centroid -> area centroid (always defined)
m.bounding_box.volume; m.bounding_box_oriented.primitive.extents   # AABB vol; tight OBB dims
len(m.vertices), len(m.faces)
```

**Volume is trustworthy only when `is_watertight` AND `is_winding_consistent` are both True.** Non-watertight/inverted meshes give garbage (possibly negative) volume. Repair first (§3.5).

### 3.3 Transform — move / scale / rotate

```python
import numpy as np, trimesh
m = trimesh.load_mesh("part.stl")
m.apply_translation([10, 0, 5])     # shift (in-place)
m.apply_scale(2.0)                  # uniform 2x about ORIGIN;  apply_scale([1,1,0.5]) -> non-uniform
R = trimesh.transformations.rotation_matrix(np.radians(90), [0, 0, 1], point=m.centroid)
m.apply_transform(R)                # any 4x4 homogeneous matrix
m.apply_translation([0, 0, -m.bounds[0][2]])   # drop min-Z onto build plate (z=0)
m.apply_translation(-m.bounding_box.centroid)  # center bbox on origin
```

All transforms mutate in place and return the mesh. `apply_scale` scales about the **origin** — translate to origin first to scale about the center.

### 3.4 Boolean operations (CSG) — union / difference / intersection

trimesh delegates to the **manifold3d** engine (preferred) or Blender (subprocess fallback). With manifold3d installed, no setup.

```python
a, b, c = (trimesh.load_mesh(f) for f in ("body.stl", "tool.stl", "x.stl"))
union, cut, inter = a.union(b), a.difference(b), a.intersection(b)   # method style; cut = a minus b
from trimesh import boolean
cut = boolean.difference([a, b, c])    # functional style, multi-mesh: first minus the rest
```

- The `engine` param **defaults to `None`**, auto-selecting manifold3d when importable; `engine="blender"` forces Blender (needs it on PATH); `engine="manifold"` also works. Signature: `engine: Literal['manifold','blender',None] = None`.
- `check_volume=True` (default) raises if inputs aren't watertight positive-volume solids — **booleans require watertight inputs.** Repair first. Manifold-engine output is guaranteed watertight/manifold.

### 3.5 Repair (`trimesh.repair`) + built-in fixers

Verified function set (trimesh 4.12.x):

| Function | What it does |
|---|---|
| `fix_normals(mesh, multibody=False)` | Fix winding **and** normal direction so faces point "out", in place. |
| `fix_winding(mesh)` | Make adjacent faces traverse shared edges in opposite directions. |
| `fix_inversion(mesh, multibody=False)` | Flip the whole mesh if normals point inward. |
| `fill_holes(mesh, use_fan=False)` | Fan-fill boundary holes in place (poor on non-convex holes). |
| `broken_faces(mesh, color=None)` | Return indices of faces breaking watertightness (optionally color them). |
| `stitch(mesh, faces=None, insert_vertices=False)` | Fan-stitch over a boundary; returns new triangles. |

Canonical repair order: `m.process(validate=True)` → `m.remove_unreferenced_vertices()` → `repair.fix_winding(m)` → `repair.fix_normals(m)` (also fixes winding) → `repair.fix_inversion(m)` → `m.fill_holes()` if not watertight (convenience method == `repair.fill_holes(m)`). Full runnable version with manifold escalation: cookbook §8.1. For holes `fill_holes` can't close (large/non-convex), escalate to **pymeshlab** (§6) or a **manifold round-trip** (§4.3) which re-derives a clean manifold.

### 3.6 Split & 3.7 Scenes (multiple bodies on one plate)

```python
parts = m.split(only_watertight=False)   # list[Trimesh] per connected component (True drops loose shells)
for i, p in enumerate(parts): p.export(f"body_{i}.stl")
```

A `trimesh.Scene` holds named geometries with their own transforms — the structure for "arrange N parts on a plate" and the **only** way to keep separate objects in a 3MF (full arrange loop: cookbook §8.2).

```python
scene = trimesh.Scene()
scene.add_geometry(a, node_name="partA"); scene.add_geometry(b, node_name="partB")
scene.export("plate.3mf")                # distinct objects + units preserved
scene.to_geometry().export("plate.stl")  # flattened to one mesh — STL can't hold separate objects
```

### 3.8 Exporting 3MF — units gotcha (READ THIS)

trimesh's `export_3MF` (in `trimesh/exchange/threemf.py`) **hardcodes the model unit attribute to millimeter** (`{"unit": "millimeter"}`). Signature: `export_3MF(mesh, batch_size=4096, compression=8, compresslevel=5)` (`compression=8` == `ZIP_DEFLATED`).

- The written 3MF always declares `unit="millimeter"`; trimesh does **not** rescale your coordinates — it just labels them mm. **Your vertex numbers must already be in millimeters.**
- "Convert STL→3MF preserving units" means: *assume the STL is in mm* (the print convention), load, export. If the STL was authored in inches, `m.apply_scale(25.4)` **before** exporting, or the 3MF is 25.4× too small.
- A non-`Scene` input is wrapped in a `Scene` internally, so a single mesh exports as one object.

---

## 4. manifold3d — robust CSG / boolean engine

Use directly for maximum robustness, a guaranteed-manifold result, or to build solids from primitives. Operates on its own `Manifold` type; convert to/from trimesh at the edges (§4.3).

### 4.1 Primitives (OpenSCAD-flavored) & 4.2 booleans

```python
import manifold3d
from manifold3d import Manifold

cube = Manifold.cube([20, 20, 20], center=True)            # x,y,z dims
ball = Manifold.sphere(12, circular_segments=64)
rod  = Manifold.cylinder(30, 4, 4, circular_segments=64)   # height, radius_low, radius_high

result = cube - ball; result = cube + ball; result = cube ^ ball   # diff / union / intersect
big_union = Manifold.batch_boolean([m1, m2, m3], manifold3d.OpType.Add)   # many-at-once
```

**`OpType` is a module-level enum (`manifold3d.OpType`), NOT an attribute of `Manifold`.** Use `manifold3d.OpType.Add` (also `.Subtract`, `.Intersect`). `Manifold.OpType.Add` raises `AttributeError: type object 'manifold3d.Manifold' has no attribute 'OpType'`.

Transforms: `.translate([x,y,z])`, `.scale([sx,sy,sz])`, `.rotate([rx,ry,rz])` (degrees), `.transform(mat3x4)`, `.mirror([nx,ny,nz])`.
Measures (3.x names): `.volume()`, `.surface_area()`, `.bounding_box()`, `.num_tri()`, `.num_vert()`. The old 2.x `get_volume()` / `get_surface_area()` / `from_mesh()` are **absent** in 3.x. Pin the version; `dir(Manifold)` if unsure.

### 4.3 Interop with trimesh (round-trip = a free manifold repair)

The **3.x** constructor pattern (the 2.x `Manifold.from_mesh()` classmethod was removed — a known trimesh breakage around manifold3d 2.3.1):

```python
import numpy as np, trimesh
from manifold3d import Manifold, Mesh

def tm2man(tm):    # trimesh -> Manifold
    return Manifold(Mesh(vert_properties=np.asarray(tm.vertices, np.float32),
                         tri_verts=np.asarray(tm.faces, np.uint32)))   # int32 also accepted

def man2tm(man):   # Manifold -> trimesh
    m = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(m.vert_properties)[:, :3],   # first 3 cols XYZ
                           faces=np.asarray(m.tri_verts), process=False)    # tri_verts comes back int32

# Robust difference guaranteeing watertight output:
out = man2tm(tm2man(trimesh.load_mesh("body.stl")) - tm2man(trimesh.load_mesh("tool.stl")))
out.export("cut.stl")
```

If the input isn't manifold, `Manifold(...)` flags an error status; for "slightly off" meshes manifold provides a merge step, but repair badly broken meshes in trimesh/pymeshlab first.

**CrossSection (2D → 3D):** `CrossSection` builds 2D shapes (`.circle()`, `.square()`, polygons) that you `Manifold.extrude(...)` / `Manifold.revolve(...)` into a `Manifold` — for generating new solids to cut/add.

---

## 5. numpy-stl (`stl`) — lightweight STL-only fallback

Use when you only need to read/write/translate/rotate raw triangles fast, minimal deps, and don't need watertight checks, booleans, or repair.

```python
import numpy as np
from stl import mesh, Mode      # package 'numpy-stl', import name 'stl'

m = mesh.Mesh.from_file("part.stl")
m.vectors          # (N,3,3): N triangles, 3 verts, xyz. This IS the data.
m.normals          # (N,3) face normals;  m.points  # (N,9) flattened triangles
volume, cog, inertia = m.get_mass_properties()    # volume, center of gravity, inertia tensor
mins = m.vectors.reshape(-1, 3).min(axis=0); maxs = m.vectors.reshape(-1, 3).max(axis=0)  # bbox

m.translate([10, 0, 0])
m.rotate([0, 0, 1], np.radians(90))               # axis, angle(rad)
m.vectors *= 2.0                                  # uniform 2x scale

m.save("out.stl")                                 # binary default
m.save("out_ascii.stl", mode=Mode.ASCII)          # Mode is stl.Mode, NOT mesh.Mode
```

**`Mode` lives at `stl.Mode` — import via `from stl import mesh, Mode`, NOT `stl.mesh.Mode`.** `mesh.Mode` raises `AttributeError: module 'stl.mesh' has no attribute 'Mode'`. Signature: `save(self, filename, fh=None, mode=<Mode.AUTOMATIC: 0>, update_normals=True)`.

**Limits:** STL only — no 3MF/OBJ/PLY, no `is_watertight`/`fill_holes`/booleans/repair. For anything beyond moving triangles, use trimesh.

---

## 6. pymeshlab — heavy repair / remesh / decimate

Wraps MeshLab's filter graph. Reach for it when trimesh's repair is insufficient: closing large/non-convex holes, manifold reconstruction, decimation, remeshing, smoothing.

```python
import pymeshlab
ms = pymeshlab.MeshSet(); ms.load_new_mesh("broken.stl")
ms.meshing_remove_duplicate_vertices(); ms.meshing_remove_duplicate_faces()
ms.meshing_remove_unreferenced_vertices(); ms.meshing_repair_non_manifold_edges()
ms.meshing_close_holes(maxholesize=200)                                        # up to N boundary edges
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=20000, preservenormal=True)  # reduce tri count
ms.meshing_isotropic_explicit_remeshing(iterations=3)                          # even triangle sizing
ms.save_current_mesh("fixed.stl")
```

**Caveats:** filter names drift between releases. Discover at runtime: `[f for f in dir(ms) if "hole" in f]`, `pymeshlab.print_filter_list()` (all filters), `pymeshlab.print_filter_parameter_list("meshing_close_holes")` (params — module-level, not on MeshSet). Large binary wheel; install only when needed.

---

## 7. build123d / cadquery — when you need STEP (real CAD)

Mesh libraries can't emit STEP (STL/OBJ/PLY are faceted, not B-rep). For a **parametric, editable, exact solid** — or a CAD consumer — author with a code-CAD library on the OpenCascade kernel. Both export STEP **and** STL.

```python
# build123d — Pythonic; use the MODULE functions (deprecated Shape.export_stl was removed):
from build123d import *
with BuildPart() as bracket:
    Box(50, 30, 10)
    Hole(radius=4)                           # through hole
export_step(bracket.part, "bracket.step")    # exact B-rep, units (mm) + color/labels
export_stl(bracket.part,  "bracket.stl")     # faceted for printing

# cadquery — fluent; exporters module OR .export() (docs-recommended):
import cadquery as cq
r = cq.Workplane("XY").box(50, 30, 10).faces(">Z").workplane().hole(8)
cq.exporters.export(r, "bracket.step"); cq.exporters.export(r, "bracket.stl")
r.export("bracket.step")                     # also valid
```

**Prefer code-CAD when:** you need STEP, parametric/feature edits, exact fillets/chamfers, named-part assemblies, or guaranteed-valid solids. **Stay in mesh libs when:** input is already a mesh, you're doing scan repair, or output is just printable STL/3MF. Install gotcha: build123d ≥0.9 changed the `cadquery-ocp` dependency; on conflicts use a fresh venv or `pip uninstall vtk && pip install vtk==9.3.1`.

---

## 8. Cookbook — copy-paste recipes

Most one-shots are covered by `scripts/mesh_tool.py` (§0): `measure`, `scale`, `boolean --op difference`, `convert`, `arrange`. Quick inline forms — measure/scale/convert (§3.2/§3.3/§3.8), arrange (§3.7); boolean-cut a hole:

```python
import trimesh
body = trimesh.load_mesh("body.stl")
tool = trimesh.creation.cylinder(radius=4.0, height=50.0, sections=64)   # Ø8mm, 50mm
tool.apply_translation([20, 15, 0])
cut = body.difference(tool)                  # engine=None auto-selects manifold3d
assert cut.is_watertight; cut.export("body_with_hole.stl")
# STEP in/out needs a CAD kernel (build123d/cadquery, §7) — mesh libs can't write STEP.
```

### 8.1 Repair to printable, escalating to a manifold round-trip (`mesh_tool.py repair`)

```python
import numpy as np, trimesh
from trimesh import repair

def make_printable(in_path, out_path):
    m = trimesh.load_mesh(in_path)
    if isinstance(m, trimesh.Scene): m = m.to_geometry()
    m.process(validate=True); m.remove_unreferenced_vertices()
    repair.fix_winding(m); repair.fix_normals(m); repair.fix_inversion(m)
    if not m.is_watertight: m.fill_holes()

    ok = m.is_watertight and m.is_winding_consistent
    if not ok:                       # escalate: manifold round-trip re-derives a clean solid
        try:
            from manifold3d import Manifold, Mesh
            rm = Manifold(Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                               tri_verts=np.asarray(m.faces, np.uint32))).to_mesh()
            m = trimesh.Trimesh(vertices=np.asarray(rm.vert_properties)[:, :3],
                                faces=np.asarray(rm.tri_verts), process=True)
            ok = m.is_watertight
        except Exception as e:
            print("manifold repair failed, try pymeshlab close_holes:", e)

    m.export(out_path)
    return {"watertight": bool(m.is_watertight), "winding_ok": bool(m.is_winding_consistent),
            "volume_mm3": float(m.volume) if m.is_watertight else None, "printable": bool(ok)}
```

---

## 9. Gotchas checklist

1. **Units are implicit in STL/OBJ/PLY.** Treat STL as mm. trimesh's 3MF export *labels* mm but never rescales — fix coordinates first (`apply_scale(25.4)` if authored in inches).
2. **`trimesh.load` may return a `Scene`** — branch on `isinstance(x, trimesh.Scene)` before assuming `Trimesh` (or use `load_mesh`).
3. **`mesh.volume` lies on non-watertight/inverted meshes** — check `is_watertight` AND `is_winding_consistent` first.
4. **Booleans need watertight inputs** — repair both operands; `check_volume=True` raises otherwise.
5. **manifold3d 2.x → 3.x is breaking.** Use `Manifold(Mesh(vert_properties=..., tri_verts=...))`; `from_mesh()`/`get_volume()` gone. **`OpType` is `manifold3d.OpType`, NOT `Manifold.OpType`.**
6. **numpy-stl ASCII save is `Mode.ASCII`** via `from stl import mesh, Mode` — `mesh.Mode` does not exist.
7. **trimesh boolean `engine` defaults to `None`** (auto-selects manifold) — rarely pass it.
8. **STL can't hold multiple named objects or color** — Scene→STL flattens to one mesh. Use 3MF.
9. **You can't make STEP from a mesh** — it's B-rep; author in build123d/cadquery.
10. **`apply_scale` scales about the origin** — translate to origin first to scale about the center.
11. **pymeshlab filter names drift** — discover via `pymeshlab.print_filter_list()`.
12. **Pin every version.** manifold3d, pymeshlab, OCP-based CAD libs break across majors.

---

## Sources

- trimesh — docs https://trimesh.org/ · boolean https://trimesh.org/trimesh.boolean.html · repair https://trimesh.org/trimesh.repair.html · 3MF exchange source https://github.com/mikedh/trimesh/blob/main/trimesh/exchange/threemf.py · version-break issue #2112 https://github.com/mikedh/trimesh/issues/2112
- manifold3d — PyPI https://pypi.org/pypi/manifold3d/json · repo https://github.com/elalish/manifold · all-APIs example https://github.com/elalish/manifold/blob/master/bindings/python/examples/all_apis.py · docs https://manifoldcad.org/docs/html/
- numpy-stl — PyPI https://pypi.org/pypi/numpy-stl/json · docs https://numpy-stl.readthedocs.io/
- pymeshlab — PyPI https://pypi.org/pypi/pymeshlab/json · docs https://pymeshlab.readthedocs.io/
- cadquery — import/export https://cadquery.readthedocs.io/en/latest/importexport.html · build123d — import/export https://build123d.readthedocs.io/en/latest/import_export.html
- 3MF Consortium spec: https://3mf.io/specification/
