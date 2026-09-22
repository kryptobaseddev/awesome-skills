#!/usr/bin/env python3
"""Find the exact source span of one element, or refuse to say.

This is the piece that was missing before structural edits were possible at all.
`ux_live.py` could locate the LINE an element came from, which is enough to write a
CSS rule scoped to it, and nowhere near enough to wrap it in new markup or insert a
sibling beside it. Those need the element's boundaries: where `<Card ...>` opens and
where its matching `</Card>` closes.

Scanning for `<` and `>` does not survive real code. Every one of these is a `<` or a
`>` that is not a tag boundary, and each one silently shifts the span by a few
characters -- which is worse than failing, because the edit still applies and still
looks plausible:

    <button onClick={() => setOpen(!open)}>      an arrow inside an expression
    <Cell value={a > b ? a : b} />               a comparison inside an expression
    <p title="a > b">                            a bare > inside an attribute string
    const [x] = useState<Row[]>([])              a TypeScript generic
    {/* <Legacy /> was here */}                  a tag inside a JSX comment
    // <Old /> kept for reference                a tag inside a line comment

So this scans with a small state machine that knows about strings, template literals,
both comment forms, and brace depth inside a tag, and then it **verifies the span it
found** before returning it: the span has to open and close with the same tag name,
contain the anchor exactly once, and be internally balanced. Anything it cannot verify
comes back as a refusal carrying the reason, and the caller writes nothing.

    jsxspan.py FILE --anchor "some visible text"
    jsxspan.py FILE --anchor "..." --json

Exit: 0 the span was resolved, 2 it was not.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr"}
RAW_TEXT = {"script", "style"}
NAME = re.compile(r"[A-Za-z_$][A-Za-z0-9._:$-]*")


def tags(text: str) -> list:
    """Every real tag in `text`, as dicts, skipping everything that only looks like one.

    A tag is `{kind, name, start, end}` where kind is `open`, `close` or `self`, and
    `start`/`end` bracket the whole tag including its angle brackets."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]

        # --- things that can contain a '<' and must be skipped whole -------------
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j == -1 else j + 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c in "\"'`":
            q, j = c, i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == q:
                    break
                j += 1
            i = j + 1
            continue
        if c != "<":
            i += 1
            continue

        # --- a '<' that might be a tag -------------------------------------------
        j = i + 1
        closing = False
        if j < n and text[j] == "/":
            closing, j = True, j + 1
        if j < n and text[j] == ">":
            # A fragment, <> or </>. Real, and it has no name, so it can never be the
            # element somebody picked -- but it must still be counted for balance.
            out.append({"kind": "close" if closing else "open", "name": "",
                        "start": i, "end": j + 1})
            i = j + 1
            continue
        m = NAME.match(text, j)
        if not m:
            i += 1              # `a < b`, or a generic's `<` -- not a tag
            continue
        name = m.group(0)
        k, depth, kind = m.end(), 0, "close" if closing else "open"
        # Walk the attribute area to its '>', tracking what a '>' might be inside.
        while k < n:
            ch = text[k]
            if ch in "\"'`":
                q, k2 = ch, k + 1
                while k2 < n:
                    if text[k2] == "\\":
                        k2 += 2
                        continue
                    if text[k2] == q:
                        break
                    k2 += 1
                k = k2 + 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif ch == ">" and depth <= 0:
                if not closing and text[k - 1] == "/":
                    kind = "self"
                break
            k += 1
        if k >= n:
            i += 1              # unterminated -- a generic, or truncated source
            continue
        if kind == "open" and name.lower() in VOID:
            kind = "self"
        out.append({"kind": kind, "name": name, "start": i, "end": k + 1})
        # A <script>/<style> body is not markup; skip it so its contents cannot
        # register as tags.
        if kind == "open" and name.lower() in RAW_TEXT:
            close = re.search(r"</\s*" + re.escape(name) + r"\s*>", text[k + 1:], re.I)
            if close:
                out.append({"kind": "close", "name": name,
                            "start": k + 1 + close.start(), "end": k + 1 + close.end()})
                i = k + 1 + close.end()
                continue
        i = k + 1
    return out


def spans(text: str) -> list:
    """Every element with a resolved start and end, innermost last.

    Unbalanced tags are not an error here -- half of real JSX has a conditional close
    somewhere -- they simply produce no span, so nothing can be edited by mistake."""
    out, stack = [], []
    for t in tags(text):
        if t["kind"] == "self":
            out.append({"name": t["name"], "start": t["start"], "end": t["end"],
                        "open_end": t["end"], "self": True})
        elif t["kind"] == "open":
            stack.append(t)
        else:
            for idx in range(len(stack) - 1, -1, -1):
                if stack[idx]["name"] == t["name"]:
                    o = stack[idx]
                    out.append({"name": o["name"], "start": o["start"],
                                "end": t["end"], "open_end": o["end"], "self": False})
                    del stack[idx:]
                    break
    out.sort(key=lambda s: (s["end"] - s["start"]))
    return out


# A repeated element is authored once and rendered N times. Editing it is legitimate --
# it is often exactly what somebody means -- but it is not a local change, and a tool
# that applies it without saying so has quietly edited every row of a table.
REPEATERS = [
    (re.compile(r"\.\s*(map|flatMap|forEach)\s*\("), ")", "a .{0}() callback"),
    (re.compile(r"\{\s*#each\b"), "{/each}", "a Svelte {#each} block"),
    (re.compile(r"\{\s*#for\b"), "{/for}", "an {#for} block"),
]
# `\b` before `*ngFor` never matches: the character before `*` is a space, and two
# non-word characters have no boundary between them, so Angular's form was silently
# never detected. A negative lookbehind works for every spelling and still refuses to
# match inside a longer attribute like `data-v-for`.
_ATTR_REPEAT = re.compile(r"(?<![\w-])(v-for|x-for|\*ngFor|ng-repeat)\s*=", re.I)


def _closes(text: str, open_at: int, opener: str, closer: str) -> int:
    """Where the construct starting at `open_at` ends, by balancing its delimiters."""
    if len(closer) > 1:                      # a literal terminator like {/each}
        j = text.find(closer, open_at)
        return j + len(closer) if j != -1 else -1
    depth, i, n = 0, open_at, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":                       # skip strings; a paren inside one is text
            q, i = c, i + 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == q:
                    break
                i += 1
        elif c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def repeated(text: str, start: int, end: int) -> dict | None:
    """Is this span inside something that renders it more than once, and where.

    This is the honest half of what a framework adapter buys. An adapter would know the
    component graph; this knows only the file. But the question that actually decides
    whether a structural edit is safe -- "does this markup run once, or once per row?"
    -- is answerable from the text, and answering it turns "wrapped the element" into
    "wrapped every row of the table", which is the difference between a change somebody
    asked for and one they have to find later."""
    best = None
    for pat, closer, what in REPEATERS:
        for m in pat.finditer(text, 0, start):
            opener = "(" if closer == ")" else ""
            at = text.find("(", m.end() - 1) if closer == ")" else m.start()
            if closer == ")":
                stop = _closes(text, at, "(", ")")
            else:
                stop = _closes(text, m.start(), "", closer)
            if stop != -1 and m.start() < start and end <= stop:
                if best is None or m.start() > best["at"]:
                    # Name the method that is actually there. Reporting `forEach` as
                    # ".map()" is a small lie about somebody's code, and this text is
                    # read by a person deciding whether an edit is safe.
                    label = (what.format(m.group(1)) if "{0}" in what and m.groups()
                             else what)
                    best = {"at": m.start(), "kind": label,
                            "line": text[:m.start()].count("\n") + 1}
    # An attribute-based repeat sits on an ANCESTOR tag, so look at every open tag that
    # encloses the span rather than at text before it.
    # Includes the span ITSELF, not only its ancestors: `v-for` sits on the element
    # being repeated, so the element somebody picks IS the one carrying the attribute.
    # Requiring a strict ancestor missed every Vue and Alpine case.
    for s in spans(text):
        if s["start"] <= start and end <= s["end"]:
            head = text[s["start"]:s["open_end"]]
            m = _ATTR_REPEAT.search(head)
            if m and (best is None or s["start"] > best["at"]):
                best = {"at": s["start"], "kind": f"a {m.group(1)} on <{s['name']}>",
                        "line": text[:s["start"]].count("\n") + 1}
    return best


def verify(text: str, s: dict, anchor: str) -> tuple[bool, str]:
    """Is this span safe to edit? Three checks, each one a way the scan could be wrong."""
    body = text[s["start"]:s["end"]]
    if not body.startswith("<"):
        return False, "the span does not begin with a tag"
    if not (body.endswith(">")):
        return False, "the span does not end with a tag"
    if body.count(anchor) != 1:
        return False, (f"the span contains the anchor {body.count(anchor)} times, "
                       f"so editing it would move more than the picked element")
    if not s["self"]:
        inner = tags(body)
        opens = sum(1 for t in inner if t["kind"] == "open")
        closes = sum(1 for t in inner if t["kind"] == "close")
        if opens != closes:
            return False, (f"the span has {opens} opening and {closes} closing tag(s), "
                           f"so its boundaries are not established")
    return True, ""


def find(text: str, anchor: str, want_tag: str | None = None) -> dict:
    """The verified element containing `anchor`, or a refusal with the reason.

    `want_tag` is the DOM tag the browser reported for the element somebody actually
    picked, and passing it is not optional in practice. Without it this returns the
    INNERMOST element containing the anchor, which is wrong the moment a container is
    picked: `<section>`'s innerText begins with its first heading's text, so picking
    the section and asking to wrap it wrapped the `<h1>` instead -- an edit that
    applied cleanly, looked right in the diff, and moved something nobody named.

    A capitalised span name is a component (`<Heading>`), whose rendered DOM tag
    cannot be known from source, so it is allowed to match anything. A *lowercase*
    name that differs from the picked tag is a provable mismatch and refuses."""
    hits = [m.start() for m in re.finditer(re.escape(anchor), text)]
    if not hits:
        return {"found": False, "why": f"{anchor!r} is not in this file"}
    if len(hits) > 1:
        return {"found": False,
                "why": f"{anchor!r} appears {len(hits)} times in this file, so there is "
                       f"no single element to edit"}
    at = hits[0]
    rejected = []
    for s in spans(text):
        if not (s["start"] <= at and at + len(anchor) <= s["end"]):
            continue
        if want_tag and s["name"] and s["name"][:1].islower() \
                and s["name"].lower() != want_tag.lower():
            rejected.append({"name": s["name"],
                             "line": text[:s["start"]].count("\n") + 1,
                             "why": f"this is a <{s['name']}>, but the element picked "
                                    f"in the browser was a <{want_tag.lower()}>"})
            continue
        ok, why = verify(text, s, anchor)
        if ok:
            line = text[:s["start"]].count("\n") + 1
            indent = re.match(r"[ \t]*",
                              text[text.rfind("\n", 0, s["start"]) + 1:]).group(0)
            return {"found": True, "name": s["name"], "start": s["start"],
                    "end": s["end"], "open_end": s["open_end"], "self": s["self"],
                    "line": line, "indent": indent,
                    "repeated": repeated(text, s["start"], s["end"]),
                    "source": text[s["start"]:s["end"]], "rejected": rejected}
        rejected.append({"name": s["name"], "line": text[:s["start"]].count("\n") + 1,
                         "why": why})
    return {"found": False, "rejected": rejected,
            "why": ("no element around that text has boundaries this can establish. "
                    + (f"Closest: {rejected[0]['why']}" if rejected else
                       "Nothing enclosing it parsed as an element at all."))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--anchor", required=True)
    ap.add_argument("--tag", help="the DOM tag the element was picked as; a lowercase "
                                 "span with a different name is refused")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        text = Path(a.file).read_text(errors="replace")
    except OSError as e:
        sys.stderr.write(f"{e}\n")
        return 2
    r = find(text, a.anchor, a.tag)
    if a.json:
        print(json.dumps(r, indent=1))
        return 0 if r["found"] else 2
    if not r["found"]:
        sys.stderr.write(f"\nNOT RESOLVED. {r['why']}\n\n")
        for x in r.get("rejected", [])[:5]:
            sys.stderr.write(f"  <{x['name']}> at line {x['line']}: {x['why']}\n")
        sys.stderr.write("\n")
        return 2
    rep = r.get("repeated")
    note = (f"  inside {rep['kind']} at line {rep['line']} -- this markup renders once "
            f"PER ITEM\n" if rep else "")
    sys.stderr.write(f"\n<{r['name']}> at {a.file}:{r['line']}"
                     f"{' (self-closing)' if r['self'] else ''}\n"
                     f"{note}"
                     f"  {len(r['source'])} char(s), indent {len(r['indent'])}\n\n"
                     f"{r['source'][:600]}\n\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
