# Design for Additive Manufacturing (DFAM) — FDM/FFF Reference

*Numeric design rules for desktop FDM/FFF printing — overhangs, walls, holes, fits, threads, inserts, orientation. Read this before emitting CAD geometry or a slicer config so the part prints without supports, carries load along its strong axis, and compensates for FDM's undersize holes / oversize first layers.*

Assumed default config: **0.4 mm nozzle, ~0.42–0.45 mm line width, 0.2 mm layer height, PLA/PETG.** Every number is a *starting point* — FDM is printer-, material-, and calibration-dependent; print a tolerance/calibration test on the real machine + filament for any critical fit.

## Contents
- [0. Cheat sheet](#0-cheat-sheet)
- [1. Overhangs & the 45° rule](#1-overhangs--the-45-rule)
- [2. Bridging](#2-bridging)
- [3. Minimum wall thickness](#3-minimum-wall-thickness)
- [4. Features, pins, text](#4-features-pins-text)
- [5. Holes: undersize, elephant foot, horizontal](#5-holes-undersize-elephant-foot-horizontal)
- [6. Tolerances & fits](#6-tolerances--fits)
- [7. Orientation & anisotropy](#7-orientation--anisotropy)
- [8. Support strategy](#8-support-strategy)
- [9. Infill](#9-infill)
- [10. First-layer adhesion](#10-first-layer-adhesion)
- [11. No-supports checklist](#11-no-supports-checklist)
- [12. Shrinkage & warping](#12-shrinkage--warping)
- [13. Threads](#13-threads)
- [14. Heat-set inserts](#14-heat-set-inserts)
- [15. Living hinges](#15-living-hinges)
- [16. Counterbores & countersinks](#16-counterbores--countersinks)
- [17. Verification protocol](#17-verification-protocol)
- [Sources](#sources)

---

## 0. Cheat sheet
(0.4 mm nozzle, 0.2 mm layer)

| Parameter | Value | Source |
|---|---|---|
| Max self-supporting overhang (from vertical) | ≤ 45° safe | Hubs/Protolabs |
| Overhang envelope (good cooling) | < 50° recommended, up to ~70° on modern printers | Hydra Research |
| Max unsupported bridge span | ≤ 5 mm clean; < 10 mm design rule; 50 mm+ tuned (stunt) | Hubs, Hydra, MatterHackers |
| Minimum wall thickness | 0.8 mm absolute (2 perimeters); **1.2 mm recommended**; multiples of 0.4 mm | Formlabs, Mandarin3D, Hubs |
| Minimum hole diameter (modeled) | ≥ 2 mm (drill/ream if precision needed) | Hydra Research |
| Minimum feature / pin diameter | ≥ 1.8 mm (4× line width, ≥ 2 perimeters) | Hydra Research |
| Min embossed text | ≥ 0.9 mm stroke, raised ≥ 0.4–0.6 mm | Hydra, Formlabs |
| Min engraved text | ≥ 0.5 mm stroke, 0.2–0.6 mm deep | Hydra, Formlabs |
| Press / interference fit | **~0.1 mm** (printer-dependent — test) | Hydra, 3DChimera, Snapmaker |
| Snug / transition fit | **~0.2 mm** | Hydra, 3DChimera |
| Sliding / clearance fit | **~0.3–0.4 mm** | Snapmaker, Zbotic, MatterHackers |
| Print-in-place clearance | ~0.3–0.5 mm between moving surfaces | Snapmaker |
| Elephant-foot slicer compensation | ~0.2 mm negative XY, first layer only | Prusa KB |
| Base chamfer to defeat elephant foot | ~0.4–0.6 mm @ 45° (or 0.2 mm slicer comp) | Hydra Research, Prusa KB |
| Heat-set pilot hole (CNC Kitchen) | M3=4.0 mm datasheet (~4.25 as-printed); M4=5.6; M5=6.4; M6=8.0 | CNC Kitchen |
| Modeled threads | only ≥ M5 / UNC #10; smaller → insert or tap | Hydra Research |
| Layer-line strength penalty (Z vs XY) | Z ~30–55% of XY strength | CNC Kitchen |

---

## 1. Overhangs & the 45° rule

**Rule:** measured **from the vertical (Z) axis**, an overhang up to **45° prints cleanly without support** ([Hubs/Protolabs](https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview)). Steeper droops/curls and usually needs support. At 45°, ~50% of each new bead overlaps the layer below — the practical break-even point.

**Angle convention:** 0° = vertical wall (no overhang), 90° = flat horizontal ceiling (full overhang). "45° rule" = 45° away from vertical. ([Aleader](https://www.aleader-china.com/blog/45-degree-rule-3d-printing-design-guide))

**Real-world envelope (good part cooling, PLA):**
- ≤ 45°: reliably clean on any machine. ([Hubs/Protolabs](https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview))
- **< 50°: Hydra Research recommended value**; many modern printers reach **up to ~70°** with dialed-in cooling, lower temp, slower speed — surface quality degrades toward the top of that range. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

**Agent rule:** keep unsupported overhangs ≤ 45° from vertical to be safe; treat 45–50° as "probably fine, recommend testing"; flag anything > ~60° as "needs support OR redesign."

**Y / H / T mnemonic** ([Hubs/Protolabs](https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview)):
- **Y** = arms at ~45° → no support.
- **H** = horizontal crossbar is a **bridge**; OK unsupported if span ≤ ~5 mm, else support.
- **T** = arms stick straight out (90° cantilever, unanchored) → always needs support.

**Flexible (TPU) sags more** — keep overhangs **< 45°** and slow bridges. ([Fictiv](https://www.fictiv.com/articles/flexible-materials-for-3d-printing-guide))

---

## 2. Bridging

A **bridge** spans a gap anchored **on both ends** (unlike a cantilever overhang). The nozzle pulls a molten strand taut between anchors; rapid cooling holds it, so bridges beat the 45° rule. ([Wevolver](https://www.wevolver.com/article/3d-print-overhang))

- **≤ 5 mm:** clean, no tuning, no support. ([Hubs/Protolabs](https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview))
- **< 10 mm:** safe design rule. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))
- **> 5–10 mm:** add support if accurate surface finish required, or build an intermediate vertical pillar to split the span. ([Hubs/Protolabs](https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview))
- **~50 mm:** commonly achievable; some machines do 80–100 mm+ with 100% fan and tuned bridge settings. Treat as "stunt" numbers, not design rules. ([MatterHackers](https://www.matterhackers.com/articles/a-guide-to-understanding-the-tolerances-of-your-3d-printer))

**Bridge tuning levers:** 100% part-cooling fan, bridge speed ~20–30 mm/s, reduce flow ~85%, drop nozzle temp 5–10 °C. ([Zbotic](https://zbotic.in/3d-printing-overhangs-without-supports-bridging-tricks-that-actually-work))

**Orientation:** run the strand the **shortest distance** between two solid anchors, and make the bridge the **last/top** feature over the gap (one pass). Avoid geometry the slicer treats as a partial overhang.

**Unsupported flat edges** (ceiling-edge cantilever, not a bridge) ≤ **0.9 mm** (2× line width) or they sag cosmetically. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

---

## 3. Minimum wall thickness

Walls are built from beads ~0.42–0.45 mm wide. **Wall thickness must be a multiple of the line width** or the slicer leaves an internal void or runs noisy gap-fill — both weaken the part. ([Mandarin3D](https://mandarin3d.com/blog/wall-thickness-guide-minimum-and-optimal-measurements))

For a 0.4 mm nozzle, design walls at **0.8 / 1.2 / 1.6 / 2.0 mm**, etc.

| Wall purpose | Absolute min | Recommended | Notes |
|---|---|---|---|
| Any wall (2 perimeters) | **0.8 mm** | 1.2 mm | Below this, structurally unreliable |
| Vase-mode single wall | ~0.4–0.45 mm | — | One perimeter, decorative |
| General / cosmetic | 0.8 mm | **1.2–1.6 mm** | |
| Structural / load-bearing | 1.2 mm | **2.0 mm+ (3–5 perimeters)** | Perimeters beat infill for strength |
| Enclosures (typical) | — | 1.5–2.0 mm | Rule of thumb |

Cross-refs: [Formlabs](https://formlabs.com/blog/minimum-wall-thickness-3d-printing) (FDM min 1 mm, prefer 1.2 mm); [Hubs](https://www.hubs.com/talk/t/suggested-wall-thickness-for-a-box/6899) (2 mm good start); [Hydra Research](https://www.hydraresearch3d.com/design-rules) (≥ 0.9 mm = 2 line widths). **Agent rule:** never emit a wall < 0.8 mm (except vase mode); default cosmetic 1.2 mm, structural 2.0 mm; snap to multiples of line width.

---

## 4. Features, pins, text

**Minimum feature size:** ≥ **1.8 mm** (= 4× line width, ensures ≥ 2 full perimeters). ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

**Pins/pegs:** ≥ **1.8 mm Ø** absolute; ≥ **3 mm Ø** functional. For smaller/stronger pins, use a metal pin in a printed hole.

| Text feature | Min stroke width | Depth / height | Source |
|---|---|---|---|
| **Embossed (raised)** | ≥ 0.9 mm (2× line width) | raise ≥ 0.4–0.6 mm; ≤ 2 mm so it doesn't sag | [Hydra](https://www.hydraresearch3d.com/design-rules), [Formlabs](https://formlabs.com/blog/minimum-wall-thickness-3d-printing) |
| **Engraved (recessed)** | ≥ 0.5 mm | 0.2–0.6 mm deep | [Hydra](https://www.hydraresearch3d.com/design-rules), [Formlabs](https://formlabs.com/blog/minimum-wall-thickness-3d-printing) |

**Legible-text target:** stroke ≥ 0.6–0.9 mm, raised/recessed ≥ 0.4–0.6 mm, char height ≥ ~3 mm. Prefer **engraved on top surfaces**, **embossed on vertical side walls** (both print supportless); text on a **downward-facing** surface prints badly — avoid or flip. ([Prusa Forum](https://forum.prusa3d.com/forum/english-forum-original-prusa-i3-mk4-how-do-i-print-this-printing-help/debossed-embossed-text-without-supports-how))

---

## 5. Holes: undersize, elephant foot, horizontal

### 5a. Holes print undersize
FDM holes come out **smaller than modeled** from (1) polygonal STL approximation pulling the wall inward and (2) inward pull of cooling inner-perimeter extrusions. A **10 mm modeled hole may print ~9.7 mm** (≈ 0.3 mm undersize). ([3DChimera](https://3dchimera.com/blogs/connecting-the-dots/3d-printing-tolerances-fits), [Zbotic](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits))

**Compensation:**
- Oversize the hole ~0.2–0.4 mm (plus intended clearance). For a sliding fit on a 10 mm shaft, model ~10.5 mm.
- Precision: model undersize, then **drill/ream to size** ([Hydra Research](https://www.hydraresearch3d.com/design-rules)). Minimum modeled hole **≥ 2 mm Ø**. Use slicer **X/Y hole compensation** to fix globally.

### 5b. Elephant foot (first-layer XY expansion)
The squished, warm first layer bulges outward, making the base oversized and breaking fits. ([Wevolver](https://www.wevolver.com/article/3d-printing-elephant-foot), [Creality](https://www.creality.com/blog/3d-printer-elephant-foot))

**Fixes:**
- **Slicer compensation:** negative value ≈ measured foot. PrusaSlicer/OrcaSlicer call it *Elephant Foot Compensation*; Cura calls it *Initial Layer Horizontal Expansion* (use −0.1 to −0.4 mm). **~0.2 mm works well for a default 0.4 mm nozzle** and is on by default in Prusa profiles. ([Prusa KB](https://help.prusa3d.com/article/elephant-foot-compensation_114487))
- **Design fix:** add a **~0.4–0.6 mm chamfer (45°) on all bottom edges** that touch the bed. The chamfer absorbs the squish so the true cross-section starts clean. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))
- **Machine fixes:** raise Z-offset ~0.05 mm at a time, lower bed temp 5–10 °C, increase first-layer cooling. ([Creality](https://www.creality.com/blog/3d-printer-elephant-foot))

### 5c. Horizontal holes (axis parallel to bed)
A horizontal round hole sags at the **12-o'clock crown** (flat overhang) and flattens at the bottom. Fixes:

1. **Teardrop hole:** replace the top semicircle with a 45° peak so the top obeys the overhang rule — supportless. ([Snapmaker](https://www.snapmaker.com/blog/45-degree-rule-3d-printing))
2. **Hydra bridged-ceiling trick:** extrude two tangent rectangles above the hole — first = 1× layer height, second = 2× layer height — so the crown bridges in two clean steps. Offset `a ≈ layer height` (use 2a for very fine ~0.1 mm layers). ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

**Fastener clearance:** leave a single-layer "membrane" over a horizontal hole and drill through after printing. ([Reddit](https://www.reddit.com/r/3Dprinting/comments/8hhwlm/bridging_a_countersunk_hole))

---

## 6. Tolerances & fits

**FDM process tolerance is roughly ±0.15 to ±0.5 mm** (machine/calibration dependent). A well-tuned printer holds a 20 mm cube to ~±0.05 mm. ([Snapmaker](https://www.snapmaker.com/blog/3d-printing-tolerances))

### Fit clearance (diametral / total gap, 0.4 mm nozzle, PLA/PETG)

| Fit type | Recommended gap | Use case | Source(s) |
|---|---|---|---|
| **Press / interference** | **~0.1 mm** (line-to-line to ~0.05/side) | Permanent press-fit, needs force; may need crush ribs | [Snapmaker](https://www.snapmaker.com/blog/3d-printing-tolerances), [Markforged](https://markforged.com/resources/blog/heat-set-inserts), [3DChimera](https://3dchimera.com/blogs/connecting-the-dots/3d-printing-tolerances-fits) |
| **Snug / transition** | **~0.2 mm** | Alignment pegs, friction-held lids | [Hydra](https://www.hydraresearch3d.com/design-rules), [3DChimera](https://3dchimera.com/blogs/connecting-the-dots/3d-printing-tolerances-fits) |
| **Sliding / clearance** | **~0.3–0.4 mm** | Sliding rails, rotating shafts, drawers, print-in-place | [Snapmaker](https://www.snapmaker.com/blog/3d-printing-tolerances), [Zbotic](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits), [MatterHackers](https://www.matterhackers.com/articles/a-guide-to-understanding-the-tolerances-of-your-3d-printer) |
| **Very loose / rattle** | 0.5–1.0 mm+ | Free-flopping play | [Zbotic](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits) |

Cross-check: Markforged lists Press 0.00–0.05, Close 0.05–0.10, Free 0.10–0.20 mm ([Markforged](https://markforged.com/resources/blog/heat-set-inserts)). RapidDirect (industrial FDM, more conservative) lists press 0.25–0.35, sliding 0.50–0.60 mm ([RapidDirect](https://www.rapiddirect.com/blog/3d-printing-design)). Desktop-PLA community consensus: 0.1 mm/side ≈ snug, 0.2 mm/side ≈ slides easily.

> **Caveat (state with any fit):** these gaps are **printer-, material-, and orientation-dependent**. Print a **tolerance test** (a comb of pins/pockets stepping by 0.05–0.1 mm) on the actual machine + filament and pick the winning gap before committing.

**Crush ribs:** for reliable interference without cracking, design a clearance fit then add **~0.2 mm vertical ribs** around the shaft/bore that deform on assembly ([AON3D](https://www.aon3d.com/applications/engineering-fits-how-to-design-for-3d-printed-assemblies)). **Print-in-place:** leave **~0.3–0.5 mm** between moving surfaces so they don't fuse but stay captive; keep **≥ ~0.5 mm** between any distinct parts that must not bond ([Endeavor3D](https://endeavor3d.com/designing-3d-printed-hinges-and-interlocking-components)).

---

## 7. Orientation & anisotropy

**Strength is anisotropic.** FDM parts are strongest **within the XY plane (along layers)** and weakest **across layer lines (Z, tensile)** — Z holds roughly **30–55% of XY strength**, so ideal orientation is ~3× stronger than the worst. CNC Kitchen's Prusament hooks: standing (across-layer) failed at **~55% of lying-flat for PLA, 46% PETG, 29% ASA**. ([rahix](https://blog.rahix.de/design-for-3d-printing), [CNC Kitchen](https://www.cnckitchen.com/blog/comparing-pla-petg-amp-asa-feat-prusament))

**Priorities (in order):**
1. **Orient so loads run along layers, not across them** — put the weak across-layer direction where tensile stress is lowest.
2. **Put critical/cosmetic surfaces up or outward**, away from bed and support contact (XY surfaces hold tighter tolerance than Z).
3. **Minimize/eliminate supports** by rotating (a "T" upright needs none; on its side needs lots).
4. **Bed contact tradeoff:** maximize for adhesion, OR minimize first-layer area for auto-ejection in mass production (Slant3D: print at 45° on an edge). These conflict — choose by use case.

**45° tilt trick:** tilting a boxy part up by 45° converts long flat tops and large bridges into uniform diagonal faces — eliminates supports, removes top/bottom finish mismatch, minimizes first-layer contact. May need a brim. ([rahix](https://blog.rahix.de/design-for-3d-printing), [Slant3D](https://www.slant3d.com/slant3d-blog/8-essential-design-rules-for-mass-production-3d-printing))

**Strength-vs-supports dilemma:** the strongest orientation sometimes needs supports while the support-free one is weak across layers. Decide per part by the actual load.

---

## 8. Support strategy

Two base types (Bambu Studio terms; equivalents in Cura/PrusaSlicer/OrcaSlicer) ([Bambu Wiki](https://wiki.bambulab.com/en/software/bambu-studio/support)):

- **Normal:** project overhangs straight down to bed ("grid"/"snug"). Strongest for broad flat overhangs; more material; can mar surfaces.
- **Tree / organic:** branch up to sampled overhang nodes, away from the part. Less material, easier removal, gentler surfaces; weaker for large flat overhangs.

**Controls:** threshold angle (auto-supports above ~30–55° from vertical); interface layers (tune for clean peel); painted enforcers (force support, e.g. tall thin faces); blockers (forbid support on flat bottoms/protrusions); support material — soluble (PVA/water, HIPS/limonene) or breakaway "Support for PLA/PETG," PVA needs **Standard** style not tree ([Bambu Wiki](https://wiki.bambulab.com/en/filament/support)); Z-distance / air gap default ~0.3 mm (reduce for surface, increase for release).

**Agent default:** design to avoid supports first (chamfers, teardrops, bridged ceilings, reorientation). When unavoidable: **tree/organic** for sparse/organic overhangs, **normal+interface** for broad flat overhangs, plus blockers where not needed.

---

## 9. Infill

| Use case | Density | Notes |
|---|---|---|
| Visual / non-structural | **10–20%** | Fastest; gyroid OK at ≥ 10–15% |
| Functional prototype | **25–40%** | Handled / stress-tested |
| Load-bearing / end-use | **40–60%** (3+ perimeters) | Shells > infill |
| Max strength / tooling | up to 100% | Heavy, slow; diminishing returns if shells are thick |

**Key insight:** **adding perimeters increases strength more per gram than increasing sparse infill.** Tune shells before pushing infill past ~60%. ([SimpleMachining](https://www.simplemachining.com/blogs/understanding-3d-printing-infill-for-better-part-design))

**Patterns:** **gyroid** — near-isotropic, great strength-to-weight, good damping, ~10–15% min density; best general-purpose for functional parts ([Wevolver](https://www.wevolver.com/article/gyroid-infill)). **Grid/lines** — fastest, directional, good vertical compression. **Triangular/honeycomb** — strong against shear (honeycomb ~30% less material vs grid). **Cubic/tri-hexagon** — isotropic gyroid alternatives.

**Agent default:** **20% gyroid** general; 30–40% functional; grid for speed-critical visual prints.

---

## 10. First-layer adhesion

- **First layer:** print at **0.2–0.24 mm** even if the rest is finer; first-layer line width ~120–150% of nozzle; flow 95–105%; speed ~20–30 mm/s; fan off for first few layers (esp. PETG/ABS). ([Siraya](https://siraya.tech/blogs/news/first-layer-adhesion-problems-solutions))
- **Bed temps:** PLA 50–65 °C, PETG 70–85 °C, ABS/ASA 90–110 °C (enclosure), Nylon 60–80 °C (garolite/PEI + glue).
- **Skirt:** loop *around* (not touching) — primes nozzle, confirms level; no adhesion benefit. **Brim:** flat collar *attached* to the base — spreads shrinkage stress, anchors corners; use for tall/narrow parts, small footprints, warp-prone materials ([Xometry](https://www.xometry.com/resources/3d-printing/3d-print-warping-pla-petg-abs)). **Raft:** sacrificial platform under the whole part — absorbs elephant foot, helps adhesion on warpy/uneven beds, at material/time cost.
- **Rounded base corners (R ≥ 4 mm)** on large parts disperse warping forces. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

---

## 11. No-supports checklist (DfAM)

- **Use 45° chamfers instead of overhangs** on downward-facing transitions/bases — each layer keeps > 50% overlap. ([Snapmaker](https://www.snapmaker.com/blog/45-degree-rule-3d-printing))
- **Avoid downward-facing fillets** — they start near-horizontal and droop; use chamfers there. (Upward fillets fine; min fillet ⌀ ~1 mm.) ([Hydra Research](https://www.hydraresearch3d.com/design-rules))
- **Teardrop horizontal holes** so the crown is ≤ 45°.
- **Bridged ceilings on horizontal holes** (Hydra two-step extrude, §5c).
- **Reorient / tilt to 45°** to convert overhangs into self-supporting slopes.
- **Build internal pillars** to break a long bridge into ≤ 5–10 mm segments.
- **Slant3D summary:** "make it thicker, make it rounder, minimize first-layer contact area, avoid supports." ([Slant3D](https://www.slant3d.com/slant3d-blog/8-essential-design-rules-for-mass-production-3d-printing))

---

## 12. Shrinkage & warping

All thermoplastics contract on cooling, so parts print **slightly smaller** than CAD. Compensate via slicer **XY shrinkage compensation / scale factor** (e.g. OrcaSlicer → Filament → Shrinkage Compensation) or calibrate from a printed test cube. ([GrandpaCAD](https://grandpacad.com/en/tools/material-shrinkage-calculator))

| Material | Linear shrinkage (typical) | Range | Warp risk |
|---|---|---|---|
| **PLA** | ~0.3% | 0.2–0.5% | Low |
| **PETG** | ~0.4% | 0.2–1.0% | Low–moderate |
| **ASA** | ~0.5% | 0.4–0.7% | High (enclosure) |
| **ABS** | ~0.8% | 0.7–1.6% | High (enclosure) |
| **HIPS** | ~0.5% | 0.2–0.8% | Moderate |
| **PC** | ~0.6% | 0.5–0.8% | High |
| **TPU 95A** | ~0.8% | 0.4–1.4% | Low–moderate |
| **Nylon (PA12)** | ~1.4% | 0.7–2.0% | Very high |
| **Nylon (PA6/66)** | ~1.5% | 0.7–3.0% | Very high |
| **PP** | ~1.5% | 1.0–3.0% | Very high |
| **PVDF** | ~3% | 2.0–4.0% | Very high |
| Fiber-reinforced (CF/GF) | lower than base | 0.5–1.0% | Reduced vs unfilled |

Sources: [GrandpaCAD](https://grandpacad.com/en/tools/material-shrinkage-calculator), [filament2print](https://filament2print.com/en/blog/warping-contractions-3d-printing).

- **Amorphous** plastics (PLA, PETG, ABS, ASA, PC) shrink less; **semi-crystalline** (Nylon, PP, PVDF) shrink much more due to crystallization. Shrinkage is **proportional to size** — a 200 mm PLA base can warp more than a 50 mm ABS part.
- **Warping** = uneven cooling lifting corners or delaminating layers. Mitigate: heated bed at material temp, **enclosure** (mandatory for ABS/ASA/Nylon/PC), brim, rounded base corners (R ≥ 4 mm), reduced fan for warp-prone materials. For first-try reliability **default to PLA** (low shrink, sticks well). ([Xometry](https://www.xometry.com/resources/3d-printing/3d-print-warping-pla-petg-abs))

---

## 13. Threads

**Modeled (printed) threads:** reliable only for **≥ M5 / UNC #10**. Below that (M3/M4) the ISO metric flanks are too fine for FDM to resolve — use a **heat-set insert or tap** instead. **Never print threads on horizontal holes.** ([Hydra Research](https://www.hydraresearch3d.com/design-rules))

For robust printed threads, **BOSL2** generates clean, clearance-aware geometry in OpenSCAD. Tune thread fit via the **`$slop` special variable** rather than nominal dimensions:

```scad
include <BOSL2/std.scad>
include <BOSL2/threading.scad>

$slop = 0.10;               // printer-tuned fit clearance — print a test, then set
threaded_rod(d=8, l=20, pitch=1.25, $slop=$slop);     // M8x1.25 bolt
threaded_nut(nutwidth=13, id=8, h=8, pitch=1.25, $slop=$slop);  // matching nut
```

**Post-process thread hole sizing** ([Hydra Research](https://www.hydraresearch3d.com/design-rules)):
- **Thread tap:** model hole at **90%** of thread major diameter.
- **Self-tapping screw** into bare hole: **96%** of major diameter.
- **Heat-set insert:** **98%** of insert's outer (pilot) diameter.

**Captive nut pockets:** design hex pockets with **~0.2 mm clearance per flat** and **~0.3 mm extra depth** (for bottom over-extrusion); the nut drops in and is captured by geometry above. ([Zbotic](https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits))

---

## 14. Heat-set inserts

Brass inserts are melted in with a soldering iron (~10–20 °C above print temp: ~225 °C PLA, 245 °C PETG, 265 °C ABS). ([CNC Kitchen](https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey))

### Pilot-hole diameter (standard brass inserts, FDM)

| Thread | Pilot hole Ø | Notes / source |
|---|---|---|
| **M2** | ~3.0–3.2 mm | [Accu](https://accu-components.com/us/p/488-threaded-insert-hole-size-charts-for-3d-printing-pla-petg-resin), [Weerg](https://www.weerg.com/faq/guide-to-threaded-inserts-mjf-fdm-printing) |
| **M2.5** | ~3.8–4.0 mm | [Weerg](https://www.weerg.com/faq/guide-to-threaded-inserts-mjf-fdm-printing) |
| **M3** | **4.0 mm (CNC Kitchen datasheet)** | Burr-free as-printed at ~4.2–4.3 mm → **design ~4.25 mm in CAD** to compensate for hole shrinkage. ([CNC Kitchen](https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey)) |
| **M3.5** | ~4.8 mm | [Accu](https://accu-components.com/us/p/488-threaded-insert-hole-size-charts-for-3d-printing-pla-petg-resin) |
| **M4** | **5.6 mm** | Exact CNC Kitchen value |
| **M5** | **6.4 mm** | Exact CNC Kitchen value |
| **M6** | **8.0 mm** | Exact CNC Kitchen value |
| **M8** | ~9.6 mm | [Weerg](https://www.weerg.com/faq/guide-to-threaded-inserts-mjf-fdm-printing) |

> The CNC Kitchen **datasheet hole** is the nominal recommendation (M3 = 4.0 mm). Their test article found the back-side burr disappears when the **as-printed** hole is ~4.2–4.3 mm; since FDM holes print undersize, model ~4.25 mm in CAD to land there. M4/M5/M6 = 5.6 / 6.4 / 8.0 mm are exact CNC Kitchen datasheet values.

**Design rules:**
- **No standard insert OD** — same thread size has many profiles. Size the hole to the **specific insert's pilot/narrowest diameter** (tight slip / light drive fit), or use the **98% of insert OD** rule. ([Hydra Research](https://www.hydraresearch3d.com/design-rules))
- **Blind hole depth = insert length + ~1 mm** (Ricoh: +5 mm for melt displacement in their industrial process). ([Ricoh](https://3d.ricoh.com/wp-content/uploads/2022/06/Ricoh-3D_Threaded-Inserts-Guide.pdf))
- Add a **small chamfer at the hole mouth** to guide the insert straight; don't fillet the pilot.
- **Boss around insert:** ≥ ~2 mm of material around and below; min boss OD ~2× insert OD; if < 2 mm wall, drop to a smaller insert. ([Markforged](https://markforged.com/resources/blog/heat-set-inserts))
- **Insert length ≥ 1.5× bolt diameter** for strength (plastic fails before brass). If unsure, print an **array of holes stepping by 0.1 mm** and pick the one with no back-side burr (CNC Kitchen: M3 burr-free at ~4.25 mm hole).

---

## 15. Living hinges

A thin, continuous web that flexes through material deformation. ([Mandarin3D](https://mandarin3d.com/blog/designing-living-hinges-for-flexible-3d-prints))

- **Thickness: 0.4–0.6 mm** (sweet spot). Under 0.3 mm tears; over 0.8 mm the whole part deforms instead of folding. ([Hubs](https://www.hubs.com/knowledge-base/how-design-living-hinges-3d-printing))
- **Length (parallel to fold): ≥ 8–12× thickness;** min 2 layers through the hinge.
- Best FDM material: **Nylon (PA12)** or **TPU** — PLA is brittle and cracks.
- **Print the fold axis along layer lines, not across them** — flexing across layers delaminates ([Endeavor3D](https://endeavor3d.com/designing-3d-printed-hinges-and-interlocking-components)). Long outer path, short inner path; don't fold fully flat — design a **10–15° minimum "closed" angle** + a hard stop to limit peak strain.

---

## 16. Counterbores & countersinks

- **Counterbore** (cylindrical pocket for socket-head/cap screws): preferred — the screw exerts **purely compressive** force and the bore buries the head. Bore Ø = head OD + clearance; depth ≥ head height. ([nophead/HydraRaptor](https://hydraraptor.blogspot.com/2020/12/sinkholes.html))
- **Countersink** (conical seat for flat-head screws): creates **lateral splitting stress** in plastic — use only when flush mounting is required and material is thin. A printed cone has a real edge thickness ≈ **1/10 of the screw diameter** (not a sharp zero edge); account for it or oversize slightly so the head sits flush.
- **Orient the opening facing up.** A downward-facing counterbore/countersink is a flat overhang/bridge — print a single-layer membrane and drill it, or reorient. ([Reddit](https://www.reddit.com/r/3Dprinting/comments/8hhwlm/bridging_a_countersunk_hole))

---

## 17. Verification protocol

State with any final design:

1. **All numeric fits are printer/material/calibration-dependent.** Print a tolerance test (fit comb stepping 0.05–0.1 mm, insert-hole array, overhang/bridge tower) on the **actual machine + filament** before committing critical dimensions.
2. **Calibrate first:** single-wall cube + calipers; enable slicer **XY hole/contour compensation**, **elephant-foot compensation (~0.2 mm)**, and **shrinkage compensation** before trusting modeled dimensions. ([Prusa KB](https://help.prusa3d.com/article/elephant-foot-compensation_114487))
3. **Holes undersize, first layers oversize** — compensate in opposite directions.
4. **Strength is anisotropic** — orientation can change strength ~3× (Z ~30–55% of XY); always state which axis carries the load.

---

## Sources

Primary / first-party:
- Bambu Lab Wiki — Support, Support Painting, Filaments: https://wiki.bambulab.com/en/software/bambu-studio/support
- Prusa Knowledge Base — Elephant Foot Compensation: https://help.prusa3d.com/article/elephant-foot-compensation_114487
- Protolabs / Hubs — Supports, Living Hinges DFM: https://www.hubs.com/knowledge-base/supports-3d-printing-technology-overview
- Hydra Research — Design Rules for FFF (CC BY-SA 4.0): https://www.hydraresearch3d.com/design-rules
- Formlabs — Minimum Wall Thickness / Engineering Fits: https://formlabs.com/blog/minimum-wall-thickness-3d-printing
- Slant3D — 8 Design Rules for Mass Production: https://www.slant3d.com/slant3d-blog/8-essential-design-rules-for-mass-production-3d-printing
- CNC Kitchen — Heat-Set Inserts; PLA/PETG/ASA strength: https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey
- nophead / HydraRaptor — Sinkholes (counterbores/countersinks): https://hydraraptor.blogspot.com/2020/12/sinkholes.html
- Accu / Ricoh / Weerg — Heat-set insert pilot-hole charts: https://accu-components.com/us/p/488-threaded-insert-hole-size-charts-for-3d-printing-pla-petg-resin · https://3d.ricoh.com/wp-content/uploads/2022/06/Ricoh-3D_Threaded-Inserts-Guide.pdf

Supporting:
- Markforged — Heat-Set Inserts / fits: https://markforged.com/resources/blog/heat-set-inserts
- MatterHackers — Understanding Tolerances: https://www.matterhackers.com/articles/a-guide-to-understanding-the-tolerances-of-your-3d-printer
- Snapmaker — Tolerances; 45° Rule: https://www.snapmaker.com/blog/3d-printing-tolerances
- Mandarin3D — Wall Thickness; Living Hinges: https://mandarin3d.com/blog/wall-thickness-guide-minimum-and-optimal-measurements
- 3DChimera — Tolerances & Fits: https://3dchimera.com/blogs/connecting-the-dots/3d-printing-tolerances-fits
- Zbotic — Tolerances / overhangs: https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits
- rahix — Design for 3D Printing: https://blog.rahix.de/design-for-3d-printing
- BOSL2 — threading.scad (`threaded_rod`, `threaded_nut`, `$slop`): https://github.com/BelfrySCAD/BOSL2
