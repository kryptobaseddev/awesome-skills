#!/usr/bin/env python3
"""mesh_tool.py — inspect, validate, repair, measure, convert, and edit 3D meshes.

The programmatic-STL workhorse: it lets an agent modify a mesh that already exists
(an STL/3MF/OBJ someone downloaded or another tool produced) WITHOUT a GUI CAD app.
For *generating* parametric geometry from scratch, prefer OpenSCAD (see render.sh) —
mesh editing is destructive and can't recover lost parametric intent.

Backed by trimesh; boolean ops use the manifold3d engine (robust, watertight output).

Install (once):
    python3 -m pip install "trimesh[easy]" manifold3d numpy-stl

Subcommands (run `mesh_tool.py <cmd> -h` for details):
    info FILE                 format, triangles, watertight/manifold, volume, bbox
    validate FILE             exit 1 if not printable (not watertight/manifold)
    repair FILE -o OUT        fill holes, fix normals, drop degenerate tris
    measure FILE [--material] bbox in mm, volume, area, est. filament length/mass
    convert IN OUT            change format (stl/3mf/obj/ply/off) — units preserved
    scale FILE -o OUT (...)   uniform factor, or fit to a target size in mm
    transform FILE -o OUT     translate / rotate / uniform-scale
    boolean OP -o OUT A B...  union | difference | intersection (manifold engine)
    arrange -o OUT A B...     lay parts out on the XY build plate, dropped to z=0
"""
import argparse
import json
import math
import os
import sys

EXT_OK = {".stl", ".3mf", ".obj", ".ply", ".off", ".glb", ".gltf"}

# PLA at 1.24 g/cm^3, 1.75 mm filament -> cross-section 2.405 mm^2 = 0.002405 cm^2
PLA_DENSITY_G_CM3 = 1.24
FILAMENT_AREA_CM2 = math.pi * (0.175 / 2) ** 2  # 1.75 mm dia, in cm


def _die(msg, code=2):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def _require_trimesh():
    try:
        import trimesh  # noqa
        return __import__("trimesh")
    except ImportError:
        _die(
            "trimesh is not installed. Run:\n"
            '    python3 -m pip install "trimesh[easy]" manifold3d numpy-stl',
            3,
        )


def _load(path):
    tm = _require_trimesh()
    if not os.path.exists(path):
        _die(f"no such file: {path}")
    mesh = tm.load(path, force="mesh")
    if mesh is None or not hasattr(mesh, "vertices"):
        _die(f"could not load a mesh from {path}")
    return tm, mesh


def _safe(fn, default=None):
    """Some trimesh properties need scipy/networkx; degrade gracefully if absent."""
    try:
        return fn()
    except Exception:
        return default


def _facts(mesh):
    """Common geometry facts as a dict (mm units assumed — STL is unitless)."""
    ext = mesh.bounds[1] - mesh.bounds[0]
    watertight = bool(mesh.is_watertight)
    winding = bool(mesh.is_winding_consistent)
    is_vol = _safe(lambda: bool(mesh.is_volume), watertight and winding)
    return {
        "triangles": int(len(mesh.faces)),
        "vertices": int(len(mesh.vertices)),
        "watertight": watertight,
        "winding_consistent": winding,
        "is_volume": is_vol,  # closed, consistent, outward normals
        "bbox_mm": [round(float(v), 3) for v in ext],
        "volume_mm3": round(float(mesh.volume), 3) if is_vol else None,
        "area_mm2": round(float(mesh.area), 3),
        "euler_number": _safe(lambda: int(mesh.euler_number)),
        "body_count": _safe(lambda: int(mesh.body_count), 1),
    }


def cmd_info(a):
    tm, mesh = _load(a.file)
    f = _facts(mesh)
    f["format"] = os.path.splitext(a.file)[1].lstrip(".").lower()
    f["printable"] = f["watertight"] and f["winding_consistent"]
    if a.json:
        print(json.dumps(f, indent=2))
        return
    print(f"{a.file}")
    print(f"  format        {f['format']}   triangles {f['triangles']}   bodies {f['body_count']}")
    print(f"  size (mm)     {f['bbox_mm'][0]} x {f['bbox_mm'][1]} x {f['bbox_mm'][2]}")
    vol = f["volume_mm3"]
    print(f"  volume        {vol} mm^3" + (f"  ({vol/1000:.2f} cm^3)" if vol else "  (n/a — not closed)"))
    print(f"  watertight    {f['watertight']}")
    print(f"  manifold/vol  {f['is_volume']} (winding {f['winding_consistent']})")
    verdict = "PRINTABLE" if f["printable"] else "NOT printable as-is — run: mesh_tool.py repair"
    print(f"  => {verdict}")


def cmd_validate(a):
    tm, mesh = _load(a.file)
    f = _facts(mesh)
    problems = []
    if not f["watertight"]:
        problems.append("not watertight (open edges / holes)")
    if not f["winding_consistent"]:
        problems.append("inconsistent winding (normals not all outward)")
    if f["body_count"] > 1 and not a.allow_multibody:
        problems.append(f"{f['body_count']} disconnected bodies (use --allow-multibody if intended)")
    if problems:
        print(f"FAIL {a.file}")
        for p in problems:
            print(f"  - {p}")
        print("  fix with: mesh_tool.py repair " + a.file + " -o fixed.stl")
        sys.exit(1)
    print(f"PASS {a.file} — watertight, manifold, ready to slice")


def cmd_repair(a):
    tm, mesh = _load(a.file)
    before = _facts(mesh)
    # trimesh.repair: consistent winding, outward normals, fill holes, drop junk
    mesh.process(validate=True)
    mesh.remove_degenerate_faces() if hasattr(mesh, "remove_degenerate_faces") else None
    mesh.update_faces(mesh.unique_faces())
    mesh.remove_unreferenced_vertices()
    tm.repair.fix_normals(mesh)
    tm.repair.fix_winding(mesh)
    tm.repair.fill_holes(mesh)
    tm.repair.fix_inversion(mesh)
    after = _facts(mesh)
    mesh.export(a.output)
    print(f"repaired {a.file} -> {a.output}")
    print(f"  watertight {before['watertight']} -> {after['watertight']}")
    print(f"  is_volume  {before['is_volume']} -> {after['is_volume']}")
    print(f"  triangles  {before['triangles']} -> {after['triangles']}")
    if not after["watertight"]:
        print("  WARNING: still not watertight. Heavy damage may need pymeshlab or a re-model.", file=sys.stderr)


def cmd_measure(a):
    tm, mesh = _load(a.file)
    f = _facts(mesh)
    ext = f["bbox_mm"]
    print(f"bounding box : {ext[0]} x {ext[1]} x {ext[2]} mm")
    print(f"surface area : {f['area_mm2']:.1f} mm^2")
    if f["volume_mm3"]:
        vol_cm3 = f["volume_mm3"] / 1000.0
        print(f"volume       : {f['volume_mm3']:.1f} mm^3  ({vol_cm3:.2f} cm^3)")
        if a.material:
            # rough SOLID-fill estimate; real prints use infill, so this is an upper bound
            mass_g = vol_cm3 * a.density
            length_mm = f["volume_mm3"] / (FILAMENT_AREA_CM2 * 100.0)  # mm^3 / (mm^2)
            print(f"~solid mass  : {mass_g:.1f} g at {a.density} g/cm^3 (100% infill upper bound)")
            print(f"~filament    : {length_mm/1000:.2f} m of 1.75 mm (100% infill upper bound)")
    else:
        print("volume       : n/a (mesh is not closed — repair first)")


def cmd_convert(a):
    tm, mesh = _load(a.inp)
    ext = os.path.splitext(a.out)[1].lower()
    if ext not in EXT_OK:
        _die(f"unsupported output format '{ext}'. Supported: {sorted(EXT_OK)}")
    mesh.export(a.out)
    print(f"converted {a.inp} -> {a.out}")
    if ext == ".3mf":
        print("  (3MF carries mm units + color/material; preferred for Bambu Studio)")


def cmd_scale(a):
    tm, mesh = _load(a.file)
    ext = mesh.bounds[1] - mesh.bounds[0]
    if a.factor is not None:
        s = [a.factor, a.factor, a.factor]
    elif a.to_x is not None:
        k = a.to_x / ext[0]
        s = [k, k, k]
    elif a.fit is not None:
        tx, ty, tz = [float(v) for v in a.fit.lower().split("x")]
        k = min(tx / ext[0], ty / ext[1], tz / ext[2])
        s = [k, k, k]
    else:
        _die("give one of --factor, --to-x, or --fit XxYxZ")
    mesh.apply_scale(s)
    mesh.export(a.output)
    new = mesh.bounds[1] - mesh.bounds[0]
    print(f"scaled {a.file} -> {a.output}  (x{s[0]:.4f})")
    print(f"  new size: {new[0]:.2f} x {new[1]:.2f} x {new[2]:.2f} mm")


def cmd_transform(a):
    tm, mesh = _load(a.file)
    if a.scale is not None:
        mesh.apply_scale(a.scale)
    if a.rotate:
        axis_name, deg = a.rotate.split(",")
        axis = {"x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}[axis_name.strip().lower()]
        R = tm.transformations.rotation_matrix(math.radians(float(deg)), axis, mesh.centroid)
        mesh.apply_transform(R)
    if a.translate:
        dx, dy, dz = [float(v) for v in a.translate.split(",")]
        mesh.apply_translation([dx, dy, dz])
    mesh.export(a.output)
    print(f"transformed {a.file} -> {a.output}")


def _manifold_boolean(tm, op, meshes):
    try:
        return tm.boolean.boolean_manifold(meshes, op) if hasattr(tm.boolean, "boolean_manifold") \
            else getattr(tm.boolean, op)(meshes)
    except Exception as e:
        _die(f"boolean {op} failed ({e}). Ensure manifold3d is installed: pip install manifold3d", 3)


def cmd_boolean(a):
    tm = _require_trimesh()
    meshes = [tm.load(p, force="mesh") for p in a.files]
    if len(meshes) < 2:
        _die("boolean needs at least 2 input meshes")
    result = _manifold_boolean(tm, a.op, meshes)
    result.export(a.output)
    f = _facts(result)
    print(f"{a.op}({', '.join(a.files)}) -> {a.output}")
    print(f"  watertight {f['watertight']}  volume {f['volume_mm3']} mm^3")


def cmd_arrange(a):
    tm = _require_trimesh()
    meshes = [tm.load(p, force="mesh") for p in a.files]
    gap = a.gap
    # simple shelf-packing on XY, drop each to z=0
    cols = max(1, int(math.ceil(math.sqrt(len(meshes)))))
    scene = tm.Scene()
    x = y = 0.0
    row_h = 0.0
    placed = 0
    for i, m in enumerate(meshes):
        ext = m.bounds[1] - m.bounds[0]
        m.apply_translation(-m.bounds[0])  # corner to origin, min-z -> 0
        m.apply_translation([x, y, 0])
        scene.add_geometry(m)
        x += ext[0] + gap
        row_h = max(row_h, ext[1])
        placed += 1
        if placed % cols == 0:
            x = 0.0
            y += row_h + gap
            row_h = 0.0
    combined = tm.util.concatenate(scene.dump())
    combined.export(a.output)
    print(f"arranged {len(meshes)} parts -> {a.output} ({cols} columns, {gap} mm gap)")


def build_parser():
    p = argparse.ArgumentParser(prog="mesh_tool.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("info", help="summarize a mesh")
    s.add_argument("file")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_info)

    s = sub.add_parser("validate", help="exit 1 if not printable")
    s.add_argument("file")
    s.add_argument("--allow-multibody", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("repair", help="attempt to make watertight/manifold")
    s.add_argument("file")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_repair)

    s = sub.add_parser("measure", help="dimensions, volume, filament estimate")
    s.add_argument("file")
    s.add_argument("--material", action="store_true", help="also estimate solid mass/filament")
    s.add_argument("--density", type=float, default=PLA_DENSITY_G_CM3, help="g/cm^3 (default PLA 1.24)")
    s.set_defaults(func=cmd_measure)

    s = sub.add_parser("convert", help="change file format")
    s.add_argument("inp")
    s.add_argument("out")
    s.set_defaults(func=cmd_convert)

    s = sub.add_parser("scale", help="resize")
    s.add_argument("file")
    s.add_argument("-o", "--output", required=True)
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--factor", type=float, help="uniform multiplier (e.g. 2.0)")
    g.add_argument("--to-x", type=float, help="scale so X equals this many mm")
    g.add_argument("--fit", help="uniformly scale to fit within XxYxZ mm (e.g. 200x200x200)")
    s.set_defaults(func=cmd_scale)

    s = sub.add_parser("transform", help="translate/rotate/scale")
    s.add_argument("file")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--translate", help="dx,dy,dz in mm")
    s.add_argument("--rotate", help="axis,deg e.g. z,90")
    s.add_argument("--scale", type=float, help="uniform factor")
    s.set_defaults(func=cmd_transform)

    s = sub.add_parser("boolean", help="CSG on existing meshes")
    s.add_argument("op", choices=["union", "difference", "intersection"])
    s.add_argument("files", nargs="+")
    s.add_argument("-o", "--output", required=True)
    s.set_defaults(func=cmd_boolean)

    s = sub.add_parser("arrange", help="lay parts out on the build plate")
    s.add_argument("files", nargs="+")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--gap", type=float, default=5.0, help="mm between parts (default 5)")
    s.set_defaults(func=cmd_arrange)

    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
