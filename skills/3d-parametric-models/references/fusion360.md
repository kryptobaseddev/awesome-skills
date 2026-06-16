# Fusion 360 ⇄ code-first parametric 3D printing

*Maps Autodesk Fusion (formerly "Fusion 360") concepts to/from a code-first OpenSCAD + mesh workflow. Read this when a user knows Fusion and you must explain, translate, or move a design between Fusion and code — the centerpiece is the User Parameters ⇄ OpenSCAD variables mapping (§3).*

Autodesk dropped "360" from the name (now **Autodesk Fusion**); "Fusion 360" persists colloquially and in help URLs. Treat as synonyms.

## 1. Parametric paradigm: sketch → constrain → dimension → feature

Fusion is a **history-based parametric** modeler:

1. **Sketch** a 2D profile on a plane/face.
2. Apply **geometric constraints** (relationships) and **dimensional constraints** (numbers/expressions).
3. Turn the profile 3D with a **feature** (extrude, revolve, sweep, loft).
4. Every step is recorded in the **timeline** and re-editable.

**12 sketch constraint types:** horizontal/vertical, coincident, tangent, equal, parallel, perpendicular, symmetry, **curvature** (the G2 constraint — *not* "smooth"), midpoint, fix/unfix (locked), concentric, collinear. Geometric constraints control *relationships*; dimensional constraints control *numeric size*.

**Constraint color signal:** a fully constrained sketch entity renders **black**; an entity with remaining degrees of freedom renders **blue**. Fastest way to tell whether a sketch is deterministic.

**Dimensions can be expressions.** Sketch Dimension tool (shortcut **D**). A dimension accepts a literal (`50 mm`) or an expression referencing parameters (`Width = Height * 2`). On-ramp to parametric driving (§3). Double-click to edit.

**Bridge to OpenSCAD.** A Fusion *sketch + constraints + dimensions* is the geometry OpenSCAD builds with primitives (`square`, `circle`, `polygon`) plus transforms — but the philosophies invert. Fusion is **constraint-solver-driven** (under-specify, the solver finds a consistent solution); OpenSCAD is **fully explicit** (state every coordinate; no solver, no "degrees of freedom"). The blue-vs-black question does not exist in OpenSCAD — code is always fully determined by its variables. Tell the user: *"In OpenSCAD there is no constraint solver; you trade auto-solving for total reproducibility."*

## 2. Timeline / history tree

The **timeline** (bottom of Design workspace) records every operation in order — sketches, features, construction geometry, joints. Interactive: drag the marker to roll back, edit a feature's parameters, reorder, suppress, or delete; Fusion recomputes downstream.

Fusion also supports **history-off / Direct Modeling** ("Do not capture Design History") — push/pull geometry with no timeline. The "dumb solid" mode, useful for editing imported geometry with no feature history.

**Bridge to OpenSCAD.** The timeline is Fusion's imperative, replayable build script. OpenSCAD source **is** that script, as text top-to-bottom. "Edit a timeline feature" ⇄ "edit a line of `.scad`"; "roll back the marker" ⇄ "comment out trailing code." Key contrast: the Fusion timeline lives inside a **binary cloud document**; the OpenSCAD timeline is a **plain-text file you can diff, `git`-version, and code-review**. History-off mode is the one case where Fusion behaves *less* like code.

## 3. ★ USER PARAMETERS ⇄ OpenSCAD variables — the key mapping ★

**The single most important bridge.** Fusion **User Parameters** are functionally OpenSCAD's top-of-file variables.

**Where:** `Design > Solid > Modify > Change Parameters` → opens the **Parameters** dialog.

**Create one:** click **Add** (Add User Parameter) → dialog fields:
- **Name** — unique identifier (e.g. `wallThickness`).
- **Expression** — expression used to calculate the value; **Value is auto-computed from Expression**.
- **Unit** — mm, deg, or *No Units* (pure ratio/count).
- **Comments** (optional).

**Two parameter kinds shown:**
- **Model Parameters** — auto-named (`d0`, `d1`, …), created every time you add a dimension or feature value.
- **User Parameters** — the named parameters *you* define and reuse.

**Equations.** The Expression field accepts equations referencing other parameters: `height = width * 2`, `holeDia = boltDia + 0.4 mm` (clearance), `count = 8`. You can also create a named parameter **on the fly** by typing `name = value` directly into any dimension/feature field.

**Driving a model:** wire every meaningful dimension and feature extent to a user parameter, then changing one number ripples through the timeline and rebuilds the part.

### ★ The core mapping

| Fusion User Parameter | OpenSCAD equivalent |
|---|---|
| `Add` → Name / Expression / Unit | A variable: `wall_thickness = 2;` |
| Expression referencing params (`height = width*2`) | `height = width * 2;` |
| Unit field (mm/deg) | OpenSCAD is **unitless** — every number is a millimeter by convention (slicers assume mm). No unit metadata. |
| `No Units` parameter (count, ratio) | a plain number in a `for`/loop count or a multiplier |
| Change Parameters dialog = central control panel | the variable block at the **top of the `.scad` file** (surfaced as Customizer sliders via `//` annotations) |
| Equations rebuild the timeline | re-running / auto-reloading the script re-renders the model |

Teaching line: *"Everything in `Modify > Change Parameters` is what a code-first workflow does with variables at the top of the file. A User Parameter `wallThickness` = `2 mm` becomes `wall_thickness = 2;`. `height = width*2` is literally the same line of code. The difference: OpenSCAD variables are unitless, version-controllable text, and can be swept headless in a batch — but you lose Fusion's unit awareness and live constraint solver."*

**OpenSCAD gotcha to convey:** OpenSCAD variables are **last-assignment-wins within a scope** (lexical, not imperative). State each variable once at the top — Fusion users will not expect this.

## 4. Core 3D feature tools (Create panel)

- **Extrude** — adds depth to open/closed sketch profiles or faces (Twist via *Taper Angle*).
- **Revolve** — revolves a profile/planar face around a selected axis.
- **Sweep** — sweeps a profile along a path. `Path` and `Path + Guide Rail` types; **Taper** (scale section) and **Twist** (rotate section). Must keep a **single consistent cross-section**.
- **Loft** — transitional shape between **two or more** profiles/faces. `Loft with Centerline` sweeps multiple profiles along a path.

Conceptual unifier (Autodesk): extrude/revolve/sweep are all sweep variants — extrude = path perpendicular to sketch plane, revolve = arc path around the axis.

| Fusion feature | OpenSCAD equivalent |
|---|---|
| Extrude (straight) | `linear_extrude(height=h) { 2D-shape };` |
| Extrude with Twist/Taper | `linear_extrude(height=h, twist=θ, scale=s)` |
| Revolve | `rotate_extrude(angle=a) { 2D-profile };` |
| Sweep along a path | **No native primitive.** BOSL2 `path_sweep()`/`sweep()`, or hull/minkowski chains. Genuinely harder. |
| Loft between profiles | **No native primitive.** BOSL2 `skin()`/`vnf_*`, or `hull()` of stacked slices. |

Teaching line: *"Extrude and revolve map cleanly to `linear_extrude`/`rotate_extrude`. Sweep and Loft are where Fusion's surfacing engine beats stock OpenSCAD — reach for BOSL2 (`path_sweep`, `skin`), and it's more work."* BOSL2 is a third-party library (`include <BOSL2/std.scad>`), not core OpenSCAD — confirm it's installed.

## 5. Modify panel: fillet / chamfer / shell / pattern

- **Fillet** — rounds an edge (radius, variable/rule fillet); strong multi-edge blends.
- **Chamfer** — bevels an edge (distance, two-distance, distance+angle).
- **Shell** — hollows a body to a wall thickness, optionally removing faces (the core "make it a shell" 3D-print op).
- **Pattern** — Rectangular, Circular, Path; duplicates features/bodies/components.
- Also: **Press Pull**, **Combine** (boolean), **Replace Face**, **Split Body/Face**, **Move/Copy**, **Align**, **Change Parameters** (§3).

| Fusion Modify | OpenSCAD equivalent |
|---|---|
| Fillet | BOSL2 `rounding`/`fillet()` edge masks, or `minkowski()` w/ a sphere (crude). **Hard** — Fusion far stronger. |
| Chamfer | BOSL2 `chamfer()`, or subtract an angled prism. |
| Shell | `difference()` of an outer solid and an inset inner solid (offset the 2D profile, or scale). |
| Combine (join/cut/intersect) | `union()` / `difference()` / `intersection()` — **exact 1:1**, arguably cleaner in code. |
| Pattern (rect/circular) | `for (i=[0:n-1]) translate(...)` / `for (a=[0:step:360]) rotate([0,0,a])` |

Teaching line: *"Booleans and patterns are trivial and elegant in OpenSCAD. Fillet and chamfer are Fusion's home turf — clean organic blends across many edges are painful in code."*

## 6. Bodies vs. Components

- A **Body** is raw 3D geometry — a collection of connected features. Multiple bodies can live in one component.
- A **Component** is a position/motion-independent part of an assembly. It has **its own origin/planes**, can carry **joints/motion**, and is **required for assemblies and 2D drawings**. "Components are made of bodies" — think of a component as an empty container you fill with bodies.
- **Rule #1:** build inside **Components** if the design will become an assembly; a lone **Body** is fine for a quick single-part print. Gotcha: **activate** the component you intend to edit, or new features land in the wrong place.

**Bridge to OpenSCAD.** Body ≈ geometry produced by a `module` call. Component ≈ a reusable, parameterized **`module`** (which can be `translate`d/`rotate`d into place); the file/`include`/`use` structure ≈ the assembly tree. Fusion **joints/assemblies/motion have no OpenSCAD equivalent** — OpenSCAD produces static geometry only. Hard boundary: *if the user needs kinematic joints, motion study, or exploded assemblies, OpenSCAD cannot do it; stay in Fusion.*

## 7. Workspaces: Design / Form (Sculpt, T-Splines) / Mesh

- **Design (Solid + Surface)** — default parametric BRep modeler. **Best for mechanical/printable parts** driven by user parameters. ~95% of code-bridgeable work.
- **Form** (a.k.a. **Sculpt**, **T-Splines**) — enter via **`Solid > Create > Create Form`** (icons turn purple). Freeform organic modeling: push/pull subdivided surfaces like clay. **Best for** ergonomic grips, organic shells, characters. Start from a primitive (Box, Sphere, Cylinder, Quad Ball, Plane); use **Box Mode** (low-res cage) vs **Smooth Mode**; **Finish Form** converts to solid BRep (an *open* T-Spline becomes a surface body). Use the **fewest divisions** that give the shape — easy to add, hard to remove.
- **Mesh** — works directly on triangle meshes (STL/OBJ/3MF): **Reduce** (lower facets), repair, remesh, plane-cut, **Convert Mesh** to BRep (§9). **Best for** cleaning scans/downloaded STLs. (Older docs say "Sculpt workspace"; current UI says **Create Form** — same T-Spline tech.)

| Fusion workspace | Code-first analog |
|---|---|
| Design (Solid) | **OpenSCAD itself** — direct, strong mapping. |
| Form / Sculpt (T-Splines) | **No good OpenSCAD analog.** Organic subdivision ≈ Blender (sculpt/subdiv) in a mesh pipeline. Code-first parametric tools are weak at organic sculpting. |
| Mesh | **MeshLab / Blender / `admesh` / Meshmixer / PrusaSlicer repair** — the mesh-repair/decimation stage. OpenSCAD can `import()` an STL but cannot edit its topology. |

Teaching line: *"Design workspace maps to OpenSCAD almost directly. Form/Sculpt leaves the code-first world — that's Blender/mesh territory."*

## 8. Exporting for print: STL / 3MF / OBJ / STEP

### 8a. Save As Mesh (primary print export)

**"Save As STL" was renamed "Save As Mesh"** (it now also writes `.3mf`). Access: Design workspace → right-click a component/body in the Browser → **Save As Mesh**.

Dialog settings:
- **Format** — **STL (Binary)**, **STL (ASCII)**, **3MF**, **OBJ**. For printing choose **STL Binary** unless your slicer supports 3MF.
- **Structure** — **One File** vs **One File per Body**.
- **Refinement** — **High / Medium / Low / Custom**. Higher = more triangles = finer surface, larger file. **Medium** is sane for mechanical parts; **High** for organic/figurine surfaces.
- **Refinement Options (Custom)** — **Surface Deviation**, **Normal Deviation**, **Maximum Edge Length**, **Aspect Ratio**.

**Built-in preset values.** The exact numbers Fusion's **"High" Refinement preset** writes into the dialog: **Surface Deviation 0.004479 mm, Normal Deviation 10, Maximum Edge Length 89.58 mm, Aspect Ratio 21.5**. These are Autodesk preset output, *not* a community-invented custom preset — Aspect Ratio 21.5 in particular is hard-set by **every** built-in preset. Practitioner notes: **Normal Deviation** is the dominant knob for curve smoothness; pushing Surface Deviation very low can balloon a single STL to ~1 GB.

### 8b. File > Export (other formats incl. STEP)

`File > Export` writes **STEP (`.step`/`.stp`)**, **IGES**, **SAT**, **Fusion archive (`.f3d`)**, plus mesh formats. **STEP** matters for the OpenSCAD bridge (§11): it preserves **true BRep solid geometry**, not triangles.

**3MF advantages:** embeds **unit** info (no scale mistakes); the spec requires a **manifold** mesh (fewer import errors); supports color/material; often smaller than STL. Tradeoff: STL works **everywhere**; 3MF works in PrusaSlicer, Bambu Studio, Cura 5.0+ and most modern slicers but may be rejected by older/industrial tools and some print services.

**Bridge to OpenSCAD.** OpenSCAD's `export` produces **STL / 3MF / OFF / AMF / DXF / SVG / CSG** (and PNG renders). **No STEP, no IGES in any build.** OBJ export is **version-dependent**: the stable **2021.01** release has **no OBJ export**, but development/nightly builds (2025) added **OBJ (Wavefront) export** — verify the user's build before claiming OBJ is unavailable. OpenSCAD output is *always tessellated mesh* (no BRep kernel), so it is the analog of Fusion's *Save As Mesh* path, never of *Export STEP*.

STL encoding: stable OpenSCAD 2021.01 exports **binary STL by default** (ASCII optional) — but the **OpenSCAD CLI** historically defaults to **ASCII**. Fusion's GUI defaults to binary STL. Fusion's **Refinement** slider ⇄ OpenSCAD's **`$fn` / `$fa` / `$fs`** facet-resolution variables — both control how finely curved surfaces are triangulated for the STL.

### 8c. Utilities > Make > 3D Print (send straight to a slicer)

The **3D Print utility** pushes a model directly into a slicer. Access: **`Utilities > Make > 3D Print`** (the "Tools" tab was renamed "Utilities"; older builds: `Tools > Make > 3D Print` or `File > 3D Print`). Opens the Save As Mesh dialog. Current builds expose a **Preparation Type (Manufacturing | Export)** selector; older builds use a **"Send to 3D Print Utility"** checkbox + slicer **Application** picker (choose a built-in preset or **Custom** → browse to `prusa-slicer.exe`/Bambu Studio executable; first run prompts you to locate it). Untick to fall back to writing a mesh file you import manually.

**Known gotchas:** direct transfer can **fail if the slicer is already open** (close it, let Fusion launch it); empty-build-plate-after-OK bugs reported; reliability varies by OS. Many practitioners prefer exporting **3MF or STEP** and importing manually.

**Bridge to OpenSCAD.** The code-first analog is a headless CLI: `openscad -o part.stl part.scad`, then `prusa-slicer --export-gcode part.stl` (or a CLI slicer call). Fusion's "Send to 3D Print Utility" button ≈ a two-line shell script — but the OpenSCAD version is **scriptable and batchable** (render N variants overnight) in a way the GUI button is not.

## 9. Importing a mesh + Convert Mesh → BRep limitations

Bring an STL/OBJ/3MF in via **Insert > Insert Mesh** (lands in the **Mesh** workspace as a mesh body). To make it editable as a solid: **Mesh > Modify > Convert Mesh** (Mesh → BRep).

**Hard limitations (the gotchas):**
- **Facet count ceiling** for faceted/prismatic BRep conversion: **< 10,000 facets converts clean**, **10,000–49,999 warns**, **≥ 50,000 hard-errors** and aborts. (Some versions add a "parametric/organic" convert option that handles more; the classic faceted convert is facet-limited.)
- **Fix with Mesh > Modify > Reduce** to drop facet count (percentage or target face count) before converting.
- **Watertight/manifold required.** A mesh with holes converts to a **surface body, not a solid** — patch holes first.
- A converted faceted mesh is **not** clean parametric geometry — every triangle becomes a face. Editable but ugly; treat mesh→BRep as a last resort.

**Bridge to OpenSCAD.** OpenSCAD can **`import("file.stl")`** and boolean against it, but treats the mesh as an **opaque solid** — there is **no mesh→BRep / "make it parametric again" path at all**; you cannot recover sketches/features from an STL. So Fusion's mesh→BRep, despite its facet limits, is *more* capable here. For reverse-engineering an STL into editable solid geometry, that's a point for Fusion (or a job for Blender + retopo).

## 10. Fusion scripting API (Python) vs OpenSCAD text-first

Fusion ships a **Scripts and Add-Ins** API (Python and C++). Access: **`Utilities > Add-Ins > Scripts and Add-Ins`** (`Shift+S`). Object-oriented, mirrors the GUI ("an extrusion is represented by the `ExtrudeFeature` object").

**Object model (top-down):** `Application` → `Document` → `Design` (`Product`) → `rootComponent`. Everything (sketches, features, construction geometry, child components) hangs off the **root component**. Two main modules:
- **`adsk.core`** — application + geometry math (`Application`, `Point3D`, `ValueInput`, `Matrix3D`, UI).
- **`adsk.fusion`** — modeling domain (`Design`, `Component`, `Sketch`, `ExtrudeFeatures`, `FeatureOperations`, parameters).

**ValueInput — the units bridge (easy to get wrong):**
- `ValueInput.createByReal(x)` — interprets `x` as **database units: length always centimeters, angle always radians**. A literal `0.5` here is 0.5 cm = 5 mm.
- `ValueInput.createByString("15 mm")` — **honors explicit units** and **accepts equations/parameters** like `"d0 / 2"`.

**Script entry points:** define `def run(context):` (optionally `def stop(context):`). Wrap work in try/except; surface errors via `ui.messageBox(traceback.format_exc())`.

**Parameters via API:** `design.userParameters` (named User Parameters from §3) and `design.allParameters`; read/write `.expression` or `.value` to drive the model — the API equivalent of the Change Parameters dialog.

### Minimal example (parametric extrude, official `addSimple` pattern)

```python
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent

        # drive the model with a named user parameter (createByString honors units)
        design.userParameters.add(
            'radius',
            adsk.core.ValueInput.createByString('5 mm'),
            'mm', 'outer radius')

        # sketch a circle on the XY plane — createByReal uses cm (DB units)
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0), 0.5)   # 0.5 cm = 5 mm
        prof = sk.profiles.item(0)

        # extrude 10 mm as a new body (createByString honors units)
        dist = adsk.core.ValueInput.createByString('10 mm')
        root.features.extrudeFeatures.addSimple(
            prof, dist, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
```

**For more control:** `extrudeFeatures.createInput(prof, op)` → `setOneSideExtent(DistanceExtentDefinition.create(dist), ExtentDirections.PositiveExtentDirection)`; set `input.isSolid = False` for a surface extrude.

| Fusion Python API | OpenSCAD |
|---|---|
| Imperative script that **drives the GUI app** to build geometry | A **declarative DSL** that *is* the model; no host app at author time |
| `ValueInput.createByReal` uses **cm/radians DB units** (easy to mis-enter); `createByString` honors units/equations | numbers unitless (mm by convention); angles in **degrees** |
| `userParameters.add(...)` to script a parameter | `radius = 5;` at file top |
| `extrudeFeatures.addSimple(prof, dist, op)` | `linear_extrude(10) circle(5);` |
| Runs **inside Fusion** (app installed + a document) | Runs **headless** anywhere: `openscad -o out.stl in.scad` |
| Output: live BRep in a Fusion doc | Output: tessellated STL/3MF directly |

Teaching line: *"Fusion's API is **automation of a GUI app** (manipulates a running session, cm/radian DB units, needs Fusion installed); OpenSCAD is **the model expressed as code** (self-contained, unitless, headless, version-controlled). For LLM generation and reproducible variants, emit OpenSCAD; for driving Fusion's surfacing/assembly engine programmatically, use the Fusion API."*

## 11. Decision: when Fusion wins, when code wins, how to move between

### Fusion beats OpenSCAD when
- **Complex fillets / chamfers / blends** across many edges — clean BRep rounds, painful in code.
- **Organic / freeform surfaces** — Form/T-Spline has no real OpenSCAD equivalent.
- **Assemblies, joints, motion studies, exploded views** — OpenSCAD is static geometry only.
- **2D manufacturing drawings** — require Components; OpenSCAD has none.
- **Simulation/FEA, CAM/toolpaths, generative design** — Fusion-only.
- **GUI exploration / ideation** — direct manipulation + solver beat blind coding.
- **Reverse-engineering an STL** into editable solids (mesh→BRep, within facet limits).
- **True BRep / STEP output** for machine shops and downstream CAD.

### OpenSCAD / code beats Fusion when
- **Version control** — `.scad` is plain text: `git diff`, code review, branch/merge. Fusion files are binary cloud docs.
- **Fully reproducible parametric variants** — change variables, re-render; sweep a whole family in a loop. No solver surprises.
- **LLM-generatable** — an agent emits/modifies `.scad` directly; reliable Fusion-API scripts are much harder and require the app.
- **Free and cross-platform** — no subscription/license server; runs on Linux.
- **Headless / batch / CI** — `openscad -o out.stl in.scad` on a GUI-less server.
- **Lightweight & scriptable** — tiny files, no cloud dependency, no account.

### Moving a design between them

**Fusion → OpenSCAD:** Export **STEP** (`File > Export > STEP`) to preserve true solids, **but OpenSCAD cannot import STEP directly.** Workarounds:
1. **STEP → mesh:** open STEP in **FreeCAD**, export **STL**, then `import("file.stl")` (opaque solid, not parametric).
2. **STEP → SCAD polyhedron:** the experimental **`openscad-step-reader`** (Assaf Gordon, OpenCASCADE-based) emits a `polyhedron()` definition (`--stl-scad` / `--stl-faces`). Proof-of-concept; faceted, not parametric; README gives no build/OpenCASCADE pin — verify it still builds.

You generally **do not recover a parametric model** going Fusion→OpenSCAD; you get static geometry. Re-author parametrically in OpenSCAD if you need the parameters back.

**OpenSCAD → Fusion:** OpenSCAD exports **STL/3MF**; import into Fusion's **Mesh** workspace, optionally **Convert Mesh → BRep** (mind the ≥50k-facet error; **Reduce** first). For a clean **STEP** out of OpenSCAD (a shop demands it), OpenSCAD can't export STEP — use **FreeCAD as a converter**:
- GUI: open the STL → Part workbench → *Create shape from mesh* (**Sew shape = 0.01**) → *Refine shape* → *Export* as `STEP with colors`.
- Scripted: export OpenSCAD **CSG**, then a FreeCAD Python script `importCSG.open(...)` → `Part.export(...)`.

The resulting STEP is **tessellated**, not true smooth BRep — fine for reference, suboptimal for precision CAM.

## 12. Cheat-sheet (Fusion ⇄ OpenSCAD)

| Fusion concept | OpenSCAD / code |
|---|---|
| Sketch + constraints + dimensions (solver, blue/black) | Explicit 2D primitives + transforms (no solver) |
| Timeline / history tree | The `.scad` source file (text, git-diffable) |
| **User Parameter (Modify > Change Parameters)** | **A top-of-file variable** (`x = 5;`) — the key mapping |
| Equation in Expression field | The same arithmetic in code |
| Extrude / Revolve | `linear_extrude` / `rotate_extrude` |
| Sweep / Loft | BOSL2 `path_sweep` / `skin` (no native primitive) |
| Fillet / Chamfer | BOSL2 rounding / `minkowski` (hard) |
| Shell | `difference()` of outer & inset inner |
| Combine join/cut/intersect | `union` / `difference` / `intersection` |
| Pattern (rect/circular) | `for` loop with `translate`/`rotate` |
| Body | geometry from a `module` call |
| Component / assembly / joint | a positioned `module`; **joints have no equivalent** |
| Form/Sculpt (T-Splines) | **no equivalent** → Blender/mesh territory |
| Mesh workspace (reduce/repair) | MeshLab / Blender / admesh / slicer repair |
| Save As Mesh Refinement (High/Med/Low/Custom) | `$fn` / `$fa` / `$fs` |
| Export STL / 3MF / OBJ | `export` STL / 3MF / OFF (OBJ only in 2025 nightlies, not 2021.01) |
| Export STEP (true BRep) | **not supported in any build** (FreeCAD workaround) |
| Utilities > Make > 3D Print → slicer | `openscad -o x.stl x.scad` + CLI slicer |
| Scripts & Add-Ins (Python API, `run(context)`) | the `.scad` text itself (declarative, headless) |
| `ValueInput.createByReal` cm/radian DB units | unitless numbers, degrees for angles |

## Sources

Fusion UI/concepts: [Change Parameters](https://help.autodesk.com/view/fusion360/ENU/?guid=SLD-MODIFY-CHANGE-PARAMETERS) · [Parameters reference](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-76272551-3275-46C4-AE4D-10D58B408C20) · [Sketch constraints](https://help.autodesk.com/view/fusion360/ENU/?contextId=SKT-CONSTRAINTS) · [12 constraints (PDO)](https://productdesignonline.com/day-17-of-learn-fusion-360-in-30-days-for-complete-beginners-2023-edition-learn-all-12-fusion-360-sketch-constraints/) · [Tool names](https://help.autodesk.com/view/fusion360/ENU/?guid=LP-TOOL-LIST-DESIGN) · [Bodies vs components](https://help.autodesk.com/view/fusion360/ENU/courses/AP-BODIES-VS-COMPONENTS) · [Create T-Spline forms](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-A0F0D052-A500-4632-8E35-347D98ED4AE6)

Export / mesh / refinement: [Save As Mesh](https://help.autodesk.com/view/fusion360/ENU/?guid=MESH-SAVE-AS-MESH) · [Export STL/3MF](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-export-an-STL-file-from-Fusion-360.html) · [Refinement settings (forum)](https://forums.autodesk.com/t5/fusion-design-validate-document/need-docs-for-save-as-mesh-gt-refinement-settings/td-p/13169437) · [STLExportOptions.meshRefinement (API)](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/STLExportOptions_meshRefinement.htm) · [STL for best print quality](https://www.fusion3design.com/exporting-stl-files-for-best-3d-print-quality/) · [3D Print utility](https://help.autodesk.com/view/fusion360/ENU/?guid=SLD-3D-PRINT) · [Convert STL→BRep](https://productdesignonline.com/fusion-360-tutorials/how-to-convert-stl-mesh-file-solid-brep-in-fusion-360/) · [STL→BRep facet error (forum)](https://forums.autodesk.com/t5/fusion-360-design-validate/stl-to-brep-error-large-number-of-facets/td-p/7460194)

Fusion API: [Basic Concepts](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/BasicConcepts_UM.htm) · [Units / createByString](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Units_UM.htm) · [ValueInput.createByReal](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ValueInput_createByReal.htm) · [addSimple sample](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/extrudeFeatures_addSimple_Sample.htm)

OpenSCAD & bridges: [downloads](https://openscad.org/downloads.html) · [release notes (binary STL default)](https://github.com/openscad/openscad/blob/master/RELEASE_NOTES.md) · [OpenSCAD (Wikipedia — OBJ export, no STEP/IGES)](https://en.wikipedia.org/wiki/OpenSCAD) · [BOSL2 wiki](https://github.com/BelfrySCAD/BOSL2/wiki) · [openscad-step-reader](https://github.com/agordon/openscad-step-reader) · [STL→STEP via FreeCAD](https://www.donovanbrown.com/post/How-to-get-a-STEP-file-from-STL) · [OpenSCAD→STEP via FreeCAD (gist)](https://gist.github.com/mdeweerd/d14274ac53b64f23d983b5fdabed8f9e)
