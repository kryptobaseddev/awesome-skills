#!/usr/bin/env python3
"""ux-laws inventory: decompose a brownfield frontend into components, where they are used,
and where the codebase bypasses its own system.

Read-only. Stdlib only. Heuristic (regex, not an AST): every count is a lead to verify in
source, not proof. The report says so, and so should any summary built from it.

What it finds
  definitions   React/Preact/Solid function, arrow, forwardRef, memo and class components;
                Vue, Svelte and Astro single-file components (the file is the component)
  usages        <Name ...> / <Name.Part ...> / <kebab-name ...> tags, mapped back to definitions
  routes        Next (app/ and pages/), Remix/React Router, SvelteKit, Nuxt, Astro, TanStack Router files
  families      definitions grouped by UI role (Card, Button, Field, Modal, Toast...) -
                a family with several members is a consolidation candidate
  raw elements  native <button>, <input>, <select>, <textarea>, <table>, <dialog>, <img> used
                OUTSIDE the file that defines the matching primitive - library bypass
  style drift   hex/rgb/hsl literals, Tailwind arbitrary values ([13px], [#abc]), inline style
                objects, versus var(--token) use - token adoption
  data views    files that fetch data, and whether they mention loading / error / empty states

Usage
  python3 inventory.py <project-root> [--out DIR] [--json] [--include GLOB ...] [--exclude NAME ...]

  --out DIR   write inventory.json and inventory.md into DIR (default: print markdown to stdout)
  --json      print JSON to stdout instead of markdown
  --top N     rows per table in the markdown (default 25)
  --where X   print every definition and usage site (file:line) of component X, then exit -
              the blast radius to read before changing X

Exit code 0 on success, 2 when the root has no recognised source files.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SRC_EXT = {".tsx", ".jsx", ".ts", ".js", ".mjs", ".vue", ".svelte", ".astro", ".html"}
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".pcss"}
SFC_EXT = {".vue", ".svelte", ".astro"}
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", ".next", ".nuxt", ".svelte-kit", ".output",
    ".astro", "coverage", ".turbo", ".vercel", ".cache", "vendor", "storybook-static", "__snapshots__",
    ".expo", "android", "ios", "public", "static", "target",
}
TEST_RE = re.compile(r"(\.test|\.spec|\.stories|\.story|\.d)\.[a-z]+$|/(__tests__|__mocks__|e2e|cypress|tests?)/")

# --- component definitions (JSX family) --------------------------------------------------
DEF_PATTERNS = [
    re.compile(r"^\s*export\s+default\s+function\s+([A-Z][A-Za-z0-9_]*)\s*[(<]", re.M),
    re.compile(r"^\s*(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*[(<]", re.M),
    re.compile(r"^\s*(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z0-9_.<>\[\], ]+)?=\s*(?:React\.)?(?:forwardRef|memo|styled[.(]|observer\()", re.M),
    re.compile(r"^\s*(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z0-9_.<>\[\], ]+)?=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*[^=]+)?=>", re.M),
    re.compile(r"^\s*(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*(?::\s*[A-Za-z0-9_.<>\[\], ]+)?=\s*(?:async\s*)?[a-z_][A-Za-z0-9_]*\s*=>", re.M),
    re.compile(r"^\s*(?:export\s+)?class\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+(?:React\.)?(?:Pure)?Component\b", re.M),
]
JSX_HINT = re.compile(r"<[A-Za-z][A-Za-z0-9.]*[\s/>]|React|jsx|return\s*\(")
COMPOUND_RE = re.compile(r"(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*=\s*Object\.assign\(\s*([A-Z][A-Za-z0-9_]*)\s*,\s*\{([^}]*)\}")
PART_ASSIGN_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9_]*)\.([A-Z][A-Za-z0-9_]*)\s*=\s*([A-Z][A-Za-z0-9_]*)\s*;?\s*$", re.M)
TAG_RE = re.compile(r"<([A-Z][A-Za-z0-9_]*)((?:\.[A-Z][A-Za-z0-9_]*)*)[\s/>]")
KEBAB_TAG_RE = re.compile(r"<([a-z][a-z0-9]*(?:-[a-z0-9]+)+)[\s/>]")
IMPORT_RE = re.compile(r"import\s+(?:type\s+)?([^'\";]+?)\s+from\s+['\"]([^'\"]+)['\"]")

RAW_ELEMENTS = {
    "button": re.compile(r"<button[\s>]"),
    "input": re.compile(r"<input[\s/>]"),
    "select": re.compile(r"<select[\s>]"),
    "textarea": re.compile(r"<textarea[\s>]"),
    "table": re.compile(r"<table[\s>]"),
    "dialog": re.compile(r"<dialog[\s>]"),
    "img": re.compile(r"<img[\s/>]"),
    "a": re.compile(r"<a\s"),
}
# which family owns each raw element - a raw element inside a member of that family is fine
RAW_OWNER = {"button": "button", "input": "field", "select": "field", "textarea": "field",
             "table": "table", "dialog": "overlay", "img": "media", "a": "link"}

# UI role families, keyed by PascalCase word. The head noun (last word) decides, so
# ProductCard -> card and ArrowIcon -> media. Part words (CardHeader, TableRow) defer to the
# owning word before them, so compound parts stay with their parent family.
FAMILIES = {
    "toast": "toast snack snackbar notification notifications notice alert banner flash callout",
    "overlay": "modal dialog drawer sheet popover lightbox overlay",
    "tooltip": "tooltip hint hovercard",
    "menu": "menu dropdown combobox command autocomplete",
    "field": "input field textfield textarea select checkbox radio switch toggle slider datepicker picker otp searchbar searchbox",
    "form": "form wizard stepper",
    "button": "button btn cta iconbutton fab",
    "link": "link anchor",
    "table": "table datagrid datatable",
    "list": "list feed timeline pagination pager",
    "card": "card tile panel widget",
    "badge": "badge chip tag pill status",
    "avatar": "avatar",
    "nav": "nav navbar navigation sidebar breadcrumb breadcrumbs tabbar tabs topbar appbar menubar header footer",
    "feedback": "spinner loader loading skeleton progress empty emptystate placeholder errorstate errorboundary",
    "media": "image img icon logo illustration video media chart graph sparkline",
    "layout": "layout container stack grid section page screen shell wrapper split columns",
}
WORD_FAMILY = {w: fam for fam, words in FAMILIES.items() for w in words.split()}
PART_WORDS = {"header", "footer", "body", "title", "content", "item", "row", "cell", "actions", "action",
              "trigger", "description", "group", "label", "close", "overlay", "head", "column", "section",
              "media", "image", "price", "skeleton", "list", "root", "portal", "content", "icon"}

HEX_RE = re.compile(r"(?<![\w&/-])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FN_COLOR_RE = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(\s*[\d.]")
TOKEN_RE = re.compile(r"var\(--[A-Za-z0-9_-]+")
TW_ARBITRARY_RE = re.compile(r"\b[a-z][a-z0-9-]*-\[[^\]\s]+\]")
INLINE_STYLE_RE = re.compile(r"\bstyle=\{\{|\bstyle=\"[^\"]+\"|:style=\"")
PX_LITERAL_RE = re.compile(r"(?<![\w-])\d+(?:\.\d+)?px\b")

FETCH_RE = re.compile(r"\b(?:fetch\(|useQuery|useSuspenseQuery|useInfiniteQuery|useSWR|axios\.|createResource|useFetch|useAsyncData|\$fetch|createQuery|loader\s*[:=(]|load\s*[:=(]|getServerSideProps|trpc\.)")
LOADING_RE = re.compile(r"loading|isPending|isFetching|pending|skeleton|spinner|Suspense|fallback", re.I)
ERROR_RE = re.compile(r"\berror\b|isError|ErrorBoundary|catch\s*\(|onError|errorElement|\+error", re.I)
EMPTY_RE = re.compile(r"\.length\s*(?:===?|<=?|<)\s*[01]\b|!\w+\.length|\bempty\b|no results|nothing (?:here|yet)|EmptyState|zero", re.I)

ROUTE_RULES = [
    ("next-app", re.compile(r"(^|/)app/(.*/)?(page|layout)\.(tsx|jsx|ts|js|mdx)$")),
    ("next-pages", re.compile(r"(^|/)pages/(?!api/).+\.(tsx|jsx|ts|js)$")),
    ("sveltekit", re.compile(r"(^|/)routes/(.*/)?\+(page|layout)\.svelte$")),
    ("remix/rr", re.compile(r"(^|/)app/routes/.+\.(tsx|jsx|ts|js)$")),
    ("tanstack", re.compile(r"(^|/)routes/.+\.(tsx|jsx)$")),
    ("nuxt", re.compile(r"(^|/)pages/.+\.vue$")),
    ("astro", re.compile(r"(^|/)pages/.+\.(astro|md|mdx)$")),
]


def family_of(name: str) -> str | None:
    words = [w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", name)]
    if not words:
        return None
    joined = "".join(words)
    if joined in WORD_FAMILY:
        return WORD_FAMILY[joined]
    head = words[-1]
    if head in PART_WORDS and len(words) > 1:
        for w in reversed(words[:-1]):
            if w in WORD_FAMILY:
                return WORD_FAMILY[w]
    for w in reversed(words):
        if w in WORD_FAMILY:
            return WORD_FAMILY[w]
    return None


def kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def iter_files(root: Path, includes: list[str], excludes: set[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and d not in excludes and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            rel = p.relative_to(root).as_posix()
            if includes and not any(fnmatch.fnmatch(rel, g) for g in includes):
                continue
            if p.suffix in SRC_EXT or p.suffix in STYLE_EXT:
                yield p, rel


def read(p: Path) -> str:
    try:
        if p.stat().st_size > 1_500_000:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?m)(^|[^:\"'])//.*$", r"\1", src)
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


def line_of(src: str, idx: int) -> int:
    return src.count("\n", 0, idx) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--include", nargs="*", default=[])
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--where")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    defs: dict[str, list[dict]] = defaultdict(list)       # name -> [{file, line, kind}]
    usages: dict[str, list[dict]] = defaultdict(list)     # name -> [{file, line}]
    file_src: dict[str, str] = {}
    routes: list[dict] = []
    style_stats: dict[str, Counter] = {}
    raw_hits: dict[str, Counter] = {}
    data_views: list[dict] = []
    tests_skipped = 0
    part_alias: dict[str, str] = {}       # "Card.Media" -> "CardMedia"
    root_alias: dict[str, str] = {}       # "Card" -> "CardRoot"

    for p, rel in iter_files(root, a.include, set(a.exclude)):
        if TEST_RE.search("/" + rel):
            tests_skipped += 1
            continue
        src = read(p)
        if not src:
            continue
        code = strip_comments(src)
        file_src[rel] = code

        # styles: counted everywhere (source and stylesheets)
        sc = Counter()
        sc["hex"] = len(HEX_RE.findall(code))
        sc["fn_color"] = len(FN_COLOR_RE.findall(code))
        sc["token_refs"] = len(TOKEN_RE.findall(code))
        if p.suffix not in STYLE_EXT:
            sc["tw_arbitrary"] = len(TW_ARBITRARY_RE.findall(code))
            sc["inline_style"] = len(INLINE_STYLE_RE.findall(code))
        else:
            sc["px_literals"] = len(PX_LITERAL_RE.findall(code))
        if sum(sc.values()):
            style_stats[rel] = sc
        if p.suffix in STYLE_EXT:
            continue

        for kind, rx in ROUTE_RULES:
            if rx.search(rel):
                routes.append({"file": rel, "router": kind})
                break

        # definitions
        if p.suffix in SFC_EXT:
            stem = p.stem
            if stem in ("index", "+page", "+layout", "+error") or stem.startswith("+") or stem.startswith("["):
                stem = p.parent.name.title().replace("-", "") or stem
            name = stem[:1].upper() + stem[1:]
            defs[name].append({"file": rel, "line": 1, "kind": p.suffix[1:]})
        elif p.suffix in {".tsx", ".jsx"} or (p.suffix in {".ts", ".js", ".mjs"} and JSX_HINT.search(code) and TAG_RE.search(code)):
            seen = set()
            for rx in DEF_PATTERNS:
                for m in rx.finditer(code):
                    n = m.group(1)
                    if n in seen:
                        continue
                    # skip constants (ALL_CAPS) and obvious non-components
                    if n.isupper() or n.endswith(("Context", "Provider", "Schema", "Store", "Type", "Props")):
                        if not n.endswith("Provider"):
                            continue
                    seen.add(n)
                    # comments are stripped from `code`, so look for the JSDoc tag in the raw source
                    dep = bool(re.search(r"@deprecated(?:(?!\*/).)*\*/\s*(?:export\s+)?(?:default\s+)?(?:function|const|class)\s+" + n + r"\b", src, re.S))
                    defs[n].append({"file": rel, "line": line_of(code, m.start()), "kind": "jsx", "deprecated": dep})
            for m in COMPOUND_RE.finditer(code):
                root, impl, body = m.group(1), m.group(2), m.group(3)
                if root not in seen:
                    seen.add(root)
                    defs[root].append({"file": rel, "line": line_of(code, m.start()), "kind": "jsx"})
                root_alias[impl] = root
                for key, val in re.findall(r"([A-Z][A-Za-z0-9_]*)\s*(?::\s*([A-Z][A-Za-z0-9_]*))?", body):
                    part_alias[f"{root}.{key}"] = val or key
            for m in PART_ASSIGN_RE.finditer(code):
                part_alias[f"{m.group(1)}.{m.group(2)}"] = m.group(3)

        # usages
        for m in TAG_RE.finditer(code):
            usages[m.group(1)].append({"file": rel, "line": line_of(code, m.start()), "part": m.group(2) or ""})
        if p.suffix in {".vue", ".html", ".astro", ".svelte"}:
            for m in KEBAB_TAG_RE.finditer(code):
                usages["kebab:" + m.group(1)].append({"file": rel, "line": line_of(code, m.start()), "part": ""})

        # raw elements
        rc = Counter()
        for el, rx in RAW_ELEMENTS.items():
            n = len(rx.findall(code))
            if n:
                rc[el] = n
        if rc:
            raw_hits[rel] = rc

        # data views and their states
        if FETCH_RE.search(code):
            data_views.append({
                "file": rel,
                "loading": bool(LOADING_RE.search(code)),
                "error": bool(ERROR_RE.search(code)),
                "empty": bool(EMPTY_RE.search(code)),
            })

    if not file_src:
        print(f"no source files found under {root}", file=sys.stderr)
        return 2

    # compound parts: <Card.Header> is also a usage of CardHeader (the usual definition name of the part)
    for name in list(usages):
        for u in list(usages[name]):
            if u["part"]:
                key = name + u["part"]
                target = part_alias.get(key) or name + u["part"].replace(".", "")
                usages[target].append({**u, "part": ""})
    for impl, root in root_alias.items():   # CardRoot is used wherever Card is
        usages[impl].extend(usages.get(root, []))
    parts_and_impls = set(part_alias.values()) | set(root_alias)

    # fold kebab usages into PascalCase definitions (Vue/Web components)
    kebab_map = {kebab(n): n for n in defs}
    for key in [k for k in usages if k.startswith("kebab:")]:
        n = kebab_map.get(key[6:])
        if n:
            usages[n].extend(usages[key])
        del usages[key]

    if a.where:
        dl = defs.get(a.where, [])
        ul = [u for u in usages.get(a.where, []) if not any(u["file"] == d["file"] for d in dl)]
        print(f"# {a.where}: {len(dl)} definition(s), {len(ul)} usage(s) in {len({u['file'] for u in ul})} file(s)")
        for d in dl:
            print(f"def  {d['file']}:{d['line']}")
        for u in sorted(ul, key=lambda u: (u["file"], u["line"])):
            print(f"use  {u['file']}:{u['line']}{('  <' + a.where + u['part'] + '>') if u['part'] else ''}")
        return 0 if dl or ul else 1

    components = []
    for name, dl in sorted(defs.items()):
        ul = [u for u in usages.get(name, []) if not any(u["file"] == d["file"] for d in dl)]
        files_using = sorted({u["file"] for u in ul})
        fam = family_of(name)
        components.append({
            "deprecated": all(d.get("deprecated") for d in dl),
            "name": name,
            "family": fam,
            "definitions": dl,
            "duplicate_name": len(dl) > 1,
            "usage_count": len(ul),
            "used_in_files": files_using,
            "fan_in": len(files_using),
        })

    route_files = {r["file"] for r in routes}
    unused = [c["name"] for c in components if c["usage_count"] == 0 and not any(d["file"] in route_files for d in c["definitions"])
              and not c["name"].endswith(("Page", "Layout", "App", "Root", "Provider", "Document"))]
    single_use = [c["name"] for c in components if c["usage_count"] == 1]

    deprecated_names = {c["name"] for c in components if c["deprecated"]}
    families: dict[str, list[str]] = defaultdict(list)
    for c in components:
        if c["family"]:
            families[c["family"]].append(c["name"])
    # compound parts (CardHeader beside Card, defined in the same file) are one component, not a duplicate family
    file_of = {c["name"]: {d["file"] for d in c["definitions"]} for c in components}
    for fam, members in families.items():
        roots = [m for m in members if m not in parts_and_impls and m not in deprecated_names
                 and not any(m != o and m.startswith(o) and file_of[m] & file_of[o] for o in members)]
        families[fam] = roots
    families = defaultdict(list, {k: v for k, v in families.items() if v})
    # members that render another member of their family are compositions over it (ProductCard built on
    # Card): the healthy end state, so they don't count toward "consolidation candidate"
    comp_by = {c["name"]: c for c in components}
    composed: dict[str, list[str]] = {}
    for fam, members in families.items():
        for m in members:
            mfiles = {d["file"] for d in comp_by[m]["definitions"]}
            bases = [o for o in members if o != m and mfiles & set(comp_by[o]["used_in_files"])]
            if bases:
                composed[m] = bases

    # raw-element bypass: a raw <button> outside a file that defines a button-family component
    family_files: dict[str, set[str]] = defaultdict(set)
    for c in components:
        if c["family"]:
            for d in c["definitions"]:
                family_files[c["family"]].add(d["file"])
    has_primitive = {fam: bool(files) for fam, files in family_files.items()}
    # <img> and <a> are only "bypass" when the project has a dedicated Image / Link component,
    # not merely any icon or nav component in the same family
    names = set(defs)
    image_files = {d["file"] for n in names if re.search(r"(Image|Img|Picture)$", n) for d in defs[n]}
    link_files = {d["file"] for n in names if re.search(r"Link$", n) for d in defs[n]}
    family_files["media"] = image_files
    family_files["link"] = link_files
    has_primitive["media"] = bool(image_files)
    has_primitive["link"] = bool(link_files)
    bypass: dict[str, list[dict]] = defaultdict(list)
    for rel, rc in raw_hits.items():
        for el, n in rc.items():
            owner = RAW_OWNER[el]
            if rel in family_files.get(owner, set()):
                continue
            bypass[el].append({"file": rel, "count": n})
    for el in bypass:
        bypass[el].sort(key=lambda x: -x["count"])

    totals = Counter()
    for sc in style_stats.values():
        totals.update(sc)
    literals = totals["hex"] + totals["fn_color"] + totals["tw_arbitrary"]
    adoption = round(totals["token_refs"] / (totals["token_refs"] + literals), 3) if (totals["token_refs"] + literals) else None

    dv_missing = [d for d in data_views if not (d["loading"] and d["error"] and d["empty"])]

    report = {
        "root": str(root),
        "heuristic": True,
        "note": "Regex-based. Verify every lead in source before acting on it; a count is not a finding.",
        "counts": {
            "source_files": len(file_src),
            "tests_skipped": tests_skipped,
            "components": len(components),
            "routes": len(routes),
            "families_with_multiple_members": sum(1 for v in families.values() if len([m for m in v if m not in composed]) > 1),
            "duplicate_component_names": sum(1 for c in components if c["duplicate_name"]),
            "unused_components": len(unused),
            "single_use_components": len(single_use),
            "data_views": len(data_views),
            "data_views_missing_a_state": len(dv_missing),
        },
        "style": {
            "totals": dict(totals),
            "token_adoption": adoption,
            "hotspots": sorted(({"file": f, **dict(sc)} for f, sc in style_stats.items()),
                               key=lambda r: -(r.get("hex", 0) + r.get("fn_color", 0) + r.get("tw_arbitrary", 0) + r.get("inline_style", 0)))[:200],
        },
        "routes": routes,
        "components": sorted(components, key=lambda c: (-c["fan_in"], c["name"])),
        "families": {k: sorted(v) for k, v in sorted(families.items())},
        "composed": composed,
        "unused": sorted(unused),
        "deprecated": sorted({"name": c["name"], "fan_in": c["fan_in"]} for c in components if c["deprecated"]) if False else
                      [{"name": c["name"], "fan_in": c["fan_in"]} for c in sorted(components, key=lambda c: c["name"]) if c["deprecated"]],
        "single_use": sorted(single_use),
        "raw_element_bypass": {el: rows for el, rows in sorted(bypass.items())},
        "primitive_exists": has_primitive,
        "data_views": data_views,
    }

    md = render_md(report, a.top)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "inventory.json").write_text(json.dumps(report, indent=2))
        (out / "inventory.md").write_text(md)
        print(f"wrote {out/'inventory.json'} and {out/'inventory.md'}", file=sys.stderr)
    if a.json:
        print(json.dumps(report, indent=2))
    elif not a.out:
        print(md)
    return 0


def render_md(r: dict, top: int) -> str:
    c = r["counts"]
    L = [f"# Component inventory - {Path(r['root']).name}", "",
         "> Heuristic scan (regex, not AST). Every row is a lead to confirm in source.", "",
         "## Counts", "", "| metric | value |", "|---|---|"]
    L += [f"| {k.replace('_', ' ')} | {v} |" for k, v in c.items()]
    s = r["style"]
    t = s["totals"]
    L += ["", "## Token adoption", "",
          f"- `var(--token)` references: {t.get('token_refs', 0)}",
          f"- hex literals: {t.get('hex', 0)} · rgb/hsl/oklch literals: {t.get('fn_color', 0)} · Tailwind arbitrary values: {t.get('tw_arbitrary', 0)} · inline style blocks: {t.get('inline_style', 0)} · px literals in stylesheets: {t.get('px_literals', 0)}",
          f"- **adoption ratio** (token refs / (token refs + color & arbitrary literals)): {s['token_adoption'] if s['token_adoption'] is not None else 'n/a'}",
          "", "| file | hex | rgb/hsl | arbitrary | inline style | tokens |", "|---|---|---|---|---|---|"]
    for h in s["hotspots"][:top]:
        L.append(f"| `{h['file']}` | {h.get('hex', 0)} | {h.get('fn_color', 0)} | {h.get('tw_arbitrary', 0)} | {h.get('inline_style', 0)} | {h.get('token_refs', 0)} |")

    L += ["", "## Most-used components (blast radius)", "", "| component | family | fan-in (files) | uses | defined in |", "|---|---|---|---|---|"]
    for comp in r["components"][:top]:
        d = comp["definitions"][0]
        dup = " ⚠ duplicate name" if comp["duplicate_name"] else ""
        L.append(f"| `{comp['name']}`{dup} | {comp['family'] or '-'} | {comp['fan_in']} | {comp['usage_count']} | `{d['file']}:{d['line']}` |")

    L += ["", "## Families (consolidation candidates when > 1 member)", ""]
    comp = r.get("composed", {})
    for fam, names in r["families"].items():
        independent = [n for n in names if n not in comp]
        mark = " **← review**" if len(independent) > 1 else ""
        shown = ", ".join(f"`{n}`" + (f" (built on {', '.join(comp[n])})" if n in comp else "") for n in names[:30]) + (" …" if len(names) > 30 else "")
        L.append(f"- **{fam}** ({len(names)}){mark}: {shown}")

    if r.get("deprecated"):
        L += ["", "## Deprecated adapters (delete when fan-in reaches 0)", ""]
        L += [f"- `{d['name']}`: fan-in {d['fan_in']}" for d in r["deprecated"]]

    dups = [comp for comp in r["components"] if comp["duplicate_name"]]
    if dups:
        L += ["", "## Same name, several definitions", ""]
        for comp in dups[:top]:
            L.append(f"- `{comp['name']}`: " + ", ".join(f"`{d['file']}:{d['line']}`" for d in comp["definitions"]))

    L += ["", "## Library bypass (raw native elements outside their primitive)", ""]
    if not r["raw_element_bypass"]:
        L.append("- none found")
    for el, rows in r["raw_element_bypass"].items():
        prim = "primitive exists" if r["primitive_exists"].get(RAW_OWNER[el]) else "no primitive found"
        total = sum(x["count"] for x in rows)
        L.append(f"- `<{el}>` × {total} in {len(rows)} files ({prim}): " + ", ".join(f"`{x['file']}` ({x['count']})" for x in rows[:8]) + (" …" if len(rows) > 8 else ""))

    dv = r["data_views"]
    L += ["", "## Data views and their states (Doherty, Postel, Peak-End)", ""]
    if not dv:
        L.append("- no data-fetching files detected")
    else:
        L += ["| file | loading | error | empty |", "|---|---|---|---|"]
        for d in sorted(dv, key=lambda d: (d["loading"] + d["error"] + d["empty"], d["file"]))[:top]:
            f = lambda b: "yes" if b else "**missing?**"
            L.append(f"| `{d['file']}` | {f(d['loading'])} | {f(d['error'])} | {f(d['empty'])} |")

    L += ["", "## Routes (walk these in the browser)", ""]
    L += [f"- `{x['file']}` ({x['router']})" for x in r["routes"][: max(top, 60)]] or ["- none detected; derive routes from the router config or the nav"]

    if r["unused"]:
        L += ["", f"## Possibly unused ({len(r['unused'])})", "", "Dynamic imports, string registries and barrel re-exports hide usages from this scan - grep before deleting.", "",
              ", ".join(f"`{n}`" for n in r["unused"][: top * 2])]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    sys.exit(main())
