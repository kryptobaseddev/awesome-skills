// R-CONTRAST -- contrast of actually rendered text against its actual painted
// backdrop, walking up through transparent ancestors. NUM-001 / NUM-002.
(() => {
  const lin = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);

  // Colour parsing, by format, refusing to guess.
  //
  // This used to be `s.match(/[\d.]+/g).slice(0,3)` treated as sRGB 0-255, which
  // is correct for rgb() and catastrophic for everything else: Chrome serves
  // lab() and oklch() from getComputedStyle, so lab(37.88 37.17 52.27) was read
  // as rgb(37,37,52) and amber-800 on amber-50 was reported at 1.1:1 when it is
  // really 6.84:1. Eight "severe" failures on one page, every one an artifact.
  // A checker that invents failures is worse than one that reports nothing, so an
  // unrecognised format now returns null and is counted as unmeasured.
  const clamp255 = v => Math.max(0, Math.min(255, Math.round(v)));
  const gam = c => { const a = Math.abs(c); const v = a <= 0.0031308
      ? 12.92 * a : 1.055 * Math.pow(a, 1 / 2.4) - 0.055; return clamp255(Math.sign(c) * v * 255); };
  const oklabToRgb = (L, a, b) => {
    const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
    const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
    const s_ = L - 0.0894841775 * a - 1.2914855480 * b;
    const l = l_ ** 3, m = m_ ** 3, sK = s_ ** 3;
    return [gam(+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * sK),
            gam(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * sK),
            gam(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * sK)];
  };
  // CIE Lab is D50-referred. Round-trips pixel-exact against the Python
  // implementation in checks/_util.py for amber-800, amber-50, blue, ink, white
  // and red-300 -- that equivalence is the test, not the formula's looks.
  const labToRgb = (L, A, B) => {
    const k = 24389 / 27, e = 216 / 24389;
    const fy = (L + 16) / 116, fx = fy + A / 500, fz = fy - B / 200;
    const xr = fx ** 3 > e ? fx ** 3 : (116 * fx - 16) / k;
    const yr = L > k * e ? fy ** 3 : L / k;
    const zr = fz ** 3 > e ? fz ** 3 : (116 * fz - 16) / k;
    const X = xr * 0.9642956764295677, Y = yr, Z = zr * 0.8251046025104602;
    return [gam(3.1341359569958707 * X - 1.6173863321612538 * Y - 0.4906619460083532 * Z),
            gam(-0.9787795029126160 * X + 1.9161404439944446 * Y + 0.0334968639352926 * Z),
            gam(0.0719553798841168 * X - 0.2289909920330008 * Y + 1.4052137177337440 * Z)];
  };
  let unparsed = 0;
  const nums = str => (str.match(/-?[\d.]+%?/g) || []).map(t =>
    t.endsWith('%') ? parseFloat(t) : parseFloat(t));
  const pct = (t, scale) => (String(t).endsWith('%') ? parseFloat(t) / 100 * scale : parseFloat(t));

  // Returns {rgb:[r,g,b], a:number} or null when the format is not understood.
  const color = raw => {
    if (!raw) return null;
    const s = String(raw).trim().toLowerCase();
    if (s === 'transparent') return { rgb: [0, 0, 0], a: 0 };
    if (s === 'currentcolor' || s.startsWith('var(')) return null;
    let m;
    if ((m = s.match(/^#([0-9a-f]{3,8})$/))) {
      const h = m[1];
      const ex = h.length <= 4 ? h.split('').map(c => c + c).join('') : h;
      const v = i => parseInt(ex.slice(i * 2, i * 2 + 2), 16);
      return { rgb: [v(0), v(1), v(2)], a: ex.length === 8 ? v(3) / 255 : 1 };
    }
    if ((m = s.match(/^rgba?\(([^)]*)\)$/))) {
      const parts = m[1].split(/[,/\s]+/).filter(Boolean);
      if (parts.length < 3) { unparsed++; return null; }
      const rgb = parts.slice(0, 3).map(t => clamp255(pct(t, 255)));
      return { rgb, a: parts[3] !== undefined ? pct(parts[3], 1) : 1 };
    }
    if ((m = s.match(/^(oklab|lab|oklch|lch)\(([^)]*)\)$/))) {
      const kind = m[1];
      const parts = m[2].split(/[,/\s]+/).filter(Boolean);
      if (parts.length < 3) { unparsed++; return null; }
      const a = parts[3] !== undefined ? pct(parts[3], 1) : 1;
      let L = parseFloat(parts[0]);
      if (String(parts[0]).endsWith('%')) L = L / 100 * (kind.startsWith('ok') ? 1 : 100);
      const c2 = parseFloat(parts[1]), h = parseFloat(parts[2]);
      if (kind === 'oklab') return { rgb: oklabToRgb(L, c2, h), a };
      if (kind === 'lab') return { rgb: labToRgb(L, c2, h), a };
      const rad = (h * Math.PI) / 180, A = c2 * Math.cos(rad), B = c2 * Math.sin(rad);
      return kind === 'oklch' ? { rgb: oklabToRgb(L, A, B), a } : { rgb: labToRgb(L, A, B), a };
    }
    if ((m = s.match(/^color\(srgb\s+([^)]*)\)$/))) {
      const parts = m[1].split(/[,/\s]+/).filter(Boolean);
      if (parts.length < 3) { unparsed++; return null; }
      return { rgb: parts.slice(0, 3).map(t => clamp255(pct(t, 1) * 255)),
               a: parts[3] !== undefined ? pct(parts[3], 1) : 1 };
    }
    unparsed++;                      // a gamut or space this probe cannot convert
    return null;
  };
  const parse = s => { const c = color(s); return c && c.a > 0 ? c.rgb : (c ? c.rgb : null); };
  const alpha = s => { const c = color(s); return c ? c.a : 1; };
  const over = (fg, bg, a) => fg.map((c, i) => c * a + bg[i] * (1 - a));
  // What is actually painted behind this text.
  //
  // An ancestor walk is the obvious implementation and it is wrong on real pages.
  // A hero whose gradient is painted by an absolutely positioned SIBLING --
  // `<div class="absolute inset-0 bg-gradient-to-br">` behind `<div
  // class="relative">text</div>`, which is how every Tailwind hero is built --
  // has an ancestor chain that ends at an opaque white section. The walk
  // therefore resolved white, the text was white, and the probe reported 1:1 for
  // fifteen headings anyone can read. Flagging them as unjudged was not enough
  // either: `resolved` was true, because an opaque ancestor genuinely existed.
  //
  // So ask the browser. elementsFromPoint returns the whole stack at a point in
  // paint order, siblings included, which is the only thing that actually knows
  // what is behind this text. The ancestor walk survives as the fallback for
  // elements the hit test cannot locate.
  const ancestorBackdrop = el => {
    let n = el;
    while (n && n !== document.documentElement) {
      const s = getComputedStyle(n), c = parse(s.backgroundColor), a = alpha(s.backgroundColor);
      if (s.backgroundImage !== 'none') return { rgb: [255, 255, 255], image: true, resolved: false };
      if (c && a >= 0.99) return { rgb: c, image: false, resolved: true };
      n = n.parentElement;
    }
    const root = getComputedStyle(document.documentElement);
    if (root.backgroundImage !== 'none') return { rgb: [255, 255, 255], image: true, resolved: false };
    const rc = parse(root.backgroundColor), ra = alpha(root.backgroundColor);
    if (rc && ra >= 0.99) return { rgb: rc, image: false, resolved: true };
    return { rgb: [255, 255, 255], image: false, resolved: false };
  };

  const backdrop = el => {
    const r = el.getBoundingClientRect();
    const x = Math.round(Math.min(Math.max(r.left + Math.min(r.width / 2, 40), 1),
                                  innerWidth - 2));
    const y = Math.round(Math.min(Math.max(r.top + r.height / 2, 1), innerHeight - 2));
    let stack;
    try { stack = document.elementsFromPoint(x, y); } catch (e) { stack = null; }
    if (!stack || !stack.length) return ancestorBackdrop(el);
    let i = stack.indexOf(el);
    if (i < 0) {
      // The text's own box may not be the hit target (inline wrappers, pointer
      // events). Start from its nearest ancestor that IS in the stack.
      for (let n = el.parentElement; n; n = n.parentElement) {
        const j = stack.indexOf(n);
        if (j >= 0) { i = j; break; }
      }
    }
    if (i < 0) return ancestorBackdrop(el);
    let acc = null;
    for (let k = i; k < stack.length; k++) {
      const s = getComputedStyle(stack[k]);
      if (s.visibility === 'hidden' || +s.opacity === 0) continue;
      if (s.backgroundImage !== 'none') {
        return { rgb: [255, 255, 255], image: true, resolved: false };
      }
      const c = parse(s.backgroundColor), a = alpha(s.backgroundColor);
      if (!c || a <= 0) continue;
      // A partially transparent layer tints whatever is under it; keep going and
      // composite once something opaque turns up.
      if (a >= 0.99) return { rgb: acc ? over(acc, c, 1) : c, image: false, resolved: true };
      acc = acc ? over(acc, c, a) : c.map((v, idx) => v * a + 255 * (1 - a));
    }
    return ancestorBackdrop(el);
  };
  const out = [], unjudged = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  let node;
  while ((node = walk.nextNode())) {
    const t = node.textContent.trim();
    if (t.length < 2) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    seen.add(el);
    let r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    // elementsFromPoint only sees the viewport, so bring the candidate into it.
    // `center` also keeps it clear of sticky top and bottom bars, which would
    // otherwise be measured as its backdrop.
    if (r.bottom < 0 || r.top > innerHeight) {
      try { el.scrollIntoView({ block: 'center', inline: 'nearest' }); } catch (e) {}
      r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
    }
    const s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
    let fg = parse(s.color); if (!fg) continue;
    const bd = backdrop(el);
    if (!bd.resolved) {
      // Not a pass and not a failure. R-PIXEL-CONTRAST is what would settle it.
      // Record the page-absolute box so R-PIXEL-CONTRAST can find these runs in
      // a full-page screenshot. Without the coordinates the honest "unmeasured"
      // verdict has no route to ever becoming a measurement.
      const px0 = parseFloat(s.fontSize);
      unjudged.push({ text: t.slice(0, 48), color: s.color,
                      fontPx: +px0.toFixed(1),
                      large: px0 >= 24 || (+s.fontWeight >= 700 && px0 >= 18.66),
                      need: (px0 >= 24 || (+s.fontWeight >= 700 && px0 >= 18.66)) ? 3 : 4.5,
                      box: { x: Math.round(r.left + scrollX), y: Math.round(r.top + scrollY),
                             w: Math.round(r.width), h: Math.round(r.height) },
                      dpr: devicePixelRatio,
                      reason: bd.image ? 'backdrop is an image or gradient'
                                       : 'no opaque background found in the paint stack' });
      continue;
    }
    // Translucent text over a known opaque backdrop IS computable: composite it.
    // Judging rgba(255,255,255,0.8) as if it were opaque white overstates the
    // contrast, which is the error that matters in this direction.
    const fa = alpha(s.color);
    if (fa < 0.99) fg = over(fg, bd.rgb, fa);
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
  return { probe: 'contrast', examined: seen.size, failures: out.slice(0, 60),
           unparsed, unjudged: unjudged.slice(0, 40), unjudged_count: unjudged.length };
})()
