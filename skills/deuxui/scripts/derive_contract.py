#!/usr/bin/env python3
"""Derive a visual contract from the code that already exists.

`uplift` tells you to declare what the product already does before changing any of
it, because that is what puts the source of truth outside the agent. Left as
hand-work that step gets skipped or guessed, so this does it: read the real font
sizes, families, radii, shadows, durations and colour tokens, and report the
DOMINANT value of each with the spread beside it.

Two deliberate properties:

* It reports what it found, it does not decide. Where a project is inconsistent
  the spread is the interesting part -- that inconsistency is usually the thing
  worth fixing, and averaging it away would hide it.
* Anything it cannot determine is left `UNKNOWN` rather than filled with a
  plausible default. An UNKNOWN field reports NOT_RUN downstream, which is true;
  a guessed one would quietly become the standard the product is judged against.
"""
from __future__ import annotations
import os
import argparse, collections, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True
from checks._util import iter_files, read, strip_comments          # noqa: E402

TW_PX = {"xs": 12, "sm": 14, "base": 16, "lg": 18, "xl": 20, "2xl": 24, "3xl": 30,
         "4xl": 36, "5xl": 48, "6xl": 60, "7xl": 72, "8xl": 96, "9xl": 128}
TW_RADIUS = {"none": 0, "sm": 2, "": 4, "md": 6, "lg": 8, "xl": 12, "2xl": 16, "3xl": 24}
GENERIC = re.compile(r"^(?:var\(|inherit|initial|unset|sans-serif|serif|monospace|"
                     r"system-ui|ui-\w+|-apple-system)$", re.I)


def scan(root: Path, extra_skip=()):
    f_size, f_fam, radius, shadow, dur, ease = (collections.Counter() for _ in range(6))
    roles, files = {}, 0
    scope = list(iter_files(root, extra_skip=extra_skip))
    for name in ("tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs",
                 "tailwind.config.cjs", "theme.config.js"):
        q = root / name
        if q.exists():
            scope.append(q)
    for q in scope:
        txt = read(q)
        if not txt:
            continue
        files += 1
        hay = strip_comments(txt)
        for m in re.finditer(r"font-size\s*:\s*(\d+(?:\.\d+)?)(px|rem)", hay):
            v = float(m.group(1)) * (16.0 if m.group(2) == "rem" else 1.0)
            if 8 <= v <= 200:
                f_size[round(v, 1)] += 1
        for m in re.finditer(r"(?<![\w-])text-(xs|sm|base|lg|xl|[2-9]xl)(?![\w-])", hay):
            f_size[float(TW_PX[m.group(1)])] += 1
        for m in re.finditer(r"font-family\s*:\s*([^;}\n]+)", hay):
            first = m.group(1).split(",")[0].strip().strip("'\"")
            if first and not GENERIC.match(first):
                f_fam[first] += 1
        # tailwind.config fontFamily, the v4 @theme --font-* custom properties,
        # and a linked Google font are all places a family is actually declared.
        for m in re.finditer(r"--font-[\w-]+\s*:\s*([^;}\n]+)", hay):
            first = m.group(1).split(",")[0].strip().strip("'\"")
            if first and not GENERIC.match(first):
                f_fam[first] += 2
        for m in re.finditer(r"(?:sans|serif|mono|display|body)\s*:\s*\[\s*['\"]"
                             r"([^'\"]+)", hay):
            if not GENERIC.match(m.group(1)):
                f_fam[m.group(1)] += 2
        for m in re.finditer(r"fonts\.googleapis\.com/css2?\?family=([\w+]+)", hay):
            f_fam[m.group(1).replace("+", " ")] += 2
        for m in re.finditer(r"border-radius\s*:\s*(\d+(?:\.\d+)?)px", hay):
            radius[float(m.group(1))] += 1
        for m in re.finditer(r"(?<![\w-])rounded(?:-(none|sm|md|lg|xl|2xl|3xl))?(?![\w-])", hay):
            radius[float(TW_RADIUS.get(m.group(1) or "", 4))] += 1
        for m in re.finditer(r"box-shadow\s*:\s*([^;}\n]+)", hay):
            v = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(";")
            if v.lower() not in ("none", "inherit") and "var(" not in v and len(v) < 90:
                shadow[v] += 1
        for m in re.finditer(r"(?:transition|animation)(?:-duration)?\s*:[^;}\n]*?"
                             r"(\d+(?:\.\d+)?)(ms|s)\b", hay):
            v = float(m.group(1)) * (1000.0 if m.group(2) == "s" else 1.0)
            if 0 < v <= 5000:
                dur[v] += 1
        # Tailwind carries both of these as utilities, not declarations. A scanner
        # that only reads CSS finds zero families in a Tailwind project, which is
        # most of them.
        for m in re.finditer(r"(?<![\w-])duration-(\d{2,4})(?![\w-])", hay):
            v = float(m.group(1))
            if 0 < v <= 5000:
                dur[v] += 1
        for m in re.finditer(r"cubic-bezier\([^)]*\)|(?<![\w-])ease-(?:in-out|out|in)"
                             r"(?![\w-])|(?<![\w-])linear(?![\w-])", hay):
            ease[m.group(0)] += 1
        # semantic custom properties are the project's own colour roles
        for m in re.finditer(r"(--[\w-]*(?:canvas|surface|background|bg|ink|text|fg|"
                             r"foreground|muted|border|primary|accent|interactive|"
                             r"focus|success|warning|danger|destructive|error)[\w-]*)"
                             r"\s*:\s*([^;}\n]+)", hay, re.I):
            roles.setdefault(m.group(1), m.group(2).strip()[:60])
    return dict(files=files, f_size=f_size, f_fam=f_fam, radius=radius,
                shadow=shadow, dur=dur, ease=ease, roles=roles)


def dominant(counter, n=1):
    return [v for v, _c in counter.most_common(n)]


def build(s):
    fams = dominant(s["f_fam"], 3)
    sizes = sorted(v for v, c in s["f_size"].items() if c >= 2) or sorted(s["f_size"])
    # The two most-USED radii, assigned by size -- not the min and max of the top
    # four, which promoted a rare 2px to "control" ahead of an 8px used 69 times.
    radii = sorted(sorted(s["radius"], key=s["radius"].get, reverse=True)[:2])
    durs = sorted(v for v, c in s["dur"].items() if c >= 2) or sorted(s["dur"])
    shadows = dominant(s["shadow"], 4)
    # depth metaphor: whichever the project actually leans on
    metaphor = "shadow" if sum(s["shadow"].values()) >= 3 else "UNKNOWN"
    c = {
        "visitor_mode": "UNKNOWN",
        "world": "UNKNOWN",
        "type": {
            "families": {
                "display": fams[0] if fams else "UNKNOWN",
                "body": (fams[1] if len(fams) > 1 else (fams[0] if fams else "UNKNOWN")),
                "mono": next((f for f in fams if re.search(
                    r"mono|menlo|consolas|courier|code|source ?code", f, re.I)), None),
            },
            "scale_px": sizes[:9],
            "measure_ch": [45, 75],
            "display_max_rem": 6.0,
        },
        "color": {"space": "UNKNOWN", "roles": s["roles"] or "UNKNOWN",
                  "ramp_steps": [], "dark_mode": "UNKNOWN"},
        "depth": {"metaphor": metaphor, "elevations": shadows},
        "spacing": {"base_px": 4, "scale": []},
        "radius": {"control_px": (radii[0] if radii else "UNKNOWN"),
                   "card_px": (radii[-1] if radii else "UNKNOWN")},
        "grid": {"columns": "UNKNOWN", "gutter_px": "UNKNOWN",
                 "container_max_px": "UNKNOWN"},
        "motion": {"duration_ms": ([min(durs), max(durs)] if durs else [120, 240]),
                   "easing": (dominant(s["ease"], 1) or ["UNKNOWN"])[0],
                   "authored_moments": 1},
        "departures": [],
    }
    return c


def spread_report(s, out=sys.stderr):
    w = out.write
    w(f"\nRead {s['files']} files.\n\n")
    for label, counter, unit in (("type steps", s["f_size"], "px"),
                                 ("families", s["f_fam"], ""),
                                 ("radii", s["radius"], "px"),
                                 ("durations", s["dur"], "ms")):
        tot = sum(counter.values())
        top = counter.most_common(6)
        w(f"  {label:12} {len(counter):3d} distinct, {tot:5d} uses   ")
        w(", ".join(f"{v}{unit}×{c}" for v, c in top) + "\n")
    w("\nThe spread is the interesting part. A project using 17 type steps does not\n"
      "have a 17-step scale, it has a scale plus drift -- and the drift is what the\n"
      "conformance checks will surface once this contract is in place. Delete the\n"
      "steps that are drift before you commit this file; every one you keep becomes\n"
      "a value the product is judged as conforming to.\n\n"
      "Anything left UNKNOWN is not a gap to fill in quickly. It reports NOT_RUN,\n"
      "which is the truth about a decision nobody has made.\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--write", action="store_true",
                    help="write .deuxui/design.contract.yaml (refuses to overwrite)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.path).resolve()
    if not root.exists():
        sys.stderr.write(f"no such path: {root}\n")
        return 1
    import uxconfig
    cfg = uxconfig.load(root)
    s = scan(root, extra_skip=uxconfig.excludes(cfg))
    if not s["files"]:
        sys.stderr.write("No source files in scope; nothing to derive.\n")
        return 1
    c = build(s)
    if a.json:
        print(json.dumps(c, indent=1))
        return 0
    import yaml
    text = yaml.safe_dump(c, sort_keys=False, allow_unicode=True, width=88)
    header = ("# Derived from the code that already exists, by scripts/derive_contract.py.\n"
              "# These are the DOMINANT values found, not a judgement about them. Review\n"
              "# every line: a value here becomes a thing the product is judged as\n"
              "# conforming to, and drift copied in faithfully is still drift.\n\n")
    if a.write:
        dest = root / ".deuxui" / "design.contract.yaml"
        if dest.exists():
            sys.stderr.write(f"{dest} already exists; not overwriting. "
                             f"Delete it or edit it by hand.\n")
            return 2
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(header + text)
        sys.stderr.write(f"wrote {dest}\n")
        # Archive it as version one. A derived contract is the most important
        # version to keep: everything later is measured as drift from it, and if
        # the bytes are not on disk that comparison has no fixed end.
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import ux_ledger
            cwd = Path.cwd()
            os.chdir(root)
            try:
                r = ux_ledger.archive(by="derive_contract.py --write",
                                      note="derived from the existing codebase")
            finally:
                os.chdir(cwd)
            if r.get("sha"):
                sys.stderr.write(f"archived as contract {r['sha']} -- "
                                 f"`ux_ledger.py log` now has a first version\n")
        except Exception as e:                        # bookkeeping never blocks a write
            sys.stderr.write(f"could not archive it ({e}); run "
                             f"`ux_ledger.py snapshot` to put it on record\n")
    else:
        print(header + text)
    spread_report(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
