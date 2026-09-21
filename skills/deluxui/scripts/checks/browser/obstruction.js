// R-STICKY-OBSTRUCTION (LAY-008) and R-ORIENTATION (LAY-004).
// Sticky headers and cookie bars are the classic way a focused field ends up
// underneath something. SC 2.4.11 is about exactly this.
(() => {
  const sticky = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (s.position !== 'fixed' && s.position !== 'sticky') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 8) continue;
    sticky.push({ el, r, cls: (el.className || '').toString().slice(0, 40) });
  }
  const vh = window.innerHeight;
  const heavy = sticky
    .filter(s => s.r.height / vh > 0.25)
    .map(s => ({ cls: s.cls, pct: Math.round((s.r.height / vh) * 100) }));

  // Tab through and see whether any stop lands underneath a sticky layer.
  const SEL = 'a[href],button:not([disabled]),input:not([type=hidden]):not([disabled]),' +
              'select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
  const obscured = [];
  const prev = document.activeElement;
  for (const el of [...document.querySelectorAll(SEL)].slice(0, 120)) {
    const r0 = el.getBoundingClientRect();
    if (r0.width === 0 || r0.height === 0) continue;
    try { el.focus({ preventScroll: false }); } catch (e) { continue; }
    if (document.activeElement !== el) continue;
    const r = el.getBoundingClientRect();
    for (const s of sticky) {
      const sr = s.el.getBoundingClientRect();
      const overlap = !(r.right < sr.left || r.left > sr.right ||
                        r.bottom < sr.top || r.top > sr.bottom);
      if (!overlap) continue;
      // the sticky layer must actually paint above it
      const mid = document.elementFromPoint(
        Math.min(window.innerWidth - 1, Math.max(0, r.left + r.width / 2)),
        Math.min(vh - 1, Math.max(0, r.top + r.height / 2)));
      if (mid && mid !== el && !el.contains(mid) && s.el.contains(mid)) {
        obscured.push({ tag: el.tagName.toLowerCase(),
                        label: (el.getAttribute('aria-label') || el.textContent || '')
                                 .trim().slice(0, 36),
                        behind: s.cls });
        break;
      }
    }
    if (obscured.length >= 10) break;
  }
  try { prev && prev.focus && prev.focus({ preventScroll: true }); } catch (e) {}

  return { probe: 'obstruction', sticky_count: sticky.length,
           viewport_hogs: heavy, focus_obscured: obscured };
})()
