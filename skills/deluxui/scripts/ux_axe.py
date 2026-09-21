#!/usr/bin/env python3
"""R-AXE -- run axe-core against the live page.

  ux_axe.py --out .deluxui/reports/runtime --route /
  ux_axe.py --no-fetch      # only use a copy already on this machine

axe-core covers rule families deluxui's own probes do not reproduce: ARIA
attribute validity, role-required-children, duplicate ids in active contexts, the
long tail of name-computation cases. deluxui's probes cover things axe does not
touch at all -- forced states, real hit-area spacing, reflow at five widths, the
craft floor. Neither subsumes the other, and both are floors: automated rules
reach a minority of the WCAG success criteria however many of them you run, which
is why this reports a PASS as "no violations", never as conformance.

Where axe comes from, in order, because the skill's dependency floor is python3 +
pyyaml and this must not raise it:

  1. the project's own node_modules/axe-core -- the version the project tests with
  2. a cached copy under the system temp dir, from an earlier run
  3. a one-time fetch from a CDN, pinned by version and checked for plausibility

If none of those work it reports NOT_RUN with the reason. It never silently skips,
and it never reports a pass for a scan that did not happen.
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile, urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cdp                                                    # noqa: E402

VERSION = "4.10.2"
CDNS = [f"https://cdnjs.cloudflare.com/ajax/libs/axe-core/{VERSION}/axe.min.js",
        f"https://unpkg.com/axe-core@{VERSION}/axe.min.js"]
CACHE = Path(tempfile.gettempdir()) / f"deluxui-axe-{VERSION}.js"

# The rule families deluxui already measures directly. Reporting them twice makes
# a report look longer without making it say more, and the two implementations
# disagree at the margins -- which reads as a contradiction rather than as two
# tools with different scopes.
OVERLAP = {"color-contrast", "color-contrast-enhanced", "target-size",
           "meta-viewport", "meta-viewport-large"}


def _plausible(js: str) -> bool:
    """A CDN can serve an error page with a 200. Check for the thing we asked for
    rather than for the absence of an error."""
    return len(js) > 200_000 and "axe" in js[:2000] and "function" in js[:2000]


def source(no_fetch=False, root: Path | None = None) -> tuple[str, str]:
    """(javascript, where it came from) or ("", reason)."""
    root = root or Path.cwd()
    local = root / "node_modules" / "axe-core" / "axe.min.js"
    if local.exists():
        js = local.read_text(errors="replace")
        if _plausible(js):
            return js, f"the project's own node_modules ({local})"
    for q in root.glob("*/node_modules/axe-core/axe.min.js"):
        js = q.read_text(errors="replace")
        if _plausible(js):
            return js, f"a workspace package ({q})"
    if CACHE.exists():
        js = CACHE.read_text(errors="replace")
        if _plausible(js):
            return js, f"the cached copy at {CACHE}"
    if no_fetch:
        return "", ("axe-core is not in this project's node_modules and no cached copy "
                    "exists, and --no-fetch was given.")
    errs = []
    for url in CDNS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deluxui"})
            with urllib.request.urlopen(req, timeout=30) as f:
                js = f.read().decode("utf-8", "replace")
            if not _plausible(js):
                errs.append(f"{url} returned {len(js)} bytes that do not look like axe")
                continue
            try:
                CACHE.write_text(js)
            except OSError:
                pass
            return js, f"{url} (cached at {CACHE})"
        except Exception as e:
            errs.append(f"{url}: {type(e).__name__}")
    return "", ("axe-core could not be obtained. " + "; ".join(errs)
                + ". Install it in the project (npm i -D axe-core) to run this offline.")


RUN = """
(async () => {
  if (typeof axe === 'undefined') return JSON.stringify({error: 'axe did not define itself'});
  try {
    const r = await axe.run(document, {
      resultTypes: ['violations', 'incomplete'],
      reporter: 'v2',
    });
    return JSON.stringify({
      version: (axe.version || ''),
      passes: (r.passes || []).length,
      incomplete: (r.incomplete || []).length,
      incompleteIds: (r.incomplete || []).map(v => v.id).slice(0, 25),
      violations: (r.violations || []).map(v => ({
        id: v.id, impact: v.impact, help: v.help,
        nodes: (v.nodes || []).length,
        target: ((v.nodes || [])[0] || {}).target
                  ? String(((v.nodes || [])[0].target || []).join(' '))
                  : '',
      })),
    });
  } catch (e) {
    return JSON.stringify({error: String(e && e.message || e)});
  }
})()
"""


def run(out_dir: Path, route: str, url: str | None = None, no_fetch=False) -> int:
    js, where = source(no_fetch=no_fetch)
    if not js:
        _write(out_dir, route, {"probe": "axe", "ran": False, "reason": where,
                                "violations": []})
        sys.stderr.write(f"axe: {where}\n")
        return 0
    ws, info = cdp.connect_page(url)
    if ws is None:
        _write(out_dir, route, {"probe": "axe", "ran": False, "reason": str(info),
                                "violations": []})
        sys.stderr.write(f"axe: {info}\n")
        return 0
    try:
        cdp.evaluate(ws, js + "\n;1")          # define axe in the page
        res = cdp.evaluate(ws, RUN)
        if not isinstance(res, dict) or res.get("error"):
            payload = {"probe": "axe", "ran": False, "violations": [],
                       "reason": f"axe ran but returned an error: "
                                 f"{(res or {}).get('error', 'unreadable result')}"}
        else:
            kept = [v for v in (res.get("violations") or [])
                    if v.get("id") not in OVERLAP]
            dropped = len(res.get("violations") or []) - len(kept)
            payload = {"probe": "axe", "ran": True, "source": where,
                       "axe_version": res.get("version", VERSION),
                       "passes": res.get("passes", 0),
                       "incomplete": res.get("incomplete", 0),
                       "incompleteIds": res.get("incompleteIds", []),
                       "violations": kept,
                       "suppressed_overlap": dropped,
                       "overlap_note": ("Contrast and target-size violations are left to "
                                        "R-CONTRAST, R-PIXEL-CONTRAST and R-TARGET, which "
                                        "measure them directly and against the project's "
                                        "own thresholds."
                                        if dropped else "")}
    except Exception as e:
        payload = {"probe": "axe", "ran": False, "violations": [],
                   "reason": f"{type(e).__name__}: {e}"}
    finally:
        ws.close()
    _write(out_dir, route, payload)
    if payload.get("ran"):
        sys.stderr.write(f"axe {payload.get('axe_version')}: "
                         f"{len(payload['violations'])} violation(s), "
                         f"{payload.get('incomplete', 0)} incomplete, from {where}\n")
    else:
        sys.stderr.write(f"axe: {payload.get('reason')}\n")
    return 0


def _write(out_dir: Path, route: str, payload: dict):
    slug = (route.strip("/").replace("/", "_") or "root")
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{slug}__axe.json").write_text(json.dumps(payload, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=".deluxui/reports/runtime")
    ap.add_argument("--url", help="the page under test; without it the probe attaches to whichever tab is first, which is wrong the moment two are open")
    ap.add_argument("--route", default="/")
    ap.add_argument("--no-fetch", action="store_true",
                    help="never reach the network; use a local or cached copy only")
    a = ap.parse_args(argv)
    return run(Path(a.out), a.route, a.url, no_fetch=a.no_fetch)


if __name__ == "__main__":
    sys.exit(main())
