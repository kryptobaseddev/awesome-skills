#!/usr/bin/env python3
"""Generate the readable rule packs from references/rules/registry.yaml.

The packs are projections, not a second source of truth. Regenerate them after
editing the registry; scripts/lint_rules.py will catch any prose that drifts
into citing a rule that no longer exists.
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

# Do not leave .pyc files beside the checks. A directory-source plugin install
# copies the working tree verbatim, so stray bytecode ships to the consumer
# despite being gitignored. Costs ~15ms per run, which nothing here notices.
sys.dont_write_bytecode = True

RULES = Path(__file__).resolve().parent.parent / "references" / "rules"

# prefix -> (filename, title, why this domain is its own pack)
PACKS = {
 ("GOV", "CTX"): ("00-governance.md", "Governance, context and exceptions",
  "These rules are about how you work, not how the interface looks. They are "
  "first because every other rule depends on them being followed: if you may "
  "invent a test result, no other rule in this document means anything.\n\n"
  "**Priority order when rules conflict.** Higher instructions and authorised "
  "task boundaries; then safety, privacy, security and accessibility; then "
  "correct outcomes and data integrity; then validated user needs and explicit "
  "requirements; then platform conventions and the existing design system; then "
  "measured performance and usability targets; and only then general heuristics "
  "and visual preference. Taste loses to every one of the others."),
 ("UX",): ("01-usability.md", "Usability principles",
  "Nielsen's heuristics and their relatives, written as testable requirements. "
  "They are heuristics, not laws, and the acceptance column is what makes them "
  "checkable. Treat them as the questions a competent reviewer would ask."),
 ("NUM",): ("02-thresholds.md", "Numeric thresholds",
  "Every number this skill enforces, with its class. STANDARD values come from "
  "WCAG and are not negotiable within their scope. PROJECT values are defaults "
  "you may override in `.deluxui/ux.config.yaml` with a recorded reason. "
  "Machine-readable form: `references/rules/thresholds.yaml`."),
 ("VIS", "LAY"): ("03-visual-layout.md", "Visual system, layout and responsiveness",
  "Hierarchy, tokens, alignment, state styling, reflow and input modes. The "
  "recurring failure here is designing for one screenshot at one width with "
  "content that is exactly the right length. Real content is longer, the user's "
  "font is bigger, and the viewport is 320px."),
 ("NAV",): ("04-navigation.md", "Information architecture and navigation",
  "Where am I, what can I do, how do I get back. Most navigation defects are "
  "really semantic defects: an action dressed as a link, or a destination that "
  "cannot be linked to."),
 ("FORM",): ("05-forms.md", "Forms, validation and authentication",
  "Forms are where users lose work. The rules cluster around three failures: "
  "asking for what you do not need, telling people they are wrong before they "
  "have finished, and discarding what they typed when something fails."),
 ("COMP",): ("06-components.md", "Component interaction contracts",
  "What a component owes its user regardless of how it looks: a name, a role, a "
  "keyboard pattern, honest states. Native elements and vetted primitives give "
  "you most of this for free, which is why COMP-001 comes first."),
 ("STATE",): ("07-state.md", "State coverage and asynchronous behaviour",
  "The states nobody builds and everybody reaches. Note the asymmetry the rules "
  "keep returning to: an unknown outcome is not a success, and a dismissed "
  "panel is not a cancelled operation. `ux_browser.sh --api` forces most of "
  "these so you can see them rather than reason about them."),
 ("A11Y",): ("08-accessibility.md", "Accessibility completeness",
  "WCAG 2.2 A and AA, as implementation requirements. Two cautions the rulebook "
  "is explicit about: automated testing covers a minority of the criteria, and "
  "a changed-component audit does not make an application conformant."),
 ("PERF",): ("09-performance.md", "Performance engineering",
  "Perceived and measured speed, kept apart on purpose. A spinner is not "
  "performance, a lab number is not a field number, and reserving layout space "
  "costs nothing while layout shift is measured directly."),
 ("CONTENT",): ("10-content.md", "Content, localisation and data presentation",
  "Copy is interface. So are units, currencies, time zones and the difference "
  "between zero, missing and stale. Test with real and extreme content, because "
  "placeholder text hides every layout problem you have."),
 ("TRUST", "AI"): ("11-trust-ai.md", "Trust, safety, privacy and AI features",
  "Consequence disclosure, dark patterns, permissions and the honest handling of "
  "generated output. The AI rules apply only when the product actually has a "
  "generative feature -- declare it with `--feature ai_features`."),
 ("MEASURE", "QA"): ("12-measurement-qa.md", "Measurement and verification quality",
  "How to know whether any of this worked, and what counts as evidence. QA-001 "
  "onwards is the answer to 'can I just say it passed'."),
}


def main() -> int:
    reg = yaml.safe_load((RULES / "registry.yaml").read_text())
    det = yaml.safe_load((RULES / "detectors.yaml").read_text())["detectors"]
    by_rule = {}
    for did, d in det.items():
        for rid in d["rules"]:
            by_rule.setdefault(rid, []).append(did)

    written = []
    for prefixes, (fname, title, intro) in PACKS.items():
        rows = [r for r in reg["rules"] if r["id"].split("-")[0] in prefixes]
        if not rows:
            continue
        out = [f"# {title}", "",
               f"{len(rows)} rules. Generated from `registry.yaml` by "
               "`scripts/build_rule_packs.py` -- edit the registry, not this file.", "",
               intro, "",
               "| Rule | Severity | Class | Requirement | Acceptance | Basis | Tested by |",
               "|---|---|---|---|---|---|---|"]
        for r in rows:
            dets = by_rule.get(r["id"], [])
            tested = ", ".join(f"`{d}`" for d in dets) if dets else "_manual only_"
            req = r["requirement"].replace("|", "\\|")
            acc = (r.get("acceptance") or "").replace("|", "\\|")
            out.append(f"| **{r['id']}** | {r['severity']} | {r['class']} | {req} | "
                       f"{acc} | {' '.join(r['basis'])} | {tested} |")
        out += ["", "## Sources cited above", "",
                "| ID | Source | Type |", "|---|---|---|"]
        cited = sorted({b for r in rows for b in r["basis"]})
        for sid in cited:
            s = reg["sources"].get(sid, {})
            out.append(f"| {sid} | {s.get('publisher','')} — {s.get('title','')} | "
                       f"{s.get('type','')} |")
        out.append("")
        (RULES / fname).write_text("\n".join(out))
        written.append((fname, len(rows)))

    for f, n in written:
        print(f"  {f:<28} {n:>3} rules")
    print(f"{len(written)} packs, {sum(n for _f, n in written)} rules total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
