#!/usr/bin/env python3
"""scad_params.py — read OpenSCAD Customizer parameters and batch-render variants.

Parametric design pays off when ONE .scad emits MANY parts. This tool:
  list   FILE.scad                     show the tunable top-level parameters
  json   FILE.scad -o params.json      emit a Customizer parameter-set file (-p)
  batch  FILE.scad matrix.json -d OUT  render every variant in matrix.json

The OpenSCAD binary is resolved from $OPENSCAD, then `openscad`, then
`openscad-nightly`. See ../references/openscad-cli.md.

A parameter is a top-level assignment `name = value;` placed before the first
module/function, optionally annotated for the Customizer:
    /* [Group] */            -> starts a tab/group
    width = 40;   // [10:100]  slider min:max  (or [10:5:100] min:step:max)
    style = "a";  // [a,b,c]    dropdown
    depth = 12;   // label / tooltip text
    // /* [Hidden] */ hides the rest from the Customizer
"""
import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys

ASSIGN_RE = re.compile(r'^(?P<indent>\s*)(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<val>.+?);\s*(?P<cmt>//.*)?$')
GROUP_RE = re.compile(r'^\s*/\*\s*\[(?P<g>[^\]]+)\]\s*\*/')
RANGE_RE = re.compile(r'\[\s*([-\d.]+)\s*:\s*([-\d.]+)\s*(?::\s*([-\d.]+)\s*)?\]')
LIST_RE = re.compile(r'\[([^\]:]+)\]')  # dropdown like [a, b, c]


def die(msg, code=2):
    print(f"scad_params.py: {msg}", file=sys.stderr)
    sys.exit(code)


def resolve_openscad():
    env = os.environ.get("OPENSCAD")
    if env and (shutil.which(env) or os.path.isfile(env)):
        return env
    for c in ("openscad", "openscad-nightly"):
        if shutil.which(c):
            return c
    die("OpenSCAD not found. Set $OPENSCAD or install it (see references/openscad-cli.md).", 3)


def parse_params(path):
    """Return list of dicts: {name, value, group, comment, slider, choices}."""
    if not os.path.exists(path):
        die(f"no such file: {path}")
    params = []
    group = "Parameters"
    in_def = False  # once we hit a module/function, top-level params end
    hidden = False
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        g = GROUP_RE.match(line)
        if g:
            name = g.group("g").strip()
            hidden = name.lower() == "hidden"
            group = name
            continue
        if re.match(r'^\s*(module|function)\s+\w+', line):
            in_def = True
        if in_def or hidden:
            continue
        m = ASSIGN_RE.match(line)
        if not m or m.group("indent"):  # only column-0 (top-level) assignments
            continue
        cmt = (m.group("cmt") or "").lstrip("/ ").strip()
        slider = None
        choices = None
        rng = RANGE_RE.search(m.group("cmt") or "")
        if rng:
            g1, g2, g3 = rng.groups()
            # OpenSCAD: [min:max] (2 vals) or [min:step:max] (3 vals — middle is the step)
            if g3 is not None:
                slider = {"min": float(g1), "max": float(g3), "step": float(g2)}
            else:
                slider = {"min": float(g1), "max": float(g2), "step": None}
            cmt = RANGE_RE.sub("", cmt).strip()
        elif (m.group("cmt") or "") and LIST_RE.search(m.group("cmt")):
            choices = [c.strip() for c in LIST_RE.search(m.group("cmt")).group(1).split(",")]
            cmt = LIST_RE.sub("", cmt).strip()
        params.append({
            "name": m.group("name"), "value": m.group("val").strip(),
            "group": group, "comment": cmt, "slider": slider, "choices": choices,
        })
    return params


def cmd_list(a):
    params = parse_params(a.file)
    if a.json:
        print(json.dumps(params, indent=2))
        return
    if not params:
        print("no top-level Customizer parameters found "
              "(are assignments at column 0, before the first module/function?)")
        return
    cur = None
    for p in params:
        if p["group"] != cur:
            cur = p["group"]
            print(f"\n[{cur}]")
        extra = ""
        if p["slider"]:
            s = p["slider"]
            extra = f"  ({s['min']}..{s['max']}" + (f" step {s['step']}" if s["step"] else "") + ")"
        elif p["choices"]:
            extra = f"  {{{', '.join(p['choices'])}}}"
        cmt = f"  — {p['comment']}" if p["comment"] else ""
        print(f"  {p['name']:<18} = {p['value']:<10}{extra}{cmt}")
    print(f"\n{len(params)} parameter(s). Override at render: render.sh {a.file} -D 'name=value'")


def cmd_json(a):
    params = parse_params(a.file)
    pset = {p["name"]: str(p["value"]).strip('"') for p in params}
    out = {"parameterSets": {a.set: pset}, "fileFormatVersion": "1"}
    with open(a.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {a.output} with set '{a.set}' ({len(pset)} params).")
    print(f"use it: render.sh {a.file} -o out.stl -p {a.output} -P {a.set}")


def _fmt_define(name, value):
    # numbers/bools/vectors pass through; bare strings get quoted for OpenSCAD
    sval = str(value)
    if isinstance(value, str) and not re.match(r'^(-?[\d.]+|true|false|\[.*\]|".*")$', sval):
        sval = f'"{value}"'
    return f"{name}={sval}"


def _variants_from_matrix(matrix):
    """matrix.json: either {'variants':[{name,params}]} or {'grid':{p:[..]}}."""
    if "variants" in matrix:
        for v in matrix["variants"]:
            yield v["name"], v["params"]
    elif "grid" in matrix:
        keys = list(matrix["grid"].keys())
        for combo in itertools.product(*[matrix["grid"][k] for k in keys]):
            params = dict(zip(keys, combo))
            name = "_".join(f"{k}{str(v).replace('.', 'p')}" for k, v in params.items())
            yield name, params
    else:
        die("matrix.json needs a 'variants' list or a 'grid' object")


def cmd_batch(a):
    bin_ = resolve_openscad()
    with open(a.matrix) as f:
        matrix = json.load(f)
    fmt = a.format or matrix.get("format", "stl")
    os.makedirs(a.outdir, exist_ok=True)
    variants = list(_variants_from_matrix(matrix))
    if not variants:
        die("no variants produced from matrix.json")
    print(f"rendering {len(variants)} variant(s) of {a.file} -> {a.outdir}/*.{fmt}")
    ok = 0
    for name, params in variants:
        out = os.path.join(a.outdir, f"{name}.{fmt}")
        cmd = [bin_, "-o", out]
        if fmt == "stl":
            cmd += ["--export-format", "asciistl" if a.ascii else "binstl"]
        for k, v in params.items():
            cmd += ["-D", _fmt_define(k, v)]
        cmd.append(a.file)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0:
            print(f"  ok   {name}.{fmt}  ({os.path.getsize(out)} B)  {params}")
            ok += 1
        else:
            print(f"  FAIL {name}.{fmt}  {params}\n       {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'no output'}")
    print(f"done: {ok}/{len(variants)} succeeded.")
    if ok < len(variants):
        sys.exit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="scad_params.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list", help="show tunable parameters")
    s.add_argument("file")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("json", help="emit a Customizer parameter-set file")
    s.add_argument("file")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--set", default="default", help="parameter-set name")
    s.set_defaults(func=cmd_json)

    s = sub.add_parser("batch", help="render every variant in matrix.json")
    s.add_argument("file")
    s.add_argument("matrix", help="JSON with 'variants':[{name,params}] or 'grid':{p:[..]}")
    s.add_argument("-d", "--outdir", required=True)
    s.add_argument("-f", "--format", help="stl|3mf|off|amf (default stl)")
    s.add_argument("--ascii", action="store_true", help="ascii STL instead of binary")
    s.set_defaults(func=cmd_batch)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
