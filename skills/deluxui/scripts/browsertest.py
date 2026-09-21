#!/usr/bin/env python3
"""Integration test for the runtime tier: run the real probes in a real browser
against a page whose defects are known, and check the numbers.

  browsertest.py [--port 8731] [--keep]

Why this exists. R-CONTRAST's colour parser was rewritten after it manufactured
eight "severe" failures on one page by reading lab(37.88 37.17 52.27) as
rgb(37,37,52). The rewrite was verified against a Python implementation to
pixel-exactness -- which proves the two agree, not that either is right. This
does the thing that was missing: it paints each declared colour on a canvas in
the same browser, reads the pixels back, and requires the probe's ratio to match
what the page actually rendered. Neither implementation is the authority; the
screen is.

Exit 0 when every assertion holds, 1 when the environment is missing (reported,
not passed), 2 when a probe disagrees with the page.
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "checks" / "browser" / "fixture"
PROBES = HERE / "checks" / "browser"


def ab(*args, timeout=120):
    r = subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def evaluate(js: str):
    """agent-browser eval prints the JSON-ish value of the expression."""
    code, out, err = ab("eval", js)
    out = out.strip()
    if not out:
        raise RuntimeError(f"eval returned nothing ({err.strip()[:200]})")
    try:
        return json.loads(out)
    except ValueError:
        # A bare string comes back quoted; anything else is a driver message.
        raise RuntimeError(f"eval returned unparseable output: {out[:300]}")


# The ground truth. Paint each element's own declared colours into a 1x1 canvas
# and read the pixel back, then apply the WCAG formula to those pixels. This is
# what the user sees, whatever format the stylesheet was written in.
PIXEL_TRUTH = r"""
(() => {
  const lin = c => { c /= 255; return c <= 0.04045 ? c/12.92 : ((c+0.055)/1.055)**2.4; };
  const lum = ([r,g,b]) => 0.2126*lin(r) + 0.7152*lin(g) + 0.0722*lin(b);
  const cv = document.createElement('canvas');
  cv.width = cv.height = 1;
  const ctx = cv.getContext('2d', { willReadFrequently: true });
  const paint = css => {
    ctx.clearRect(0,0,1,1);
    ctx.fillStyle = '#000';               // reset; an invalid value leaves the old one
    ctx.fillStyle = css;
    ctx.fillRect(0,0,1,1);
    const d = ctx.getImageData(0,0,1,1).data;
    return [d[0], d[1], d[2]];
  };
  const out = {};
  for (const el of document.querySelectorAll('[data-fmt]')) {
    const cs = getComputedStyle(el);
    const fg = paint(cs.color), bg = paint(cs.backgroundColor);
    const a = lum(fg), b = lum(bg);
    const hi = Math.max(a,b), lo = Math.min(a,b);
    out[el.id] = { fmt: el.dataset.fmt, declared_fg: cs.color, declared_bg: cs.backgroundColor,
                   painted_fg: fg, painted_bg: bg,
                   ratio: Math.round(((hi+0.05)/(lo+0.05)) * 100) / 100 };
  }
  return JSON.stringify(out);
})()
"""


def run_probe(name: str, thresholds="{}"):
    js = f"window.__uxTh={thresholds};" + (PROBES / f"{name}.js").read_text()
    code, out, err = ab("eval", js)
    out = out.strip()
    if not out:
        raise RuntimeError(f"probe {name} returned nothing ({err.strip()[:200]})")
    try:
        v = json.loads(out)
    except ValueError:
        raise RuntimeError(f"probe {name} returned unparseable output: {out[:300]}")
    return json.loads(v) if isinstance(v, str) else v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8731)
    ap.add_argument("--keep", action="store_true", help="leave the server running")
    ap.add_argument("--shot", help="reuse an existing full-page screenshot")
    a = ap.parse_args(argv)

    if not shutil.which("agent-browser"):
        print("agent-browser is not installed, so the runtime tier cannot be "
              "integration-tested here. This is NOT a pass -- the probes are "
              "unverified against a real browser on this machine.", file=sys.stderr)
        return 1

    url = f"http://127.0.0.1:{a.port}/"
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(a.port),
                            "--bind", "127.0.0.1"], cwd=str(FIXTURE),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(url, timeout=1).read()
                break
            except Exception:
                time.sleep(0.1)
        else:
            print(f"the fixture server never came up on {url}", file=sys.stderr)
            return 1

        code, out, err = ab("open", url)
        if code != 0:
            print(f"agent-browser could not open the fixture: {err.strip()[:300]}",
                  file=sys.stderr)
            return 1

        fails, notes = [], []
        w = sys.stdout.write
        EXPECT_ROWS = 10        # [data-fmt] rows in the fixture
        EXPECT_BUTTONS = 2

        # ---------------------------------------------------- R-CONTRAST
        truth = json.loads(evaluate(PIXEL_TRUTH))
        if len(truth) < EXPECT_ROWS:
            fails.append(f"only {len(truth)} of {EXPECT_ROWS} contrast rows were found "
                         f"on the page; the comparison would be vacuous")
        probe = run_probe("contrast")
        seen = probe.get("examined")
        if not isinstance(seen, int) or seen < EXPECT_ROWS:
            fails.append(f"R-CONTRAST examined {seen!r} nodes on a page with "
                         f"{EXPECT_ROWS} contrast rows")
        # The probe reports only failures, keyed by the text it read. Rows it did
        # NOT report are rows it judged as passing, so both directions matter: a
        # missed failure and an invented one are the same defect seen from
        # opposite sides, and the parser bug this fixture exists for produced the
        # second kind eight times on one page.
        by_text = {}
        for h in (probe.get("failures") or []):
            by_text[" ".join(str(h.get("text", "")).split())] = h

        w("\nR-CONTRAST -- probe ratio vs the pixels the browser painted\n")
        w(f"  {'row':<12}{'format':<13}{'painted':>9}{'probe':>9}   verdict\n")
        texts = json.loads(evaluate(
            "JSON.stringify(Object.fromEntries("
            "[...document.querySelectorAll('[data-fmt]')].map("
            "e => [e.id, e.textContent.trim()])))"))
        for rid, tr in sorted(truth.items()):
            hit = by_text.get(" ".join(texts.get(rid, "").split()))
            got = hit.get("ratio") if hit else None
            expect_fail = tr["ratio"] < 4.5
            if expect_fail and hit is None:
                fails.append(f"{rid} ({tr['fmt']}): the browser painted {tr['ratio']}:1, "
                             f"below 4.5, and the probe did not report it")
                verdict = "MISSED"
            elif not expect_fail and hit is not None:
                fails.append(f"{rid} ({tr['fmt']}): the probe reported a failure at "
                             f"{got}:1, but the browser painted {tr['ratio']}:1 from "
                             f"{tr['declared_fg']} on {tr['declared_bg']} -- an invented "
                             f"failure, which is the defect this fixture exists for")
                verdict = "INVENTED"
            elif got is not None and abs(float(got) - tr["ratio"]) > 0.05:
                fails.append(f"{rid} ({tr['fmt']}): probe {got}:1 vs painted "
                             f"{tr['ratio']}:1")
                verdict = "WRONG"
            else:
                verdict = "reported" if hit is not None else "judged passing"
            w(f"  {rid:<12}{tr['fmt']:<13}{tr['ratio']:>9}"
              f"{(got if got is not None else '-'):>9}   {verdict}\n")
        w(f"  nodes examined: {seen}\n")

        unmeasured = probe.get("unparsed") or probe.get("unmeasured") or 0
        w(f"  colours the parser refused to guess at: {unmeasured}\n")
        if unmeasured:
            notes.append(f"{unmeasured} colour(s) unparsed -- they are reported as "
                         f"unmeasured, not as passing")

        # ------------------------------------------------- R-PIXEL-CONTRAST
        # The two hero rows are painted over a gradient laid down by a positioned
        # SIBLING. CSS cannot resolve that backdrop, so R-CONTRAST must decline to
        # judge them -- reporting 1:1 for legible white text is the failure this
        # fixture was extended to catch -- and the pixel read must then settle
        # both, one passing and one failing.
        w("\nR-PIXEL-CONTRAST -- the sibling-gradient case\n")
        unj = {" ".join(str(u.get("text", "")).split()): u
               for u in (probe.get("unjudged") or [])}
        fail_texts = {" ".join(str(h.get("text", "")).split())
                      for h in (probe.get("failures") or [])}
        expect = json.loads(evaluate(
            "JSON.stringify(Object.fromEntries("
            "[...document.querySelectorAll('[data-pixel]')].map("
            "e => [e.textContent.trim(), e.dataset.pixel])))"))
        shot = Path(a.shot or "").resolve() if a.shot else None
        if shot is None:
            # A temp dir, not the skill tree. A plugin install copies the working
            # tree verbatim, so a stray artifact here ships to the consumer -- the
            # same reason bytecode is guarded against in selftest.py.
            import tempfile
            shot = Path(tempfile.gettempdir()) / "deluxui-fixture-fullpage.png"
            ab("screenshot", "--full", str(shot))
        import importlib
        sys.path.insert(0, str(HERE))
        ux_report = importlib.import_module("ux_report")
        img = ux_report._png_rows(shot) if shot.exists() else None
        if img is None:
            fails.append(f"could not decode the full-page screenshot at {shot}; "
                         f"R-PIXEL-CONTRAST cannot be tested")
        for text, want in expect.items():
            key = " ".join(text.split())
            if key in fail_texts:
                fails.append(f"{text!r} was reported as a CSS-resolved failure, but its "
                             f"backdrop is a sibling gradient that CSS cannot resolve -- "
                             f"that ratio is fabricated")
                w(f"  {want:<5} {text[:44]:<46} FABRICATED FAILURE\n")
                continue
            u = unj.get(key)
            if u is None:
                fails.append(f"{text!r} over a sibling gradient was neither judged nor "
                             f"recorded as unjudged; it vanished from the report")
                w(f"  {want:<5} {text[:44]:<46} MISSING\n")
                continue
            if img is None:
                continue
            pair = ux_report._pair_in_box(img, u["box"], float(u.get("dpr") or 1))
            if pair is None:
                fails.append(f"the pixel read could not separate text from background "
                             f"for {text!r}")
                w(f"  {want:<5} {text[:44]:<46} UNREADABLE\n")
                continue
            fg, bg, r = pair
            need = float(u.get("need") or 4.5)
            got = "pass" if r >= need else "fail"
            if got != want:
                fails.append(f"{text!r}: the pixel read says {r}:1 against a floor of "
                             f"{need}:1, which is a {got}; the fixture declares it a "
                             f"{want}")
            w(f"  {want:<5} {text[:44]:<46} {r}:1 vs {need}:1 -> {got}\n")

        # ------------------------------------------- the other probes ran at all
        w("\nother probes -- did each produce a real measurement\n")
        for name, key in (("targets", None), ("focus", None), ("layout", None),
                          ("motion", None), ("obstruction", None)):
            try:
                r = run_probe(name)
            except Exception as e:
                fails.append(f"probe {name} did not run: {e}")
                w(f"  {name:<14} FAILED TO RUN  {str(e)[:60]}\n")
                continue
            body = json.dumps(r)
            w(f"  {name:<14} ok             {body[:88]}\n")
            if body in ("{}", "null", "[]"):
                fails.append(f"probe {name} returned an empty result on a page built "
                             f"to trip it")

        w("\n" + "-" * 70 + "\n")
        for n in notes:
            w(f"  note  {n}\n")
        for f in fails:
            w(f"  FAIL  {f}\n")
        w(f"\nBROWSER INTEGRATION {'PASS' if not fails else f'FAIL ({len(fails)})'}\n")
        return 0 if not fails else 2
    finally:
        if not a.keep:
            srv.terminate()


if __name__ == "__main__":
    sys.exit(main())
