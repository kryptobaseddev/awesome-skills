#!/usr/bin/env python3
"""The order the work happens in, made into a gate rather than an intention.

deuxui's claim has always been that the contract is declared BEFORE the code it
governs, because a contract written afterwards is a description of whatever got
emitted -- it will always show conformance and it is worth nothing. That was
stated in a comment and enforced by nobody, which is the same shape as a PASS on
a check that never ran.

This is the enforcement. Seven phases, each with entry requirements that are
machine-checked, and evidence recorded at every transition:

    discover -> declare -> comp -> approve -> build -> verify -> release

Two things make it more than bookkeeping:

  * Entering `comp` takes a snapshot -- the contract's hash, the git head, and the
    hash of every UI file. Entering `verify` compares against it, so "the
    declaration came first" becomes something measured from the tree rather than
    asserted in a report. In a brownfield project the same snapshot answers the
    honest version of the question: the contract was derived from what was there,
    and conformance is about what changed after.
  * `gate write` refuses UI edits before `build`, and it is wired into the plugin's
    PostToolUse hook, so the refusal happens while the file is open.

The override is deliberate and audited. A gate with no way past it gets bypassed
by deleting the state file, and then there is no record at all; `override` leaves
one, with a reason and a name attached.

    ux_phase.py status [--json]
    ux_phase.py advance [PHASE] [--json]
    ux_phase.py gate write <file>|--stdin
    ux_phase.py gate release
    ux_phase.py check [--json]          the process detectors, for ux_report
    ux_phase.py override <PHASE> --reason "..." --who "..."
    ux_phase.py init [--brownfield|--greenfield]

Exit: 0 permitted, 1 refused by the gate, 2 requirements not met.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import yaml                                                        # noqa: E402
import ux_image                                                    # noqa: E402

STATE = Path(".deuxui/phase.yaml")
DECISIONS = Path(".deuxui/decisions")
COMPS = Path(".deuxui/comps")
REPORT = Path(".deuxui/reports/agent_report.yaml")

# Two review stages, because they answer different questions and a person can
# only answer one of them at a time. A wireframe settles structure -- what is on
# the screen, in what order, at what proportion -- and cannot settle whether the
# thing is usable, because a drawing cannot be used. A prototype settles that, and
# it is the last point before the answer costs a sprint.
PHASES = ["discover", "declare", "wireframe", "prototype", "build", "verify",
          "release"]
UI_EXT = {".tsx", ".jsx", ".ts", ".js", ".svelte", ".vue", ".astro", ".html", ".htm",
          ".css", ".scss", ".sass", ".less", ".swift", ".kt", ".kts", ".dart"}
SKIP = {"node_modules", ".git", "dist", "build", ".next", ".svelte-kit", "out",
        "coverage", ".venv", "venv", "__pycache__", ".turbo", ".cache", ".deuxui",
        "target", "Pods", ".gradle"}
MIN_REASON = 40
SELF = re.compile(r"\b(?:claude|chatgpt|gpt|copilot|cursor|codex|gemini|llm|ai|"
                  r"agent|assistant|model|bot|automated|self|me|myself|"
                  r"this session|the tool)\b", re.I)

WHAT_IT_PERMITS = {
    "discover": "Reading. Nothing about the design is decided, so nothing about it "
                "can be built.",
    "declare": "Writing PRODUCT.md and DESIGN.md. Still no UI code: what the product "
               "is for is not yet written down.",
    "wireframe": "Writing the visual contract, rendering wireframes from it, and "
                 "serving that choice. Still no UI code -- this is the stage whose "
                 "whole purpose is that it comes first. A wireframe settles "
                 "structure: what is on the screen, in what order, at what "
                 "proportion.",
    "prototype": "Building a working prototype and putting it in front of somebody. "
                 "Still not production code. A drawing cannot be used, so a drawing "
                 "cannot tell you whether the thing works; this is the stage where "
                 "someone finds out by using it.",
    "build": "Writing production UI code. The first phase where that is permitted, "
             "and it is permitted because a named person used a working prototype "
             "and accepted it.",
    "verify": "Running the tiers and fixing what they find.",
    "release": "Shipping. The gate said READY.",
}

# Where the prototype lives by default. A directory rather than a file, because a
# prototype that grows past one page is the normal case.
PROTO = Path(".deuxui/proto")


# ------------------------------------------------------------------ the tree
def ui_files(root: Path, limit=6000) -> dict:
    out = {}
    for p in root.rglob("*"):
        if len(out) >= limit:
            break
        if not p.is_file() or p.suffix.lower() not in UI_EXT:
            continue
        if any(part in SKIP for part in p.relative_to(root).parts):
            continue
        try:
            out[str(p.relative_to(root))] = hashlib.sha256(
                p.read_bytes()).hexdigest()[:16]
        except OSError:
            continue
    return out


def git(*args) -> str | None:
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ the state
def load() -> dict:
    if STATE.exists():
        return yaml.safe_load(STATE.read_text()) or {}
    return {}


def save(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(yaml.safe_dump(st, sort_keys=False, allow_unicode=True, width=92))


def init_state(mode: str | None) -> dict:
    root = Path.cwd()
    files = ui_files(root)
    detected = "brownfield" if len(files) >= 5 else "greenfield"
    st = {"phase": "discover", "mode": mode or detected,
          "mode_detected": detected, "ui_files_at_init": len(files),
          "started_at": now(), "git_head_at_init": git("rev-parse", "HEAD"),
          "history": [], "overrides": []}
    save(st)
    return st


# ------------------------------------------------------- entry requirements
def _text_ok(p: Path, min_chars=200) -> tuple[bool, str]:
    if not p.exists():
        return False, f"{p} does not exist"
    t = p.read_text(errors="replace")
    body = re.sub(r"^\s*#.*$", "", t, flags=re.M)
    blanks = len(re.findall(r"\bUNKNOWN\b|\bTODO\b|<[a-z ]+>", t))
    if len(body.strip()) < min_chars:
        return False, (f"{p} is {len(body.strip())} characters of content; it has not "
                       f"been filled in")
    if blanks > 2:
        return False, (f"{p} still has {blanks} placeholders (UNKNOWN / TODO / "
                       f"angle-bracket blanks). A template is not a declaration")
    return True, f"{p} is written ({len(body.strip())} chars)"


def comps_on_disk() -> list:
    return sorted(COMPS.glob("*.comps.yaml"))


def stage_of(d: dict) -> str:
    """Which stage a decision record belongs to.

    A review of a working prototype and a choice between drawings are different
    approvals, and only the first one can authorise production code. The record
    says which it is: `ux_review.py` writes `approves_a_build`, `ux_question.py`
    does not."""
    if "approves_a_build" in d or "ux_review" in str(d.get("source") or ""):
        return "prototype"
    return "wireframe"


def vetted_decisions() -> tuple[list, list, list]:
    """(admissible, inadmissible, superseded). The same bar the report applies.

    Superseded is its own outcome and not a failure. A later decision about the
    same comp set replaces the earlier one, and treating the earlier as a standing
    defect meant one re-render blocked the build permanently -- which teaches the
    obvious lesson of deleting the record, and then there is no history at all."""
    live, older = {}, []
    rows = []
    for f in sorted(DECISIONS.glob("DEC-*.yaml")):
        d = yaml.safe_load(f.read_text()) or {}
        rows.append((f, d))
    for f, d in rows:
        key = str(d.get("source") or f.stem)
        prev = live.get(key)
        if prev is None or str(d.get("recorded_at") or "") >= str(
                prev[1].get("recorded_at") or ""):
            if prev is not None:
                older.append(prev)
            live[key] = (f, d)
        else:
            older.append((f, d))

    ok, bad = [], []
    for f, d in live.values():
        why = []
        who = str(d.get("who") or "").strip()
        if not who:
            why.append("no `who`")
        elif SELF.search(who):
            why.append(f"`who: {who}` names the party that produced the comps")
        if not str(d.get("date") or "").strip():
            why.append("no `date`")
        # A record that is not an approval does not also need a long reason: the
        # outcome already disqualifies it, and listing both makes the decisive
        # fact harder to find.
        approving = (d.get("approves_a_build", True)
                     and str(d.get("chosen") or "").strip()
                     not in ("", "reject", "changes"))
        if approving and len(str(d.get("rationale") or "").strip()) < MIN_REASON:
            why.append("the reason is too thin to weigh")
        chosen = str(d.get("chosen") or "").strip()
        if "approves_a_build" in d:
            # A live review states its own outcome. "Request changes" is a real,
            # useful answer and it is not an approval; reading it as one would let
            # a work list authorise the build it is a list of complaints about.
            if not d.get("approves_a_build"):
                why.append(f"the outcome was {d.get('outcome', chosen)!r}, which is "
                           f"not an approval")
        elif chosen in ("", "reject", "changes"):
            why.append(f"chosen is {chosen!r}, which is not an approval")
        for s in d.get("shown") or []:
            if not s.get("image"):
                continue
            q = Path(s["image"])
            cur = hashlib.sha256(q.read_bytes()).hexdigest()[:16] if q.exists() else None
            if cur is None:
                why.append(f"{s['image']} no longer exists")
            elif s.get("image_sha") and cur != s["image_sha"]:
                why.append(f"{s['image']} changed after it was approved")
        (bad if why else ok).append((f, d, "; ".join(why)))
    return ok, bad, [(f, d, "superseded by a later decision about the same comps")
                     for f, d in older]


def changed_since_snapshot(st: dict) -> tuple[list, list]:
    """(written after the declaration, unchanged since it)."""
    snap = (st.get("snapshot") or {}).get("ui_files") or {}
    cur = ui_files(Path.cwd())
    after = [f for f, h in cur.items() if snap.get(f) != h]
    same = [f for f in cur if f in snap and snap[f] == cur[f]]
    return sorted(after), sorted(same)


def requirements(target: str, st: dict) -> list:
    """[(met, statement)] -- everything the phase needs, each independently true
    or false so a refusal names the missing thing instead of the phase."""
    out = []
    if target == "declare":
        for p in (Path(".deuxui/PRODUCT.md"), Path(".deuxui/DESIGN.md")):
            out.append(_text_ok(p))
    elif target == "wireframe":
        c = ux_image.load_contract(None)
        if not c.raw:
            out.append((False, "no .deuxui/design.contract.yaml -- there is nothing "
                               "to build against"))
        else:
            und = c.undeclared
            out.append((not und,
                        "every required contract field is declared" if not und else
                        f"{len(und)} contract fields are still UNKNOWN: "
                        f"{', '.join(und)}. Each one is a decision nobody has made, "
                        f"and a comp cannot settle a field it was drawn with a "
                        f"placeholder for"))
    elif target == "prototype":
        sets = comps_on_disk()
        n = sum(len((yaml.safe_load(s.read_text()) or {}).get("rendered") or [])
                for s in sets)
        out.append((bool(sets), f"{len(sets)} wireframe set(s) rendered"
                    if sets else "no wireframes rendered -- run "
                    "`ux_image.py render <brief.yaml>`"))
        out.append((n >= 2, f"{n} wireframes to choose between"
                    if n >= 2 else f"{n} wireframe(s). One invites a rubber stamp; "
                                   "two is the minimum that makes a decision possible"))
        ok, bad, _sup = vetted_decisions()
        wf = [(f, d, w) for f, d, w in ok if stage_of(d) == "wireframe"]
        out.append((bool(wf), (f"a structure was chosen: "
                               + ", ".join(f.stem for f, _d, _w in wf)) if wf else
                    "nobody has chosen a structure. Serve the wireframes: "
                    "`ux_question.py ask .deuxui/comps/<set>.comps.yaml`"))
        for f, _d, why in bad:
            if stage_of(_d) == "wireframe":
                out.append((False, f"{f.stem} is on record but not admissible ({why})"))
    elif target == "build":
        proto = sorted(PROTO.rglob("*.html")) if PROTO.exists() else []
        out.append((bool(proto), f"{len(proto)} prototype page(s) in {PROTO}"
                    if proto else
                    f"no prototype in {PROTO}. A drawing cannot be used, so it "
                    f"cannot tell you whether the thing works: "
                    f"`ux_proto.py --write {PROTO}/index.html`"))
        ok, bad, sup = vetted_decisions()
        pr = [(f, d, w) for f, d, w in ok if stage_of(d) == "prototype"]
        out.append((bool(pr), (f"somebody used it and accepted it: "
                               + ", ".join(f.stem for f, _d, _w in pr)) if pr else
                    "no accepted prototype review. Put it in front of a person: "
                    "`ux_review.py serve --variant \"proposed=" + str(PROTO)
                    + "/index.html\"`"))
        for f, d, why in bad:
            if stage_of(d) == "prototype":
                out.append((False, f"{f.stem} is on record but not admissible ({why})"))
        if sup:
            out.append((True, f"{len(sup)} superseded record(s) ignored: "
                              + ", ".join(f.stem for f, _d, _w in sup)))
    elif target == "verify":
        after, same = changed_since_snapshot(st)
        snap = st.get("snapshot") or {}
        if not snap:
            out.append((False, "no snapshot was taken, so the order the work happened "
                               "in cannot be established. Re-enter `wireframe`"))
        elif st.get("mode") == "brownfield":
            out.append((bool(after),
                        f"{len(after)} file(s) changed since the contract was derived; "
                        f"conformance is about those" if after else
                        "nothing has changed since the contract was derived, so there "
                        "is no new work to verify"))
        else:
            out.append((bool(after),
                        f"{len(after)} UI file(s) were written after the contract was "
                        f"declared" if after else
                        "no UI file has changed since the contract was declared. "
                        "Either nothing was built, or the code predates the "
                        "declaration -- and a contract written after the code always "
                        "shows conformance"))
    elif target == "release":
        if not REPORT.exists():
            out.append((False, f"no {REPORT}. Run `ux_report.py --merge --release`"))
        else:
            r = yaml.safe_load(REPORT.read_text()) or {}
            d = r.get("release_decision")
            out.append((d == "READY", f"the gate says {d}: {r.get('decision_reason')}"))
    return out


# --------------------------------------------------------------- transitions
def advance(target: str | None, st: dict) -> tuple[int, dict]:
    cur = st.get("phase", "discover")
    i = PHASES.index(cur)
    target = target or (PHASES[i + 1] if i + 1 < len(PHASES) else cur)
    if target not in PHASES:
        return 2, {"error": f"{target} is not a phase"}
    j = PHASES.index(target)
    if j <= i:
        return 2, {"error": f"already at {cur}; phases do not go backwards. Use "
                            f"`override` with a reason, or `init` to start again"}
    if j > i + 1:
        return 2, {"error": f"cannot jump {cur} -> {target}. The next phase is "
                            f"{PHASES[i + 1]}, and each one exists because skipping "
                            f"it is how a specific thing ships unexamined"}
    reqs = requirements(target, st)
    unmet = [why for met, why in reqs if not met]
    if unmet:
        return 2, {"phase": cur, "target": target, "unmet": unmet,
                   "met": [w for m, w in reqs if m]}
    ev = {"to": target, "at": now(), "git_head": git("rev-parse", "HEAD"),
          "evidence": [w for _m, w in reqs]}
    if target == "wireframe":
        c = ux_image.load_contract(None)
        # Archive the bytes, not just the hash. `snapshot` recorded a sha that
        # nothing could resolve, which is a fingerprint of a document nobody kept.
        try:
            import ux_ledger
            ux_ledger.archive(by="ux_phase.py advance (entering wireframe)")
        except Exception:
            pass
        st["snapshot"] = {"taken_at": now(), "contract_sha": c.sha(),
                          "git_head": git("rev-parse", "HEAD"),
                          "ui_files": ui_files(Path.cwd())}
        ev["snapshot_files"] = len(st["snapshot"]["ui_files"])
    if target == "build":
        ok, _bad, _sup = vetted_decisions()
        ev["approved_by"] = [{"decision": f.stem, "stage": stage_of(d),
                              "who": d.get("who"), "chosen": d.get("chosen"),
                              "date": d.get("date"),
                              "options_sha": d.get("options_sha")}
                             for f, d, _w in ok]
    st["phase"] = target
    st.setdefault("history", []).append(ev)
    save(st)
    return 0, {"phase": target, "evidence": ev}


# --------------------------------------------------------------- the process
def process_checks(st: dict) -> dict:
    """{detector: (status, note)} for the process tier.

    Reported as its own family because it is a claim about how the work happened,
    which no scan of the artifact can establish -- exactly the same reason the
    report has a self-audit tier."""
    out = {}
    if not st:
        why = ("No .deuxui/phase.yaml. The order the work happened in was never "
               "recorded, so nothing here can be established either way. Start it "
               "with `ux_phase.py init` -- this is NOT_RUN and not a pass.")
        return {k: ("NOT_RUN", why) for k in
                ("A-PHASE-ORDER", "A-COMP-APPROVED", "A-DECISION-VETTED",
                 "A-PROTO-ACCEPTED")}

    # --- declaration before code
    snap = st.get("snapshot") or {}
    if not snap:
        out["A-PHASE-ORDER"] = ("NOT_RUN",
            "No snapshot: the project has not reached the `wireframe` phase, so "
            "there is no recorded moment at which the contract existed and the code "
            "did not.")
    else:
        after, same = changed_since_snapshot(st)
        mode = st.get("mode", "greenfield")
        if mode == "brownfield" and not after:
            out["A-PHASE-ORDER"] = ("NOT_RUN",
                f"Brownfield: the contract was derived from "
                f"{len(snap.get('ui_files') or {})} existing files on "
                f"{snap.get('taken_at')} and nothing has changed since. There is no "
                f"new work whose order could be wrong, so this establishes nothing "
                f"either way -- which is not the same as the order being right.")
        elif mode == "brownfield":
            out["A-PHASE-ORDER"] = ("PASS",
                f"Brownfield: the contract was derived from {len(snap.get('ui_files') or {})} "
                f"existing files on {snap.get('taken_at')}, and {len(after)} have "
                f"changed since. Conformance is a claim about those, not about the "
                f"code the contract was read out of.")
        elif after:
            out["A-PHASE-ORDER"] = ("PASS",
                f"The contract was declared at {snap.get('taken_at')} (hash "
                f"{snap.get('contract_sha')}, git {str(snap.get('git_head'))[:8]}), and "
                f"{len(after)} UI file(s) were written after it. The declaration "
                f"preceded the code, and that is measured from the tree rather than "
                f"asserted.")
        else:
            out["A-PHASE-ORDER"] = ("FAIL",
                f"The contract was declared at {snap.get('taken_at')} and not one UI "
                f"file has changed since. Either nothing was built against it, or it "
                f"was written to describe code that already existed -- and a contract "
                f"written afterwards always shows conformance, so every S-CONTRACT-* "
                f"PASS in this report would be circular.")

    # --- an approval exists, by somebody, against what was shown
    ok, bad, sup = vetted_decisions()
    if not ok and not bad:
        out["A-COMP-APPROVED"] = ("NOT_RUN",
            "No decision records at all. Nobody has been asked to approve a "
            "structure or to use a prototype, so there is no approval to check. "
            "Serve the choice with `ux_question.py ask`, and the working thing "
            "with `ux_review.py serve`.")
        out["A-DECISION-VETTED"] = ("NOT_RUN", "No decision records to vet.")
        out["A-PROTO-ACCEPTED"] = ("NOT_RUN",
            "No live review has been recorded. Nobody has used a working version of "
            "this and said so, which is a different fact from nobody having liked a "
            "drawing of it.")
        return out
    if ok:
        f, d, _ = ok[-1]
        stages = sorted({stage_of(x[1]) for x in ok})
        note = (f"{f.stem}: {d.get('who')} chose {d.get('chosen')} on {d.get('date')} "
                f"against shown-hash {d.get('options_sha')}. Stages approved: "
                f"{', '.join(stages)}.")
        if "prototype" not in stages:
            note += (" No prototype has been used and accepted, so the structure is "
                     "agreed and the thing itself is not.")
        out["A-COMP-APPROVED"] = ("PASS", note)
    else:
        out["A-COMP-APPROVED"] = ("FAIL",
            f"{len(bad)} decision record(s) exist and none is admissible: "
            + "; ".join(f"{f.stem} ({why})" for f, _d, why in bad)[:400])
    # --- did anybody USE it, or only look at a picture of it
    used = [(f, d) for f, d, _w in ok if stage_of(d) == "prototype"]
    refused = [(f, d) for f, d, _w in bad if stage_of(d) == "prototype"]
    if used:
        f, d = used[-1]
        out["A-PROTO-ACCEPTED"] = ("PASS",
            f"{f.stem}: {d.get('who')} reviewed a running prototype on "
            f"{d.get('date')} and accepted it ({d.get('outcome')}). "
            f"{len(d.get('notes') or [])} element note(s) came out of that session.")
    elif refused:
        f, d = refused[-1]
        out["A-PROTO-ACCEPTED"] = ("FAIL",
            f"{f.stem}: a live review happened and the outcome was "
            f"{d.get('outcome')!r}, which is not an acceptance. "
            f"{len(d.get('notes') or [])} element note(s) are the work list.")
    else:
        out["A-PROTO-ACCEPTED"] = ("NOT_RUN",
            "Decisions exist, but all of them are about drawings. Nobody has used a "
            "working version of this -- and a wireframe cannot be used, so it cannot "
            "establish that the thing works.")

    if bad:
        out["A-DECISION-VETTED"] = ("FAIL",
            f"{len(bad)} of {len(ok) + len(bad)} standing decision records do not "
            f"carry what a decision needs: "
            + "; ".join(f"{f.stem}: {why}" for f, _d, why in bad)[:400])
    else:
        out["A-DECISION-VETTED"] = ("PASS",
            f"All {len(ok)} standing decision record(s) name a person who is not the "
            f"agent, a date, a reason long enough to weigh, and the hash of exactly "
            f"what they were shown."
            + (f" {len(sup)} earlier record(s) are superseded and authorise nothing."
               if sup else ""))
    return out


# ------------------------------------------------------------------ the gate
def gate_write(path: str, st: dict) -> tuple[int, str]:
    p = Path(path)
    if p.suffix.lower() not in UI_EXT:
        return 0, f"{path} is not UI source; this gate has nothing to say about it."
    if any(part in SKIP for part in p.parts):
        return 0, f"{path} is outside the source tree this gate covers."
    if not st:
        return 0, ("No phase state, so nothing is being gated. `ux_phase.py init` "
                   "turns this on; until then deuxui reports the order of work as "
                   "NOT_RUN rather than enforcing it.")
    cur = st.get("phase", "discover")
    if PHASES.index(cur) >= PHASES.index("build"):
        return 0, f"phase {cur}: writing UI is permitted."
    reqs = requirements(PHASES[PHASES.index(cur) + 1], st)
    unmet = [w for m, w in reqs if not m]
    return 1, (
        f"REFUSED: the project is at phase `{cur}` and {path} is UI source.\n"
        f"  {WHAT_IT_PERMITS.get(cur, '')}\n"
        f"  Writing the screen before the direction is approved is the failure this "
        f"gate exists for: the code becomes the decision, and the approval that "
        f"follows is a formality about something already built.\n"
        f"  To reach `build`, the next phase is `{PHASES[PHASES.index(cur) + 1]}` and "
        f"it needs:\n" + "".join(f"    - {w}\n" for w in unmet or ["(nothing -- run "
                                                                   "`ux_phase.py advance`)"])
        + f"  If this is deliberate: ux_phase.py override build --who NAME --reason "
          f"\"...\"  (recorded, not silent)")


# ------------------------------------------------------------------------ CLI
def cmd_init(a) -> int:
    mode = "brownfield" if a.brownfield else ("greenfield" if a.greenfield else None)
    st = init_state(mode)
    sys.stderr.write(
        f"\nphase state started at {STATE}\n"
        f"  mode:  {st['mode']}  (detected {st['mode_detected']} from "
        f"{st['ui_files_at_init']} UI files)\n"
        f"  phase: discover\n\n"
        f"{'Brownfield: derive the contract from what is there (derive_contract.py), then advance.' if st['mode'] == 'brownfield' else 'Greenfield: nothing exists yet, so the declaration genuinely comes first.'}\n")
    return 0


def cmd_status(a) -> int:
    st = load()
    if not st:
        if a.json:
            print(json.dumps({"phase": None}))
        sys.stderr.write("No .deuxui/phase.yaml. Nothing is gated and the order of "
                         "work is NOT_RUN. Start it: ux_phase.py init\n")
        return 0
    cur = st.get("phase", "discover")
    i = PHASES.index(cur)
    nxt = PHASES[i + 1] if i + 1 < len(PHASES) else None
    reqs = requirements(nxt, st) if nxt else []
    if a.json:
        print(json.dumps({"phase": cur, "mode": st.get("mode"), "next": nxt,
                          "requirements": [{"met": m, "statement": w} for m, w in reqs],
                          "process": {k: {"status": v[0], "note": v[1]}
                                      for k, v in process_checks(st).items()},
                          "overrides": st.get("overrides") or []}, indent=1))
        return 0
    w = sys.stderr.write
    w(f"\n{'  '.join((x.upper() if x == cur else x) for x in PHASES)}\n\n")
    w(f"phase {cur} ({st.get('mode')})\n  {WHAT_IT_PERMITS.get(cur, '')}\n")
    if nxt:
        w(f"\nto reach `{nxt}`:\n")
        for met, why in reqs:
            w(f"  [{'x' if met else ' '}] {why}\n")
        if reqs and all(m for m, _ in reqs):
            w(f"\n  ready:  python3 scripts/ux_phase.py advance\n")
    for k, (stt, note) in process_checks(st).items():
        w(f"\n{k}: {stt}\n  {note}\n")
    if st.get("overrides"):
        w(f"\n{len(st['overrides'])} override(s) on record:\n")
        for o in st["overrides"]:
            w(f"  {o['at']}  -> {o['phase']}  {o['who']}: {o['reason'][:90]}\n")
    return 0


def cmd_advance(a) -> int:
    st = load() or init_state(None)
    code, res = advance(a.phase, st)
    if a.json:
        print(json.dumps(res, indent=1))
    elif code == 0:
        sys.stderr.write(f"\n-> {res['phase']}\n" + "".join(
            f"  {e}\n" for e in res["evidence"]["evidence"]) +
            f"  {WHAT_IT_PERMITS.get(res['phase'], '')}\n")
    else:
        sys.stderr.write(f"\nstill at {res.get('phase', st.get('phase'))}. "
                         f"{res.get('error', '')}\n")
        for w in res.get("unmet", []):
            sys.stderr.write(f"  [ ] {w}\n")
        for w in res.get("met", []):
            sys.stderr.write(f"  [x] {w}\n")
    return code


def cmd_gate(a) -> int:
    st = load()
    if a.what == "release":
        cur = st.get("phase") if st else None
        if cur == "release":
            sys.stderr.write("phase release: shipping is permitted.\n")
            return 0
        sys.stderr.write(f"REFUSED: phase is {cur or 'unset'}, not release.\n")
        return 1
    target = a.file
    if a.stdin:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            return 0
        target = ((payload.get("tool_input") or {}).get("file_path")
                  or payload.get("file_path") or "")
        if not target:
            return 0
    if not target:
        sys.stderr.write("give a file, or --stdin\n")
        return 2
    code, msg = gate_write(target, st)
    if a.stdin:
        # PreToolUse speaks JSON. Emitting a decision object is the documented way
        # to refuse a tool call; the exit code is kept as well because some hosts
        # read that instead, and a gate that is ignored by the host is not a gate.
        if code:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": msg}}))
            return 2
        return 0
    sys.stderr.write(msg + "\n")
    return code


def cmd_check(a) -> int:
    res = process_checks(load())
    if a.json:
        print(json.dumps({k: {"status": v[0], "note": v[1]}
                          for k, v in res.items()}, indent=1))
    else:
        for k, (s, n) in res.items():
            sys.stderr.write(f"{k}: {s}\n  {n}\n\n")
    return 2 if any(v[0] == "FAIL" for v in res.values()) else 0


def cmd_override(a) -> int:
    st = load() or init_state(None)
    if a.phase not in PHASES:
        sys.stderr.write(f"{a.phase} is not a phase\n")
        return 2
    if len(a.reason.strip()) < MIN_REASON:
        sys.stderr.write(f"the reason is {len(a.reason.strip())} characters; "
                         f"{MIN_REASON} is the minimum. An override with no account "
                         f"of itself is indistinguishable from deleting the file.\n")
        return 2
    if SELF.search(a.who):
        sys.stderr.write(f"`{a.who}` names the agent. An override is a person "
                         f"deciding to proceed without the evidence; the agent "
                         f"cannot grant itself that.\n")
        return 2
    st["phase"] = a.phase
    st.setdefault("overrides", []).append(
        {"phase": a.phase, "who": a.who.strip(), "reason": a.reason.strip(),
         "at": now(), "git_head": git("rev-parse", "HEAD"),
         "unmet_at_override": [w for m, w in requirements(a.phase, st) if not m]})
    save(st)
    sys.stderr.write(f"\nphase forced to {a.phase} by {a.who}. Recorded in {STATE} and "
                     f"reported by A-PHASE-ORDER.\n")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init")
    i.add_argument("--brownfield", action="store_true")
    i.add_argument("--greenfield", action="store_true")
    i.set_defaults(fn=cmd_init)
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)
    ad = sub.add_parser("advance")
    ad.add_argument("phase", nargs="?")
    ad.add_argument("--json", action="store_true")
    ad.set_defaults(fn=cmd_advance)
    g = sub.add_parser("gate")
    g.add_argument("what", choices=["write", "release"])
    g.add_argument("file", nargs="?")
    g.add_argument("--stdin", action="store_true")
    g.set_defaults(fn=cmd_gate)
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)
    o = sub.add_parser("override")
    o.add_argument("phase")
    o.add_argument("--reason", required=True)
    o.add_argument("--who", required=True)
    o.set_defaults(fn=cmd_override)
    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 1
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
