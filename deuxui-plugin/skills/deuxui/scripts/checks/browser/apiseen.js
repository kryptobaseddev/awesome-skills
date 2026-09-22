// Does this route fetch anything client-side at all?
//
// The three forced-state probes (abort, empty, offline) intercept a request
// pattern and then ask what the interface said. On a server-rendered route there
// is no client request to intercept, so nothing is forced -- and the probes then
// report on an ordinary page as though a failure had been injected. On a real
// Next.js app that produced a FAIL for "request failed but the page says nothing
// about it" when no request had failed, and an empty-state FAIL against Chrome's
// own network error page.
//
// This is measured on the FIRST, healthy load, before any condition is forced,
// because "does this route fetch client-side" is a property of the route and not
// of the state being injected. Measuring it while offline would find nothing for
// the wrong reason.
//
// The pattern is a glob (`**\/api\/**`). Rather than convert it to a regex, every
// literal run between the wildcards has to appear in the URL in order -- which is
// what the glob means here and cannot over-match.
(() => {
  const pattern = (typeof window.__uxApi === 'string' && window.__uxApi) || '';
  const lits = pattern.split(/\*+/).filter(s => s.length > 1);
  const matches = url => {
    if (!lits.length) return false;
    let at = 0;
    for (const lit of lits) {
      const i = url.indexOf(lit, at);
      if (i < 0) return false;
      at = i + lit.length;
    }
    return true;
  };
  let all = [];
  try {
    all = performance.getEntriesByType('resource').map(e => e.name);
  } catch (e) { /* no Resource Timing: reported as unknown below */ }
  const hits = all.filter(matches);
  return {
    probe: 'apiseen',
    pattern: pattern,
    resource_entries: all.length,
    api_requests: hits.length,
    api_seen: hits.length > 0,
    // Resource Timing unavailable means nobody looked, which is not the same as
    // "this route makes no requests".
    measured: all.length > 0 || performance.getEntriesByType !== undefined,
    sample: hits.slice(0, 5)
  };
})()
