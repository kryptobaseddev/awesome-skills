#!/usr/bin/env python3
"""deuxui static tier -- source checks bound to rule IDs.

Reports PASS / FAIL / NOT_RUN / NOT_APPLICABLE per rule. It never reports PASS
for something it did not examine, which is the whole point: a check that could
not run is more useful as an admission than as a silent gap.

  ux_check.py <path> [--json] [--detector ID]... [--inventory INTENT] [--signals]
  echo '<PostToolUse hook json>' | ux_check.py --stdin   # JSON on stdout, exit 0

Exit: 0 clean, 2 findings, 1 usage error.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

# Do not leave .pyc files beside the checks. A directory-source plugin install
# copies the working tree verbatim, so stray bytecode ships to the consumer
# despite being gitignored. Costs ~15ms per run, which nothing here notices.
sys.dont_write_bytecode = True

# A PostToolUse hook fires on every Write and Edit the agent makes, and most of
# those are not interface files. Sniff the payload here, before the rule registry
# and fifteen check modules load, so editing a .py or .md costs a bare interpreter
# start rather than 60ms of imports. stdin can only be read once, so the resolved
# path is stashed for main(). HOOK_EXT must stay in step with SOURCE_EXT|STYLE_EXT;
# selftest.py asserts that it does.
HOOK_EXT = {".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue", ".astro",
            ".html", ".htm", ".css", ".scss", ".sass", ".less",
            ".swift", ".kt", ".kts", ".dart"}
_HOOK_PATH = None
if "--stdin" in sys.argv:
    try:
        _p = (json.loads(sys.stdin.read() or "{}").get("tool_input") or {}).get("file_path")
    except ValueError:
        sys.exit(0)
    if not _p or Path(_p).suffix not in HOOK_EXT or not Path(_p).is_file():
        sys.exit(0)
    _HOOK_PATH = Path(_p).resolve()

sys.path.insert(0, str(Path(__file__).parent))
import yaml
import rulepack
import uxconfig
from checks import ALL, FileCtx, Project
from checks._util import (NATIVE_EXT, SOURCE_EXT, STYLE_EXT, collect_css_vars,
                          css_of, iter_files, is_generated, read, scan_tags)

RULES_DIR = Path(__file__).resolve().parent.parent / "references" / "rules"


def load_rules():
    reg, det, _th = rulepack.load()
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
    p.platforms = detect_platforms(root, p.deps)
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


def detect_platforms(root: Path, deps: set) -> set:
    """Which platforms this project ships to, measured rather than declared.

    An `ios/` directory next to an `android/` one is the React Native and Flutter
    shape; an .xcodeproj or Package.swift is native Apple; a build.gradle or
    settings.gradle(.kts) is native Android; a pubspec.yaml is Flutter, which
    ships to both unless its platform directories say otherwise. Declaring
    `features: [ios]` in ux.config.yaml still works and is unioned in -- this
    only removes the need to declare what the tree already states."""
    out = set()
    cross = bool(deps & {"react-native", "expo"}) or (root / "pubspec.yaml").exists()
    if (root / "ios").is_dir() or any(root.glob("*.xcodeproj")) \
            or any(root.glob("*.xcworkspace")) or (root / "Package.swift").exists():
        out.add("ios")
    if (root / "android").is_dir() or (root / "build.gradle").exists() \
            or (root / "build.gradle.kts").exists() \
            or (root / "settings.gradle").exists() or (root / "settings.gradle.kts").exists():
        out.add("android")
    if cross and not out:
        # A cross-platform project whose native directories are generated at
        # build time (Expo prebuild, managed workflow) still ships to both.
        out |= {"ios", "android"}
    return out


_RN_IMPORT = re.compile(r"""from\s+["'](?:react-native|expo(?:-\w+)?|"""
                        r"""@react-navigation/[\w-]+|react-native-\w[\w-]*)["']""")


def classify(text: str) -> str:
    """Only Remotion gets its own surface. A page that happens to embed a 3D
    canvas is still an interface -- the 3D checks opt into "ui" as well, so
    reclassifying the whole file would silently disable every other check on it.
    That mistake is exactly the kind of quiet gap this tool exists to prevent."""
    if re.search(r"from\s+[\"']remotion[\"']|@remotion/", text):
        return "video"
    # React Native in a .tsx is a native surface, not a web one. Left as "ui" it
    # collected web findings that cannot apply -- an <Image> with no alt, a
    # <Pressable> with no href -- while the platform checks never saw it.
    if _RN_IMPORT.search(text):
        return "native"
    return "ui"


# ----------------------------------------------------------------- run
def run(scope: Path, root: Path | None = None, only=None, cfg=None):
    """`scope` is what gets read; `root` is the project it belongs to.

    These were one argument, which meant `ux_check.py src/components` silently
    walked up to the nearest package.json and rescanned the whole project. The
    project root still supplies package.json, tokens and the component inventory
    -- it just no longer decides what to read."""
    root = root or scope
    cfg = cfg if cfg is not None else {}
    reg, det = load_rules()
    detectors = det["detectors"]
    project = detect_project(root)
    project.th, project.threshold_overrides_refused = uxconfig.thresholds(cfg)
    project.contract = uxconfig.contract(root)
    off = uxconfig.disabled(cfg)
    skip = uxconfig.excludes(cfg)

    files = []
    for f in iter_files(scope, extra_skip=skip):
        txt = read(f)
        if not txt or is_generated(f, txt):
            continue
        ext = f.suffix
        rel = str(f.relative_to(scope) if scope.is_dir() else f.name)
        files.append(FileCtx(path=f, rel=rel,
                             text=txt, ext=ext,
                             tags=scan_tags(txt) if ext in SOURCE_EXT else [],
                             surface="native" if ext in NATIVE_EXT else classify(txt),
                             css=css_of(f, txt)))

    findings, status = [], {}
    for did, chk in sorted(ALL.items()):
        if only and did not in only:
            continue
        meta = detectors.get(did, {})
        if did.startswith("S-CONTRACT-") and not project.contract:
            status[did] = ("NOT_RUN", meta.get("not_run_when",
                           "No .deuxui/design.contract.yaml, so there is no declared "
                           "system to conform to. Run `deuxui design` for new work or "
                           "`deuxui uplift` to derive one from the code."))
            continue
        if did in off:
            # Disabled in project config. NOT_RUN, never PASS -- config narrows
            # what was examined, it does not turn a finding into a pass.
            status[did] = ("NOT_RUN", "Disabled in .deuxui/ux.config.yaml "
                                      "(disabled_checks).")
            continue
        if chk.requires and not chk.requires(project):
            status[did] = ("NOT_RUN", meta.get("not_run_when", "Precondition not met."))
            continue
        pool = [f for f in files
                if (not chk.exts or f.ext in chk.exts) and f.surface in chk.surfaces]
        if not pool:
            status[did] = ("NOT_APPLICABLE", "No files of this kind in scope.")
            continue
        hits = []
        # `scope="project"` means the check states one fact about the whole
        # project. It was declared and never read, so such a check ran once per
        # file and reported the same finding 172 times on a mid-sized codebase --
        # the report drowning its own signal.
        targets = pool[:1] if chk.scope == "project" else pool
        for f in targets:
            try:
                hits.extend(chk.fn(f, project) or [])
            except Exception as e:                      # a broken check must not fake a pass
                status[did] = ("NOT_RUN", f"Check raised {type(e).__name__}: {e}")
                break
        else:
            hits, extra = _cap(hits)
            project.counts[did] = {"matched": len(hits) + extra, "listed": len(hits)}
            status[did] = ("FAIL" if hits else "PASS",
                           (f"project-level check over {len(pool)} files"
                            if chk.scope == "project" else f"{len(pool)} files examined")
                           + (f"; {len(hits) + extra} matched, {len(hits)} listed "
                              f"(at most {PER_FILE_CAP} per file)" if extra else ""))
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


SINGLE_FILE_NOTE = ("Single-file scope. One file cannot establish that a "
                    "product-wide rule holds -- only its findings are evidence.")


def rollup(reg, detectors, status, single_file=False, exceptions=()):
    """Per-rule status. A rule nobody can test is NOT_RUN, never PASS.

    In single-file scope every PASS becomes NOT_RUN. A detector that read one
    file and found nothing has learned something about that file, not about the
    product, and reporting 116 of 190 rules as PASS off the back of one edited
    component is the exact laundering this tool exists to refuse."""
    by_rule = {}
    for did, (st, _why) in status.items():
        for rid in detectors.get(did, {}).get("rules", []):
            by_rule.setdefault(rid, []).append((did, st))
    excepted = {e["rule_id"]: e for e in exceptions if e.get("active")}
    out = {}
    for r in reg["rules"]:
        rid = r["id"]
        sts = [s for _d, s in by_rule.get(rid, [])]
        if not sts:
            out[rid] = ("NOT_RUN", "No automated detector. Needs manual verification.")
        elif "FAIL" in sts and rid in excepted and r.get("class") in uxconfig.EXCEPTABLE_CLASSES:
            e = excepted[rid]
            out[rid] = ("APPROVED_EXCEPTION",
                        f"{e.get('exception_id') or 'exception'} (owner "
                        f"{e.get('owner') or 'unnamed'}, review "
                        f"{e.get('expires_or_review_on') or 'no date'}). Still measured "
                        "as failing; the owner has ruled on it.")
        elif "FAIL" in sts:
            out[rid] = ("FAIL", "")
        elif "PASS" in sts:
            out[rid] = (("NOT_RUN", SINGLE_FILE_NOTE) if single_file else
                        ("PASS", "Static tier only. The runtime tier checks this properly."))
        elif "NOT_RUN" in sts:
            out[rid] = ("NOT_RUN", next(w for d, (s, w) in status.items()
                                        if s == "NOT_RUN" and rid in
                                        detectors.get(d, {}).get("rules", [])))
        else:
            out[rid] = ("NOT_APPLICABLE", "")
    return out


# ----------------------------------------------------------------- output
def severity_of(reg, detectors):
    """Worst severity among the rules a detector is bound to."""
    sev = {r["id"]: r["severity"] for r in reg["rules"]}

    def worst(f):
        return min((sev.get(r, "P2")
                    for r in detectors.get(f.detector, {}).get("rules", [])), default="P2")
    return worst


# Strictest first. A detector bound to a STANDARD and a PROJECT rule is reported
# under the standard: the floor is what decides whether it can be ruled away.
CLASS_ORDER = ("STANDARD", "PLATFORM", "PROJECT", "HEURISTIC")
CLASS_HEADINGS = {
    "STANDARD": "Floors -- STANDARD rules. Not overridable; a failure here is a "
                "failure against a published standard.",
    "PLATFORM": "Platform requirements -- PLATFORM rules. The platform's to set, "
                "not the project's.",
    "PROJECT": "Project defaults -- PROJECT rules. A trade-off the product owner "
               "decides (density, house style). Rule on one in "
               ".deuxui/exceptions.yaml and it reports APPROVED_EXCEPTION.",
    "HEURISTIC": "Heuristics -- HEURISTIC rules. Research-backed tendencies; judge "
                 "each in context.",
}


def class_of(reg, detectors):
    cls = {r["id"]: r.get("class") or "PROJECT" for r in reg["rules"]}

    def strictest(f):
        got = {cls.get(r, "PROJECT") for r in detectors.get(f.detector, {}).get("rules", [])}
        return next((c for c in CLASS_ORDER if c in got), "PROJECT")
    return strictest


def tally(project, findings):
    """(matched, listed). `matched` is what the detectors found; `listed` is what
    survived the per-file cap. The headline used to be `listed`, printed as the
    total -- a floor, wrong by an unknown factor per rule and per file, and quoted
    back to a field-report author as a work estimate."""
    counts = getattr(project, "counts", {}) or {}
    matched = sum(c["matched"] for c in counts.values()) if counts else len(findings)
    return matched, len(findings)


def human(project, reg, detectors, findings, status, rules, limit=40, single_file=False):
    """The rule matrix leads. A finding count from a heuristic source scan is raw
    hits, unranked, with false positives in it; a rule row is a verdict with a
    citation. Leading with the count made 3,790 the number people quoted and hid
    the 24 failing rules that were the actual worklist."""
    w = sys.stderr.write
    worst = severity_of(reg, detectors)
    klass = class_of(reg, detectors)
    conf = {d: (m or {}).get("confidence") for d, m in detectors.items()}
    matched, listed = tally(project, findings)

    counts = {k: sum(1 for v in rules.values() if v[0] == k)
              for k in ("FAIL", "APPROVED_EXCEPTION", "NOT_RUN", "PASS", "NOT_APPLICABLE")}
    rclass = {r["id"]: r.get("class") or "PROJECT" for r in reg["rules"]}
    if not single_file:
        w("\n" + "-" * 70 + "\n")
        w(f"rules      FAIL {counts['FAIL']}   APPROVED_EXCEPTION "
          f"{counts['APPROVED_EXCEPTION']}   NOT_RUN {counts['NOT_RUN']}   PASS "
          f"{counts['PASS']}   NOT_APPLICABLE {counts['NOT_APPLICABLE']}   of {len(rules)}\n")
        if counts["FAIL"]:
            by = {c: sum(1 for rid, v in rules.items()
                         if v[0] == "FAIL" and rclass.get(rid) == c) for c in CLASS_ORDER}
            w("  failing  " + "   ".join(f"{c} {n}" for c, n in by.items() if n) + "\n")
            fails = sorted(rid for rid, v in rules.items() if v[0] == "FAIL")
            w("  rules    " + ", ".join(fails[:24])
              + (f", +{len(fails) - 24} more" if len(fails) > 24 else "") + "\n")
        w("\nThe rule matrix is the result. NOT_RUN is the count of rules nothing has\n"
          "checked yet, and it is not a pass. This is the static tier -- it reads source\n"
          "text heuristically and cannot see computed styles, real hit areas, focus order\n"
          "or any state the app only reaches at runtime. Run scripts/ux_browser.sh against\n"
          "a running app to convert those rows into real results.\n")

    sevc = {s: sum(1 for f in findings if worst(f) == s) for s in ("P0", "P1", "P2")}
    w("\n" + "-" * 70 + "\n")
    w(f"findings   raw heuristic hits, unranked, may include false positives. The\n"
      f"           [detector, confidence] tag is the detector's declared confidence,\n"
      f"           not a measured precision.\n"
      f"           {matched} matched, {listed} listed (at most {PER_FILE_CAP} per file per "
      f"detector)   P0 {sevc['P0']}   P1 {sevc['P1']}   P2 {sevc['P2']} of those listed\n")
    if single_file:
        w(f"\nOne file was read, so there is no rule matrix to report. {SINGLE_FILE_NOTE}\n"
          f"Point this at the project directory for a rule-by-rule result.\n")

    rank = {c: i for i, c in enumerate(CLASS_ORDER)}
    ordered = sorted(findings, key=lambda f: (rank[klass(f)], worst(f), f.file, f.line))
    shown = ordered[:limit]
    for c in CLASS_ORDER:
        group = [f for f in shown if klass(f) == c]
        if not group:
            continue
        total = sum(1 for f in findings if klass(f) == c)
        w(f"\n== {CLASS_HEADINGS[c]}  [{total} listed]\n")
        by_file = {}
        for f in group:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            w(f"\n{fname}\n")
            for f in sorted(by_file[fname], key=lambda x: x.line):
                ruled = ""
                for rid in detectors.get(f.detector, {}).get("rules", []):
                    if rules.get(rid, ("",))[0] == "APPROVED_EXCEPTION":
                        ruled = f"  (ruled: {rid} under an approved exception)"
                w(f"  {f.line:>5}  {worst(f)} [{f.detector}, "
                  f"{conf.get(f.detector) or f.confidence}] {f.snippet}{ruled}\n")
                w(f"         -> {f.fix}\n")
    if len(ordered) > limit:
        w(f"\n... {len(ordered) - limit} more listed findings. Use --json for all of them, "
          f"or --max N to show more here.\n")


def hook_report(reg, detectors, findings, limit=10, matched=None):
    """The PostToolUse contract: JSON on stdout, exit 0, and nothing whatsoever
    when the file is clean.

    Findings go out as additionalContext rather than as an exit-2 blocking error.
    Exit 2 on PostToolUse renders as a failure on a write that in fact succeeded,
    and the hook's job is to put the defect in front of the agent while it is
    still holding the file -- not to report a failure that did not happen."""
    if not findings:
        return 0
    worst = severity_of(reg, detectors)
    ordered = sorted(findings, key=lambda f: (worst(f), f.line))
    urgent = [f for f in ordered if worst(f) in ("P0", "P1")][:limit]
    deferred = len(ordered) - len(urgent)
    if not urgent:                      # P2 only: not worth interrupting for
        return 0

    name = Path(ordered[0].file).name
    lines = [f"deuxui checked {name} as you wrote it and found "
             f"{len(urgent)} issue{'s' if len(urgent) != 1 else ''} worth fixing now:"]
    for f in urgent:
        lines.append(f"  {worst(f)} line {f.line} [{f.detector}] {f.snippet.strip()[:100]}")
        lines.append(f"     {f.fix}")
    unlisted = (matched or len(ordered)) - len(ordered)
    if deferred or unlisted > 0:
        lines.append(f"  ...{len(urgent)} shown of {matched or len(ordered)} matched. Run "
                     f"ux_check.py on the file to see the rest.")
    lines.append("Fix these in the file you just wrote rather than noting them for later. "
                 "This is one file read statically, so it is not a pass for anything else.")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "\n".join(lines),
    }}))
    return 0


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
    ap.add_argument("--config", help="project config (default: nearest "
                                     ".deuxui/ux.config.yaml at or above the target)")
    a = ap.parse_args(argv)

    target = _HOOK_PATH or Path(a.path).resolve()

    if not target.exists():
        sys.stderr.write(f"no such path: {target}\n")
        return 1

    # The project root supplies package.json, tokens and the component inventory.
    # It does NOT decide what to read -- `target` does. Conflating the two meant
    # `ux_check.py src/components` rescanned the entire project.
    root = target if target.is_dir() else target.parent
    while root != root.parent and not (root / "package.json").exists():
        root = root.parent
    if not (root / "package.json").exists():
        root = target if target.is_dir() else target.parent

    cfg = uxconfig.load(root, a.config)

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
                          "platforms": sorted(p.platforms),
                          "dependency_count": len(p.deps)}, indent=1))
        return 0

    scope = target                      # exactly what was asked for, file or directory
    single_file = scope.is_file()
    project, reg, detectors, findings, status = run(
        scope, root=root, only=set(a.detector or []) or None, cfg=cfg)
    rules = rollup(reg, detectors, status, single_file=single_file,
                   exceptions=uxconfig.exceptions(cfg, root=root))

    if a.stdin:
        return hook_report(reg, detectors, findings, limit=a.max,
                           matched=tally(project, findings)[0])

    if a.json:
        print(json.dumps({
            "tier": "static",
            "root": str(root),
            "project": {"tailwind_major": project.tailwind_major,
                        "theme_vars": len(project.cssvars),
                        "components": len(project.inventory),
                        # Measured platforms. ux_report unions these into
                        # `features`, so the iOS and Android rule families become
                        # applicable because the tree says so, not because
                        # somebody remembered to declare them.
                        "platforms": sorted(project.platforms)},
            "detectors": {k: {"status": v[0], "note": v[1],
                              **project.counts.get(k, {})} for k, v in status.items()},
            # `listed` is what `findings` holds; `matched` is what the detectors
            # found. Aggregate the first and you are counting a display choice.
            "counts": dict(zip(("matched", "listed"), tally(project, findings))),
            "rules": {k: {"status": v[0], "note": v[1]} for k, v in rules.items()},
            "findings": [f.__dict__ for f in findings],
            "scope": "file" if single_file else "directory",
            "scanned": str(scope),
            "config": {"path": cfg.get("_path"),
                       "features": uxconfig.features(cfg),
                       "disabled_checks": sorted(uxconfig.disabled(cfg)),
                       "exclude": uxconfig.excludes(cfg),
                       "refused_overrides": project.threshold_overrides_refused},
            "caveat": "Static tier. Heuristic source scanning; PASS here means no source "
                      "evidence of a defect, not a verified pass."
                      + (" " + SINGLE_FILE_NOTE if single_file else ""),
        }, indent=1))
    else:
        human(project, reg, detectors, findings, status, rules, limit=a.max,
              single_file=single_file)
    return 2 if findings else 0        # CI contract; the hook path returned above


if __name__ == "__main__":
    sys.exit(main())
