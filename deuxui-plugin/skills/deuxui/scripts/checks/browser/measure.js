// R-MEASURE -- characters per line as actually rendered (NUM-016).
// A declared max-width tells you the intent; only layout tells you the result,
// because font, size and container all move it.
(() => {
  const vis = el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 40 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const probe = document.createElement('span');
  probe.style.cssText = 'position:absolute;visibility:hidden;white-space:pre';
  document.body.appendChild(probe);

  const out = [];
  for (const el of document.querySelectorAll('p, li, blockquote, dd, .prose *')) {
    if (!vis(el)) continue;
    const text = (el.textContent || '').trim();
    if (text.length < 80) continue;          // too short to have a measure problem
    const s = getComputedStyle(el);
    probe.style.font = s.font || `${s.fontSize} ${s.fontFamily}`;
    // a representative lowercase sample beats "0" for average advance width
    probe.textContent = 'abcdefghijklmnopqrstuvwxyz ';
    const avg = probe.getBoundingClientRect().width / 27;
    if (!avg || !isFinite(avg)) continue;
    const contentWidth = el.getBoundingClientRect().width
      - parseFloat(s.paddingLeft || 0) - parseFloat(s.paddingRight || 0);
    const ch = Math.round(contentWidth / avg);
    if (ch > 80) {
      out.push({ ch, tag: el.tagName.toLowerCase(),
                 fontPx: Math.round(parseFloat(s.fontSize)),
                 text: text.slice(0, 48) });
    }
  }
  probe.remove();
  return { probe: 'measure', examined: out.length, too_wide: out.slice(0, 20) };
})()
