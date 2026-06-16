#!/usr/bin/env python3
"""scaffold.py — stand up a runnable parametric-3D-printing project in one command.

Creates a self-contained folder you can render and slice immediately:

    <name>/
      <name>.scad      parametric, Customizer-annotated starter (box + friction-fit lid)
      params.json      a Customizer parameter set (use with: render.sh -p params.json -P default)
      variants.json    an example grid for batch rendering (make variants)
      Makefile         make stl | 3mf | png | variants | clean
      README.md        how to render, validate, slice, and print
      scad_params.py   copied helper so `make variants` works standalone

Usage:
    scaffold.py my-box                 # -> ./my-box/
    scaffold.py knob --outdir ~/cad    # -> ~/cad/knob/
    scaffold.py bracket --starter blank

Then:
    cd my-box && make            # -> my-box.stl   (needs OpenSCAD on PATH or $OPENSCAD)
"""
import argparse
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = os.path.normpath(os.path.join(HERE, "..", "assets", "templates"))

BLANK_SCAD = '''\
// {name}.scad — parametric part. Units = mm, Z up, part sits on the bed (z = 0).

/* [Main] */
size  = 30;     // [10:120]  overall size
wall  = 2;      // [0.8:0.2:5] wall thickness (>= 2x nozzle)

/* [Quality] */
fn = 64;        // [16:8:160] facets per circle

/* [Hidden] */
$fn = fn;

// Build your part here. Example: a cube with a centered through-hole.
difference() {{
    cube([size, size, size/2], center = true);
    cylinder(h = size, d = size/3, center = true);
}}
'''

VARIANTS_JSON = '''\
{
  "format": "stl",
  "grid": { "width": [40, 60, 80], "height": [20, 30] }
}
'''

README_TMPL = '''\
# {name}

A parametric 3D-printable part authored in OpenSCAD. Every dimension is a named
parameter at the top of `{name}.scad`, so you regenerate variants instead of
re-modeling.

## Build

```bash
make            # -> {name}.stl   (binary STL)
make 3mf        # -> {name}.3mf   (preferred for Bambu Studio: carries mm units + color)
make png        # -> {name}.png   (preview; on a headless server: xvfb-run -a make png)
make variants   # render every combination in variants.json into ./build/
make clean
```

Override the OpenSCAD binary if it isn't on PATH:

```bash
make OPENSCAD=/path/to/openscad
```

## Tune parameters

List what's tunable, then override per-render without editing the file:

```bash
python3 scad_params.py list {name}.scad
openscad -D 'size=80' -D 'wall=3' -o big.stl {name}.scad     # ad-hoc override
openscad -p params.json -P default -o {name}.stl {name}.scad # saved parameter set
```

## Validate before slicing

```bash
python3 mesh_tool.py info {name}.stl     # watertight? manifold? size & volume
```

A part must be **watertight + manifold + mm units** to slice cleanly.

## Slice & print (Bambu Lab)

1. Open `{name}.3mf` (or `.stl`) in **Bambu Studio** or **OrcaSlicer**.
2. Pick your printer + filament profile (PLA 0.20 mm is a safe default).
3. Orient so the strongest direction runs along the layers; add supports only for
   overhangs steeper than ~45°.
4. Slice, preview, and send to the printer (LAN or cloud).

See the skill's `references/bambu-lab.md` and `references/design-for-printing.md`
for profiles, supports, tolerances, and design rules.
'''


def die(msg):
    print(f"scaffold.py: {msg}", file=sys.stderr)
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="project name (also the .scad basename)")
    ap.add_argument("--outdir", default=".", help="where to create the project folder")
    ap.add_argument("--starter", choices=["box", "blank"], default="box",
                    help="box = parametric box+lid (default); blank = minimal stub")
    ap.add_argument("--force", action="store_true", help="overwrite an existing folder")
    a = ap.parse_args()

    if not re.match(r'^[A-Za-z0-9_-]+$', a.name):
        die("name must be letters/digits/-/_ only")
    proj = os.path.join(os.path.expanduser(a.outdir), a.name)
    if os.path.exists(proj) and not a.force:
        die(f"{proj} already exists (use --force to overwrite)")
    os.makedirs(proj, exist_ok=True)

    scad_path = os.path.join(proj, f"{a.name}.scad")
    if a.starter == "box":
        src = os.path.join(TEMPLATES, "parametric-box.scad")
        if os.path.exists(src):
            shutil.copyfile(src, scad_path)
        else:  # templates not alongside (e.g. script copied out) -> fall back to blank
            open(scad_path, "w").write(BLANK_SCAD.format(name=a.name))
    else:
        open(scad_path, "w").write(BLANK_SCAD.format(name=a.name))

    # Makefile from template, names substituted
    mk_src = os.path.join(TEMPLATES, "Makefile.tmpl")
    mk_text = open(mk_src).read() if os.path.exists(mk_src) else \
        "all:\n\t$(OPENSCAD) -o __NAME__.stl __NAME__.scad\n"
    open(os.path.join(proj, "Makefile"), "w").write(mk_text.replace("__NAME__", a.name))

    open(os.path.join(proj, "variants.json"), "w").write(VARIANTS_JSON)
    open(os.path.join(proj, "README.md"), "w").write(README_TMPL.format(name=a.name))

    # copy helper scripts so the project is standalone (make variants / validation)
    for helper in ("scad_params.py", "mesh_tool.py"):
        s = os.path.join(HERE, helper)
        if os.path.exists(s):
            shutil.copyfile(s, os.path.join(proj, helper))

    # a params.json starter (best-effort: parse the scad if scad_params is importable)
    try:
        sys.path.insert(0, HERE)
        import scad_params  # noqa
        params = scad_params.parse_params(scad_path)
        import json
        pset = {p["name"]: str(p["value"]).strip('"') for p in params}
        json.dump({"parameterSets": {"default": pset}, "fileFormatVersion": "1"},
                  open(os.path.join(proj, "params.json"), "w"), indent=2)
    except Exception:
        open(os.path.join(proj, "params.json"), "w").write(
            '{\n  "parameterSets": { "default": {} },\n  "fileFormatVersion": "1"\n}\n')

    print(f"created {proj}/")
    for f in sorted(os.listdir(proj)):
        print(f"  {f}")
    print(f"\nnext:  cd {proj} && make            # builds {a.name}.stl")
    print(f"       python3 mesh_tool.py info {a.name}.stl")


if __name__ == "__main__":
    main()
