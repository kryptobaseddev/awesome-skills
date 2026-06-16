# OpenSCAD Language Reference

*Covers the OpenSCAD language for writing, reading, and refactoring parametric, 3D-printable `.scad` models — primitives, transforms, CSG, modules/functions, the immutable-variable gotcha, resolution control, libraries, and a refactoring playbook. Read when generating or improving OpenSCAD code. Units are millimeters throughout.*

## Contents
[0. Mental model](#0-mental-model) · [1. Version & backend](#1-version--backend-status) · [2. 3D primitives](#2-3d-primitives) · [3. 2D, extrude, projection, offset](#3-2d-primitives-extrusion-projection-offset) · [4. Transforms](#4-transforms) · [5. Boolean CSG, hull, minkowski](#5-boolean-csg-hull-minkowski) · [6. Modules, functions, children](#6-modules-functions-children) · [7. The variable gotcha](#7-the-variable-gotcha-immutable-last-assignment-wins) · [8. Special vars & resolution](#8-special-variables--resolution) · [9. Loops, comprehensions, assert](#9-loops-conditionals-comprehensions-let-assert-echo) · [10. use vs include](#10-use-vs-include) · [11. Writing parametric SCAD](#11-writing-good-parametric-scad) · [12. Refactoring](#12-refactoring-existing-scad) · [13. Libraries](#13-library-ecosystem) · [14. Snippets](#14-quick-reference-snippets) · [15. Pitfall checklist](#15-pitfall-checklist) · [Sources](#sources)

## 0. Mental model

OpenSCAD is a **declarative, functional, compile-time** CAD language — not imperative. You describe a Constructive Solid Geometry (CSG) tree of solids combined with booleans and transforms; the engine evaluates the whole program, then renders. There is no statement-by-statement execution order. Two namespaces: **modules** produce geometry (called as statements, end with `;`); **functions** produce values (used inside expressions, no side effects).

## 1. Version & backend status

- **Stable `2021.01`** (2021-01-31). Uses the **CGAL** kernel; comparatively slow. Still the only stable tag as of 2026.
- **Nightlies** carry years of features: function literals, `each`/C-style comprehensions, `textmetrics`, `roof()`, `fill()`, the `--backend` flag, lazy-union, and the **Manifold** engine. Packaged as macOS universal, Windows installer/zip, Linux AppImage (x86-64+ARM64), Snap (`openscad-nightly`), Flatpak beta, WASM, Docker.
- **Manifold engine** (Emmett Lalish): guaranteed-manifold mesh-boolean kernel, commonly 10×–1000× faster than CGAL. Nightly `2024.09.28` took it out of "experimental" (selectable at Preferences → Advanced → 3D Rendering → Backend, or `--backend=manifold`; CGAL still default then). **2025-08-17**: Marius Kintel announced **Manifold is now the DEFAULT backend** in dev snapshots; CGAL stays available via `openscad --backend=cgal`.
- **Guidance**: assume a modern nightly with Manifold default; recommend nightlies over 2021.01 for any non-trivial model. BOSL2 (§13) **requires 2021.01+** (function literals), so a nightly is safest.

**`--backend` flag (verified, with a stale-docs caveat):** `--backend=manifold` / `--backend=cgal` are current. Canonical `--help` values are **capitalized** (`CGAL`, `Manifold`) but **lowercase is accepted**. **Stale help text**: even on 2025-08-17 builds, `--help` / the Wikibooks CLI manual still print `--backend arg ... 'CGAL' [default] or 'Manifold'` — treat `[default] = CGAL` as **stale**; the runtime default in nightlies built after 2025-08-17 is **Manifold**. **Dead flag**: older nightlies used `--enable=manifold`, which now **errors** — `--backend=...` is the only correct form.

**Manifold caveat**: stricter about valid (manifold) input than the old preview path — non-manifold `polyhedron()` and self-intersecting geometry that "worked" under CGAL preview may now error. A *feature* for printing: forces watertight output.

## 2. 3D primitives

```scad
cube(10);                       // 10^3, corner at origin (center=false default)
cube([20,10,5], center=true);   // centered on origin

sphere(r = 5);                  // sphere(d=10) diameter form (must be named)
sphere(r = 5, $fn = 64);        // explicit facet count

cylinder(h=20, r=5);                  // Z axis; center=false -> base at z=0
cylinder(h=20, d=10, center=true);    // centered vertically
cylinder(h=15, r1=10, r2=0);          // cone (apex at top)
cylinder(h=15, r1=8, r2=3);           // frustum
cylinder(h=10, r=5, $fn=6);           // hexagonal prism (low $fn -> regular prism)
```
- `cylinder` `r` sets `r1=r2`; use `r1`/`r2` (or `d1`/`d2`) for cones. Facet count uses the **larger** radius. Low `$fn` (e.g. 6) is handy for nut/bolt-head sockets.
- Smoothness via `$fn`/`$fa`/`$fs` (§8); defaults `$fa=12, $fs=2`.

### `polyhedron` (general solid — the manifold minefield)
```scad
points = [[0,0,0],[10,0,0],[10,7,0],[0,7,0],[0,0,5],[10,0,5],[10,7,5],[0,7,5]];
faces  = [[0,1,2,3],[4,5,1,0],[7,6,5,4],[5,6,2,1],[6,7,3,2],[7,4,0,3]];
polyhedron(points, faces, convexity = 10);
```
- **Winding**: each face ordered **clockwise viewed from outside**. Wrong winding = inside-out = non-manifold; in "Thrown Together" (F5) preview backwards faces render **pink**.
- **Manifold requirement**: exactly **two faces meet at every edge**; no holes; consistent winding. Manifold backend *rejects* bad polyhedra at render (F6).
- `convexity` is a *preview* hint (front+back surfaces a ray crosses); does not affect the final mesh.

## 3. 2D primitives, extrusion, projection, offset

2D shapes live in the Z=0 plane; turn them 3D with `linear_extrude`/`rotate_extrude`.

```scad
square([20,10], center=true);
circle(r = 10);                  // or circle(d=20); circle(5,$fn=6) -> hexagon
polygon(points=[[0,0],[20,0],[20,10],[0,10]]);              // CCW outline
polygon(points=[[0,0],[30,0],[30,30],[0,30],[10,10],[20,10],[20,20],[10,20]],
        paths=[[0,1,2,3],[4,5,6,7]], convexity=4);          // outer path + hole path
text("OpenSCAD", size=10, font="Liberation Sans", halign="center", valign="center");
text("Bold", font="Liberation Sans:style=Bold");
```

### `linear_extrude` (2D → 3D along Z)
```scad
linear_extrude(height=10, center=true) circle(5);
linear_extrude(height=20, twist=360, slices=100) translate([4,0]) circle(1); // twisted
linear_extrude(height=10, scale=[1,3]) circle(2);                            // tapered
```
Params: `height`, `center`, `twist` (deg), `slices`, `scale` (scalar or `[x,y]`), `convexity`. Twist resolution from `slices`/`$fn`.

### `rotate_extrude` (2D profile → solid of revolution around Z)
```scad
rotate_extrude(convexity=10) translate([20,0]) circle(5);               // torus
rotate_extrude(angle=270, convexity=10) translate([10,0]) square([3,8]); // partial (2019.05+)
```
The 2D profile **must be entirely on one side** (X ≥ 0 by convention); crossing X=0 is invalid.

### `projection` (3D → 2D) and `offset`
```scad
projection(cut=true)  translate([0,0,-2]) sphere(10); // cross-section at Z=0
projection(cut=false) rotate([60,0,0]) cube(10);      // orthographic shadow onto Z=0

offset(r=2)        square([20,10]);             // rounded outward (radial)
offset(delta=2)    square([20,10]);             // straight/mitered corners
offset(delta=2, chamfer=true) square([20,10]);  // chamfered corners
offset(r=-1.5)     circle(10);                  // inset (negative shrinks)
```
`r` → rounded; `delta` → straight; `chamfer=true` needs `delta`. Great for clearances/fillets on 2D outlines before extruding.

## 4. Transforms

A transform is written **before** the object(s) it modifies and applies to all children.
```scad
translate([10,0,5]) cube(4);
rotate([0,0,45]) square(10);          // applied X then Y then Z order
rotate(a=90, v=[1,0,0]) cube(5);      // about arbitrary axis
scale([2,1,0.5]) cube(10);            // non-uniform; scale(2) uniform
resize([30,0,0]) sphere(5);           // set X=30; 0 = unchanged unless auto=true
mirror([1,0,0]) translate([5,0,0]) cube(4);   // reflect across YZ (normal=X)
color("red") sphere(3);  color("#33aaff", 0.5) cube(5);  color([0.2,0.8,0.2]) cube(5);
multmatrix(m=[[1,0,0,0],[0.5,1,0,0],[0,0,1,0],[0,0,0,1]]) cube(10);  // shear
```
- `rotate([x,y,z])` order is **X then Y then Z** — for composed rotations prefer separate `rotate()` calls or `multmatrix`.
- `color()` affects **preview (F5) only**; not in STL (3MF/AMF can carry color in newer builds).

## 5. Boolean CSG, hull, minkowski

```scad
union()        { cube(10); translate([5,5,5]) sphere(5); } // merge
difference()   { cube(10); translate([5,5,5]) sphere(5); } // first child MINUS rest
intersection() { cube(10); translate([5,5,5]) sphere(7); } // overlap only
```
**`difference()` gotcha**: the **first child is the base**; *all* subsequent children are subtracted. Order is load-bearing.
```scad
hull() { circle(3); translate([20,0]) circle(3); }        // 2D stadium
minkowski() { cube([20,20,4]); cylinder(r=3, h=0.01); }   // rounded-in-XY box
```
**Performance (critical for refactoring):**
- `minkowski()` is **expensive**: cost scales with the *product* of children's facet counts (two `$fn=100` cylinders ≈ 10,000 ops); memory blows up fast. Prefer low `$fn` on the rounding element, or BOSL2 `rounding`/`offset_sweep`.
- `hull()` is far cheaper in 2D than 3D; prefer 2D `hull()` then `linear_extrude`.
- When `hull`/`minkowski` get multiple children meant as *one* shape, wrap in `union()` first.

## 6. Modules, functions, children

```scad
function inc(x = 0) = x + 1;                                 // default param
function clamp(x, lo, hi) = x < lo ? lo : (x > hi ? hi : x); // ternary = the conditional

module washer(od, id, h) {
    difference() {
        cylinder(d=od, h=h);
        translate([0,0,-0.5]) cylinder(d=id, h=h+1);  // overshoot to avoid coplanar faces
    }
}
washer(od=20, id=8, h=3);
```

### Operator modules with `children()`
```scad
module ring(n, r) { for (i=[0:n-1]) rotate([0,0,i*360/n]) translate([r,0,0]) children(); }
ring(6, 20) sphere(2);

module spread(space) { for (i=[0:$children-1]) translate([i*space,0,0]) children(i); }
spread(15) { cube(5); sphere(4); cylinder(h=8,r=3); }
```
`children()` all · `children(i)` i-th · `children([a:b])`/`children([a:step:b])`/`children([i,j,k])` subsets · `$children` read-only count.

### Function literals (2021.01+) and recursion
```scad
sq = function (x) x * x;  echo(sq(5));                        // 25
function apply(f, v) = [for (x = v) f(x)];                    // higher-order
function fact(n) = n <= 1 ? 1 : n * fact(n-1);               // depth ~ thousands max
function sum_to(n, acc=0) = n == 0 ? acc : sum_to(n-1, acc+n); // TAIL recursion -> ~1,000,000
```
Use tail-recursive accumulator form for large iteration counts.

## 7. The variable gotcha (immutable, last-assignment-wins)

**The single most surprising thing about OpenSCAD and the #1 source of LLM bugs.**

- Variables are **compile-time constants**, bound once, never mutated at "runtime."
- Within a scope, **the last assignment wins for the entire scope** — assignments are not sequential:
```scad
a = 1;     // effectively discarded
echo(a);   // prints 2  (!!)
a = 2;     // this binding takes effect everywhere in this scope
```
There is no way to "increment a variable in a loop." You **cannot** do `total = total + x;` imperatively. Instead use **`for` loop scopes** (each iteration is its own scope) for geometry, and **recursion / list comprehensions / `sum`-style functions** to accumulate values:
```scad
// WRONG: total = 0; for (x=[1,2,3]) total = total + x;   // total stays the last binding
function vsum(v, i=0, acc=0) = i >= len(v) ? acc : vsum(v, i+1, acc+v[i]);
echo(vsum([1,2,3,4]));  // 10
```
- Since 2015.03 assignments are allowed in any scope, but **values cannot leak to an outer scope** — `let()` and for-iteration bindings are local.
- **Override exception**: a top-level variable from an `include`d file *can* be redefined in the including file without a warning — this is how libraries expose overridable defaults.

## 8. Special variables & resolution

```
fragments = ($fn > 0) ? $fn : ceil( max( min(360/$fa, r*2*PI/$fs), 5 ) );
```
| Var | Meaning | Default |
|---|---|---|
| `$fa` | min angle per fragment (caps facets at `360/$fa`) | 12° (min 0.01) |
| `$fs` | min fragment length in mm (bigger circles → more facets) | 2 (min 0.01) |
| `$fn` | explicit fragment count; **when >0 overrides `$fa`/`$fs`** | 0 |

Minimum is always **5** fragments. `$fn` divisible by 4 keeps a circle's bounding box axis-aligned (`$fn=8,12,16` for clean polygonal holes/bolt clearances). Tradeoff: high `$fn` = smooth but slow/large mesh; put `$fn` on **primitives where it matters**, prefer `$fa`/`$fs` globally so big features smooth and tiny ones don't waste facets.

```scad
$t           // animation time 0..1-1/steps
$preview     // true in F5 preview, false in F6 render
$children    // child count in operator modules
$vpr $vpt $vpd $vpf   // viewport rotation/translation/distance/FOV (read+write at top level)
$fn = $preview ? 24 : 96;                          // fast preview, smooth render
$vpr = [60, 0, $t*360];                            // turntable camera for video export
```

## 9. Loops, conditionals, comprehensions, let, assert, echo

```scad
for (i=[0:2:10]) translate([i,0,0]) sphere(1);                  // step 2
for (a=[0:30:359], r=[5,10]) rotate(a) translate([r,0]) circle(1); // nested product
intersection_for (a=[0:60:359]) rotate([0,0,a]) cube([20,2,5], center=true);
```
`for` **unions** its iterations; `intersection_for` **intersects** them (a plain `for` inside `intersection()` would still union).
```scad
if (reinforced) translate([0,0,5]) cube([50,10,3]); else translate([0,3,5]) cube([50,4,1]);
h = (d > 10) ? 8 : 4;                                          // ternary in expressions
function lerp(a,b,t) = let (u = 1-t) a*u + b*t;
let (w=20, h=10) translate([w/2,h/2]) square([w,h]);           // module-context let (2019.05+)
```

### List comprehensions
```scad
[for (i=[0:2:10]) i]                    // [0,2,4,6,8,10]
[for (a=[1:8]) if (a%2==0) a]           // filter -> [2,4,6,8]
[for (a=[1:4]) let (b=a*a) [a,b]]       // [[1,1],[2,4],[3,9],[4,16]]
[for (a=[1:3]) each [a,-a]]             // flatten -> [1,-1,2,-2,3,-3]
[for (a=0,b=1; a<4; a=a+1,b=b*2) [a,b]] // C-style -> [[0,1],[1,2],[2,4],[3,8]]
polygon([for (t=[0:5:359]) [20*cos(t), 30*sin(t)]]);  // parametric ellipse
```

### Validation & I/O (use generously in generated code)
```scad
assert(teeth >= 3, "gear needs >= 3 teeth");
echo(my_h = h, my_r = r);                          // labeled console output, 5 sig figs
render(convexity=4) difference() { big(); holes(); } // force CGAL mesh in preview for tricky CSG
import("part.stl", convexity=10);                   // STL/OFF/3MF/AMF/SVG/DXF
surface(file="heightmap.png", center=true);         // PNG/text heightmap -> mesh
```

## 10. use vs include

```scad
use <lib.scad>;       // imports MODULES and FUNCTIONS only; does NOT run top-level code
include <lib.scad>;   // textually inserts the file: runs top-level geometry AND imports defs
```
- **`use`** — safe default: no stray geometry, no variable pollution.
- **`include`** — top-level geometry *renders*; the file's top-level variables become **overridable** defaults (last-assignment-wins). BOSL2 requires `include <BOSL2/std.scad>` because its API uses top-level constants (`TOP`, etc.).
- Angle brackets `< >` search library paths (§13); quotes `" "` are relative paths.

## 11. Writing good parametric SCAD

### 11.1 Structure & naming
- **Top-of-file parameter block** first, then helper functions, then modules, then a single top-level call. One source of truth for every dimension.
- Names: `snake_case`, descriptive, **carry units when ambiguous** (`wall_thickness_mm`, `hole_d`). Identifiers `[A-Za-z0-9_]`, case-sensitive.
- **DRY**: never repeat a magic number — derive everything from named parameters.
```scad
/* ---- Parameters (mm) ---- */
wall=2; inner_w=60; inner_d=40; inner_h=25; corner_r=3; $fn=48;
/* ---- Derived ---- */
outer_w = inner_w + 2*wall;  outer_d = inner_d + 2*wall;  outer_h = inner_h + wall;
/* ---- Modules ---- */
module rrect(w,d,r) offset(r=r) square([w-2*r, d-2*r], center=true);
module box() {
    difference() {
        linear_extrude(outer_h) rrect(outer_w, outer_d, corner_r);
        translate([0,0,wall]) linear_extrude(outer_h) rrect(inner_w, inner_d, max(corner_r-wall,0.1));
    }
}
box();
```

### 11.2 Customizer annotations
Variable must be in the **main file**, have a **literal** value (number, bool, string, or vector ≤4 numbers), be **before the first `{`**, and not in `[Hidden]`. A `//` comment on the **line before** is the label; a `//` comment **after** the value defines the widget.
```scad
quality = 2;        // [0, 1, 2, 3]                      number dropdown
size    = 10;       // [10:Small, 20:Medium, 30:Large]   labeled dropdown
shape   = "round";  // [round, square, hex]              string dropdown
gap     = 5;        // [50]                              slider, max only (0..50)
width   = 30;       // [10:100]                          slider, min:max
notch   = 2;        // [0:0.5:10]                        slider, min:step:max
offset  = 1.5;      // .25                               spinbox custom step
label   = "PART-A"; // 12                                textbox max length
dims    = [10,20,5];// [1:50]                            vector, per-element range
hollow  = true;     //                                   checkbox
```
**Grouping** via block comments. `/* [Box Dimensions] */`, `/* [Lid] */`; special `[Global]` shows on every tab, `[Hidden]` hides derived/internal values from the UI. CLI presets: `openscad -o out.stl -p params.json -P SetName model.scad`.

### 11.3 3D-printing correctness
- **Manifold/watertight is mandatory.** Avoid zero-thickness walls, self-intersections, coplanar overlapping faces, T-junctions, inside-out `polyhedron` winding.
- **Overshoot trick**: when subtracting a through-hole, make the tool **longer than the body and shift it back by half the overshoot** so its end faces are *not coplanar* with the body's (coplanar faces → z-fighting / non-manifold booleans):
```scad
difference() { cube([20,20,5]); translate([10,10,-0.5]) cylinder(h=6, d=6); } // h=6>5, start at -0.5
```
- **Min feature/wall ≈ 0.8–1.2 mm** for FDM (≥2 perimeters); thin walls won't print.
- **`$fn` discipline**: small holes need *fewer* facets than big curves; don't slap `$fn=200` globally. For functional holes use `$fn` divisible by 4 and slightly oversize — a circle of `r` at low `$fn` is **inscribed** (smaller than `r`).
- **Units are mm**; slicers assume mm. Add `assert()`s for impossible combos (e.g. `wall*2 >= inner_w`).

## 12. Refactoring existing .scad

### 12.1 Code smells → fixes
| Smell | Fix |
|---|---|
| **Magic numbers** repeated (`12.7`, `1.5` scattered) | Hoist to a named parameter block; derive everything. |
| Copy-pasted geometry blocks | Extract a **module**; parameterize the difference. |
| Deeply nested `translate/rotate` pyramids | Extract operator modules, or adopt **BOSL2 attachments** (§13). |
| Imperative accumulation (`x = x + …`) | Replace with **list comprehension** or recursive `vsum`. |
| Global `$fn=200` everywhere | `$fa`/`$fs` globally + per-primitive `$fn`; gate with `$preview`. |
| Coplanar boolean faces (flicker, non-manifold) | Add overshoot (`-0.5 … +1`) to subtraction tools. |
| Hard-coded model, no parameters | Lift driving dimensions to a Customizer block; express the rest as ratios. |
| `include` where `use` suffices | Switch to `use` (unless the lib needs `include`, e.g. BOSL2). |
| Heavy `minkowski()` for rounding | Replace with `offset()` (2D) or BOSL2 `rounding`/`cuboid(rounding=)`/`round_anything`. |

### 12.2 Parametrize a hard-coded model (recipe)
1. **Inventory** every literal number and what it represents.
2. Separate **independent inputs** (the few real ones) from **derived** values (box: inputs = `inner_w/d/h, wall, corner_r`; derived = outer sizes).
3. **Create the parameter block** with Customizer annotations; move derived values to a `[Hidden]`/derived section.
4. **Replace literals** with named variables; encode relationships (`outer = inner + 2*wall`) rather than re-typing numbers.
5. **Extract repeated structure** into modules; add `assert()`s and `echo()`s.
6. **Add a `$fn` preview/render gate** and verify F6 render is manifold.

### 12.3 Performance
- **Use Manifold** (default in modern nightlies; `--backend=manifold`). Single biggest speedup; recommend switching off CGAL.
- **`$fn` discipline** — facet count is the dominant cost multiplier across booleans.
- **Avoid deep/large `minkowski()`** and 3D `hull()` (multiplicative in facet counts) — prefer 2D `offset`/`hull` then extrude.
- **Cache via modules, not re-computation**; lift invariant subtrees out of loops. Comprehension-built `polyhedron`/`polygon` is fast; deeply nested CSG of thousands of primitives is the slow path.

## 13. Library ecosystem

**User library path** (drop a library folder here; `< >` includes search it):
| OS | Path |
|---|---|
| Linux | `$HOME/.local/share/OpenSCAD/libraries/` |
| macOS | `$HOME/Documents/OpenSCAD/libraries/` |
| Windows | `<My Documents>\OpenSCAD\libraries\` |

Or set **`OPENSCADPATH`** (colon-separated Linux/macOS, semicolon Windows). GUI: **File → Show Library Folder…**.

### 13.1 BOSL2 — Belfry OpenSCAD Library v2 (the primary one)
Repo `github.com/BelfrySCAD/BOSL2`. **Requires OpenSCAD 2021.01+** (function literals). Install the `BOSL2` folder into the user library path, then `include <BOSL2/std.scad>` (must be `include` — API uses top-level constants). Areas: **attachments** (anchor positioning), **rounding/filleting**, **distributors**, extended **shapes** (cuboid/cyl/tube/prismoid), **threading/screws/nuts**, **gears**, **paths/beziers/skinning/sweeps**, shorthand transforms (`up()`, `left()`, `xrot()`, `zcyl()`).

```scad
include <BOSL2/std.scad>
// anchors: TOP BOTTOM LEFT RIGHT FWD BACK CENTER (and combos)
cuboid([40,30,20], rounding=4, anchor=BOTTOM) {
    attach(TOP)   cyl(d=10, h=8);
    attach(RIGHT) sphere(d=12);
    position(FRONT+TOP) color("red") sphere(2);     // mark a point, no reorient
}
diff() cuboid([40,40,15], rounding=3) {
    tag("remove") attach(TOP, overlap=0.01) cyl(d=20, h=6);   // subtractive pocket
}
```
**Threading / screws / gears (verified signatures):**
```scad
include <BOSL2/threading.scad>
threaded_rod(d=12, l=30, pitch=1.75, $fa=1, $fs=1);
include <BOSL2/screws.scad>
difference() { cuboid([20,20,20]); screw_hole("M6x1", length=20, thread=true, anchor=TOP); }
include <BOSL2/gears.scad>
spur_gear(circ_pitch=5, teeth=20, thickness=8, shaft_diam=5);
spur_gear2d(circ_pitch=5, teeth=20, shaft_diam=5);   // 2D profile
```
BOSL2 recommends **blunt-start threads** (default in recent versions) for printing — fewer partial end threads, less cross-threading.

**Gear center-distance helper — `gear_dist()` (there is NO `spur_gear_dist`):**
```scad
include <BOSL2/std.scad>
include <BOSL2/gears.scad>
cp = 5;
spur_gear(circ_pitch=cp, teeth=20, thickness=6, shaft_diam=5);
right(gear_dist(circ_pitch=cp, teeth1=20, teeth2=12))            // center distance helper
  spur_gear(circ_pitch=cp, teeth=12, thickness=6, shaft_diam=4);
```
**Distributors / shorthand:** `xcopies(20, n=3) cube(5,center=true);` · `up(10) left(5) cyl(d=4,l=20);` · `xcyl(l=20,d=4);`
**Use BOSL2 when**: clean relative assembly, rounded edges without minkowski, real threads/screws/gears, sweeps/skins — the default for most non-trivial mechanical parts.

### 13.2 MCAD
Bundled with OpenSCAD. Basic shapes (rounded boxes, regular polygons/polyhedra), involute **gears**, **motors** (NEMA), **bearings/materials**, boolean helpers. **Use when**: a quick standard gear/bearing/NEMA mount without BOSL2's depth.
```scad
use <MCAD/involute_gears.scad>
use <MCAD/boxes.scad>
roundedBox([30,20,10], radius=3, sidesonly=true);
```

### 13.3 NopSCADlib
`github.com/nophead/NopSCADlib`. Large mechanical/enclosure library with **vitamins** (fans, PSUs, screws, motors, electronics) and tooling for **BOMs and assembly instructions**. **Use when**: machine frames, enclosures, anything needing a bill of materials.

### 13.4 dotSCAD
`justinsdk.github.io/dotSCAD`. Math/algorithm-heavy: parametric **curves** (bezier/bspline), voxels, fractals, path ops. Quirk: set `OPENSCADPATH` to its `src/` folder; each public name == its `.scad` filename, so `use <line2d.scad>`. **Use when**: generative/algorithmic geometry, splines, lattices.

### 13.5 Round-Anything
`github.com/Irev-Dev/Round-Anything`. Robust **radii/fillets on 2D polygons** and smooth 3D shapes via `polyRound`. Install: unzip, rename folder to `Round-Anything`, drop in library path. **Use when**: controlled per-corner rounding on custom outlines (better than minkowski).
```scad
include <Round-Anything/polyround.scad>
polygon(polyRound([[0,0,2],[30,0,2],[30,20,8],[0,20,2]], fn=16));  // [x, y, radius] triples
```

### 13.6 Relativity
`relativity.scad` — relative/declarative positioning (an earlier take on what BOSL2 attachments now solve more comprehensively). **Use when**: maintaining legacy code; for new work prefer BOSL2 attachments.

**Decision guide**: relative assembly/rounding/threads/gears/sweeps → **BOSL2** · quick standard gear/bearing/NEMA → **MCAD** · machine/enclosure + BOM + vitamins → **NopSCADlib** · splines/fractals/algorithmic → **dotSCAD** · per-corner fillets on custom polygons → **Round-Anything**.

## 14. Quick-reference snippets
(Rounded box → §11.1; BOSL2 gear pair with `gear_dist` → §13.1.)
```scad
// Counterbored bolt clearance hole, with overshoot
module counterbore(through_d, head_d, head_h, body_h) {
  translate([0,0,-0.5]) cylinder(d=through_d, h=body_h+1);
  translate([0,0,body_h-head_h]) cylinder(d=head_d, h=head_h+0.5);
}
// Hex nut pocket (across_flats measured flat-to-flat)
module hex_pocket(across_flats, depth) cylinder(h=depth, d=across_flats/cos(30), $fn=6);
```

## 15. Pitfall checklist

1. Imperative `x = x + …` accumulation? → rewrite functionally (§7).
2. Subtraction tools coplanar with the body? → add overshoot (§11.3).
3. `polyhedron` winding consistent & manifold? → check pink faces (§2).
4. Global `$fn` too high/low? → `$fa`/`$fs` + `$preview` gate (§8, §11.2).
5. `minkowski()`/3D `hull()` on the hot path? → `offset`/BOSL2 rounding (§5, §12).
6. `include` leaking geometry/vars where `use` would do? (§10).
7. Magic numbers not lifted to a Customizer-annotated parameter block? (§11).
8. Backend = Manifold? Use `--backend=manifold`, **not** the dead `--enable=manifold` (§1, §12.3).
9. BOSL2 gear spacing via `gear_dist()`, **not** the nonexistent `spur_gear_dist()`? (§13.1).
10. Units in mm? `assert()` guarding impossible parameter combos? (§9, §11.3).

## Sources
- OpenSCAD User Manual (Wikibooks): [The Language](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/The_OpenSCAD_Language), [General](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/General), [Primitive Solids](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Primitive_Solids), [2D Subsystem](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_the_2D_Subsystem), [Transformations](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Transformations), [Functions & Modules](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/User-Defined_Functions_and_Modules), [List Comprehensions](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/List_Comprehensions), [Other Language Features](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Other_Language_Features), [Customizer](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Customizer), [Libraries](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Libraries), [CLI environment](https://en.wikibooks.org/wiki/OpenSCAD_User_Manual/Using_OpenSCAD_in_a_command_line_environment)
- [openscad.org/downloads](https://openscad.org/downloads.html), [openscad.org/libraries](https://openscad.org/libraries.html), [Wikipedia: OpenSCAD](https://en.wikipedia.org/wiki/OpenSCAD)
- Manifold-default announcement (2025-08-17): [lists thread A](https://lists.openscad.org/empathy/thread/D6KV3ZLXHLBHSITSQ5GPUZUKHURU4ABE), [thread B (backend default)](https://lists.openscad.org/empathy/thread/TMJEJCZINIJNYJX2YF7IDNBAPQY66KIF); Manifold non-experimental (2024.09): [OpenSCAD Mastodon](https://fosstodon.org/@OpenSCAD/113256867413539398)
- BOSL2: [repo](https://github.com/BelfrySCAD/BOSL2), [threading.scad](https://github.com/BelfrySCAD/BOSL2/wiki/threading.scad), [screws.scad](https://github.com/BelfrySCAD/BOSL2/wiki/screws.scad), [gears.scad (gear_dist)](https://github.com/BelfrySCAD/BOSL2/wiki/gears.scad), [CheatSheet](https://github.com/BelfrySCAD/BOSL2/wiki/CheatSheet)
- Other libs: [MCAD](https://github.com/openscad/MCAD), [NopSCADlib](https://github.com/nophead/NopSCADlib), [dotSCAD](https://justinsdk.github.io/dotSCAD/), [Round-Anything](https://github.com/Irev-Dev/Round-Anything)
