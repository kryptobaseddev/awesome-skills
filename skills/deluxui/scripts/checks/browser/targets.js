// R-TARGET / R-TARGET-SPACING -- real hit areas, measured on the rendered page.
// Source cannot answer this: padding, line-height, transforms and pseudo-elements
// all change the box. NUM-004 (24px), NUM-005 (44px coarse), SC 2.5.8 spacing.
(() => {
  // NUM-004 is the WCAG floor; NUM-005 is a PROJECT default a project may lower
  // in .deluxui/ux.config.yaml. ux_browser.sh injects window.__uxTh.
  const _t = ((window.__uxTh || {}).target_size) || {};
  const MIN = _t.web_min_px || 24;
  const COARSE = _t.web_coarse_min_px || 44;
  const CIRCLE = _t.undersized_spacing_circle_px || 24;
  const SEL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,' +
              '[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox],' +
              '[role=radio],[role=switch],[tabindex]:not([tabindex="-1"])';
  const vis = el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' &&
           s.display !== 'none' && s.opacity !== '0';
  };
  const els = [...document.querySelectorAll(SEL)].filter(vis);
  const boxes = els.map(el => {
    const r = el.getBoundingClientRect();
    return { r, el,
      label: (el.getAttribute('aria-label') || el.textContent || el.value || '')
               .trim().slice(0, 50),
      tag: el.tagName.toLowerCase() };
  });
  const under = [], crowded = [];
  for (const b of boxes) {
    const min = Math.min(b.r.width, b.r.height);
    if (min < MIN) {
      // SC 2.5.8 spacing exception: a 24px circle on each undersized target
      // must not touch another target's circle.
      const clash = boxes.some(o => {
        if (o === b) return false;
        const dx = (b.r.left + b.r.width / 2) - (o.r.left + o.r.width / 2);
        const dy = (b.r.top + b.r.height / 2) - (o.r.top + o.r.height / 2);
        return Math.hypot(dx, dy) < CIRCLE;
      });
      under.push({ tag: b.tag, label: b.label, w: Math.round(b.r.width),
                   h: Math.round(b.r.height), spacing_exception_met: !clash });
    } else if (min < COARSE) {
      crowded.push({ tag: b.tag, label: b.label, w: Math.round(b.r.width),
                     h: Math.round(b.r.height) });
    }
  }
  // The key names used to be under_24 / under_44, which became wrong the moment
  // a project overrode the coarse minimum. They carry the value they used.
  return { probe: 'targets', examined: boxes.length,
           floor_px: MIN, coarse_px: COARSE,
           under_floor: under, under_coarse: crowded.slice(0, 40),
           under_24: under, under_44: crowded.slice(0, 40) };
})()
