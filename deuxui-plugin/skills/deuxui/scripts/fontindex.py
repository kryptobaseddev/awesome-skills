#!/usr/bin/env python3
"""Which typefaces this project can actually render, and which it only names.

The failure this exists to catch is silent by construction. A contract declares
`display: Söhne`, every type decision downstream is made about Söhne, the CSS
says `font-family: Söhne, sans-serif` -- and no file in the repository provides
the face. The browser falls back without a warning, ships a different typeface at
the declared sizes and leading, and every subsequent judgement about the type is
a judgement about a face nobody chose.

One thing this tool refuses to do, and the refusal is the point: it does not
treat the faces installed on THIS machine as evidence that a visitor has them. A
build host's font list describes the build host. For anything served over the
web, a face is available if the project ships it or if it is genuinely present
across the platforms the product supports -- and `fc-list` can tell you neither.
Host faces are reported separately and labelled as what they are.

    fontindex.py [ROOT]            what the project provides, and what it names
    fontindex.py --json
    fontindex.py --check           exit 2 when a declared family is not provided
    fontindex.py --pair "Fraunces" "Inter"    would these two carry different jobs

Feeds `typescale.py` (which takes families as given) and the
`S-CONTRACT-FONT-AVAIL` detector.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import uxconfig                                                   # noqa: E402

FONT_FILE = (".woff2", ".woff", ".ttf", ".otf", ".eot")
CSSISH = (".css", ".scss", ".sass", ".less", ".styl")
SRCISH = (".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue", ".astro", ".html", ".htm", ".mdx")
SKIP_DIR = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit", "out",
            "coverage", ".venv", "venv", "__pycache__", ".turbo", ".cache", "target"}

# Faces that are actually on the machines people use, with the platforms that
# have them. "web safe" is mostly folklore; what matters is whether the stack has
# a real face on every platform the product supports. A stack of Segoe UI alone
# is a Windows design with an unspecified appearance everywhere else.
SYSTEM_FACES = {
    "system-ui": {"web", "ios", "android"}, "ui-sans-serif": {"web", "ios", "android"},
    "ui-serif": {"web", "ios"}, "ui-monospace": {"web", "ios"},
    "ui-rounded": {"ios"},
    "-apple-system": {"ios"}, "blinkmacsystemfont": {"ios"},
    "sf pro": {"ios"}, "sf pro text": {"ios"}, "sf pro display": {"ios"},
    "sf mono": {"ios"}, "new york": {"ios"},
    "segoe ui": {"windows"}, "segoe ui variable": {"windows"},
    "calibri": {"windows"}, "cambria": {"windows"}, "consolas": {"windows"},
    "candara": {"windows"}, "corbel": {"windows"},
    "roboto": {"android", "web"}, "roboto mono": {"android"},
    "roboto flex": {"android"}, "noto sans": {"android"},
    "helvetica": {"ios", "web"}, "helvetica neue": {"ios"},
    "arial": {"web", "windows", "ios"}, "arial black": {"web"},
    "verdana": {"web"}, "tahoma": {"windows"}, "trebuchet ms": {"web"},
    "georgia": {"web"}, "times new roman": {"web"}, "times": {"web"},
    "palatino": {"ios"}, "palatino linotype": {"windows"},
    "courier new": {"web"}, "courier": {"web"},
    "menlo": {"ios"}, "monaco": {"ios"}, "lucida console": {"windows"},
    "impact": {"web"}, "comic sans ms": {"web"},
    # Generic families. Always resolvable; never a design decision on their own.
    "sans-serif": {"web", "ios", "android"}, "serif": {"web", "ios", "android"},
    "monospace": {"web", "ios", "android"}, "cursive": {"web"}, "fantasy": {"web"},
    "math": {"web"}, "emoji": {"web"},
}
GENERIC = {"sans-serif", "serif", "monospace", "cursive", "fantasy", "system-ui",
           "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "math", "emoji"}

# Classification by name, because it is the only signal available for a webfont
# whose file this tool will not parse. Deliberately coarse: it exists to answer
# "would these two read as different voices", not to catalogue a foundry.
CLASS_TOKENS = [
    ("mono", r"\bmono|code|consol|courier|menlo|monaco|term(?:inal)?\b"),
    ("slab", r"\bslab|rockwell|clarendon|egyptienne\b"),
    ("serif", r"\bserif|garamond|georgia|times|caslon|baskerville|bodoni|didot|"
              r"minion|freight|tiempos|lora|merriweather|playfair|spectral|"
              r"newsreader|fraunces|source serif|ibm plex serif|charter|literata|"
              r"crimson|libre baskerville|eb garamond|cormorant|petrona|new york\b"),
    ("script", r"\bscript|hand|cursive|brush|pacifico|dancing|caveat|satisfy\b"),
    ("display", r"\bdisplay|poster|headline|title(?:ing)?|black|ultra|condensed|"
                r"expanded|stencil|impact|bebas|anton|oswald|archivo black\b"),
    ("sans", r"\bsans|grotesk|grotesque|helvetica|arial|inter|roboto|univers|"
             r"akzidenz|neue|gothic|futura|avenir|nunito|lato|montserrat|poppins|"
             r"work sans|dm sans|plus jakarta|manrope|figtree|geist|satoshi|"
             r"sohne|söhne|circular|graphik|aeonik|segoe|verdana|tahoma|"
             r"trebuchet|open sans|source sans|ibm plex sans|noto sans|"
             r"instrument sans|general sans|switzer\b"),
]


def classify(name: str) -> str:
    n = " " + name.lower().strip().strip("'\"") + " "
    for cls, pat in CLASS_TOKENS:
        if re.search(pat, n):
            return cls
    return "unknown"


def norm(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().strip("'\"").lower())


def fold(name: str) -> str:
    """A comparison key that survives the two ways the same face gets written down.

    `Söhne` in a contract and `sohne-web-buch.woff2` on disk are the same typeface;
    an exact match on either spelling reports the face as missing while it sits in
    the tree. Diacritics come off, weight and style words come off, everything but
    letters and digits comes off."""
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b(?:regular|italic|oblique|bold|semibold|demibold|medium|book|"
               r"buch|light|extralight|ultralight|thin|black|heavy|extrabold|"
               r"variable|var|vf|wght|web|text|display|pro|std|latin|ext|subset|"
               r"\d{3,4})\b", " ", s)
    return " ".join(s.split())


def _fuzzy(fam: str, keys) -> str | None:
    """The provided key that is the same face as `fam`, or None.

    Containment in either direction, and only on a token of real length -- `sans`
    matching `sans` would pair every grotesque in existence."""
    want = fold(fam)
    if not want:
        return None
    wt = set(want.split())
    best = None
    for k in keys:
        have = fold(k)
        if not have:
            continue
        if have == want:
            return k
        ht = set(have.split())
        shared = {x for x in (wt & ht) if len(x) >= 4}
        if shared and (wt <= ht or ht <= wt):
            if best is None or len(fold(k)) < len(fold(best)):
                best = k
    return best


# ------------------------------------------------------------------ discovery
def iter_files(root: Path, exts):
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        if any(part in SKIP_DIR for part in p.parts):
            continue
        yield p


def read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")
    except OSError:
        return ""


def project_faces(root: Path) -> dict:
    """family -> {how: [...], files: [...]}  for every face the PROJECT ships.

    Five ways a face legitimately arrives, and all five have to be looked for or
    the answer is wrong in the common case: an @font-face rule, a @fontsource
    package, next/font, a font file sitting in the tree, and a Google Fonts
    request. A project using next/font has no @font-face anywhere."""
    out: dict[str, dict] = {}

    def add(fam, how, where):
        k = norm(fam)
        if not k or k in GENERIC:
            return
        e = out.setdefault(k, {"name": str(fam).strip().strip("'\""),
                               "how": [], "files": []})
        if how not in e["how"]:
            e["how"].append(how)
        w = str(where)
        if w not in e["files"]:
            e["files"].append(w)

    # 1. @font-face in any stylesheet, and in <style> blocks / template literals.
    for p in list(iter_files(root, CSSISH)) + list(iter_files(root, SRCISH)):
        t = read(p)
        if "@font-face" not in t and "fontsource" not in t and "next/font" not in t \
                and "fonts.googleapis" not in t and "font-family" not in t:
            continue
        rel = p.relative_to(root)
        for m in re.finditer(r"@font-face\s*\{([^}]*)\}", t, re.S):
            fam = re.search(r"font-family\s*:\s*([^;]+)", m.group(1))
            if fam:
                add(fam.group(1), "@font-face", rel)
        # 2. @fontsource/<family> -- the import IS the declaration.
        for m in re.finditer(r"['\"]@fontsource(?:-variable)?/([a-z0-9-]+)", t):
            add(m.group(1).replace("-", " "), "@fontsource", rel)
        # 3. next/font -- named import for Google faces, localFont for files.
        if "next/font" in t:
            for m in re.finditer(r"import\s*\{([^}]+)\}\s*from\s*['\"]next/font/google",
                                 t):
                for nm in m.group(1).split(","):
                    nm = nm.strip().split(" as ")[0].strip()
                    if nm:
                        add(re.sub(r"(?<!^)(?=[A-Z])", " ", nm).replace("_", " "),
                            "next/font/google", rel)
            if "next/font/local" in t:
                for m in re.finditer(r"(?:family|variable)\s*:\s*['\"]([^'\"]+)", t):
                    add(m.group(1), "next/font/local", rel)
        # 5. Google Fonts over the network.
        for m in re.finditer(r"fonts\.googleapis\.com/css2?\?([^\"'\s)]+)", t):
            for fm in re.finditer(r"family=([^&:]+)", m.group(1)):
                add(fm.group(1).replace("+", " "), "google fonts link", rel)

    # 2b. @fontsource and friends declared as dependencies. A project that
    # imports the package in a layout file is covered above; one that lists it in
    # the manifest and imports it through a bundler alias is not, and reporting a
    # shipped face as missing is the same defect in the other direction.
    for mf in list(root.glob("package.json")) + list(root.glob("*/package.json")):
        if any(part in SKIP_DIR for part in mf.parts):
            continue
        try:
            data = json.loads(read(mf))
        except ValueError:
            continue
        deps = {}
        for key in ("dependencies", "devDependencies"):
            d = data.get(key)
            if isinstance(d, dict):
                deps.update(d)
        for dep in deps:
            m = re.match(r"@fontsource(?:-variable)?/(.+)$", dep)
            if m:
                add(m.group(1).replace("-", " "), "@fontsource (manifest)",
                    mf.relative_to(root))
            elif dep in ("geist", "@vercel/font"):
                add("geist", f"{dep} (manifest)", mf.relative_to(root))

    # 4. A font file in the tree. The filename is the only name available, and a
    # hashed build artefact has none -- recorded as a file without a family so the
    # report can say "three faces are shipped and none is named".
    unnamed = []
    for p in iter_files(root, FONT_FILE):
        rel = p.relative_to(root)
        stem = re.sub(r"[-_](?:regular|italic|bold|medium|light|thin|black|"
                      r"semibold|extrabold|variable|wght|subset|latin(?:-ext)?|"
                      r"\d{3,4})\b", " ", p.stem, flags=re.I)
        stem = re.sub(r"[-_.]+", " ", stem).strip()
        if re.fullmatch(r"[0-9a-f]{8,}", p.stem) or not stem:
            unnamed.append(str(rel))
            continue
        add(stem, "font file", rel)
    return out, unnamed


def declared_stacks(root: Path) -> dict:
    """family -> the stacks it appears in, from CSS and Tailwind config.

    A family only ever named in a stack, never provided, is the whole defect."""
    stacks: dict[str, list] = {}
    for p in list(iter_files(root, CSSISH)) + list(iter_files(root, SRCISH)):
        t = read(p)
        if "font-family" not in t and "fontFamily" not in t and "--font" not in t:
            continue
        rel = str(p.relative_to(root))
        for m in re.finditer(r"font-family\s*:\s*([^;}\n]+)", t):
            raw = m.group(1).strip().rstrip(",")
            if "var(" in raw and "," not in raw:
                continue
            fams = [x.strip() for x in raw.split(",") if x.strip()]
            for f in fams:
                if f.startswith("var("):
                    continue
                stacks.setdefault(norm(f), []).append({"file": rel, "stack": fams})
    return stacks


def host_faces() -> tuple[list, str]:
    """Faces on THIS machine. Informational, never evidence about a visitor."""
    fc = shutil.which("fc-list")
    if not fc:
        return [], ("fc-list is not on PATH, so the host's own font list is "
                    "unknown. This changes nothing about the verdict: a build "
                    "host's fonts were never evidence about a visitor's.")
    try:
        r = subprocess.run([fc, "--format", "%{family[0]}\n"],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return [], f"fc-list failed: {e}"
    fams = sorted({norm(x) for x in r.stdout.splitlines() if x.strip()})
    return fams, (f"{len(fams)} faces are installed on this machine. They are "
                  f"listed for orientation only -- the visitor's machine is the "
                  f"one that renders the product, and nothing here says what it "
                  f"has.")


# ------------------------------------------------------------------- analysis
def platforms_of(fam: str) -> set:
    return SYSTEM_FACES.get(norm(fam), set())


def primary(fam: str) -> str:
    """The face a declared value actually asks for: the first entry in the stack.

    A contract may legitimately declare a stack rather than a bare name --
    `ui-sans-serif, system-ui, sans-serif` is a complete and honest declaration for a
    product that ships no webfont. Treated as one opaque name it matched nothing in
    the generic list and nothing in the project, so it was reported as a missing
    face; the fix is to read it as CSS reads it. If the first entry is generic the
    whole stack always renders, and there is no availability question to answer."""
    first = str(fam or "").split(",")[0].strip().strip("'\"")
    return first or str(fam or "")


def resolve(fam: str, provided: dict) -> tuple[str, str]:
    """(verdict, why) for one declared value. Four outcomes, deliberately distinct."""
    fam = primary(fam)
    k = norm(fam)
    if k in GENERIC:
        return ("generic", "A generic family. Always renders, and names no face -- "
                           "the appearance is the user agent's choice.")
    if k in provided:
        how = ", ".join(provided[k]["how"])
        return ("shipped", f"Provided by the project ({how}).")
    near = _fuzzy(fam, provided.keys())
    if near:
        how = ", ".join(provided[near]["how"])
        return ("shipped", f"Provided by the project as `{provided[near]['name']}` "
                           f"({how}). The spelling differs from the declaration; if "
                           f"that is not the same face, the contract and the tree "
                           f"disagree about which typeface this product uses.")
    plats = platforms_of(k)
    if plats:
        if len(plats) == 1 and plats != {"web"}:
            return ("platform-limited",
                    f"Present on {sorted(plats)[0]} and not established elsewhere. "
                    f"On every other platform this entry is skipped, so whatever "
                    f"follows it in the stack is the real design.")
        return ("system", f"A face genuinely present on {', '.join(sorted(plats))}.")
    return ("missing", "No @font-face, @fontsource, next/font, font file or Google "
                       "Fonts request in this project provides it, and it is not a "
                       "face that ships with the major platforms. It will not render; "
                       "the next entry in the stack will.")


def pairing(a: str, b: str) -> tuple[str, str]:
    ca, cb = classify(a), classify(b)
    if ca == "unknown" or cb == "unknown":
        return ("unknown", f"Cannot classify {'both' if ca == cb else a if ca == 'unknown' else b}"
                           f" from the name alone. Look at the specimen.")
    if ca != cb:
        return ("contrasting", f"{a} reads as {ca}, {b} as {cb}. Different enough that "
                               f"a reader can tell which is which, which is the whole "
                               f"job of a second family.")
    if ca == "mono":
        return ("same", "Two monospace families is two code voices. Pick one.")
    return ("low-contrast",
            f"{a} and {b} are both {ca}. A second family earns its weight by being "
            f"legible as a different voice; two of the same class read as one family "
            f"rendered inconsistently. Either take the contrast (a serif against a "
            f"sans, a display against a text face) or drop to one family and carry "
            f"the hierarchy on weight and size, which is cheaper and usually better.")


def analyse(root: Path, contract: dict | None = None) -> dict:
    provided, unnamed = project_faces(root)
    stacks = declared_stacks(root)
    contract = contract if contract is not None else (uxconfig.contract(root) or {})
    fams = ((contract.get("type") or {}).get("families") or {}) \
        if isinstance(contract.get("type"), dict) else {}

    findings, declared = [], {}
    for role in ("display", "body", "mono"):
        name = fams.get(role)
        if name in (None, "", "UNKNOWN", "null"):
            continue
        verdict, why = resolve(name, provided)
        declared[role] = {"family": name, "verdict": verdict, "why": why,
                          "class": classify(primary(name)),
                          "named_in": [s["file"] for s in stacks.get(norm(name), [])][:5]}
        if verdict == "missing":
            findings.append({
                "severity": "high", "role": role, "family": name,
                "detail": f"The contract declares {role}: {name} and nothing provides "
                          f"it. {why} Every type decision made about {name} -- the "
                          f"scale, the leading, the tracking -- was made about a face "
                          f"this product does not render. Ship it (@fontsource, "
                          f"next/font, or a woff2 plus @font-face), or change the "
                          f"contract to the face that is actually rendering."})
        elif verdict == "platform-limited":
            findings.append({
                "severity": "medium", "role": role, "family": name,
                "detail": f"{role}: {name} -- {why}"})

    # A stack whose first real entry is missing, with no cross-platform fallback,
    # is a stack that renders as the generic default on most machines.
    for fam, uses in stacks.items():
        v, _why = resolve(fam, provided)
        if v != "missing":
            continue
        for u in uses[:1]:
            rest = [x for x in u["stack"][1:] if norm(x) != fam]
            ok = any(resolve(x, provided)[0] in ("shipped", "system", "generic")
                     for x in rest)
            if norm(u["stack"][0]) == fam and not ok:
                findings.append({
                    "severity": "high", "role": "stack", "family": u["stack"][0],
                    "detail": f"{u['file']}: `{', '.join(u['stack'])}` leads with a "
                              f"face nothing provides and has no fallback that "
                              f"resolves anywhere. This renders as the browser "
                              f"default, which is a typeface nobody chose."})

    named_roles = [(r, d["family"]) for r, d in declared.items() if r != "mono"]
    if len(named_roles) == 2:
        verdict, why = pairing(named_roles[0][1], named_roles[1][1])
        if verdict in ("low-contrast", "same"):
            findings.append({"severity": "low", "role": "pairing",
                             "family": f"{named_roles[0][1]} + {named_roles[1][1]}",
                             "detail": why})
    if len([1 for r in ("display", "body", "mono") if r in declared]) > 3:
        findings.append({"severity": "medium", "role": "count", "family": "",
                         "detail": "More than three families. Each one is a voice a "
                                   "reader has to learn."})

    host, host_note = host_faces()
    return {"root": str(root), "provided": provided, "unnamed_font_files": unnamed,
            "declared": declared, "stacks_named": sorted(stacks),
            "findings": findings, "host_faces_count": len(host), "host_note": host_note,
            "contract_present": bool(contract)}


# --------------------------------------------------------------------- output
def human(a: dict) -> None:
    w = sys.stderr.write
    w(f"\nfont index -- {a['root']}\n")
    prov = a["provided"]
    w(f"\nProvided by the project: {len(prov)}\n")
    for k, v in sorted(prov.items()):
        w(f"  {v['name']:<28} {classify(v['name']):<8} {', '.join(v['how'])}\n")
    if not prov:
        w("  (none -- every family this project names comes from the platform or "
          "does not render)\n")
    if a["unnamed_font_files"]:
        w(f"\n{len(a['unnamed_font_files'])} font file(s) ship with no recoverable "
          f"family name (hashed build output). They may be any of the above.\n")
    if a["declared"]:
        w("\nDeclared in the contract:\n")
        for role, d in a["declared"].items():
            w(f"  {role:<8} {d['family']:<24} {d['verdict'].upper():<16} {d['why']}\n")
    elif a["contract_present"]:
        w("\nThe contract declares no type.families, so there is nothing to resolve. "
          "NOT_RUN, not a pass.\n")
    else:
        w("\nNo .deuxui/design.contract.yaml. Nothing is declared, so nothing can "
          "be checked against a declaration.\n")
    if a["findings"]:
        w(f"\n{len(a['findings'])} finding(s):\n")
        for f in a["findings"]:
            w(f"\n  [{f['severity']}] {f['role']}: {f['family']}\n    {f['detail']}\n")
    else:
        w("\nNo findings. Every declared family is provided or genuinely present on "
          "the supported platforms.\n")
    w(f"\n{a['host_note']}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="exit 2 when a declared family is not provided")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"),
                    help="report whether two families carry different jobs")
    a = ap.parse_args(argv)

    if a.pair:
        v, why = pairing(a.pair[0], a.pair[1])
        if a.json:
            print(json.dumps({"a": a.pair[0], "b": a.pair[1], "verdict": v,
                              "why": why, "class_a": classify(a.pair[0]),
                              "class_b": classify(a.pair[1])}, indent=2))
        else:
            sys.stderr.write(f"\n{a.pair[0]} + {a.pair[1]}: {v.upper()}\n  {why}\n")
        return 0

    res = analyse(Path(a.root).resolve())
    if a.json:
        print(json.dumps(res, indent=2, sort_keys=False))
    else:
        human(res)
    if a.check:
        hard = [f for f in res["findings"] if f["severity"] == "high"]
        return 2 if hard else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
