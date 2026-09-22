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
  let pinned = 0;
  const active = document.activeElement;
  els.forEach((el, i) => {
    const before = snap(el);
    try { el.focus({ preventScroll: true }); } catch (e) { return; }
    if (document.activeElement !== el) return;
    const after = snap(el);
    const r = el.getBoundingClientRect();
    // A fixed or sticky element does not live at a document position, so adding
    // scrollY to it produces a number that means nothing -- a bottom nav pinned at
    // y=847 was compared against a footer link at document y=10058 and read as a
    // 9,000px jump backwards. They are excluded from the order walk entirely: their
    // reading position is the viewport, not the page.
    const pos = getComputedStyle(el).position;
    if (pos === 'fixed' || pos === 'sticky') { pinned++; return; }
    order.push({ i, top: Math.round(r.top + window.scrollY), left: Math.round(r.left) });
    if (before === after) {
      invisible.push({ tag: el.tagName.toLowerCase(),
                       label: (el.getAttribute('aria-label') || el.textContent || '')
                                .trim().slice(0, 40) });
    }
  });
  try { active && active.focus && active.focus({ preventScroll: true }); } catch (e) {}
  // DOM order vs reading order. `top` alone is not reading order: in a multi-column
  // grid, several controls share a row, and comparing only their vertical position
  // read a perfectly ordinary column-major footer as scrambled -- the count tracked
  // the grid's column count (1 at 320px, 4 at 768px, 5 at 1024px) and nothing else.
  //
  // Reading order is (row, then inline position). Two controls within ROW_BAND of
  // each other are on the same row, and there a backjump means moving LEFT. Below
  // that, it means moving UP. The band is not a tolerance for noise -- it is the
  // definition of a row.
  const ROW_BAND = 24;
  let backjumps = 0;
  for (let i = 1; i < order.length; i++) {
    const a = order[i - 1], b = order[i];
    const sameRow = Math.abs(b.top - a.top) <= ROW_BAND;
    if (sameRow ? b.left < a.left - ROW_BAND : b.top < a.top - ROW_BAND) backjumps++;
  }
  const positive = [...document.querySelectorAll('[tabindex]')]
    .filter(e => +e.getAttribute('tabindex') > 0).length;
  return { probe: 'focus', focusable: els.length,
           no_visible_focus_style: invisible.slice(0, 40),
           focus_order_backjumps: backjumps, order_checked: order.length,
           pinned_excluded: pinned, positive_tabindex: positive };
})()
