// R-FORCED-COLORS -- what the interface loses when the operating system takes the
// palette away. VIS-008.
//
// Run twice, once normally and once with `forced-colors: active` emulated through
// CDP, then diff the two fingerprints. Measuring the DIFFERENCE is the whole
// design: a forced-colors defect is by definition something that was carrying
// meaning before and is not carrying it after, and no single-pass inspection can
// see that. Chrome in this mode overrides color, background-color and
// border-color with the system palette and DROPS box-shadow entirely, which is
// where almost every real failure comes from.
//
// Returns a fingerprint keyed by a stable path, so the Python side can pair the
// two runs element by element.
(() => {
  const path = el => {
    const parts = [];
    for (let n = el; n && n.nodeType === 1 && parts.length < 12; n = n.parentElement) {
      const p = n.parentElement;
      const i = p ? [...p.children].indexOf(n) : 0;
      parts.unshift(`${n.tagName}:${i}`);
    }
    return parts.join('/');
  };

  const FOCUSABLE = 'a[href],button,input,select,textarea,summary,[tabindex]:not([tabindex="-1"])';
  const fp = el => {
    const s = getComputedStyle(el);
    const pe = el.parentElement;
    const ps = pe ? getComputedStyle(pe) : null;
    // Sibling backgrounds, because the sharpest forced-colors loss is a
    // DISTINCTION rather than a boundary: a selected row among unselected ones, a
    // success chip among neutral ones. Both collapse to one system colour.
    const sibs = pe ? [...pe.children].filter(c => c !== el)
                        .slice(0, 12).map(c => getComputedStyle(c).backgroundColor) : [];
    return {
      pBg: ps ? ps.backgroundColor : '',
      sibBg: sibs,
      kids: el.children.length,
      bg: s.backgroundColor, color: s.color,
      bImg: s.backgroundImage === 'none' ? '' : 'yes',
      bStyle: s.borderTopStyle + ' ' + s.borderBottomStyle,
      bWidth: parseFloat(s.borderTopWidth) + parseFloat(s.borderBottomWidth),
      bColor: s.borderTopColor,
      shadow: s.boxShadow === 'none' ? '' : 'yes',
      adjust: s.forcedColorAdjust || '',
      fill: s.fill || '',
      opacity: s.opacity,
    };
  };

  const out = { mode: matchMedia('(forced-colors: active)').matches ? 'forced' : 'normal',
                elements: {}, focus: {}, optouts: [] };

  // Candidates: anything interactive, anything painting its own surface, and any
  // icon. A page of 4,000 nodes does not need sampling wholesale -- the elements
  // that can lose meaning are the ones that had some.
  const seen = new Set();
  const add = el => {
    if (seen.has(el) || seen.size > 400) return;
    seen.add(el);
    const k = path(el);
    out.elements[k] = fp(el);
    out.elements[k].tag = el.tagName.toLowerCase();
    out.elements[k].label = (el.getAttribute('aria-label')
      || (el.textContent || '').trim().slice(0, 40) || el.className.toString().slice(0, 40));
  };

  // The second run must sample the SAME elements, not re-select them. Selection
  // partly depends on "does this element's background differ from its parent's",
  // and in forced-colors every background is the one system colour -- so a
  // re-selecting second run found 3 candidates where the first found 14 and the
  // diff quietly dropped eleven elements, including every one whose boundary was
  // painted as a background. Which is the defect this probe exists to find.
  const pinned = (typeof window.__uxFcPaths !== 'undefined' && window.__uxFcPaths)
    ? window.__uxFcPaths : null;
  if (pinned) {
    const byPath = new Map();
    for (const el of document.querySelectorAll('*')) byPath.set(path(el), el);
    for (const k of pinned) {
      const el = byPath.get(k);
      if (el) add(el);
    }
  } else {
    document.querySelectorAll(FOCUSABLE).forEach(add);
    document.querySelectorAll('svg,[class*="icon"],[class*="Icon"]').forEach(add);
    for (const el of document.querySelectorAll('*')) {
      if (seen.size > 400) break;
      const s = getComputedStyle(el);
      if (s.backgroundImage !== 'none') { add(el); continue; }
      const a = s.backgroundColor.match(/[\d.]+/g);
      if (!a) continue;
      const opaque = a.length < 4 || parseFloat(a[3]) > 0.05;
      if (!opaque) continue;
      const p = el.parentElement;
      if (p && getComputedStyle(p).backgroundColor !== s.backgroundColor) add(el);
    }
  }

  // forced-color-adjust: none is an explicit opt-out of the whole mode. Sometimes
  // correct -- a colour swatch must keep its colour -- and usually a mistake.
  for (const el of document.querySelectorAll('*')) {
    if (getComputedStyle(el).forcedColorAdjust === 'none') {
      out.optouts.push({ path: path(el), tag: el.tagName.toLowerCase(),
                         label: (el.textContent || '').trim().slice(0, 40) });
      if (out.optouts.length > 20) break;
    }
  }

  // Focus indicators, measured focused. A ring built from box-shadow simply does
  // not exist in this mode, and that is the single most common forced-colors
  // failure in modern CSS -- Tailwind's `ring-*` utilities are box-shadow.
  const active = document.activeElement;
  const focusables = [...document.querySelectorAll(FOCUSABLE)].slice(0, 40);
  for (const el of focusables) {
    try { el.focus({ preventScroll: true }); } catch (e) { continue; }
    if (document.activeElement !== el) continue;
    const s = getComputedStyle(el);
    out.focus[path(el)] = {
      outlineStyle: s.outlineStyle,
      outlineWidth: parseFloat(s.outlineWidth) || 0,
      outlineColor: s.outlineColor,
      shadow: s.boxShadow === 'none' ? '' : 'yes',
      label: (el.getAttribute('aria-label') || (el.textContent || '').trim().slice(0, 36)
              || el.tagName.toLowerCase()),
    };
  }
  try { if (active && active.focus) active.focus({ preventScroll: true }); } catch (e) {}

  out.probe = 'forcedcolors';
  out.counts = { elements: Object.keys(out.elements).length,
                 focus: Object.keys(out.focus).length,
                 optouts: out.optouts.length };
  return JSON.stringify(out);
})()
