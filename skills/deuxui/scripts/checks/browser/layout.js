// R-REFLOW -- horizontal overflow and clipping at the current viewport. NUM-009.
// R-TABLE-HIDDEN -- content hidden sideways inside a scroll box. LAY-006.
//
// Two different questions. R-REFLOW asks whether the PAGE scrolls sideways, which
// is what WCAG 1.4.10 measures -- and 1.4.10 exempts data tables, so a table in its
// own scroll box is not a reflow failure. It can still hide the Action column,
// which is a LAY-006 failure, and getBoundingClientRect cannot say so: a table
// that stays inside the window but overflows a narrower box has nothing past the
// viewport edge at all. scrollWidth against clientWidth on the box is what shows it.
(() => {
  const th = (window.__uxTh && window.__uxTh.responsive) || {};
  const maxCols = th.table_scroll_max_columns || 6;
  const actCols = th.table_actions_min_columns || 4;
  const vw = document.documentElement.clientWidth;
  const doc = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  const scrollsX = (el) => {
    if (el === document.body || el === document.documentElement) return false;
    return /(auto|scroll)/.test(getComputedStyle(el).overflowX);
  };
  const inScrollBox = (el) => {
    for (let p = el.parentElement; p; p = p.parentElement) if (scrollsX(p)) return true;
    return false;
  };

  // Page overflow, collapsed to the outermost offender: a parent overflowing drags
  // its children with it, and listing all of them buries the one to fix.
  const hit = new Set();
  const offenders = [];
  let offenderCount = 0;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0) continue;
    if (!(r.right > vw + 1 || r.left < -1)) continue;
    const s = getComputedStyle(el);
    if (s.position === 'fixed' && r.width <= vw) continue;
    if (inScrollBox(el)) continue;           // reachable by its own scroll box
    let p = el.parentElement, nested = false;
    for (; p; p = p.parentElement) if (hit.has(p)) { nested = true; break; }
    hit.add(el);
    if (nested) continue;
    offenderCount++;
    if (offenders.length < 25)
      offenders.push({ tag: el.tagName.toLowerCase(),
                       cls: (el.className || '').toString().slice(0, 60),
                       left: Math.round(r.left), right: Math.round(r.right),
                       text: (el.textContent || '').trim().slice(0, 40) });
  }

  // Scroll boxes whose content is wider than the box, and what they hide.
  const containers = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.scrollWidth <= el.clientWidth + 1 || !scrollsX(el)) continue;
    const table = el.matches('table') ? el : el.querySelector('table');
    const box = el.getBoundingClientRect();
    let lastColumn = null, columns = 0, interactive = false, pinned = false;
    if (table) {
      const heads = table.querySelectorAll('thead th');
      const firstRow = table.querySelector('tr');
      columns = heads.length || (firstRow ? firstRow.children.length : 0);
      const lastHead = heads.length ? heads[heads.length - 1] : null;
      lastColumn = lastHead ? (lastHead.textContent || '').trim().slice(0, 40) : null;
      const lastCells = [...table.querySelectorAll('tr')]
        .map((tr) => tr.children[tr.children.length - 1]).filter(Boolean);
      interactive = /^(actions?|edit|manage|options|more|menu|controls?)$/i.test(lastColumn || '') ||
        lastCells.some((c) => c.querySelector('button, a[href], input, select, [role=button], [role=menuitem]'));
      // Pinned means the last column is actually in view: sticky and inside the box.
      pinned = lastCells.length > 0 && lastCells.every((c) => {
        const r = c.getBoundingClientRect();
        return getComputedStyle(c).position === 'sticky' && r.right <= box.right + 1;
      });
    }
    containers.push({ tag: el.tagName.toLowerCase(),
                      cls: (el.className || '').toString().slice(0, 60),
                      boxPx: Math.round(el.clientWidth), contentPx: el.scrollWidth,
                      hiddenPx: el.scrollWidth - el.clientWidth,
                      table: !!table, columns, lastColumn, interactive, pinned,
                      dataTable: !!table && (columns > maxCols || (interactive && columns >= actCols)) });
    if (containers.length >= 25) break;
  }
  return { probe: 'layout', viewport: vw, scrollWidth: doc,
           page_overflows: doc > vw + 1, offenders, offender_count: offenderCount,
           containers };
})()
