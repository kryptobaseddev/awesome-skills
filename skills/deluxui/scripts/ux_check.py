#!/usr/bin/env python3
"""deluxui static tier -- source checks bound to rule IDs.

Reports PASS / FAIL / NOT_RUN / NOT_APPLICABLE per rule. It never reports PASS
for something it did not examine, which is the whole point: a check that could
not run is more useful as an admission than as a silent gap.

  ux_check.py <path> [--json] [--detector ID]... [--inventory INTENT] [--signals]
  echo '<PostToolUse hook json>' | ux_check.py --stdin

Exit: 0 clean, 2 findings, 1 usage error.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import yaml
from checks import ALL, FileCtx, Project
from checks._util import (SOURCE_EXT, STYLE_EXT, collect_css_vars, css_of,
                          iter_files, is_generated, read, scan_tags)

RULES_DIR = Path(__file__).resolve().parent.parent / "references" / "rules"


def load_rules():
    reg = yaml.safe_load((RULES_DIR / "registry.yaml").read_text())
    det = yaml.safe_load((RULES_DIR / "detectors.yaml").read_text())
    return reg, det


# ----------------------------------------------------------------- project
def detect_project(root: Path) -> Project:
    p = Project(root=root)
    pkg = None
    for cand in (root / "package.json", *(root.glob("*/package.json"))):
        if cand.exists():
            pkg = cand
            break
    if pkg:
        try:
            data = json.loads(read(pkg))
            p.deps = set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
            tw = (data.get("dependencies", {}).get("tailwindcss")
                  or data.get("devDependencies", {}).get("tailwindcss") or "")
            m = re.search(r"(\d+)", tw)
            p.tailwind_major = int(m.group(1)) if m else 0
        except (ValueError, OSError):
            pass
    p.has_tailwind = bool(p.tailwind_major) or any("tailwind" in d for d in p.deps)
    p.has_i18n = any(re.search(r"i18n|intl|lingui|polyglot|translate", d) for d in p.deps)
    p.cssvars = collect_css_vars(root)
    if not p.tailwind_major and p.cssvars:
        p.tailwind_major = 4 if any(k.startswith("--color-") for k in p.cssvars) else 3
    css_all = []
    for f in iter_files(root, STYLE_EXT):
        t = read(f)
        css_all.append(t)
        if "@container" in t:
            p.has_container_queries = True
        if "@theme" in t or ":root" in t:
            p.token_sources.append(str(f.relative_to(root)))
    p.css_text = "\n".join(css_all)
    # Component inventory: anything under a ui/components directory.
    for f in iter_files(root, SOURCE_EXT):
        rel = str(f.relative_to(root))
        if re.search(r"(?:^|/)(?:components?|ui|design-system|primitives)/", rel):
            p.inventory.setdefault(f.stem, rel)
    return p


def classify(text: str) -> str:
    """Only Remotion gets its own surface. A page that happens to embed a 3D
    canvas is still an interface -- the 3D checks opt into "ui" as well, so
    reclassifying the whole file would silently disable every other check on it.
    That mistake is exactly the kind of quiet gap this tool exists to prevent."""
    if re.search(r"from\s+[\"']remotion[\"']|@remotion/", text):
        return "video"
    return "ui"


# ----------------------------------------------------------------- run
def run(root: Path, only=None):
    reg, det = load_rules()
    detectors = det["detectors"]
    project = detect_project(root)

    files = []
    for f in iter_files(root):
        txt = read(f)
        if not txt or is_generated(f, txt):
            continue
        ext = f.suffix
        files.append(FileCtx(path=f, rel=str(f.relative_to(root) if root.is_dir() else f.name),
                             text=txt, ext=ext,
                             tags=scan_tags(txt) if ext in SOURCE_EXT else [],
                             surface=classify(txt), css=css_of(f, txt)))

    findings, status = [], {}
    for did, chk in sorted(ALL.items()):
        if only and did not in only:
            continue
        meta = detectors.get(did, {})
        if chk.requires and not chk.requires(project):
            status[did] = ("NOT_RUN", meta.get("not_run_when", "Precondition not met."))
            continue
        pool = [f for f in files
                if (not chk.exts or f.ext in chk.exts) and f.surface in chk.surfaces]
        if not pool:
            status[did] = ("NOT_APPLICABLE", "No files of this kind in scope.")
            continue
        hits = []
        for f in pool:
            try:
                hits.extend(chk.fn(f, project) or [])
            except Exception as e:                      # a broken check must not fake a pass
                status[did] = ("NOT_RUN", f"Check raised {type(e).__name__}: {e}")
                break
        else:
            hits, extra = _cap(hits)
            status[did] = ("FAIL" if hits else "PASS",
                           f"{len(pool)} files examined"
                           + (f"; {extra} further findings of this kind not listed"
                              if extra else ""))
            findings.extend(hits)
    return project, reg, detectors, findings, status


PER_FILE_CAP = 5


def _cap(hits, cap=PER_FILE_CAP):
    """One repeated pattern in one file is one problem to fix, not forty. Report
    a few instances and say how many more there were -- a report nobody reads
    because it is 6000 lines long is worth exactly nothing."""
    seen, kept, dropped = set(), [], 0
    per_file = {}
    for h in hits:
        key = (h.file, h.line, h.snippet)
        if key in seen:
            continue
        seen.add(key)
        n = per_file.get(h.file, 0)
        if n >= cap:
            dropped += 1
            continue
        per_file[h.file] = n + 1
        kept.append(h)
    return kept, dropped


def rollup(reg, detectors, status):
    """Per-rule status. A rule nobody can test is NOT_RUN, never PASS."""
    by_rule = {}
    for did, (st, _why) in status.items():
        for rid in detectors.get(did, {}).get("rules", []):
            by_rule.setdefault(rid, []).append((did, st))
    out = {}
    for r in reg["rules"]:
        rid = r["id"]
        sts = [s for _d, s in by_rule.get(rid, [])]
        if not sts:
            out[rid] = ("NOT_RUN", "No automated detector. Needs manual verification.")
        elif "FAIL" in sts:
            out[rid] = ("FAIL", "")
        elif "PASS" in sts:
            out[rid] = ("PASS", "Static tier only. The runtime tier checks this properly.")
        elif "NOT_RUN" in sts:
            out[rid] = ("NOT_RUN", next(w for d, (s, w) in status.items()
                                        if s == "NOT_RUN" and rid in
                                        detectors.get(d, {}).get("rules", [])))
        else:
            out[rid] = ("NOT_APPLICABLE", "")
    return out


# ----------------------------------------------------------------- output
def human(project, reg, detectors, findings, status, rules, limit=40):
    w = sys.stderr.write
    sev = {r["id"]: r["severity"] for r in reg["rules"]}

    def worst(f):
        return min((sev.get(r, "P2")
                    for r in detectors.get(f.detector, {}).get("rules", [])), default="P2")

    ordered = sorted(findings, key=lambda f: (worst(f), f.file, f.line))
    shown = ordered[:limit]
    by_file = {}
    for f in shown:
        by_file.setdefault(f.file, []).append(f)
    for fname in sorted(by_file):
        w(f"\n{fname}\n")
        for f in sorted(by_file[fname], key=lambda x: x.line):
            w(f"  {f.line:>5}  {worst(f)} [{f.detector}] {f.snippet}\n")
            w(f"         -> {f.fix}\n")
    if len(ordered) > limit:
        w(f"\n... {len(ordered) - limit} more findings. Use --json for all of them, "
          f"or --max N to show more here.\n")

    counts = {k: sum(1 for v in rules.values() if v[0] == k)
              for k in ("PASS", "FAIL", "NOT_RUN", "NOT_APPLICABLE")}
    sevc = {s: sum(1 for f in ordered if worst(f) == s) for s in ("P0", "P1", "P2")}
    w("\n" + "-" * 70 + "\n")
    w(f"findings   P0 {sevc['P0']}   P1 {sevc['P1']}   P2 {sevc['P2']}"
      f"   (total {len(ordered)})\n")
    w(f"rules      NOT_RUN {counts['NOT_RUN']}   FAIL {counts['FAIL']}   "
      f"PASS {counts['PASS']}   NOT_APPLICABLE {counts['NOT_APPLICABLE']}"
      f"   of {len(rules)}\n")
    w("\nNOT_RUN is listed first on purpose: it is the count of rules nothing has\n"
      "checked yet, and it is not a pass. This is the static tier -- it reads source\n"
      "text heuristically and cannot see computed styles, real hit areas, focus order\n"
      "or any state the app only reaches at runtime. Run scripts/ux_browser.sh against\n"
      "a running app to convert those rows into real results.\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true", help="machine-readable report on stdout")
    ap.add_argument("--detector", action="append", help="run only these detector IDs")
    ap.add_argument("--inventory", metavar="INTENT",
                    help="list existing components matching INTENT (the preserve ladder)")
    ap.add_argument("--signals", action="store_true",
                    help="raw project signals as JSON; no scoring, no ranking")
    ap.add_argument("--stdin", action="store_true", help="read a PostToolUse hook payload")
    ap.add_argument("--max", type=int, default=40, help="findings to print (default 40)")
    a = ap.parse_args(argv)

    target = Path(a.path).resolve()
    if a.stdin:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            return 0
        fp = (payload.get("tool_input") or {}).get("file_path")
        if not fp or Path(fp).suffix not in (SOURCE_EXT | STYLE_EXT):
            return 0
        target = Path(fp).resolve()

    if not target.exists():
        sys.stderr.write(f"no such path: {target}\n")
        return 1

    root = target if target.is_dir() else target.parent
    while root != root.parent and not (root / "package.json").exists():
        root = root.parent
    if not (root / "package.json").exists():
        root = target if target.is_dir() else target.parent

    if a.inventory:
        p = detect_project(root)
        pat = re.compile("|".join(re.escape(w) for w in a.inventory.split()), re.I)
        hits = {n: rel for n, rel in p.inventory.items() if pat.search(n) or pat.search(rel)}
        print(json.dumps({"intent": a.inventory, "matches": hits,
                          "inventory_size": len(p.inventory),
                          "primitive_libraries": sorted(
                              d for d in p.deps
                              if re.search(r"radix|base-ui|headlessui|ark-ui|react-aria|"
                                           r"bits-ui|reka-ui|mantine", d))},
                         indent=1))
        return 0

    if a.signals:
        p = detect_project(root)
        print(json.dumps({"root": str(root), "tailwind_major": p.tailwind_major,
                          "has_tailwind": p.has_tailwind, "has_i18n": p.has_i18n,
                          "container_queries": p.has_container_queries,
                          "theme_vars": len(p.cssvars), "token_sources": p.token_sources[:10],
                          "components_found": len(p.inventory),
                          "dependency_count": len(p.deps)}, indent=1))
        return 0

    scope = target if target.is_file() else root
    project, reg, detectors, findings, status = run(scope, only=set(a.detector or []) or None)
    rules = rollup(reg, detectors, status)

    if a.json:
        print(json.dumps({
            "tier": "static",
            "root": str(root),
            "project": {"tailwind_major": project.tailwind_major,
                        "theme_vars": len(project.cssvars),
                        "components": len(project.inventory)},
            "detectors": {k: {"status": v[0], "note": v[1]} for k, v in status.items()},
            "rules": {k: {"status": v[0], "note": v[1]} for k, v in rules.items()},
            "findings": [f.__dict__ for f in findings],
            "caveat": "Static tier. Heuristic source scanning; PASS here means no source "
                      "evidence of a defect, not a verified pass.",
        }, indent=1))
    else:
        human(project, reg, detectors, findings, status, rules, limit=a.max)
    return 2 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
