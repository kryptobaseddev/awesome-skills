#!/usr/bin/env python3
"""The system of record: what the design is now, and how it got that way.

    ux_ledger.py state       what is declared, decided and open, right now
    ux_ledger.py log         every design event in order, oldest first
    ux_ledger.py show ID     one entry, with the contract it was decided against
    ux_ledger.py diff [A] [B]   what changed in the declaration between two shas
    ux_ledger.py snapshot    archive the current contract, content-addressed

Everything this tool needs already existed and none of it was readable together.
A decision was a file in `.deluxui/decisions/`, a note was a file in
`.deluxui/requests/`, the phase order was a list inside `phase.yaml`, and the
declaration was one mutable file that got overwritten. So the project had a record
of every individual event and no record of the *sequence*, which is the part
somebody arriving in month six actually needs.

Two properties make this a ledger rather than a report.

**The declaration is content-addressed.** `snapshot` archives
`design.contract.yaml` under its own sha in `.deluxui/contract/`, with a lineage
index recording which fields changed against the previous one. A decision already
carried a `contract_sha`; now that sha resolves to bytes, so "what did the palette
look like when this was approved" has an answer instead of an assumption.

**A reference that cannot be resolved is reported as a gap, never filled in from
the present.** If a decision names a contract nobody archived, this says so and
shows nothing -- the same discipline as NOT_RUN. Showing the *current* contract
beside an old approval would be the single most misleading thing a ledger could
do: it would make every past decision look like it was made with today's
information. That is the failure this file is shaped to prevent, so `state` counts
unresolvable references and `A-CONTRACT-ARCHIVED` reports them to the gate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import ux_image                                                    # noqa: E402
import uxconfig                                                    # noqa: E402

ROOT = Path(".deluxui")
CONTRACT = ROOT / "design.contract.yaml"
ARCHIVE = ROOT / "contract"
LINEAGE = ARCHIVE / "lineage.yaml"
PHASE = ROOT / "phase.yaml"
DECISIONS = ROOT / "decisions"
REQUESTS = ROOT / "requests"
COMPS = ROOT / "comps"
PROTO = ROOT / "proto"
REPORTS = ROOT / "reports"
EXCEPTIONS = ROOT / "exceptions.yaml"
# The other two declarations. PRODUCT.md owns audience, jobs and risk; DESIGN.md
# owns the visual system as built. They are archived beside each contract version
# rather than under their own hashes, because the question anyone asks of them is
# "what did the brief say when this was approved" -- which is a question about the
# contract's version, not about theirs.
BRIEFS = [("PRODUCT.md", ROOT / "PRODUCT.md", "audience, jobs, risk"),
          ("DESIGN.md", ROOT / "DESIGN.md", "the visual system as built")]

# What a declaration is made of, in the order a person reads it. The ledger names
# every one of these even when it is undeclared, because a field nobody has
# decided is the most useful thing `state` can tell you and omitting it reads as
# though the system were complete.
FIELDS = [
    ("visitor_mode", "what the visitor came to do"),
    ("world", "the world, in observable values"),
    ("type.families", "type families"),
    ("type.scale_px", "the size ladder"),
    ("color.space", "colour space"),
    ("color.roles", "colour by role"),
    ("color.ramp_steps", "the lightness steps in use"),
    ("color.dark_mode", "dark mode"),
    ("depth.metaphor", "the one depth metaphor"),
    ("depth.elevations", "the elevation set"),
    ("spacing.scale", "the spacing scale"),
    ("radius.control_px", "control radius"),
    ("radius.card_px", "card radius"),
    ("grid.columns", "columns"),
    ("grid.container_max_px", "container width"),
    ("motion.duration_ms", "the motion band"),
    ("motion.easing", "easing"),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(p: Path):
    if not p.exists():
        return None
    try:
        return yaml.safe_load(p.read_text(errors="replace"))
    except yaml.YAMLError:
        return None


def sha_of(data) -> str:
    """The identity every other part of this system uses for a contract.

    Not the hash of the file. `uxconfig.contract()` strips every `UNKNOWN` before a
    contract is handed to anything, and `Contract.sha()` hashes the result -- so a
    decision's `contract_sha` is the hash of the DECLARED subset. An archive keyed
    by the file's own bytes would therefore never match a single decision ever
    recorded, and the ledger would report every approval as unresolvable while
    looking like it was working. Two consequences worth stating:

      * A comment-only edit does not produce a new version. Correct: a comment is
        not a commitment.
      * Filling in an `UNKNOWN` does, because a key appears in the declared subset.
        Also correct, and it is the most interesting kind of edit there is.
    """
    return ux_image.Contract(uxconfig.clean_contract(data or {})).sha()


def file_sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    except OSError:
        return None


# ------------------------------------------------------------------ the archive
def flat(d, prefix="") -> dict:
    """Dotted paths to scalars, with lists compared whole.

    A changed size ladder is one decision, not eight; reporting it as eight
    changed indices buries the fact that somebody re-pitched the type scale."""
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(flat(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(d, list):
        out[prefix] = json.dumps(d, default=str)
    else:
        out[prefix] = d
    return out


def lineage() -> list:
    return load(LINEAGE) or []


def archived(sha: str) -> dict | None:
    """The contract bytes for a sha, or None. None means nobody archived it."""
    if not sha:
        return None
    p = ARCHIVE / f"{sha}.yaml"
    return load(p) if p.exists() else None


def changed_fields(prev, cur) -> list:
    a, b = flat(prev or {}), flat(cur or {})
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append({"field": k, "from": a.get(k), "to": b.get(k)})
    return out


def archive(by: str = "ux_ledger.py snapshot", note: str | None = None) -> dict:
    """Put the current contract in the archive under its own sha.

    Idempotent by content: archiving twice without an edit adds nothing, so this
    is safe to call from anywhere a contract might have been written. Which is
    the point -- an archive that depends on somebody remembering to run it is an
    archive with holes exactly where the interesting edits are."""
    data = load(CONTRACT)
    if data is None:
        return {"ok": False, "why": f"no {CONTRACT}"}
    sha = sha_of(data)          # the declared subset's identity; see sha_of
    raw = CONTRACT.read_text(errors="replace")   # what a person actually wrote
    lin = lineage()
    if lin and lin[-1].get("sha") == sha:
        return {"ok": True, "sha": sha, "new": False, "why": "unchanged since the last snapshot"}
    for e in lin:
        if e.get("sha") == sha:
            # A revert. Worth recording as its own event: the declaration coming
            # back to a previous state is a design decision, not a non-event.
            lin.append({"sha": sha, "at": now(), "parent": lin[-1].get("sha"),
                        "by": by, "note": note or "reverted to an earlier declaration",
                        "changed": changed_fields(archived(lin[-1]["sha"]), data),
                        "reverts_to": e.get("at")})
            ARCHIVE.mkdir(parents=True, exist_ok=True)
            LINEAGE.write_text(yaml.safe_dump(lin, sort_keys=False, allow_unicode=True,
                                              width=92))
            return {"ok": True, "sha": sha, "new": True, "reverted": True}
    prev = archived(lin[-1]["sha"]) if lin else None
    c = ux_image.Contract(data)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    # The file verbatim, comments and blanks included. A future reader diffing two
    # versions should see the document that was edited, not a normalised rewrite of
    # it that silently drops the reasoning in the comments.
    (ARCHIVE / f"{sha}.yaml").write_text(raw)
    briefs = {}
    for name, src, _why in BRIEFS:
        if src.exists():
            body = src.read_text(errors="replace")
            (ARCHIVE / f"{sha}.{name}").write_text(body)
            briefs[name] = file_sha(src)
    entry = {"sha": sha, "at": now(), "parent": (lin[-1].get("sha") if lin else None),
             "by": by, "declared": len(c.declared), "undeclared": c.undeclared,
             "changed": changed_fields(prev, data), "briefs": briefs}
    if not lin:
        # The first declaration is not a change from an empty contract. Reporting it
        # as "31 fields changed" invents a previous version that never existed.
        entry["changed"] = []
        entry["note"] = note or "the first declaration"
        note = None
    if note:
        entry["note"] = note
    lin.append(entry)
    LINEAGE.write_text(yaml.safe_dump(lin, sort_keys=False, allow_unicode=True, width=92))
    return {"ok": True, "sha": sha, "new": True, "changed": len(entry["changed"]),
            "first": entry["parent"] is None, "declared": entry["declared"]}


# ----------------------------------------------------------------- the entries
def decisions() -> list:
    out = []
    for p in sorted(DECISIONS.glob("DEC-*.yaml")) if DECISIONS.exists() else []:
        d = load(p)
        if isinstance(d, dict):
            out.append((p, d))
    return out


def requests() -> list:
    out = []
    for p in sorted(REQUESTS.glob("REQ-*.yaml")) if REQUESTS.exists() else []:
        d = load(p)
        if isinstance(d, dict):
            out.append((p, d))
    return out


def stage_of(d: dict) -> str:
    """Which review stage a decision settles. A wireframe cannot settle whether
    the thing works, so the two are never interchangeable in the record."""
    src = str(d.get("source") or "")
    if "ux_review" in src:
        return "prototype"
    if "ux_question" in src:
        return "wireframe"
    return str(d.get("stage") or "unknown")


def events() -> list:
    """Every design event, normalised, oldest first.

    `integrity` is the column that makes this a record rather than a listing: it
    is checked against the filesystem now, so an entry pointing at something that
    has since changed or vanished says so instead of reading as settled."""
    ev = []
    st = load(PHASE) or {}
    if st.get("started_at"):
        ev.append({"at": st["started_at"], "kind": "phase", "id": "discover",
                   "what": f"work started in {st.get('mode', 'unknown')} mode "
                           f"({st.get('ui_files_at_init', 0)} UI files present)",
                   "who": None, "ref": str(PHASE), "integrity": None})
    for h in st.get("history") or []:
        ev.append({"at": h.get("at"), "kind": "phase", "id": h.get("to"),
                   "what": f"entered `{h.get('to')}`",
                   "who": None, "ref": str(PHASE),
                   "integrity": None,
                   "detail": h.get("evidence") or []})
    for o in st.get("overrides") or []:
        ev.append({"at": o.get("at"), "kind": "override", "id": o.get("phase"),
                   "what": f"gate overridden into `{o.get('phase')}`: {o.get('reason')}",
                   "who": o.get("who"), "ref": str(PHASE),
                   "integrity": "an override is evidence that a requirement was "
                                "not met, and it does not expire"})
    for e in lineage():
        n = len(e.get("changed") or [])
        ev.append({"at": e.get("at"), "kind": "contract", "id": e.get("sha"),
                   "what": ("the first declaration" if not e.get("parent") else
                            f"the declaration changed in {n} field(s)"),
                   "who": e.get("by"), "ref": str(ARCHIVE / f"{e['sha']}.yaml"),
                   "integrity": (None if (ARCHIVE / f"{e['sha']}.yaml").exists()
                                 else "the archived bytes are missing"),
                   "detail": e.get("changed") or []})
    for p, d in decisions():
        csha = d.get("contract_sha")
        integ = None
        if not csha:
            integ = ("no contract_sha, so what was declared when this was approved "
                     "cannot be established")
        elif archived(csha) is None:
            integ = f"contract {csha} was never archived; it cannot be resolved"
        ev.append({"at": d.get("recorded_at") or d.get("date"), "kind": "decision",
                   "id": d.get("id") or p.stem,
                   "what": f"{stage_of(d)}: {d.get('outcome') or d.get('chosen')} "
                           f"-- {d.get('question') or d.get('surface') or ''}".strip(),
                   "who": d.get("who"), "ref": str(p), "integrity": integ,
                   "detail": {"contract_sha": csha,
                              "notes": len(d.get("notes") or []),
                              "approves_a_build": bool(d.get("approves_a_build"))}})
    for p, d in requests():
        ev.append({"at": d.get("at") or d.get("recorded_at"), "kind": "note",
                   "id": d.get("req") or p.stem,
                   "what": (str(d.get("text") or "").strip()[:120] or "(empty note)"),
                   "who": d.get("who"), "ref": str(p),
                   "integrity": None,
                   "detail": {"variant": d.get("variant"), "chip": d.get("chip"),
                              "selector": d.get("selector")}})
    for p in sorted(REPORTS.glob("agent_report*.yaml")) if REPORTS.exists() else []:
        r = load(p) or {}
        g = (r.get("gate") or {}) if isinstance(r.get("gate"), dict) else {}
        ev.append({"at": r.get("generated_at") or r.get("at"), "kind": "report",
                   "id": p.stem,
                   "what": f"verdict {g.get('decision') or r.get('decision') or '?'}",
                   "who": None, "ref": str(p), "integrity": None})
    # An event with no timestamp cannot be placed in a sequence, and guessing one
    # from the file's mtime would put a copied file in the wrong decade. They sort
    # last, under a heading that says why.
    dated = [e for e in ev if e.get("at")]
    undated = [e for e in ev if not e.get("at")]
    dated.sort(key=lambda e: str(e["at"]))
    return dated + undated


# ------------------------------------------------------------------ the state
def component_system() -> dict:
    """What the interface is actually built out of, measured from the tree.

    A declaration says what the design should be; this says what is installed to
    build it with. Both belong in a ledger, and they are different claims -- a
    contract declaring `depth.metaphor: shadow` over a component library whose
    every primitive ships a border is a conflict nobody would find by reading
    either one alone."""
    try:
        import ux_check
        from checks.designsystem import PRIMITIVES
    except ImportError as e:                                  # pragma: no cover
        return {"measured": False, "why": f"{e}"}
    p = ux_check.detect_project(Path.cwd())
    libs = sorted({name for dep, name in PRIMITIVES.items()
                   if any(d == dep or d.startswith(dep + "/") for d in p.deps)})
    frameworks = sorted({f for f, dep in (("React", "react"), ("Vue", "vue"),
                                          ("Svelte", "svelte"), ("Angular", "@angular/core"),
                                          ("Solid", "solid-js"), ("Astro", "astro"),
                                          ("React Native", "react-native"),
                                          ("Flutter", "flutter"))
                         if dep in p.deps})
    return {"measured": True, "frameworks": frameworks, "primitive_libraries": libs,
            "tailwind_major": p.tailwind_major or None,
            "token_sources": p.token_sources[:8],
            "css_variables": len(p.cssvars),
            "components": len(p.inventory),
            "component_sample": sorted(p.inventory.items())[:10],
            "platforms": sorted(p.platforms)}


# The fields `Contract.undeclared` insists on. Named here so `state` can mark a
# blank as "a check is waiting on this" rather than "somebody chose not to".
_REQUIRED = {"visitor_mode", "world", "type.families", "type.scale_px",
             "color.roles", "radius.card_px", "radius.control_px", "depth.metaphor",
             "depth.elevations", "spacing.scale", "motion.duration_ms"}


def declaration() -> dict:
    data = load(CONTRACT)
    c = ux_image.Contract(data)
    f = flat(data or {})
    rows = []
    for path, label in FIELDS:
        vals = {k: v for k, v in f.items() if k == path or k.startswith(path + ".")}
        stated = {k: v for k, v in vals.items()
                  if v not in (None, "", "UNKNOWN", "null", "[]", "{}")}
        rows.append({"field": path, "label": label,
                     "declared": bool(stated),
                     # Required means a detector is waiting on it. An undeclared
                     # optional field is a choice; an undeclared required one is a
                     # check that cannot run, and reading the same in a list of
                     # seventeen rows made the difference invisible.
                     "required": any(u == path or u.startswith(path + ".")
                                     or path.startswith(u + ".") for u in c.undeclared)
                                 or path in _REQUIRED,
                     "value": (list(stated.values())[0] if len(stated) == 1
                               else stated) if stated else None})
    sha = sha_of(data) if data is not None else None
    return {"exists": data is not None, "sha": sha,
            "archived": bool(sha and archived(sha)),
            "declared_count": len(c.declared), "undeclared": c.undeclared,
            "fields": rows,
            "departures": (data or {}).get("departures") or []}


def briefs() -> list:
    """PRODUCT.md and DESIGN.md: present, and how much of them is actually written.

    Reported by size because these two fail by being stubs rather than by being
    absent -- a heading with nothing under it passes an existence check and settles
    nothing, and `phase.yaml` already refuses to advance on one for that reason."""
    out = []
    for name, src, why in BRIEFS:
        if not src.exists():
            out.append({"name": name, "exists": False, "why": why, "chars": 0,
                        "sha": None, "headline": None})
            continue
        body = src.read_text(errors="replace")
        prose = re.sub(r"^\s*#.*$", "", body, flags=re.M).strip()
        head = next((ln.strip() for ln in prose.split("\n")
                     if ln.strip() and not ln.strip().startswith(("#", "-", "|", "*"))),
                    None)
        out.append({"name": name, "exists": True, "why": why, "chars": len(prose),
                    "sha": file_sha(src), "headline": head})
    return out


def approvals() -> dict:
    """What has actually been approved, by stage, and by whom.

    Latest per stage rather than a list, because an earlier approval of the same
    stage has been superseded by definition -- and a ledger that shows three
    wireframe approvals without saying which one is live is how a build ends up
    honouring the wrong one."""
    by_stage: dict = {}
    superseded = []
    for p, d in decisions():
        if not d.get("approves_a_build"):
            continue
        s = stage_of(d)
        prev = by_stage.get(s)
        if prev and str(prev[1].get("recorded_at") or "") > str(d.get("recorded_at") or ""):
            superseded.append((p, d))
            continue
        if prev:
            superseded.append(prev)
        by_stage[s] = (p, d)
    return {
        "live": {s: {"id": d.get("id") or p.stem, "who": d.get("who"),
                     "date": d.get("date"), "chosen": d.get("chosen"),
                     "contract_sha": d.get("contract_sha"),
                     "resolvable": bool(archived(d.get("contract_sha") or "")),
                     "file": str(p)}
                 for s, (p, d) in sorted(by_stage.items())},
        "superseded": [{"id": d.get("id") or p.stem, "stage": stage_of(d),
                        "date": d.get("date"), "file": str(p)}
                       for p, d in superseded],
    }


def open_work() -> list:
    """What is outstanding. Notes are work items until something closes them, and
    nothing here closes them automatically -- a note that vanished because a
    later decision was recorded would be a note quietly discarded."""
    out = []
    dec = decisions()
    cited = {n.get("id") for _p, d in dec for n in (d.get("notes") or []) if n.get("id")}
    for p, d in requests():
        rid = d.get("req") or p.stem
        out.append({"id": rid, "kind": "note",
                   "what": str(d.get("text") or "").strip()[:140],
                   "where": f"{d.get('variant') or '?'} {d.get('selector') or ''}".strip(),
                   "carried_by_a_decision": rid in cited, "file": str(p)})
    d = declaration()
    for u in d["undeclared"]:
        out.append({"id": u, "kind": "undeclared",
                    "what": f"`{u}` is not declared, so every check that would "
                            f"measure against it reports NOT_RUN",
                    "where": str(CONTRACT), "carried_by_a_decision": None,
                    "file": str(CONTRACT)})
    return out


def state() -> dict:
    st = load(PHASE) or {}
    d = declaration()
    a = approvals()
    gaps = []
    if not d["exists"]:
        gaps.append("no design.contract.yaml, so nothing about the visual system is "
                    "declared and every S-CONTRACT-* check is NOT_RUN")
    elif not d["archived"]:
        gaps.append(f"the current contract ({d['sha']}) has never been archived, so a "
                    f"decision recorded now could not be resolved back to it later -- "
                    f"run `ux_ledger.py snapshot`")
    for s, v in a["live"].items():
        if not v["contract_sha"]:
            gaps.append(f"{v['id']} ({s}) records no contract_sha, so what was "
                        f"declared when it was approved cannot be established")
        elif not v["resolvable"]:
            gaps.append(f"{v['id']} ({s}) was approved against contract "
                        f"{v['contract_sha']}, which is not in the archive")
    if not st:
        gaps.append("no phase.yaml, so the order the work happened in is NOT_RUN")
    br = briefs()
    for b in br:
        if not b["exists"]:
            gaps.append(f"no {b['name']}, so {b['why']} is nowhere on record and the "
                        f"phase gate will not advance past `declare`")
        elif b["chars"] < 200:
            gaps.append(f"{b['name']} is {b['chars']} characters of prose, which is a "
                        f"stub rather than a declaration of {b['why']}")
    return {"phase": st.get("phase"), "mode": st.get("mode"),
            "declaration": d, "briefs": br, "component_system": component_system(),
            "approvals": a, "open": open_work(),
            "contract_versions": len(lineage()),
            "events": len(events()), "gaps": gaps}


# ------------------------------------------------------------------ the process
def process_checks() -> dict:
    """One claim, for the report: does every approval resolve to archived bytes?

    Reported through the same `process` engine as the other A-* detectors because
    it is a claim about the record rather than about the artifact, and no scan of
    an interface can tell you whether the approval behind it is traceable."""
    dec = [(p, d) for p, d in decisions() if d.get("approves_a_build")]
    if not dec:
        return {"A-CONTRACT-ARCHIVED": ("NOT_RUN", "no approval on record, so there is "
                                        "nothing whose provenance could be traced")}
    bad = [d.get("id") or p.stem for p, d in dec
           if not d.get("contract_sha") or archived(d["contract_sha"]) is None]
    if bad:
        return {"A-CONTRACT-ARCHIVED": (
            "FAIL", f"{len(bad)} of {len(dec)} approval(s) cannot be resolved to the "
                    f"declaration they were made against ({', '.join(bad[:6])}). The "
                    f"approval exists; what it approved does not.")}
    return {"A-CONTRACT-ARCHIVED": (
        "PASS", f"all {len(dec)} approval(s) resolve to archived contract bytes")}


# ------------------------------------------------------------------- rendering
def w(s: str) -> None:
    sys.stderr.write(s)


def _short(v, n=64) -> str:
    if isinstance(v, dict):
        # A group of related values -- the three families, the nine roles -- reads
        # as `family.display` rather than as a Python dict repr.
        v = "  ".join(f"{k.rsplit('.', 1)[-1]} {x}" for k, x in v.items())
    s = "" if v is None else str(v)
    s = re.sub(r"\s+", " ", s)
    return s if len(s) <= n else s[:n - 1] + "…"


def cmd_state(a) -> int:
    s = state()
    if a.json:
        print(json.dumps(s, indent=1, default=str))
        return 0
    d, cs = s["declaration"], s["component_system"]
    w(f"\nphase {s['phase'] or '(none)'}"
      f"{'  mode ' + s['mode'] if s.get('mode') else ''}"
      f"   {s['contract_versions']} contract version(s)   "
      f"{s['events']} event(s) on record\n")

    got = [r for r in d["fields"] if r["declared"]]
    w(f"\nDECLARED  {len(got)} of {len(d['fields'])} field(s), contract "
      f"{d['sha'] or '(none)'}{'' if d['archived'] else '  NOT ARCHIVED'}\n")
    for r in d["fields"]:
        mark = "x" if r["declared"] else " "
        if r["declared"]:
            val = _short(r["value"])
        elif r["required"]:
            val = "NOT DECLARED -- a check is waiting on this, and reports NOT_RUN"
        else:
            # Not "nothing requires it" -- this file cannot establish that for every
            # field, and claiming it would be the same overreach as a PASS on an
            # unrun check. Blank is blank.
            val = "not declared"
        w(f"  [{mark}] {r['label']:<34} {val}\n")
    if d["departures"]:
        w(f"\n  {len(d['departures'])} declared departure(s) -- on purpose, with a reason\n")

    w("\nDECLARED IN PROSE\n")
    for b in s["briefs"]:
        if not b["exists"]:
            w(f"  [ ] {b['name']:<12} missing -- {b['why']} is nowhere on record\n")
        else:
            w(f"  [{'x' if b['chars'] >= 200 else ' '}] {b['name']:<12} "
              f"{b['chars']} chars  {_short(b['headline'] or '(no prose)', 58)}\n")

    w("\nBUILT WITH")
    if not cs.get("measured"):
        w(f"  not measured: {cs.get('why')}\n")
    else:
        w(f"  (measured from the tree, not declared)\n")
        w(f"  frameworks           {', '.join(cs['frameworks']) or 'none detected'}\n")
        libs = ", ".join(cs["primitive_libraries"]) or (
            "none -- every dialog, menu and combobox is hand-rolled")
        w(f"  primitive libraries  {libs}\n")
        w(f"  tailwind             {cs['tailwind_major'] or 'not installed'}\n")
        w(f"  tokens               {cs['css_variables']} CSS variable(s) in "
          f"{', '.join(cs['token_sources']) or 'no token source'}\n")
        w(f"  components           {cs['components']} in the inventory\n")
        if cs["platforms"]:
            w(f"  platforms            {', '.join(cs['platforms'])}\n")

    w("\nAPPROVED\n")
    if not s["approvals"]["live"]:
        w("  nothing. No stage has been accepted by a named person, so the "
          "build gate is closed.\n")
    for st_, v in s["approvals"]["live"].items():
        res = "" if v["resolvable"] else "   contract UNRESOLVABLE"
        w(f"  {st_:<10} {v['id']}  {v['chosen']}  by {v['who']} on {v['date']}{res}\n")
    for sp in s["approvals"]["superseded"]:
        w(f"  superseded  {sp['id']} ({sp['stage']}, {sp['date']})\n")

    op = s["open"]
    notes = [o for o in op if o["kind"] == "note"]
    nd = len([o for o in op if o["kind"] == "undeclared"])
    w(f"\nOPEN  {len(notes)} work item(s), "
      f"{nd} field(s) a check is waiting on\n")
    for o in notes[:12]:
        w(f"  {o['id']}  {o['where']:<24} {_short(o['what'], 72)}\n")
    if len(notes) > 12:
        w(f"  … {len(notes) - 12} more\n")

    if s["gaps"]:
        w(f"\nGAPS IN THE RECORD  {len(s['gaps'])}\n")
        for g in s["gaps"]:
            w(f"  - {g}\n")
    else:
        w("\nThe record resolves end to end: every approval names the declaration it "
          "was made against, and those bytes are on disk.\n")
    w("\n")
    return 0


KIND_MARK = {"phase": "->", "contract": "==", "decision": "**", "note": " ·",
             "override": "!!", "report": " ?"}


def cmd_log(a) -> int:
    ev = events()
    if a.kind:
        ev = [e for e in ev if e["kind"] in a.kind]
    if a.limit:
        ev = ev[-a.limit:]
    if a.json:
        print(json.dumps(ev, indent=1, default=str))
        return 0
    if not ev:
        w("\nNothing on record. Nothing has been declared, decided or gated in this "
          "project yet.\n\n")
        return 0
    w(f"\n{len(ev)} event(s), oldest first\n\n")
    for e in ev:
        at = str(e.get("at") or "undated")[:19]
        w(f"{at}  {KIND_MARK.get(e['kind'], '  ')} {e['kind']:<9} "
          f"{str(e.get('id') or ''):<12} {_short(e['what'], 90)}\n")
        if e.get("who"):
            w(f"{'':21}     by {e['who']}\n")
        if e["kind"] == "contract" and a.verbose:
            for ch in (e.get("detail") or [])[:12]:
                w(f"{'':21}     {ch['field']}: {_short(ch['from'], 28)} -> "
                  f"{_short(ch['to'], 28)}\n")
        if e.get("integrity"):
            w(f"{'':21}     GAP: {e['integrity']}\n")
    w("\n")
    return 0


def cmd_show(a) -> int:
    ident = a.id.strip()
    for p, d in decisions():
        if ident in (d.get("id"), p.stem):
            return _show_decision(p, d, a)
    for p, d in requests():
        if ident in (d.get("req"), p.stem):
            if a.json:
                print(json.dumps({"file": str(p), **d}, indent=1, default=str))
            else:
                w(f"\n{p.stem}  {d.get('variant') or ''} {d.get('selector') or ''}\n"
                  f"  “{d.get('text')}”\n  {p}\n\n")
            return 0
    for e in lineage():
        if e.get("sha", "").startswith(ident):
            if a.json:
                print(json.dumps({**e, "contract": archived(e["sha"])}, indent=1,
                                 default=str))
                return 0
            w(f"\ncontract {e['sha']}   {e.get('at')}   by {e.get('by')}\n")
            for ch in e.get("changed") or []:
                w(f"  {ch['field']}: {_short(ch['from'], 36)} -> {_short(ch['to'], 36)}\n")
            w(f"  {ARCHIVE / (e['sha'] + '.yaml')}\n\n")
            return 0
    w(f"\nNothing on record with id {ident!r}. `ux_ledger.py log` lists what is.\n\n")
    return 2


def _show_decision(p: Path, d: dict, a) -> int:
    csha = d.get("contract_sha")
    c = archived(csha) if csha else None
    if a.json:
        print(json.dumps({"file": str(p), "stage": stage_of(d),
                          "contract_resolvable": c is not None,
                          "contract": c, **d}, indent=1, default=str))
        return 0
    w(f"\n{d.get('id') or p.stem}   {stage_of(d)} stage   "
      f"{'approves a build' if d.get('approves_a_build') else 'does not approve a build'}\n")
    w(f"  question    {d.get('question') or '(none recorded)'}\n")
    w(f"  surface     {d.get('surface') or '(none)'}\n")
    w(f"  outcome     {d.get('outcome') or d.get('chosen')}\n")
    w(f"  decided by  {d.get('who')} on {d.get('date')}\n")
    w(f"  because     {d.get('rationale') or '(no reason recorded)'}\n")
    w(f"  record      {p}\n")
    w("\n  DECLARED AT THE TIME\n")
    if not csha:
        w("    No contract_sha on this record. What was declared when this was "
          "approved cannot be established, and the current contract is NOT evidence "
          "of it.\n")
    elif c is None:
        w(f"    contract {csha} is named here but is not in {ARCHIVE}/. The bytes were "
          f"never archived, so this approval cannot be resolved. Showing today's "
          f"contract instead would misrepresent what was approved.\n")
    else:
        cc = ux_image.Contract(c)
        w(f"    contract {csha}\n")
        w(f"    world       {_short(cc.world or 'UNKNOWN', 76)}\n")
        w(f"    families    {', '.join(f'{k}: {v}' for k, v in cc.families.items())}\n")
        w(f"    ladder      {', '.join(str(int(x)) for x in cc.scale)}\n")
        w(f"    roles       {', '.join(f'{k} {v}' for k, v in list(cc.roles.items())[:5])}\n")
        w(f"    depth       {cc.depth}\n")
        cur = sha_of(load(CONTRACT) or {})
        if cur != csha:
            n = len(changed_fields(c, load(CONTRACT)))
            w(f"    Since then the declaration has changed in {n} field(s): "
              f"`ux_ledger.py diff {csha} {cur}`\n")
        for name, _src, why in BRIEFS:
            at_time = ARCHIVE / f"{csha}.{name}"
            if at_time.exists():
                n = len(re.sub(r"^\s*#.*$", "", at_time.read_text(errors="replace"),
                               flags=re.M).strip())
                w(f"    {name:<11} {n} chars, archived: {at_time}\n")
            else:
                w(f"    {name:<11} not archived with this version, so {why} as it "
                  f"stood then cannot be produced\n")
    notes = d.get("notes") or []
    w(f"\n  CARRIED {len(notes)} WORK ITEM(S)\n")
    for n in notes:
        live = REQUESTS / f"{n.get('id')}.yaml"
        gone = "" if live.exists() else "   (the note file is gone)"
        w(f"    {n.get('id')}  {n.get('variant') or ''} {n.get('selector') or ''}"
          f"{gone}\n      “{_short(n.get('text'), 96)}”\n")
    w("\n")
    return 0


def cmd_diff(a) -> int:
    lin = lineage()
    if len(lin) < 2 and not (a.a and a.b):
        w(f"\n{len(lin)} contract version(s) archived. A diff needs two.\n\n")
        return 2

    def resolve(x):
        if x in (None, "current"):
            return "current", load(CONTRACT)
        for e in lin:
            if e["sha"].startswith(x):
                return e["sha"], archived(e["sha"])
        return x, None

    sa, da = resolve(a.a or (lin[-2]["sha"] if len(lin) >= 2 else None))
    sb, db = resolve(a.b or "current")
    for s_, d_ in ((sa, da), (sb, db)):
        if d_ is None:
            w(f"\ncontract {s_} is not in the archive. `ux_ledger.py log --kind contract` "
              f"lists what is.\n\n")
            return 2
    ch = changed_fields(da, db)
    if a.json:
        print(json.dumps({"from": sa, "to": sb, "changed": ch}, indent=1, default=str))
        return 0
    w(f"\n{sa} -> {sb}\n")
    if not ch:
        w("  identical\n\n")
        return 0
    for c in ch:
        w(f"  {c['field']:<28} {_short(c['from'], 30)} -> {_short(c['to'], 30)}\n")
    w(f"\n  {len(ch)} field(s) changed\n\n")
    return 0


def cmd_snapshot(a) -> int:
    r = archive(by=a.by, note=a.note)
    if a.json:
        print(json.dumps(r, indent=1, default=str))
        return 0 if r.get("ok") else 2
    if not r.get("ok"):
        w(f"\n{r.get('why')}\n\n")
        return 2
    if not r.get("new"):
        w(f"\ncontract {r['sha']} is already the head of the archive "
          f"({r.get('why')}).\n\n")
        return 0
    w(f"\narchived contract {r['sha']}"
      f"{'  (a revert to an earlier declaration)' if r.get('reverted') else ''}\n"
      f"  {ARCHIVE / (r['sha'] + '.yaml')}\n")
    if r.get("first"):
        w(f"  the first declaration on record, {r.get('declared', 0)} field(s) "
          f"declared. There is no previous version to compare it against.\n\n")
    else:
        w(f"  {r.get('changed', 0)} field(s) changed against the previous version\n\n")
    return 0


def cmd_check(a) -> int:
    res = process_checks()
    if a.json:
        print(json.dumps({k: {"status": v[0], "note": v[1]} for k, v in res.items()},
                         indent=1))
        return 0
    for k, (s_, note) in res.items():
        w(f"\n{k}: {s_}\n  {note}\n")
    w("\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("state", help="what the design is right now")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_state)

    s = sub.add_parser("log", help="every design event in order")
    s.add_argument("--kind", action="append",
                   choices=["phase", "contract", "decision", "note", "override", "report"])
    s.add_argument("--limit", type=int)
    s.add_argument("-v", "--verbose", action="store_true",
                   help="show the changed fields under each contract version")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_log)

    s = sub.add_parser("show", help="one entry, with the contract it was decided against")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("diff", help="what changed in the declaration")
    s.add_argument("a", nargs="?")
    s.add_argument("b", nargs="?")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_diff)

    s = sub.add_parser("snapshot", help="archive the current contract by its sha")
    s.add_argument("--by", default="ux_ledger.py snapshot")
    s.add_argument("--note")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_snapshot)

    s = sub.add_parser("check", help="the ledger's own process detector, for ux_report")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_check)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
