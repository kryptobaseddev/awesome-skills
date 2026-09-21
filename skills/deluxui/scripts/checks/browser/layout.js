// R-REFLOW -- horizontal overflow and clipping at the current viewport. NUM-009.
(() => {
  const vw = document.documentElement.clientWidth;
  const doc = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  const offenders = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0) continue;
    if (r.right > vw + 1 || r.left < -1) {
      const s = getComputedStyle(el);
      if (s.position === 'fixed' && r.width <= vw) continue;
      offenders.push({ tag: el.tagName.toLowerCase(),
                       cls: (el.className || '').toString().slice(0, 60),
                       left: Math.round(r.left), right: Math.round(r.right),
                       text: (el.textContent || '').trim().slice(0, 40) });
    }
  }
  // Collapse to outermost offenders: a parent overflowing drags its children with it.
  const trimmed = offenders.filter((o, i) => i < 25);
  return { probe: 'layout', viewport: vw, scrollWidth: doc,
           page_overflows: doc > vw + 1, offenders: trimmed };
})()
