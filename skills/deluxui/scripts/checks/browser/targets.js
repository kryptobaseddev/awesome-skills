// R-TARGET / R-TARGET-SPACING -- real hit areas, measured on the rendered page.
// Source cannot answer this: padding, line-height, transforms and pseudo-elements
// all change the box. NUM-004 (24px), NUM-005 (44px coarse), SC 2.5.8 spacing.
(() => {
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
    if (min < 24) {
      // SC 2.5.8 spacing exception: a 24px circle on each undersized target
      // must not touch another target's circle.
      const clash = boxes.some(o => {
        if (o === b) return false;
        const dx = (b.r.left + b.r.width / 2) - (o.r.left + o.r.width / 2);
        const dy = (b.r.top + b.r.height / 2) - (o.r.top + o.r.height / 2);
        return Math.hypot(dx, dy) < 24;
      });
      under.push({ tag: b.tag, label: b.label, w: Math.round(b.r.width),
                   h: Math.round(b.r.height), spacing_exception_met: !clash });
    } else if (min < 44) {
      crowded.push({ tag: b.tag, label: b.label, w: Math.round(b.r.width),
                     h: Math.round(b.r.height) });
    }
  }
  return { probe: 'targets', examined: boxes.length, under_24: under,
           under_44: crowded.slice(0, 40) };
})()
