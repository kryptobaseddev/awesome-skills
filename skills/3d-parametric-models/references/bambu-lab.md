# Bambu Lab 3D Printing — Slicing & Print Reference

*Covers the Bambu Lab printer lineup, Bambu Studio vs OrcaSlicer, the end-to-end slicing workflow, AMS multicolor, filament temps & calibration, headless/CLI slicing, and failure-mode fixes. Read this when generating a model for a Bambu printer, choosing a slicer/profile, picking filament settings, scripting headless slicing, or diagnosing a bad print.*

## Contents

- [TL;DR](#tldr)
- [1. Printer lineup](#1-printer-lineup)
- [2. Bambu Studio vs OrcaSlicer](#2-bambu-studio-vs-orcaslicer)
- [3. Slicing workflow](#3-slicing-workflow)
- [4. Supports](#4-supports)
- [5. Seams](#5-seams)
- [6. Brims](#6-brims)
- [7. Export / send / sharing](#7-export--send--sharing)
- [8. AMS multicolor](#8-ams-multicolor)
- [9. Filament temps & profiles](#9-filament-temps--profiles)
- [10. Calibration](#10-calibration)
- [11. Headless / CLI slicing](#11-headless--cli-slicing)
- [12. Failure modes & fixes](#12-failure-modes--fixes)
- [13. Verify before quoting](#13-verify-before-quoting)
- [Sources](#sources)

---

## TL;DR

- **Slicer = Bambu Studio (official) or OrcaSlicer (community fork, preferred for tuning).** Both descend from PrusaSlicer → Slic3r, share the same slicing engine and the same CLI. OrcaSlicer was forked from Bambu Studio by SoftFever in 2023.
- **Native project format = `.3mf`** (geometry + per-object settings + painted supports/seams + color painting + AMS mapping + plate layout). Treat `.3mf` as source of truth; `.stl`/`.step` are geometry-only.
- **AMS multicolor requires a `.3mf`** to carry per-object filament assignment and paint — an STL alone cannot encode it.
- **Headless slicing exists** via `bambu-studio` / `orca-slicer` with `--slice`, `--load-settings`, `--load-filaments`, `--export-3mf`, `--outputdir`, `--orient`, `--arrange`, `--pipe`, `--debug`. Use **hyphenated** flags. Loose JSON presets are fragile — a pre-saved `.3mf` with embedded presets is the reliable input.
- **0.4 mm nozzle layer heights:** 0.08 (Extra Fine) / 0.12 (Fine) / 0.16 (Optimal) / 0.20 (Standard) / 0.28 (Extra Draft). First-layer height = nozzle × 50% = **0.20 mm**.
- **Default filament = PLA.** Bambu first-party filament ships pre-calibrated; only run manual calibration for third-party spools or after a hardware change (new nozzle/plate/hotend).

---

## 1. Printer lineup

All Bambu FDM printers use **1.75 mm filament**.

| Model | Class | Build volume | Enclosed? | Max nozzle / bed | Notable | Status (mid-2026) |
|---|---|---|---|---|---|---|
| **A1 mini** | Bedslinger (open) | **180 × 180 × 180** | No | ~300 / 80 °C | Cheapest; AMS **lite** (external) | Active |
| **A1** | Bedslinger (open) | **256 × 256 × 256** | No | ~300 / 100 °C | Load-cell auto-cal, AMS lite | Active |
| **P1P** | CoreXY (open) | **256 × 256 × 256** | No | ~300 / 100 °C | Budget CoreXY, no lidar | Superseded |
| **P1S** | CoreXY (enclosed) | **256 × 256 × 256** | Yes | ~300 / 100 °C | Enclosed P1P; good ABS/ASA | Superseded by P2S |
| **X1** | CoreXY (enclosed) | **256 × 256 × 256** | Yes | 300 / 110 °C | Lidar + load-cell | Niche |
| **X1-Carbon (X1C)** | CoreXY (enclosed) | **256 × 256 × 256** | Yes | 300 / 110–120 °C | Flagship 2022–2025; lidar flow-cal, AMS | **EOL**, replaced by X2D |
| **H2D** | Dual-nozzle (IDEX) enclosed | single **325×320×325**, dual 300×320×325, two-nozzle total **350×320×325** | Yes (active chamber heat) | **350 °C** / 120 °C | Dual hotends, optional 10W/40W laser + drag-knife + pen | Active (Mar 2025) |

Newer models (specs move fast — re-verify before quoting): **P2S** (late 2025, refined P1S, same 256³), **H2S** (Aug 2025, ~340×320×340), **H2D Pro** (enterprise, 65 °C chamber, PPA-CF/PPS-CF), **X2D** (Apr 2026, X1C successor, dual-nozzle), **A2L** (~Jun 2026, **330×320×325**, single nozzle + cutting module).

**Practical differences that affect slicing:**
- **AMS vs AMS lite:** X1/P/H-series use enclosed **AMS** (4 slots, internal, RFID, moisture control). A1/A1 mini use **AMS lite** (open, external; better for flexible/TPU — no PTFE buffer maze).
- **Sensors:** X1C uses **lidar** (scans printed lines) for flow-rate cal + a load-cell nozzle. A1/H2D use an **eddy-current/load-cell** force sensor at the wiper for flow-dynamics cal. P1P/P1S have no lidar (rely on first-party profiles + manual cal).
- **Enclosure gates material:** open machines (A1, P1P) struggle with ABS/ASA/PA/PC warping; enclosed (P1S, X1C, H2D) are required for those.

---

## 2. Bambu Studio vs OrcaSlicer

Shared lineage: PrusaSlicer (← Slic3r) → **Bambu Studio** → **OrcaSlicer** (SoftFever's 2023 fork). Same core engine ⇒ comparable default quality; differences are in workflow, exposed settings, calibration tooling, and ecosystem.

**Pick OrcaSlicer for:**
1. Vendor-neutral / broad printer support (Bambu, Prusa, Creality, Voron, Klipper) — best for a mixed fleet.
2. Built-in **Calibration menu**: flow-rate, pressure advance, temp tower, retraction, max-volumetric-speed, tolerance, VFA.
3. More granular settings — extra infill patterns, separate accel for infill/walls/bridges, Klipper support, "Sandwich" (inner-outer-inner) wall order.

**Pick Bambu Studio for:**
1. Cleanest, most beginner-friendly UI; tabbed Prepare → Preview → Device flow.
2. Tight Bambu ecosystem: cloud sync, remote monitoring, **MakerWorld one-click**, first-party pre-calibrated profiles, best-tuned AMS behavior.
3. Official support (Wiki + ticketing). OrcaSlicer support is community.

**Calibration persistence (important, frequently misstated):**
- **Bambu Studio DOES persist Flow Rate as a filament profile** — Flow Rate Calibration generates/updates a filament preset.
- **Bambu Studio does NOT store Flow Dynamics / Pressure Advance (K-value) in the filament profile** — K lives **per-slot on the printer/cloud**, not in the filament preset.
- **OrcaSlicer keeps pressure advance in filament settings** (its full calibration suite saves into the filament profile).

So: in Bambu Studio, Flow Rate persists as a profile; PA/K does not. In OrcaSlicer, both do.

**Rule of thumb:** Bambu-only + low-effort → Bambu Studio. Tuning, multi-brand, or you want the calibration suite → OrcaSlicer. A `.3mf` saved in one opens in the other (shared format).

---

## 3. Slicing workflow

**(1) Import** STL / STEP / 3MF onto a plate (drag-drop or File → Import). STEP imports as solid geometry; 3MF restores everything. For multi-part files used for multicolor/assembly, choose **"load as a single object with multiple parts" → Yes**.

**(2) Orient & arrange.** `Auto orient` minimizes overhang/support; `Auto arrange` packs the plate. Good orientation is the cheapest way to cut supports.

**(3) Pick the printer profile** — e.g. `Bambu Lab X1 Carbon 0.4 nozzle`. Nozzle diameter is baked into the printer profile and gates which quality profiles appear.

**(4) Pick the filament profile** — Bambu first-party (`Bambu PLA Basic`, `Bambu PETG HF`, `Bambu ABS`) or `Generic PLA/PETG/...` for third-party. Assign one per AMS slot.

**(5) Pick the process/quality profile** (layer-height preset). For a **0.4 mm nozzle**:

| Layer height | Preset | Use |
|---|---|---|
| 0.08 mm | **Extra Fine** | Max detail, slowest (miniatures) |
| 0.12 mm | Fine | High detail; benefits from filament cal |
| 0.16 mm | **Optimal** | Best detail/speed balance |
| 0.20 mm | **Standard** | Default workhorse; most reliable |
| 0.28 mm | Extra Draft | Fastest, strongest layers, visible lines |

- 0.4 mm nozzle tested range = **0.08–0.28 mm** (reasonable range ≈ 20–70% of nozzle dia; 0.4 × 70% = 0.28 cap).
- **First-layer height = nozzle × 50% = 0.20 mm** default.
- Print time scales inversely with layer height (Bambu "Glowing Ghosts" example: 0.08 = 1h19m / 0.20 = 36m14s / 0.28 = 28m27s).
- Below 0.16 mm, **filament calibration matters** — Bambu profiles are best-tuned at 0.20 mm.
- Use **"Compare Presets"** to diff profiles.

**(6) Supports / seams / brim** — see §4–§6.

**(7) Slice** → inspect **Preview** (layer slider, color/flow/speed views, sequence). Check first layer, supports, seams, purge.

**(8) Export / send** — see §7.

---

## 4. Supports

**Two structures:**
- **Normal supports** — vertical grid pillars. Best for wide flat overhangs, engineering parts, and ABS/ASA (tree branches can fail to adhere in an enclosure). Faster, more stable.
- **Tree / Organic supports** — branches touching only where needed. Best for figurines, miniatures, organic shapes; ~40–60% less material, remove more cleanly (esp. PLA).

Each comes in **auto** and **manual** (paint-only) modes.

**Interface (contact layer between support and model):**
- **Top/Bottom interface layers** — more bottom interface = more stable; bottom interface 0 makes the base lines-only (bad). Top interface density/spacing controls how cleanly it peels.
- **Top Z distance** — gap between support top and model underside. Start ≈ one layer height. Smaller = better underside but harder to remove; larger = easy removal, rougher surface.
- **Base/interface pattern** — Default, Rectilinear, Rectilinear-grid, Grid. Grid is strong but hard to detach; rectilinear is the normal-support default.

**Support filament (the AMS killer feature):** print the model in one material, **supports in another** for clean release — **PVA** (water-soluble: soak 30–60 min, zero marks) or a different color PETG/PLA on a separate AMS slot. Set "support/raft interface filament" to a dedicated slot.

**Painted / manual supports:**
- **Support enforcers** — paint where you *force* supports.
- **Support blockers** — paint where supports must **not** generate (on visible faces/logos to avoid scarring; also stops auto-supports filling internal cavities).

**Gotchas:**
- **Per-object settings override global** — a downloaded model may ship with painted/forced supports baked in; check object settings if behavior surprises you.
- If **tree supports won't generate**: enable **Advanced** settings in Process, then turn off **"Remove small overhangs."**
- Bambu Studio 2.0 changed tree-support generation (some report missing interface → hard removal); re-test custom setups after a major update.

---

## 5. Seams

Set in **Process → Quality → Seam**. Four modes:
- **Nearest** — hides the seam on the closest non-overhang vertex (best for sharp-cornered models).
- **Aligned** — stacks the seam in one consistent vertical line (clean, predictable).
- **Back** — forces the seam to the rear.
- **Random** — scatters per layer; least obvious *line* but causes surface "zits."

**Fix unwanted dots/zits:** change Random → Aligned or Back.
**Painted seam:** paint a seam path manually; a "Vertical" checkbox eases straight painted seams.
**Limitation:** seam painting applies to **outer walls only**; inner walls follow the global seam mode.

---

## 6. Brims

Brim params live in the **"Other"** group and are **per-object**.

- **Brim types:** Outer brim only · Inner brim only (needs internal holes) · Outer and inner · None · **Auto** (default — analyzes shape/orientation/filament; tall-on-small-base or high-shrink materials like ABS/PC/CF get a wider brim automatically).
- **Brim-object gap:** smaller = stronger attachment, larger = easier removal. If gap=0 still shows a gap, it's usually **Elephant-foot compensation** — disable it to fully attach the brim.
- **Brim Ears:** targeted corner tabs instead of a full brim. Requires brim type = **"Painted"** first. Auto-generation places ears where the first-layer contour angle < threshold (Douglas–Peucker fit); left-click adds, right-click deletes, Shift+left multi-selects.
- **Disc / "use disc to avoid warping"** — alternative to brims for high-shrink prints (easier post-processing).

---

## 7. Export / send / sharing

**3MF project files** are the native format and canonical save — they bundle geometry, per-object settings, painted supports/seams, color painting, AMS mapping, and plate layout. Always hand off `.3mf`, not `.stl`, when settings must be preserved.

**Send-to-printer:**
- If Bambu Studio finds the printer on **LAN** and an SD card is present → file transfers **directly**. Otherwise it routes through the **cloud** then to the printer.
- Even on direct LAN transfer, by default the file is also copied to the cloud for Bambu Handy print history (removed after 90 days; 72 h if you delete history or use incognito printing).
- **LAN-only mode** keeps everything local (needs the printer's **access code** from its screen) but disables remote start and the Handy app. To fully avoid cloud: enable LAN mode or copy the sliced file to SD.

**MakerWorld** (Bambu's model-sharing platform):
- A **print profile** is a `.3mf` containing geometry + a settings group to generate G-code.
- Profiles are **not printer-locked**: MakerWorld **cloud-slices** by re-slicing against the printer/filament you select using official presets (deliberately does **not** trust the uploaded profile's printer settings, as a safety measure).
- Open in Bambu Studio directly, or download the `.3mf` (or raw model files) and import. On import for a different printer, Studio asks whether to keep the imported profile or use your own.

---

## 8. AMS multicolor

**Hardware:** AMS holds 4 spools (up to **4 AMS = 16 colors**), with RFID for Bambu spools and moisture control. **AMS lite** (A1/A1 mini) is open/external and handles flexibles (TPU) better. Color changes are mechanically intensive (cut → purge → retract → feed → purge to tower) — they wear parts faster and increase stringing, so **keep filament dry**.

**Multicolor objects require a `.3mf`** to carry the assignment/paint data. Three production methods:
1. **Per-object filament assignment** — load multi-part files as one object with parts; in **Process → Objects view**, click each part and press `1`/`2`/`3`/`4` to assign a slot. Cleanest boundaries (follow real geometry).
2. **Color painting** — paint colors onto a surface (good for logos/decals; boundaries approximate vs geometry splits).
3. **Height/Z color change** — single-color-per-band gradients.

**Flush / purge (the cost of single-nozzle multicolor):** every color change purges old filament into a **purge tower** (a.k.a. prime tower / "poop").
- **Sync AMS colors before painting/slicing** — slicer object colors must match the printer's actual slot colors or **purge volumes compute wrong** and painting can shift. Set colors on the printer, **sync in Studio**.
- **Flushing volumes** live in Filament Settings → Purging volumes: a **global multiplier** + per-color-pair matrix. Use **Auto-Calc**, then lower the multiplier (start ~0.5). Test for **color bleed** on a tower — each band should be uniform; a gradient = bleed → raise volume. Studio rounds purge to ≥100 mm³ when using a tower. Light→dark needs less purge than dark→light.
- **Reduce waste:** "Flush into infill", "Flush into objects' support" (needs a wipe tower), "Flush into this object" (sacrificial), or batch many small parts per job. Example: flush-into-objects dropped purge ratio ~30% → <1% but added ~30% print time.

---

## 9. Filament temps & profiles

> Starting ranges — land 5–10 °C above the manufacturer's stated minimum, run a temp tower for new brands, and **dry** PETG/ABS/ASA/PA/PC/TPU before printing. Select the correct **build-plate type** in the slicer to match the bed temp (Cool Plate ≠ Textured PEI).

| Material | Nozzle (typ.) | Bed (typ.) | Enclosure? | Retraction (start) | Notes |
|---|---|---|---|---|---|
| **PLA** (default, easy) | ~190–220 (≈210) | **55 °C default** (35 = Cool-Plate floor) | No | 0.8 mm @ 30–40 mm/s | Reduce bed 5–10 °C in hot ambient. Chamber off (0 °C). |
| **PETG** (tough, stringy) | ~230–265; **Bambu Generic PETG-HF default = 220** | ~70–80 °C | No (helps) | 1.0–1.5 mm @ 25–35 mm/s | Dry it; more retraction than PLA; can fuse to supports → larger top-Z. PETG-CF 240–270. |
| **ABS / ASA** (warps) | ~250–270 | **90–100 °C** (110 is a top, not typical) | **Yes** | default | Enclosure mandatory; brim/disc; avoid drafts. ASA ≈ ABS, UV-stable. Chamber off by default. |
| **TPU** (flexible) | ~220–240 | ~35–80 °C | No | 0.5–0.8 mm @ 15–20 mm/s | Print **slow**; AMS lite / external spool best; chamber off. |
| **PA / Nylon (PAHT-CF)** | ~260–290 (**typ. 280**, 290 = top) | **80–100 °C** | **Yes** (chamber 45–60 °C) | default | Very hygroscopic; **hardened steel nozzle** for CF. |
| **PC / PC-CF** | ~270 | ~110 | **Yes** (chamber 60 °C) | default | High warp; brim + adhesive; chamber on. |

**Chamber temperature defaults (Bambu Wiki):** heater module operates only **40–60 °C** (max 60 °C).
- **OFF (0 °C) by default** for PLA / PETG / TPU / PVA **and ABS/ASA** — for ABS/ASA, optionally set **60 °C** for large, warp-prone prints; it is not on by default.
- **ON (60 °C) by default** for PC / PA / PA-CF / PAHT-CF / PA6-CF / PET-CF / PPA-CF / PPA-GF / PPS / PPS-CF.

**Abrasive (CF/GF-filled) filaments require a hardened steel nozzle** (and hardened extruder gears on P1 series).

**Third-party tuning:** pick the closest Bambu profile (PLA Basic/Matte/Tough differ in PA/flow/temp), load as Generic, run filament calibration, save as a user profile.

---

## 10. Calibration

Bambu machines auto-calibrate a lot (bed mesh, Z-offset, vibration/input-shaping on by default). **Only recalibrate after a major change** — new build plate, new hotend, new nozzle diameter, or a never-printed filament. Bambu first-party filament ships pre-calibrated.

**Recommended order:** auto bed-mesh (once) → **Flow Rate** (per filament) → **Flow Dynamics / Pressure Advance** (per material family) → optional **temperature tower** + **retraction tower** per spool. ~90 min for a full first pass; 20–30 min per subsequent filament.

1. **Flow Dynamics (Pressure Advance / K-value)** — compensates extrusion lag at speed changes.
   - **X1 series:** prints lines, **lidar scans** them → auto K-value.
   - **A1 / H2D:** moves to the wiper, uses the **eddy-current/load-cell force sensor**.
   - **Manual mode** prints a PA pattern/tower; pick the best and enter K. Prefer manual for **damp filament, soft TPU** (auto often fails) or a **0.2 mm nozzle** (Bambu says auto is inaccurate). On textured plates use "pattern" over single-line.
   - Bambu Studio stores K **per-slot on the printer**, not in the filament profile. OrcaSlicer stores PA in filament settings.
2. **Flow Rate (extrusion multiplier)** — Bambu auto uses **lidar** to measure printed lines. **Fails on transparent/translucent/silk/sparkly/high-reflective filaments** → calibrate manually. **Do not select "Flow calibration" while printing on an X1/X1C** (separate procedure). In Bambu Studio, Flow Rate **is saved as a filament profile**.
3. **Temperature tower** (OrcaSlicer Calibration menu) — vary nozzle temp per band for best layer adhesion/surface; essential per new brand.
4. **OrcaSlicer Calibration menu** also covers retraction, max-volumetric-speed, tolerance, VFA — and (unlike Bambu Studio for PA/K) **saves results into the filament profile**.

> Interaction: set K first (affects corners/starts-stops), then re-check flow % with a test cube. Input shaping (default-on) lets higher accel run clean.

---

## 11. Headless / CLI slicing

Both `bambu-studio` and `orca-slicer` expose a headless CLI. Because OrcaSlicer is a Bambu Studio fork they share most flags, the same `--pipe` JSON progress format, and the same `.gcode.3mf` output structure. Differences are at the edges (a few flags, very different preset ecosystems).

### Verified BambuStudio CLI flags (official wiki)

| Flag | Meaning |
|---|---|
| `--slice <n>` | Slice plate `n` (`0` = all plates, `i` = plate i) |
| `--export-3mf <file>` | Export project (with G-code) as 3MF |
| `--export-slicedata <dir>` | Export slicing data to a folder |
| `--load-slicedata <dir>` | Load cached slicing data |
| `--export-settings <file.json>` | Export settings to JSON |
| `--load-settings "machine.json;process.json"` | Load **1 machine + 1 process** setting |
| `--load-filaments "f1.json;f2.json;..."` | Load filament settings (count ≤ filaments in the 3mf) |
| `--outputdir <dir>` | Output directory |
| `--orient` | Auto-orient |
| `--arrange <0\|1\|other>` | 0=disable, 1=enable, other=auto |
| `--scale <factor>` | Scale by float factor |
| `--pipe <pipename>` | Stream newline-delimited JSON progress to a named pipe |
| `--uptodate` | Auto-update the 3mf config to latest |
| `--info` | Print model info |
| `--debug <0..5>` | 0 fatal … 2 warning … 4 debug … 5 trace |
| `--help` / `-h` | Help |

> Flags are **hyphenated**: `--load-settings`, `--load-filaments`. The underscore forms `--load_settings` / `--load_filaments` **do not exist**. `--load-printers` and `--allow-newer-file` are **NOT** in the official BambuStudio wiki flag list (they appear in community/OrcaSlicer usage) — confirm with `-h` on the target build.

**Official BambuStudio examples (verbatim — note Bambu's own examples write `output.3mf`):**
```
./bambu-studio --slice 0 --debug 2 --export-3mf output.3mf test_data/moon.3mf

./bambu-studio --curr-bed-type "Cool Plate" \
  --load-settings "test_data/machine.json;test_data/process.json" \
  --slice 2 --debug 2 --export-3mf output.3mf test_data/moon.3mf

./bambu-studio --orient --arrange 1 \
  --load-settings "test_data/machine.json;test_data/process.json" \
  --load-filaments "test_data/filament.json" \
  --slice 2 --debug 2 --export-3mf output.3mf test_data/boat.stl
```

### Extra OrcaSlicer CLI flags
`--datadir <dir>` (profile store), `--ensure-on-bed`, `--skip-objects`, `--uptodate-settings`, `--convert-unit`, `--repetitions <n>`, `--rotate / --rotate-x / --rotate-y`, `--load-assemble-list` (multi-object/multicolor without a project file), `--filament-colour "#RRGGBB;..."`, `--min-save`. Usage form: `orca-slicer [ OPTIONS ] [ file.3mf/file.stl ... ]`.

**Realistic OrcaSlicer invocation (~2.3.x). When `--slice` + `--export-3mf` combine, OrcaSlicer writes `output.gcode.3mf`:**
```
orca-slicer --slice 1 \
  --load-settings "machine.json;process.json" \
  --load-filaments "filament1.json;filament2.json" \
  --filament-colour "#FF0000;#0000FF" \
  --min-save --debug 2 \
  --pipe /tmp/sandbox/progress.pipe \
  --export-3mf /tmp/out/output.gcode.3mf input.3mf
```

### Live progress via `--pipe`
```
mkfifo /tmp/bslicer_pipe
cat /tmp/bslicer_pipe | while IFS= read -r line; do echo "Progress: $line"; done &
bambu-studio --slice 1 --load-settings "machine.json;process.json" \
  --load-filaments "filament.json" \
  --export-3mf output.3mf --pipe /tmp/bslicer_pipe model.3mf
rm /tmp/bslicer_pipe
```

### Caveats (load-bearing — an agent will hit these)
1. **OrcaSlicer output from `--slice` + `--export-3mf` is `.gcode.3mf`, not raw `.gcode`** — a 3MF/zip archive with G-code + thumbnail. Rename to `.zip` to extract; OrcaSlicer also writes a `result.json` (`return_code`, `error_string`). Bambu's own wiki examples name the output `output.3mf`.
2. **Loose JSON presets are fragile.** `--load-settings`/`--load-filaments` JSON often gets ignored → `"filament_id":"unknown"`, `total_used_g:0.0`, or "unknown config type." **Reliable input is a Bambu Studio `.3mf` with presets already embedded** (open GUI → load → save → feed that 3mf to the CLI). Hand-assembling JSON from `resources/profiles/BBL/...` inheritance is possible but painful.
3. **Linux: use the AppImage, not Flatpak.** The Flatpak build reports "Invalid option" for `--load-settings`/`--load-filaments`; extracting the AppImage fixes it.
4. **Windows CLI is often silent** — some users only get `bambu-studio.exe model.stl --export-3mf out.3mf` to work; full commands "do nothing."
5. **Hyphenation matters** — use `--load-settings`, not `--load_settings`. Availability varies by build; run `-h` against the installed binary.
6. **CLI vs GUI drift:** the baked preset in a CLI-produced 3mf can differ from selected settings, changing time estimates when reopened in the GUI.
7. Use `--debug 2` + `--pipe` for visibility (the CLI is otherwise quiet about errors).

---

## 12. Failure modes & fixes

**Warping (corners lift/curl)** — worst on PETG/ABS/ASA/PA/PC.
- Cooling tab → "No cooling for first N layers" (3 for PLA/PETG/TPU); drop aux fan to 40–50%.
- Brim or **discs**; raise bed temp; close doors/avoid drafts; enclosure for ABS/ASA.
- High infill on large parts shrinks → switch infill to **Gyroid**; move the **seam** off the lifting corner.

**Poor first layer / bed adhesion** (usually a lost print).
- **Clean the plate** — warm soapy water then 91%+ IPA (oils kill adhesion).
- Check **Z-offset** in ±0.05 mm steps; run full auto-calibration (fixes ~60–70%).
- **Select the correct plate type** in the slicer (Cool Plate ≈35 °C vs Textured PEI ≈65 °C for PLA; PLA default bed = 55 °C).
- Use a **brim** (≈5 mm on parts <60 mm), not a skirt; drop first-layer speed to ~30–40 mm/s, first-layer flow ~105%.

**Stringing / oozing.**
- **Dry the filament** (PETG/TPU especially); airtight storage + desiccant.
- Run **Flow Dynamics (K)** + **Flow Rate** calibration; increase retraction for PETG.

**Supports hard to remove / fused to model.**
- Raise **Top Z distance** (PETG sweet spot ~0.17 mm); tune top interface layers/spacing (e.g. 4 top interface layers, 0.33 spacing). Calibrate flow/K first.
- Use a **different support material** (PVA soluble, or contrasting PETG/PLA) for clean release.

---

## 13. Verify before quoting

- **X2D / A2L / H2S / P2S** exact specs, prices, dates — secondary press, not Bambu's own spec pages.
- **H2D chamber 65 °C** — Bambu confirms "active chamber heating" but the 65 °C figure is press/H2D-Pro-sourced, not clearly the base-H2D wiki spec.
- **`--load-printers` / `--allow-newer-file`** — not in the official BambuStudio wiki flag list; confirm with `-h`.
- Per-material **temp/retraction numbers** are starting ranges; **ABS/ASA bed 110 °C and PAHT-CF nozzle 290 °C are range-tops, not typical.** Verify against the spool label and current Bambu profile.
- CLI behavior is **version-sensitive** (2.x Studio / 2.3.x Orca) — confirm against the installed build.

---

## Sources

- Bambu buying guide — https://bambulab.com/en/support/buying-guide
- H2D dual-nozzle printable range (Wiki) — https://wiki.bambulab.com/en/h2/manual/printable-range-for-dual-nozzles
- A2L (Hackster) — https://www.hackster.io/news/bambu-lab-expands-the-a-series-lineup-with-the-new-a2l-3d-printer-46a3c4826758
- Layer height (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/layer-height
- Studio pages outline (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/studio-pages-outline
- Support (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/support
- Seam settings (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/Seam
- Dots on the print (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/dots-on-the-print
- Brim / auto-brim (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/auto-brim
- Brim Ears (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/brim-ears
- Use disc to avoid warping (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/use-disc-to-avoid-warping
- Printing from Bambu Studio (Wiki) — https://wiki.bambulab.com/en/x1/manual/print-from-bambu-studio
- Enable LAN mode (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/enable-lan-mode
- MakerWorld print-profile upload (Wiki) — https://wiki.bambulab.com/en/makerworld/tutorials/print-profile-upload
- PLA Usage Guide (Wiki) — https://wiki.bambulab.com/en/filament/pla
- PETG Usage Guide (Wiki) — https://wiki.bambulab.com/en/filament/petg
- ASA-CF / PAHT-CF guide (Wiki) — https://wiki.bambulab.com/en/filament/asacf_pahtcf
- Filament material table (Wiki) — https://wiki.bambulab.com/en/general/filament-guide-material-table
- Bambu PAHT-CF Technical Data Sheet — https://www.solidprint3d.co.uk/wp-content/uploads/2023/08/Bambu-PAHT-CF_Technical-Data-Sheet.pdf
- Chamber temperature (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/chamber-temperature
- Flow Dynamics Calibration (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/calibration_pa
- Flow Rate Calibration (Wiki) — https://wiki.bambulab.com/en/software/bambu-studio/calibration_flow_rate
- Auto flow rate by micro-lidar (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/flowrate-calibration-by-microlidar
- Flow Dynamics vs Flow Rate persistence (Bambu forum) — https://forum.bambulab.com/t/when-to-use-flow-dynamics-calibration-option-when-printing/57468
- PA removed from filament setting (Bambu forum) — https://forum.bambulab.com/t/pressure-advance-removed-from-filament-setting/42540
- OrcaSlicer Calibration wiki — https://github.com/OrcaSlicer/OrcaSlicer/wiki/Calibration
- BambuStudio Command-Line Usage (official wiki) — https://github.com/bambulab/BambuStudio/wiki/Command-Line-Usage
- CLI cannot apply external presets (Bambu forum) — https://forum.bambulab.com/t/cli-cannot-apply-external-presets/197842
- OrcaSlicer CLI discussion #8593 — https://github.com/OrcaSlicer/OrcaSlicer/discussions/8593
- DeepWiki: OrcaSlicer CLI & headless — https://deepwiki.com/SoftFever/OrcaSlicer/10.2-cli-mode-and-headless-operation
- Printago Orca CLI reference — https://printago.io/blog/orca-slicer-cli-reference
- Printago Bambu Studio CLI reference — https://printago.io/blog/bambu-studio-cli-reference
- Warping (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/printed-model-warping
- First-layer test (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/identify-and-fix-first-layer-issues-with-a-test-print
- Bad print quality (Wiki) — https://wiki.bambulab.com/en/knowledge-sharing/troubleshooting-printing-issues
