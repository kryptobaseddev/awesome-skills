// R-FOCUS-WALK -- is every focusable control visibly focused, and does DOM order
// still match visual order. A11Y-003, NUM-011, LAY-003.
(() => {
  const SEL = 'a[href],button:not([disabled]),input:not([type=hidden]):not([disabled]),' +
              'select:not([disabled]),textarea:not([disabled]),summary,' +
              '[tabindex]:not([tabindex="-1"])';
  const snap = el => { const s = getComputedStyle(el);
    return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow,
            s.backgroundColor, s.color, s.borderColor].join('|'); };
  const els = [...document.querySelectorAll(SEL)].filter(el => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
  });
  const invisible = [], order = [];
  const active = document.activeElement;
  els.forEach((el, i) => {
    const before = snap(el);
    try { el.focus({ preventScroll: true }); } catch (e) { return; }
    if (document.activeElement !== el) return;
    const after = snap(el);
    const r = el.getBoundingClientRect();
    order.push({ i, top: Math.round(r.top + window.scrollY), left: Math.round(r.left) });
    if (before === after) {
      invisible.push({ tag: el.tagName.toLowerCase(),
                       label: (el.getAttribute('aria-label') || el.textContent || '')
                                .trim().slice(0, 40) });
    }
  });
  try { active && active.focus && active.focus({ preventScroll: true }); } catch (e) {}
  // DOM order vs reading order: count places where focus jumps backwards up the page.
  let backjumps = 0;
  for (let i = 1; i < order.length; i++) {
    if (order[i].top < order[i - 1].top - 24) backjumps++;
  }
  const positive = [...document.querySelectorAll('[tabindex]')]
    .filter(e => +e.getAttribute('tabindex') > 0).length;
  return { probe: 'focus', focusable: els.length,
           no_visible_focus_style: invisible.slice(0, 40),
           focus_order_backjumps: backjumps, positive_tabindex: positive };
})()
