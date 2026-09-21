#!/usr/bin/env python3
"""R-STATE-SLOW -- what the interface says while it is waiting.

  ux_slow.py --url http://localhost:5173/ --out .deluxui/reports/runtime --route /
  ux_slow.py --url ... --escalation        # also test the 10s requirement (costs ~13s)

NUM-014 and STATE-006 name two moments, and both are about honesty rather than
speed: a pending status by about one second, and an explanation of what is
happening by about ten. An interface that shows nothing for four seconds has not
failed a performance budget -- it has told the user nothing, and the user cannot
tell a slow request from a broken one.

The other forced states abort, empty or disconnect a request. This one makes it
SLOW, which nothing else in the driver could do: `Network.emulateNetworkConditions`
is CDP-only, so it goes through scripts/cdp.py like the forced-colors pass.

What this measures, said plainly: latency is applied to every request including
the document, so the page's own load is slowed as well as its data calls. The
probe therefore looks for a pending affordance that is present while requests are
still outstanding -- not for one that appears at an exact millisecond. A result
here is evidence about whether the interface speaks while waiting, not a timing
measurement.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cdp                                                    # noqa: E402

# What counts as "the interface is telling me it is working". Deliberately broad:
# the question is whether the user is told anything, not whether the developer
# used the idiom this probe would have chosen.
PENDING_JS = """
(() => {
  const txt = (document.body ? document.body.innerText : '') || '';
  const has = sel => { try { return !!document.querySelector(sel); } catch (e) { return false; } };
  const SPIN = '[class*="spinner"],[class*="Spinner"],[class*="loading"],[class*="Loading"],'
             + '[class*="skeleton"],[class*="Skeleton"],[class*="animate-pulse"],[class*="animate-spin"]';
  const PENDING_WORDS = /\\b(loading|saving|fetching|working|processing|please wait|one moment)\\b/i;
  const DELAY_WORDS = /\\b(taking longer|still working|this may take|almost there|hang on|slower than usual)\\b/i;
  const CANCEL_WORDS = /\\b(cancel|stop|abort)\\b/i;
  const pending = {
    aria_busy: has('[aria-busy="true"]'),
    status_role: has('[role="status"],[role="progressbar"],[role="alert"]'),
    output: has('output,progress'),
    spinner_class: has(SPIN),
    disabled_submit: has('button[disabled],button[aria-disabled="true"]'),
    wording: PENDING_WORDS.test(txt),
  };
  const escalation = {
    explains_delay: DELAY_WORDS.test(txt),
    offers_cancel: CANCEL_WORDS.test(txt),
    progress_value: has('progress[value],[aria-valuenow]'),
  };
  return JSON.stringify({
    pending, escalation,
    any_pending: Object.values(pending).some(Boolean),
    any_escalation: Object.values(escalation).some(Boolean),
    resources: (performance.getEntriesByType('resource') || []).length,
    ready: document.readyState,
    text_len: txt.trim().length,
    // A content fingerprint, because readyState is the wrong clock. `complete`
    // fires when the document and its subresources are done -- a fetch() started
    // by a script is not one of them, so an app that loads its data after the
    // document is "complete" the whole time it is actually waiting. That is the
    // case this detector exists for, so flight is defined by content instead:
    // a sample whose fingerprint differs from the settled one was taken before
    // the content arrived.
    fp: (() => { let h = 0; const s = txt.trim();
                 for (let i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) | 0; }
                 return h + ':' + s.length; })(),
  });
})()
"""


def _ab(*args, timeout=180):
    try:
        return subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                              timeout=timeout)
    except Exception:
        return None


def probe_at(url: str, latency_ms: int, window_s: float, throughput_kbps=50) -> dict:
    """Load `url` with latency applied and sample repeatedly WHILE it is loading.

    A single timed sample does not work. Written that way, the 1.6s sample landed
    after a small fixture had already finished, so it was measuring the settled
    page and calling it flight -- and the one signal it did find was a `role=status`
    that never gets removed, which is furniture. Polling from 200ms answers the
    real question: was anything saying "working" at any moment while work was
    outstanding, and was it gone once the work finished.

    When nothing can be sampled in flight, that is reported rather than scored. A
    route that settles in under 200ms has no waiting state to judge, and inventing
    a verdict for it would be a fabricated pass.
    """
    ws, info = cdp.connect_page(url)
    if ws is None:
        return {"error": str(info)}
    try:
        ws.call("Network.enable", {})
        ws.call("Page.enable", {})
        ws.call("Network.emulateNetworkConditions", {
            "offline": False, "latency": latency_ms,
            "downloadThroughput": throughput_kbps * 1024 / 8,
            "uploadThroughput": throughput_kbps * 1024 / 8,
        })
        ws.call("Page.navigate", {"url": url})
        samples = []
        deadline = time.time() + window_s
        while time.time() < deadline:
            time.sleep(0.15)
            try:
                s = cdp.evaluate(ws, PENDING_JS)
            except Exception:
                continue
            if not isinstance(s, dict):
                continue
            s["t"] = round(window_s - (deadline - time.time()), 2)
            samples.append(s)
        # Remove the throttle and let the page finish, then take the settled reading.
        try:
            ws.call("Network.emulateNetworkConditions", {
                "offline": False, "latency": 0,
                "downloadThroughput": -1, "uploadThroughput": -1})
        except Exception:
            pass
        settled, last_err = None, None
        for _ in range(40):
            time.sleep(0.25)
            try:
                s = cdp.evaluate(ws, PENDING_JS)
            except Exception as e:
                # Do NOT break. Runtime.evaluate throws while the execution context
                # is being replaced after a navigation, and breaking there left
                # `settled` as None -- which the caller then read as "this route has
                # no waiting state", a completely different statement. One transient
                # throw was silently converting a measurement into a shrug.
                last_err = f"{type(e).__name__}: {e}"
                continue
            if isinstance(s, dict) and s.get("ready") == "complete":
                time.sleep(0.8)            # let the render after the fetch land
                for _ in range(6):
                    try:
                        settled = cdp.evaluate(ws, PENDING_JS)
                        break
                    except Exception as e:
                        last_err = f"{type(e).__name__}: {e}"
                        time.sleep(0.3)
                if settled is None:
                    settled = s
                break
        # In flight = the content had not arrived yet, judged against the settled
        # fingerprint rather than against readyState.
        final_fp = (settled or {}).get("fp")
        if final_fp is None:
            return {"error": "the page never reported a settled state"
                             + (f" (last error: {last_err})" if last_err else ""),
                    "samples": len(samples)}
        inflight = [s for s in samples if s.get("fp") != final_fp]
        try:
            where = cdp.evaluate(ws, "location.href")
        except Exception:
            where = None
        return {
            "navigated_to": url,
            "sampled_url": where,
            "samples": len(samples),
            "inflight_samples": len(inflight),
            "pending_inflight": any(s.get("any_pending") for s in inflight),
            "escalation_inflight": any(s.get("any_escalation") for s in inflight),
            "first_inflight": inflight[0] if inflight else None,
            "settled": settled if isinstance(settled, dict) else None,
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        try:
            ws.call("Network.emulateNetworkConditions", {
                "offline": False, "latency": 0,
                "downloadThroughput": -1, "uploadThroughput": -1})
        except Exception:
            pass
        ws.close()


def run(url: str, out_dir: Path, route: str, escalation=False) -> int:
    payload = {"probe": "slow", "url": url, "ran": False, "findings": []}
    if not url:
        payload["reason"] = ("No URL to load. Pass --url, or set app.dev_url in "
                             ".deluxui/ux.config.yaml.")
        _write(out_dir, route, payload)
        sys.stderr.write(f"slow: {payload['reason']}\n")
        return 0

    one = probe_at(url, 2500, 6.0)
    if one.get("error"):
        payload["reason"] = one["error"]
        _write(out_dir, route, payload)
        sys.stderr.write(f"slow: {one['error']}\n")
        return 0
    payload["pass1"] = one
    if not one.get("inflight_samples"):
        payload["ran"] = False
        payload["reason"] = (
            f"this route reached its final content before any of the "
            f"{one.get('samples')} samples could catch it loading, even at 2500ms "
            f"latency and 50kbps. There is no waiting state here to judge, so nothing "
            f"is claimed about one -- point this at a route that fetches something.")
        _write(out_dir, route, payload)
        sys.stderr.write(f"slow: {payload['reason'][:100]}\n")
        return 0
    payload["ran"] = True
    settled = one.get("settled") or {}
    if one.get("pending_inflight") and settled.get("any_pending"):
        which = [k for k, v in (settled.get("pending") or {}).items() if v]
        payload["findings"].append(
            "the pending affordance is still showing after the page finished loading "
            f"({', '.join(which)}). Either it never clears -- an immortal spinner, which "
            "a user reads as a hang -- or it is permanent furniture that would have "
            "satisfied this check on a page that loads nothing at all. Clear it when the "
            "work completes (STATE-001).")
    elif not one.get("pending_inflight"):
        payload["findings"].append(
            f"across {one['inflight_samples']} sample(s) taken while the page was still "
            f"loading on a slow link, nothing said it was working: no aria-busy, no "
            f"role=status or progressbar, no skeleton or spinner, and no wording. A user "
            f"cannot tell a slow request from a broken one, which is what NUM-014's "
            f"one-second requirement is for.")

    if escalation:
        two = probe_at(url, 9000, 12.0, throughput_kbps=20)
        if two.get("error"):
            payload["escalation_error"] = two["error"]
        elif not two.get("inflight_samples"):
            payload["escalation_error"] = ("the route settled too quickly to hold a "
                                           "ten-second wait open.")
        else:
            payload["pass2"] = two
            if not two.get("escalation_inflight"):
                payload["findings"].append(
                    "through a heavily slowed load, nothing explained the delay and "
                    "nothing offers a way out: no wording about it taking longer, no "
                    "progress value, no cancel. NUM-014 asks for an explanation by about "
                    "ten seconds, and STATE-006 asks that a long wait stay cancellable.")
    else:
        payload["escalation_skipped"] = ("The ten-second requirement was not tested; it "
                                         "costs about thirteen seconds. Pass --escalation.")
    _write(out_dir, route, payload)
    sys.stderr.write(f"slow: {len(payload['findings'])} finding(s)"
                     f"{' (escalation not tested)' if not escalation else ''}\n")
    # Put the page back where the rest of the run expects it.
    _ab("open", url)
    return 0


def _write(out_dir: Path, route: str, payload: dict):
    slug = (route.strip("/").replace("/", "_") or "root")
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"{slug}__slow.json").write_text(json.dumps(payload, indent=1))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="")
    ap.add_argument("--out", default=".deluxui/reports/runtime")
    ap.add_argument("--route", default="/")
    ap.add_argument("--escalation", action="store_true")
    a = ap.parse_args(argv)
    return run(a.url, Path(a.out), a.route, escalation=a.escalation)


if __name__ == "__main__":
    sys.exit(main())
