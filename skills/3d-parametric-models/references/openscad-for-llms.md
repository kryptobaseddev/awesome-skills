# OpenSCAD for LLMs — authoring print-ready models, and the programmatic-CAD landscape

*Practical guidance for an LLM writing print-ready OpenSCAD: the specific mistakes models make in `.scad` and how to avoid them, plus an honest survey of the programmatic/text-to-CAD alternatives and how this code-first OpenSCAD path compares. Read on demand when generating, debugging, or choosing a tool for parametric 3D-print models.*

## Why OpenSCAD is the LLM sweet spot

Text-based, declarative, parametric, simpler than a full CAD API, and naturally print-ready (mathematically precise, trivially re-parameterized). LLMs have far more OpenSCAD training data than any other CAD surface, so it has the highest first-pass success rate. Reasoning models (o3, Gemini 2.5 Pro) are the enabler — in Will Patrick's 25-task eval, errors were "rarely syntax issues — the challenge is spatial reasoning and adhering to every constraint." Lead with reasoning models, not base chat models.

## The mistakes LLMs make in `.scad` — and how to avoid them

### 1. Coordinate-frame confusion — push transforms to deterministic code

The #1 failure. The model "knows the words" (pitched roof + rotate) but rotates around the wrong axis or origin, so geometry slices through other geometry. It also confuses `rotate([0,90,0])` vs `rotate([0,-90,0])`. Spatial reasoning is not text reasoning.

Best practice: let the LLM decide *what/where* at a high level, but never let it hand-roll brittle transform math (`atan2`, anchoring offsets). Force **BOSL2 `attach()`/anchors** so transforms are relative and named rather than absolute and guessed:

```scad
// Fragile — LLM guesses axis/origin:
rotate([0,90,0]) cylinder(d=8, h=20);

// Robust — BOSL2 named axis, no manual rotate:
xcyl(d=8, l=20);            // cylinder along X
attach(TOP) cuboid([10,10,2]);  // place relative to parent face
```

### 2. Close the visual loop — render and *look*, don't trust "it compiled"

"Renders without errors" ≠ correct geometry. Compile-success says nothing about whether the part matches intent. Render to PNG (F6, or via an OpenSCAD MCP server) and feed the image back to a vision model for a fidelity check. Reference-image-grounded evaluation outperforms text-only. Never stop at a clean compile.

### 3. Validate manifold-ness — syntax-valid ≠ manufacturable

OpenSCAD can preview (F5) fine yet fail final render (F6) with `CGAL error in CGAL_Nef_polyhedron3()` or "Object may not be a valid 2-manifold and may need repair." Caused by bad vertex ordering, zero-thickness coincident faces, or unioning overlapping meshes — invisible in preview. **F6 render + STL export is the real gate.** Score "syntax valid" and "manufacturable" separately.

Use the **Manifold backend**: faster F6 and surfaces 2-manifold warnings. Select it at **Preferences → Advanced → 3D Rendering → Backend** (or CLI `--backend=manifold` / `--backend=cgal`). The old Features-menu toggle was removed 2024-09-28. Manifold became the **default** backend in Aug 2025 dev/nightly snapshots, so in current builds it is default-on, not a menu option.

### 4. Coincident/zero-gap CSG faces — the epsilon-overshoot idiom

When `difference()` subtracts a hole flush with a surface, the coincident faces create non-manifold artifacts and z-fighting in preview. Fix: make the cutting tool overshoot each face by a small epsilon. The canonical/idiomatic value is **eps ≈ 0.01 mm**; **0.1 mm** is also common (`addabit = 0.1`). Do **not** use 1 mm — that is atypically large and can violate fit tolerances. Bake this into every `difference()` the model emits:

```scad
eps = 0.01;                       // overshoot, not a real dimension
difference() {
  cube([20, 20, 10]);
  // through-hole: extend past BOTH faces by eps
  translate([10, 10, -eps])
    cylinder(d=5, h=10 + 2*eps, $fn=48);
}
```
Rule of thumb: **extend cuts, embed joins.**

### 5. Encode 3D-printing design rules as parameters, not afterthoughts

A naive model emits geometrically-correct-but-unprintable parts. Bake FFF numbers in as named variables (all printer/material-dependent — treat as starting points):

| Rule | Value | Note |
|---|---|---|
| Min wall | ~0.8–1.2 mm | ≥ ~2× nozzle/line width (two extrusions ≈ 0.9 mm) |
| Fit clearance | **0.1–0.2 mm** | loose ~0.2 mm, tight ~0.1 mm |
| Overhang | avoid > 50° from vertical | up to ~70° on good printers |
| Min pin diameter | ≥ 1.8 mm | |
| Horizontal holes | teardrop or +layer-height offset | counters droop |
| Base edges | chamfer | fights elephant's foot |

### 6. Chamfers/fillets aren't free — supply idioms

OpenSCAD has no one-click chamfer/fillet; they are built from primitives, and LLMs flail here. Provide the canonical recipes, or mandate BOSL2:

```scad
// 45° chamfer: subtract a rotated cube (most common form)
// Fillet on a 2D profile: offset(r) offset(delta=-r) profile;
// minkowski() also works for fillets but is slow.

// Far more reliable — BOSL2 parameters:
cuboid([20,20,10], chamfer=2);
cuboid([20,20,10], rounding=2, edges="Z");
```

### 7. Manage resolution — set `$fn`/`$fa`/`$fs` deliberately

Default facetization is coarse (visible flats on holes/cylinders); naive high `$fn` everywhere explodes render time and STL triangle count/file size. Parameterize: 32–64 for visible curves, low for hidden features, or set `$fa`/`$fs` globally. Never ship a faceted hole or a multi-million-triangle STL.

```scad
$fa = 2;    // min angle per fragment
$fs = 0.4;  // min fragment size (mm)
// or per-call: cylinder(d=5, h=10, $fn=48);
```

### 8. Make it parametric *and* target-aware

The whole point is editable, re-parameterizable output (sliders / Customizer). But targets differ — pick the constraints before authoring:

- **Thingiverse Customizer** — single, fully self-contained `.scad` file; **no external `include`/`use`, so no BOSL2**. If you rely on BOSL2 for correctness, inline/vendor the needed modules or declare the target as desktop OpenSCAD.
- **MakerWorld / Bambu "Parametric Model Maker"** — exposes OpenSCAD variables as UI and **supports `include`, so BOSL2 works**.
- **Printables** — large parametric/customizable host; BOSL2-based models must ship their code dependencies.

Prompt-craft rule that lifts every path: **describe the feature tree (fillets, chamfers, holes), not just a noun ("car").**

## SCAD libraries an excellent generator should know

- **BOSL2** (Belfry OpenSCAD Library v2) — the de-facto standard. Screws/nuts/washers, gears, threads, `rounding=`/`chamfer=`, `attach()`/anchors, masks. Replaces error-prone manual `rotate()`/`translate()` math. Use via `include <BOSL2/std.scad>`.
- **MCAD** — older OpenSCAD-team library: gears, NEMA mounts, bearings, teardrop holes.
- Others (official list): dotSCAD, NopSCADlib, Round Anything, `threads.scad`, BOLTS, funcutils, YAPP Generator (enclosures).

## The competitive landscape — programmatic / LLM 3D for print

Four lanes: (A) LLM → OpenSCAD; (B) LLM → Python code-CAD (CadQuery/build123d, B-rep/STEP); (C) dedicated text-to-CAD ML services (Zoo/KittyCAD, Autodesk neural CAD); (D) mesh-first generative 3D (organic, non-parametric — art assets, not engineering parts). For editable 3D *printing*, A and B dominate, C is rising, D is out of scope.

### A — LLM → OpenSCAD (this approach)

Highest first-pass success because of training-data abundance. Tooling that closes the loop:
- **OpenSCAD MCP servers** let an agent drive OpenSCAD, render, and *see* the result: `jabberjabberjabber/openscad-mcp` (MIT, Python; 5 tools, script storage, STL export + validation); `jhacksman/OpenSCAD-MCP-Server` (text/image → preview + 3D file, multi-view reconstruction). Reddit r/openscad has an open MCP that returns renders to the AI.
- **printpal.io** — browser AI CAD modeler bundling BOSL2 + MCAD, runs printability checks after each render.
- Benchmark caution: separate **syntax validity** from **manufacturable output** when scoring.

### B — LLM → Python code-CAD (CadQuery / build123d → STEP)

Produces **true B-rep parametric STEP** (CNC/injection-mold-grade), not CSG meshes. Strongest open-source path for editable, production-quality output.
- **CadQuery** — Python on the OpenCascade (OCCT/OCP) kernel; exports STEP, DXF, AMF, 3MF, STL; fillets, lofts, parametric curves, assemblies. OCCT gives NURBS, splines, and STEP import/export that OpenSCAD's CGAL lacks.
- **build123d** — newer CadQuery-family library, more Pythonic builder API; popular for CNC-from-STEP. Codex/Claude Code produce good STEP for "simpl-ish" parts.
- Research: Text-to-CadQuery (arXiv 2505.06507) argues generating CadQuery code directly beats task-specific command sequences, because pretrained code LLMs already know Python — a 124M fine-tune beat a 363M Text2CAD transformer.
- Tooling: **OCP CAD Viewer** (VS Code) renders CadQuery/build123d live.
- **Trade-off:** LLMs "fail more" with these libs than OpenSCAD because of less training data — SCAD has higher first-pass success, while CadQuery/build123d give better *output* (STEP, real fillets, true kernel). Pick SCAD for printability speed and hobby parts; pick CadQuery/build123d when STEP/CNC/manufacturing precision matters.

### C — Dedicated text-to-CAD ML services

- **Zoo / KittyCAD** ("Stripe for hardware design") — GPU-native Geometry Engine, **B-rep output** (CNC/injection-mold ready, not mesh art), WebRTC streaming, REST API + Python/TS/Go/Rust clients. Exports STL, PLY, OBJ, STEP, GLTF, GLB, FBX. **Pricing: $0.0083 per second of server/reasoning time — no credit system.** Free tier: **$10/month of free API calls** plus **20 minutes of free Zookeeper reasoning time**. Open-source Text-to-CAD UI + Blender add-on; **Zookeeper** is a conversational CAD agent that inspects/snapshots/debugs geometry. Independent testing: single objects only, no assemblies; be explicit about size/shape/features. Zoo's own tip — *describe the feature tree (chamfered edges, fillets), not just a noun* — generalizes to all LLM CAD prompting.
- **Autodesk** — Project Bernini (research POC; text/images/sketches/voxels/point clouds → functional 3D; ~3B params, 10M shapes; not commercial). At AU 2025 Autodesk announced commercial "neural CAD" foundation models for Fusion and Forma — a non-parametric ML alternative to parametric kernels.

### D — Parametric model repositories (where parametric printing lives)

- **Thingiverse Customizer** — runs single self-contained OpenSCAD files (no external library `include`/`use`, **no BOSL2**), surfaces variables as a UI. The hard constraint for Customizer-targeted output.
- **MakerWorld / Bambu Parametric Model Maker** — OpenSCAD variable UI; **supports `include` (BOSL2 OK)**.
- **Printables** — large parametric/customizable host; BOSL2-based models must ship code separately.

## What "bleeding edge" means in 2026

- **Table stakes:** LLM emits OpenSCAD, compiles, exports STL.
- **Good:** BOSL2 anchors (no hand-rolled rotate/translate), parametric variables exposed, basic print rules.
- **Bleeding edge:** reasoning-model authoring → deterministic transform codegen → **F6/Manifold render + vision fidelity check loop** → printability validator (manifold + wall/clearance/overhang/`$fn`/epsilon checks) → target-aware output (Customizer-safe self-contained SCAD *or* STEP via CadQuery/build123d) → feature-tree prompting. Separates syntax-valid from manufacturable; never trusts "it compiled."

## Sources

- OpenSCAD Manifold backend (Preferences → Advanced; default since Aug 2025): https://lists.openscad.org/empathy/thread/D6KV3ZLXHLBHSITSQ5GPUZUKHURU4ABE · https://github.com/openscad/openscad/issues/5192
- CGAL / non-manifold F6 errors: https://3dprinting.stackexchange.com/questions/15769/openscad-render-f6-fails-with-error-cgal-error-in-cgal-nef-polyhedron3 · https://github.com/openscad/openscad/issues/2034
- Epsilon-overshoot idiom: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/CSG_Modelling · https://hunsley.io/posts/2025/openscad-tips-3d-printing/
- FFF design rules (clearance 0.1–0.2 mm, pins ≥1.8 mm, overhang): https://www.hydraresearch3d.com/design-rules · https://printpal.io/docs/3d-printing-design-guide · https://www.hubs.com/knowledge-base/fixing-most-common-stl-file-errors
- BOSL2: https://github.com/BelfrySCAD/BOSL2 · MCAD: https://github.com/openscad/MCAD · Library index: https://openscad.org/libraries.html · awesome-openscad: https://github.com/elasticdotventures/awesome-openscad
- Why LLMs fail at OpenSCAD: https://dev.to/alanwest/why-llms-fail-at-openscad-code-generation-and-how-to-fix-it-2bel · HN "Teaching LLMs how to solid model": https://news.ycombinator.com/item?id=43774990
- Will Patrick text-to-CAD eval: https://www.linkedin.com/posts/wgpatrick_it-turns-out-that-llms-can-make-cad-models-activity-7320866218985345024-ZbGC
- OpenSCAD MCP servers: https://github.com/jabberjabberjabber/openscad-mcp · https://github.com/jhacksman/OpenSCAD-MCP-Server · https://www.reddit.com/r/openscad/comments/1nnv2i4/use_ai_with_openscad_heres_an_open_source_mcp/
- CadQuery: https://cadquery.readthedocs.io/en/latest/intro.html · build123d via HN: https://news.ycombinator.com/item?id=47772725 · Text-to-CadQuery: https://arxiv.org/html/2505.06507v1 · OCP CAD Viewer: https://marketplace.visualstudio.com/items?itemName=bernhard-42.ocp-cad-viewer
- Zoo pricing / Text-to-CAD: https://zoo.dev/api-pricing · https://zoo.dev/blog/turning-on-billing-for-text-to-cad · https://zoo.dev/blog/introducing-text-to-cad · https://zoo.dev/machine-learning-api
- Autodesk Project Bernini / neural CAD: https://www.research.autodesk.com/projects/project-bernini/ · https://adsknews.autodesk.com/en/news/upcoming-3d-generative-ai-foundation-models
- Thingiverse Customizer constraints: https://www.thingiverse.com/groups/openscad/forums/general/topic:56086 · MakerWorld: https://forum.bambulab.com/t/parametric-model-maker-review-and-feedback/75758
