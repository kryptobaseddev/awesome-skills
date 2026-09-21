"""Shared scanning helpers for the static tier.

This is a tolerant scanner, not a parser. It reads the shape of markup well
enough to answer attribute and nesting questions, and it is wrong often enough
that every finding carries a confidence and every check can say NOT_RUN. If you
need certainty, use the runtime tier -- a live page cannot lie about its own
computed styles the way source text can.
"""
from __future__ import annotations
import json, os, re
from dataclasses import dataclass, field
from pathlib import Path

DATA = Path(__file__).parent / "data"
SOURCE_EXT = {".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue", ".astro", ".html", ".htm"}
STYLE_EXT = {".css", ".scss", ".sass", ".less"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit", ".nuxt",
             "out", "coverage", "vendor", "__pycache__", ".venv", "venv", ".turbo",
             ".output", "storybook-static", ".cache",
             # Not user interface: codegen and build scripts are full of HTML
             # template strings that no human ever looks at.
             "scripts", "bin", "tools", "migrations", "seeds", "seed",
             "e2e", "tests", "__tests__", "test", "cypress", "playwright",
             "supabase", "prisma", "drizzle", "functions", "docs"}
SKIP_FILE_RE = re.compile(r"\.(?:test|spec|stories|bench|config|d)\.[jt]sx?$|"
                          r"^(?:route|middleware|instrumentation)\.[jt]s$|"
                          r"\.server\.[jt]s$|^\+server\.[jt]s$|"
                          r"^(?:vite|next|nuxt|astro|svelte|tailwind|postcss|eslint)\.config\.")

INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea", "summary", "details",
                    "option"}
# <label> takes clicks, but wrapping its own control is the recommended pattern,
# so it is deliberately not counted as an interactive ancestor.
LABELLING_TAGS = {"label"}
# Common design-system wrappers that render a real control underneath.
INTERACTIVE_COMPONENTS = re.compile(
    r"^(Button|IconButton|Link|NavLink|MenuItem|Tab|Chip|Toggle|Switch|Checkbox|Radio|"
    r"Select|Input|Textarea|Anchor|Pressable|TouchableOpacity)$")


# --------------------------------------------------------------------------- files
def iter_files(root: Path, exts=None):
    exts = exts or (SOURCE_EXT | STYLE_EXT)
    if root.is_file():
        if root.suffix in exts:
            yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                       or d in (".storybook",)]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix in exts and not SKIP_FILE_RE.search(fn):
                yield p


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


_COMMENT = re.compile(r"/\*.*?\*/|(?<![:\\])//[^\n]*", re.S)


def strip_comments(text: str) -> str:
    """Prose in a comment is not code. Matching `generates` in a docblock, or a
    banned phrase in a TODO, produces findings nobody can act on -- replace each
    comment with blanks so line numbers still line up."""
    return _COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def is_generated(path: Path, text: str) -> bool:
    """Never report on, or propose edits to, a file the build owns."""
    head = text[:300]
    posix = path.as_posix()
    return ("@generated" in head or "DO NOT EDIT" in head.upper()
            or path.name.endswith(".d.ts") or ".min." in path.name
            # Generated clients and schema types rarely carry a header banner.
            or re.search(r"/(?:integrations|generated|__generated__|\.gen)/", posix)
            or path.name in ("types.gen.ts", "schema.gen.ts", "routeTree.gen.ts"))


# --------------------------------------------------------------------------- tags
@dataclass
class Tag:
    name: str
    attrs: dict
    line: int
    start: int
    end: int
    self_closing: bool
    closing: bool
    raw: str
    parent: "Tag | None" = None
    children: list = field(default_factory=list)
    inner: str = ""

    def attr(self, *names):
        for n in names:
            if n in self.attrs:
                return self.attrs[n]
        return None

    def has(self, *names):
        return any(n in self.attrs for n in names)

    def classes(self) -> list[str]:
        v = self.attr("class", "className", "classList") or ""
        return re.findall(r"[A-Za-z0-9_:\-\[\]./%#()!,'\"+*$&~=<>|^@]+", v)

    def is_interactive(self) -> bool:
        if self.name in INTERACTIVE_TAGS:
            return not (self.name == "a" and not self.has("href", "to"))
        if INTERACTIVE_COMPONENTS.match(self.name):
            return True
        return self.has("onClick", "onclick", "on:click", "@click", "onPress")


_ATTR = re.compile(r"""([:@\w][-:.\w]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|(\{)|([^\s>"'`]+))""")
_TAG_OPEN = re.compile(r"<\s*(/?)([A-Za-z][\w.:-]*)")


def _brace_span(s: str, i: int) -> int:
    """Index just past the {...} starting at i, tolerating nested braces/strings."""
    depth, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "\"'`":
            q, i = c, i + 1
            while i < n and s[i] != q:
                i += 2 if s[i] == "\\" else 1
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _parse_attrs(chunk: str) -> dict:
    out = {}
    i = 0
    while i < len(chunk):
        m = _ATTR.search(chunk, i)
        if not m:
            break
        name = m.group(1)
        if m.group(4) == "{":
            end = _brace_span(chunk, m.end() - 1)
            out[name] = chunk[m.end() - 1:end]
            i = end
        else:
            out[name] = m.group(2) or m.group(3) or m.group(5) or ""
            i = m.end()
    # valueless attributes (disabled, required, autoFocus, ...)
    for m in re.finditer(r"(?<![\w=:@.-])([A-Za-z][\w:-]*)(?=\s|$)", chunk):
        out.setdefault(m.group(1), "")
    return out


def scan_tags(text: str) -> list[Tag]:
    """Flat list of tags with parent/child links. Unmatched tags are tolerated."""
    tags: list[Tag] = []
    stack: list[Tag] = []
    i, n = 0, len(text)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", text)]

    def line_of(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    while i < n:
        m = _TAG_OPEN.search(text, i)
        if not m:
            break
        start, closing, name = m.start(), m.group(1) == "/", m.group(2)
        j = m.end()
        # walk to the matching '>' honouring {...} and quoted strings
        while j < n:
            c = text[j]
            if c == "{":
                j = _brace_span(text, j)
                continue
            if c in "\"'":
                q, j = c, j + 1
                while j < n and text[j] != q:
                    j += 2 if text[j] == "\\" else 1
            elif c == ">":
                break
            j += 1
        if j >= n:
            break
        raw = text[start:j + 1]
        self_closing = raw.rstrip().endswith("/>") or name.lower() in (
            "img", "input", "br", "hr", "meta", "link", "source", "path", "circle", "rect")
        if closing:
            for k in range(len(stack) - 1, -1, -1):
                if stack[k].name == name:
                    stack[k].inner = text[stack[k].end:start]
                    del stack[k:]
                    break
        else:
            t = Tag(name=name, attrs=_parse_attrs(text[m.end():j]), line=line_of(start),
                    start=start, end=j + 1, self_closing=self_closing, closing=False, raw=raw)
            if stack:
                t.parent = stack[-1]
                stack[-1].children.append(t)
            tags.append(t)
            if not self_closing:
                stack.append(t)
        i = j + 1
    for t in stack:
        t.inner = text[t.end:]
    return tags


def ancestors(t: Tag):
    p = t.parent
    while p:
        yield p
        p = p.parent


# --------------------------------------------------------------------------- colour
# Colours are resolved from the project, never guessed. Tailwind v4 ships its
# palette as OKLCH `--color-*` theme variables, and projects override them in
# `@theme`, so an embedded hex table would be wrong the moment anyone themes
# anything. Order: project @theme / :root vars, then the installed Tailwind
# theme.css, then literal values. Anything unresolved returns None, and the
# caller reports NOT_RUN rather than inventing a verdict.
import math

_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
_THEME_BLOCK = re.compile(r"@theme[^{]*\{(.*?)\n\}", re.S)


def collect_css_vars(root: Path) -> dict:
    """--custom-property -> raw value, from the project and its installed theme."""
    out = {}
    tw = root / "node_modules" / "tailwindcss" / "theme.css"
    if tw.exists():
        for m in _VAR_RE.finditer(read(tw)):
            out[m.group(1)] = m.group(2).strip()
    for f in iter_files(root, STYLE_EXT):
        txt = read(f)
        for blk in _THEME_BLOCK.findall(txt):          # v4 CSS-first config wins
            for m in _VAR_RE.finditer(blk):
                out[m.group(1)] = m.group(2).strip()
        for m in re.finditer(r"(?::root|:host|\[data-theme[^\]]*\])[^{]*\{([^}]*)\}", txt):
            for v in _VAR_RE.finditer(m.group(1)):
                out.setdefault(v.group(1), v.group(2).strip())
    return out


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    if len(h) < 6:
        return None
    try:
        return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
    except ValueError:
        return None


def _oklch_to_rgb(L, C, H):
    """Bjorn Ottosson's OKLab transform, clamped to sRGB gamut."""
    a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lin = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    def enc(c):
        c = min(1.0, max(0.0, c))
        c = 1.055 * (c ** (1 / 2.4)) - 0.055 if c > 0.0031308 else 12.92 * c
        return round(min(1.0, max(0.0, c)) * 255)
    return tuple(enc(c) for c in lin)


def _hsl_to_rgb(h, s, l):
    s, l = s / 100.0, l / 100.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs(((h / 60.0) % 2) - 1))
    m = l - c / 2
    r, g, b = [(c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)][int(h // 60) % 6]
    return tuple(round((v + m) * 255) for v in (r, g, b))


def _nums(s, n):
    vals = re.findall(r"-?[\d.]+%?", s)[:n]
    if len(vals) < n:
        return None
    return vals


def parse_color(v: str, cssvars: dict | None = None, _depth=0):
    """Resolve a CSS colour to (r,g,b), or None when it cannot be resolved."""
    if not v or _depth > 6:
        return None
    v = v.strip().lower().rstrip(";")
    if v in ("transparent", "currentcolor", "inherit", "none", "initial", "unset"):
        return None
    if v == "white":
        return (255, 255, 255)
    if v == "black":
        return (0, 0, 0)
    m = re.match(r"var\(\s*(--[\w-]+)\s*(?:,([^)]*))?\)", v)
    if m:
        cssvars = cssvars or {}
        got = cssvars.get(m.group(1))
        if got:
            return parse_color(got, cssvars, _depth + 1)
        return parse_color(m.group(2), cssvars, _depth + 1) if m.group(2) else None
    m = re.match(r"light-dark\(([^,]+),", v)          # judge the light side by default
    if m:
        return parse_color(m.group(1), cssvars, _depth + 1)
    if v.startswith("#"):
        return hex_to_rgb(v)
    m = re.match(r"oklch\(\s*([^)]+)\)", v)
    if m:
        p = _nums(m.group(1), 3)
        if not p:
            return None
        L = float(p[0].rstrip("%")) / (100 if p[0].endswith("%") else 1)
        return _oklch_to_rgb(L, float(p[1].rstrip("%")), float(p[2].rstrip("%")))
    m = re.match(r"hsla?\(\s*([^)]+)\)", v)
    if m:
        p = _nums(m.group(1), 3)
        return _hsl_to_rgb(float(p[0].rstrip("%")), float(p[1].rstrip("%")),
                           float(p[2].rstrip("%"))) if p else None
    m = re.match(r"rgba?\(\s*([^)]+)\)", v)
    if m:
        alpha = re.findall(r"[\d.]+", m.group(1))
        if len(alpha) >= 4 and float(alpha[3]) < 0.99:
            return None          # translucent: the real backdrop is unknown here
        p = _nums(m.group(1), 3)
        return tuple(min(255, round(float(x.rstrip("%")) * (2.55 if x.endswith("%") else 1)))
                     for x in p) if p else None
    return None


def tw_color(token: str, cssvars: dict):
    if "/" in token:             # opacity modifier -- composited, so unresolvable
        return None
    """Resolve a Tailwind colour utility through the project's own theme vars."""
    m = re.match(r"^(?:[\w@\[\]-]+:)*(?:text|bg|border|fill|stroke|ring|decoration|"
                 r"outline|accent|caret|divide|from|to|via)-"
                 r"([a-z][\w-]*?)(?:-(\d{1,3}))?(?:/\d+)?$", token)
    if not m:
        return None
    fam, shade = m.group(1), m.group(2)
    key = f"--color-{fam}-{shade}" if shade else f"--color-{fam}"
    raw = cssvars.get(key)
    if raw is None and not shade:
        if fam == "white":
            return (255, 255, 255)
        if fam == "black":
            return (0, 0, 0)
    return parse_color(raw, cssvars) if raw else None


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg, bg) -> float:
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)
