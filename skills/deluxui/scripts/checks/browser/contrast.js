// R-CONTRAST -- contrast of actually rendered text against its actual painted
// backdrop, walking up through transparent ancestors. NUM-001 / NUM-002.
(() => {
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  const parse = s => { const m = s.match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : null; };
  const alpha = s => { const m = s.match(/rgba?\([^)]*?,\s*([\d.]+)\s*\)/); return m ? +m[1] : 1; };
  const over = (fg, bg, a) => fg.map((c, i) => c * a + bg[i] * (1 - a));
  const backdrop = el => {
    let n = el, acc = null;
    while (n && n !== document.documentElement) {
      const s = getComputedStyle(n), c = parse(s.backgroundColor), a = alpha(s.backgroundColor);
      if (s.backgroundImage !== 'none') return { rgb: acc || [255, 255, 255], image: true };
      if (c && a > 0) { acc = acc ? over(acc, c, 1) : c; if (a >= 0.99) return { rgb: c, image: false }; }
      n = n.parentElement;
    }
    return { rgb: acc || [255, 255, 255], image: false };
  };
  const out = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  let node;
  while ((node = walk.nextNode())) {
    const t = node.textContent.trim();
    if (t.length < 2) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
    const fg = parse(s.color); if (!fg) continue;
    const bd = backdrop(el);
    const L1 = lum(fg), L2 = lum(bd.rgb);
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(s.fontSize);
    const bold = +s.fontWeight >= 700;
    const large = px >= 24 || (bold && px >= 18.66);
    const need = large ? 3 : 4.5;
    if (ratio + 0.005 < need) {
      out.push({ text: t.slice(0, 48), ratio: +ratio.toFixed(2), need,
                 fontPx: +px.toFixed(1), large, color: s.color,
                 backdrop_has_image: bd.image });
    }
  }
  return { probe: 'contrast', examined: seen.size, failures: out.slice(0, 60) };
})()
