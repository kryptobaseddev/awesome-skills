async () => {
  // ux-laws in-page probe. Read-only: measures the rendered page at the CURRENT viewport and returns JSON.
  // Paste this function as-is into any browser tool that evaluates a function (Playwright MCP
  // browser_evaluate, Puppeteer page.evaluate), or wrap it as `(${source})()` for tools that take an
  // expression (Chrome javascript_tool, agent-browser eval, DevTools console). walk.mjs does that for you.
  //
  // Every number here is a measurement of what rendered, not a judgement. The thresholds that turn these
  // into pass/fail live in scorecard.py and references/metrics.md.
  const vw = document.documentElement.clientWidth
  const vh = window.innerHeight
  const coarse = matchMedia('(pointer: coarse)').matches || vw < 768
  const out = { url: location.href, title: document.title, viewport: { w: vw, h: vh, dpr: devicePixelRatio, coarse } }

  const visible = (el) => {
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.height === 0) return false
    const cs = getComputedStyle(el)
    return cs.visibility !== 'hidden' && cs.display !== 'none' && Number(cs.opacity) > 0.05
  }
  const sel = (el) => {
    if (el.id) return `#${el.id}`
    const cls = (el.className && typeof el.className === 'string') ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : ''
    const txt = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim().slice(0, 40)
    return `${el.tagName.toLowerCase()}${cls}${txt ? ` "${txt}"` : ''}`
  }
  const nameOf = (el) => (el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || el.value || el.getAttribute('alt') || '').trim()

  // --- reflow (WCAG 1.4.10): nothing should force horizontal scroll -----------------------------
  const scrollW = document.documentElement.scrollWidth
  const overflowers = []
  if (scrollW > vw + 1) {
    // an element inside a horizontal scroller is contained by it - unless it is absolutely positioned and its
    // containing block sits outside the scroller (the classic sr-only / badge escape that widens the page)
    const containedByScroller = (el) => {
      let escaping = ['absolute', 'fixed'].includes(getComputedStyle(el).position)
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const cs = getComputedStyle(p)
        if (cs.overflowX !== 'visible') return !escaping
        if (escaping && cs.position !== 'static') escaping = false
      }
      return false
    }
    for (const el of document.body.querySelectorAll('*')) {
      const r = el.getBoundingClientRect()
      if (r.right > vw + 1 && (r.width > 0 || r.height > 0) && !containedByScroller(el) && getComputedStyle(el).position !== 'fixed') {
        // report the outermost offender only
        let p = el.parentElement, nested = false
        while (p && p !== document.body) { if (p.getBoundingClientRect().right > vw + 1) { nested = true; break } p = p.parentElement }
        if (!nested) overflowers.push({ el: sel(el), right: Math.round(r.right), width: Math.round(r.width) })
        if (overflowers.length >= 15) break
      }
    }
  }
  out.reflow = { scrollWidth: scrollW, horizontalOverflow: scrollW > vw + 1, overflowers }

  // --- targets (Fitts; WCAG 2.5.8 minimum 24x24 CSS px, 44 px recommended for touch) -------------
  const interactiveSel = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=link], [role=tab], [role=menuitem], [role=checkbox], [role=switch], [tabindex]:not([tabindex="-1"])'
  const interactive = [...document.querySelectorAll(interactiveSel)].filter(visible)
  const small24 = [], small44 = [], unnamed = []
  for (const el of interactive) {
    // an input wrapped by its label is hit through the label box
    const wrapLabel = el.matches('input, select, textarea') && el.closest('label')
    const r = (wrapLabel || el).getBoundingClientRect()
    const inlineLink = el.tagName === 'A' && getComputedStyle(el).display === 'inline' && el.closest('p, li, td')
    const w = Math.round(r.width), h = Math.round(r.height)
    if (!inlineLink) {
      if (w < 24 || h < 24) small24.push({ el: sel(el), w, h })
      else if (coarse && (w < 44 || h < 44)) small44.push({ el: sel(el), w, h })
    }
    if (!nameOf(el) && !el.labels?.length && !el.getAttribute('aria-labelledby')) unnamed.push(sel(el))
  }
  out.targets = { interactive: interactive.length, below24: small24.length, below44: small44.length, samples24: small24.slice(0, 15), samples44: small44.slice(0, 15), unnamed: unnamed.length, unnamedSamples: unnamed.slice(0, 10) }

  // --- form fields: labels, iOS focus-zoom (<16px), autocomplete, input types ------------------
  const fields = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=checkbox]):not([type=radio]), select, textarea')].filter(visible)
  const unlabeled = [], zoomy = [], typeHints = []
  for (const f of fields) {
    const labelled = f.labels?.length || f.getAttribute('aria-label') || f.getAttribute('aria-labelledby')
    if (!labelled) unlabeled.push(sel(f))
    if (parseFloat(getComputedStyle(f).fontSize) < 16) zoomy.push({ el: sel(f), fontSize: getComputedStyle(f).fontSize })
    const hint = `${f.name} ${f.id} ${f.placeholder}`.toLowerCase()
    if (f.tagName === 'INPUT' && (f.type === 'text' || !f.getAttribute('type'))) {
      if (/e-?mail/.test(hint)) typeHints.push({ el: sel(f), want: 'type=email' })
      else if (/phone|tel/.test(hint)) typeHints.push({ el: sel(f), want: 'type=tel' })
      else if (/zip|postal|card|cvc|cvv|otp|code/.test(hint) && !f.inputMode) typeHints.push({ el: sel(f), want: 'inputmode=numeric' })
    }
  }
  const forms = [...document.querySelectorAll('form')].filter(visible).map((f) => ({
    el: sel(f),
    fields: [...f.querySelectorAll('input:not([type=hidden]), select, textarea')].filter(visible).length,
    autocomplete: [...f.querySelectorAll('input[autocomplete]')].length,
  }))
  out.fields = { count: fields.length, unlabeled: unlabeled.length, unlabeledSamples: unlabeled.slice(0, 10), below16px: zoomy.length, below16Samples: zoomy.slice(0, 10), typeHints: typeHints.slice(0, 10), forms }

  // --- primary actions in the first viewport (Hick, Von Restorff) -----------------------------
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(',').map((x) => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 } }
  const sat = (c) => { const mx = Math.max(c.r, c.g, c.b), mn = Math.min(c.r, c.g, c.b); return mx === 0 ? 0 : (mx - mn) / mx }
  const filled = []
  for (const el of interactive) {
    if (!(el.tagName === 'BUTTON' || el.getAttribute('role') === 'button' || el.tagName === 'A')) continue
    const r = el.getBoundingClientRect()
    if (r.top > vh || r.bottom < 0) continue
    const cs = getComputedStyle(el)
    const bg = parse(cs.backgroundColor)
    const hasGrad = cs.backgroundImage && cs.backgroundImage.includes('gradient')
    if (hasGrad || (bg && bg.a > 0.5 && sat(bg) > 0.35)) filled.push({ el: sel(el), gradient: !!hasGrad })
  }
  out.primaryActions = { firstViewportFilled: filled.length, samples: filled.slice(0, 10) }

  // --- headings and landmarks ------------------------------------------------------------------
  const hs = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')].filter(visible).map((h) => Number(h.tagName[1]))
  let skips = 0
  for (let i = 1; i < hs.length; i++) if (hs[i] > hs[i - 1] + 1) skips++
  const navLinks = [...document.querySelectorAll('header nav a, nav[aria-label] a, header a, [role=navigation] a')].filter((a) => visible(a) && !a.closest('footer, [role=contentinfo]'))
  out.structure = {
    h1: hs.filter((h) => h === 1).length, headingSkips: skips, headings: hs.length,
    landmarks: { main: !!document.querySelector('main,[role=main]'), nav: !!document.querySelector('nav,[role=navigation]'), header: !!document.querySelector('header'), footer: !!document.querySelector('footer') },
    topNavLinks: new Set(navLinks.map((a) => a.href + '|' + nameOf(a))).size,
    imagesMissingAlt: [...document.querySelectorAll('img')].filter((i) => visible(i) && !i.hasAttribute('alt')).length,
    lang: document.documentElement.lang || null,
    viewportMeta: document.querySelector('meta[name=viewport]')?.getAttribute('content') || null,
  }

  // --- text: contrast (WCAG 1.4.3 approximation), tiny text, line length -----------------------
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b) }
  const bgOf = (el) => {
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n)
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null // image/gradient: cannot measure reliably
      const b = parse(cs.backgroundColor)
      if (b && b.a > 0.9) return b
    }
    return { r: 255, g: 255, b: 255, a: 1 }
  }
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: (t) => t.textContent.trim().length > 1 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT })
  const lowContrast = [], tiny = [], wide = []
  let measured = 0, unmeasurable = 0
  const seenEls = new Set()
  while (walker.nextNode() && measured + unmeasurable < 600) {
    const el = walker.currentNode.parentElement
    if (!el || seenEls.has(el) || !visible(el)) continue
    seenEls.add(el)
    const cs = getComputedStyle(el)
    const size = parseFloat(cs.fontSize), weight = Number(cs.fontWeight) || 400
    if (size < 12) tiny.push({ el: sel(el), fontSize: cs.fontSize })
    // text painted over a photo, video or canvas (an overlay caption) cannot be measured from CSS alone
    const rr = el.getBoundingClientRect()
    const stack = rr.width && rr.height && rr.top < vh && rr.bottom > 0 ? document.elementsFromPoint(Math.min(vw - 1, rr.left + rr.width / 2), Math.min(vh - 1, Math.max(0, rr.top + rr.height / 2))) : []
    const overMedia = stack.some((n) => !n.contains(el) && !el.contains(n) && (n.matches('img, video, canvas, picture, svg') || getComputedStyle(n).backgroundImage.includes('url(')))
    const fg = parse(cs.color), bg = overMedia ? null : bgOf(el)
    if (!fg || !bg) { unmeasurable++; continue }
    measured++
    const L1 = lum(fg), L2 = lum(bg)
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05)
    const large = size >= 24 || (size >= 18.66 && weight >= 700)
    if (ratio < (large ? 3 : 4.5)) lowContrast.push({ el: sel(el), ratio: Math.round(ratio * 100) / 100, fontSize: cs.fontSize })
    if (el.tagName === 'P' && el.getBoundingClientRect().width / (size * 0.5) > 90) wide.push(sel(el))
  }
  out.text = { measured, unmeasurable, lowContrast: lowContrast.length, lowContrastSamples: lowContrast.slice(0, 15), below12px: tiny.length, tinySamples: tiny.slice(0, 10), overlongLines: wide.length }

  // --- runtime system sprawl: how many distinct values actually render (Similarity, Prägnanz) --
  const fam = new Set(), sizes = new Set(), colors = new Set(), bgs = new Set(), radii = new Set(), shadows = new Set(), spacing = new Set()
  let gradients = 0
  const all = [...document.body.querySelectorAll('*')].filter(visible).slice(0, 4000)
  for (const el of all) {
    const cs = getComputedStyle(el)
    if (el.childNodes.length && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) {
      fam.add(cs.fontFamily.split(',')[0].replace(/["']/g, '').trim())
      sizes.add(cs.fontSize)
      colors.add(cs.color)
    }
    if (cs.backgroundColor !== 'rgba(0, 0, 0, 0)') bgs.add(cs.backgroundColor)
    if (cs.backgroundImage.includes('gradient')) gradients++
    if (cs.borderRadius !== '0px') radii.add(cs.borderRadius)
    if (cs.boxShadow !== 'none') shadows.add(cs.boxShadow)
    for (const k of ['paddingTop', 'paddingLeft', 'marginTop', 'rowGap', 'columnGap']) { const v = cs[k]; if (v && v !== '0px' && v !== 'normal') spacing.add(v) }
  }
  out.system = {
    fontFamilies: [...fam], fontSizes: sizes.size, fontSizeList: [...sizes].sort((a, b) => parseFloat(a) - parseFloat(b)),
    textColors: colors.size, backgroundColors: bgs.size, radii: radii.size, radiusList: [...radii].slice(0, 20), shadows: shadows.size, spacingValues: spacing.size, gradientElements: gradients,
  }

  // --- fixed/sticky chrome eating the viewport (mobile) -----------------------------------------
  let fixedArea = 0
  for (const el of all) {
    const pos = getComputedStyle(el).position
    if (pos === 'fixed' || pos === 'sticky') {
      const r = el.getBoundingClientRect()
      const h = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0)), w = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0))
      if (h * w < vw * vh * 0.95) fixedArea += h * w // ignore full-screen overlays (those are modals)
    }
  }
  out.chrome = { fixedViewportShare: Math.round((fixedArea / (vw * vh)) * 100) / 100 }

  // --- hover-only affordances (no hover on touch) -----------------------------------------------
  let hoverOnlyRules = 0
  try {
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules } catch { continue }
      for (const r of rules) {
        const t = r.cssText || ''
        if (/:hover[^{]*\{[^}]*(display\s*:\s*(block|flex|inline)|opacity\s*:\s*1|visibility\s*:\s*visible)/.test(t) && !(r.parentRule && /hover\s*:\s*hover/.test(r.parentRule.conditionText || r.parentRule.media?.mediaText || ''))) hoverOnlyRules++
      }
    }
  } catch {}
  out.hover = { revealOnHoverRulesNotGuarded: hoverOnlyRules }

  // --- copy tells (template filler; Mental Model, Peak-End) ------------------------------------
  // --- taste tells that are mechanical enough to count (judgement still needs the screenshots) ---------
  const visibleText = [...document.querySelectorAll('body *')].filter((el) => visible(el) && [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
  const eyebrows = visibleText.filter((el) => { const cs = getComputedStyle(el); return cs.textTransform === 'uppercase' && parseFloat(cs.letterSpacing) >= 1 && parseFloat(cs.fontSize) <= 14 }).length
  const hueOf = (c) => { const { r, g, b } = c; const mx = Math.max(r, g, b), mn = Math.min(r, g, b); if (mx === mn) return null
    let h = mx === r ? (g - b) / (mx - mn) : mx === g ? 2 + (b - r) / (mx - mn) : 4 + (r - g) / (mx - mn); h = (h * 60 + 360) % 360; return Math.round(h / 30) }
  const accentHues = new Set()
  for (const el of interactive) { for (const prop of ['backgroundColor', 'color', 'borderTopColor']) { const c = parse(getComputedStyle(el)[prop]); if (c && c.a > 0.5 && sat(c) > 0.45) { const h = hueOf(c); if (h !== null) accentHues.add(h) } } }
  const textAll = document.body.innerText
  out.taste = {
    emDashes: (textAll.match(/[\u2014\u2013]/g) || []).length,
    emoji: (textAll.match(/\p{Extended_Pictographic}/gu) || []).length,
    eyebrows,
    accentHues: accentHues.size,
    radii: out.system ? out.system.radii : null,
  }
  const body = document.body.innerText
  const tells = ['Welcome back', 'Get started', 'Learn more', 'Build the future', 'all in one place', 'An error occurred', 'Something went wrong', 'Lorem ipsum', 'Submit', 'Success!', 'Click here']
  out.copy = { tells: tells.filter((t) => body.toLowerCase().includes(t.toLowerCase())), words: body.split(/\s+/).filter(Boolean).length }

  // --- lab performance of THIS load (one sample, not field p75): LCP, CLS, navigation timing ----
  const observe = (type) => new Promise((res) => {
    const entries = []
    try {
      const po = new PerformanceObserver((l) => entries.push(...l.getEntries()))
      po.observe({ type, buffered: true })
      setTimeout(() => { po.disconnect(); res(entries) }, 150)
    } catch { res(null) }
  })
  const [lcpE, clsE] = await Promise.all([observe('largest-contentful-paint'), observe('layout-shift')])
  const nav = performance.getEntriesByType('navigation')[0]
  out.perf = {
    lcpMs: lcpE && lcpE.length ? Math.round(lcpE[lcpE.length - 1].startTime) : null,
    cls: clsE ? Math.round(clsE.filter((e) => !e.hadRecentInput).reduce((a, e) => a + e.value, 0) * 1000) / 1000 : null,
    ttfbMs: nav ? Math.round(nav.responseStart) : null,
    domContentLoadedMs: nav ? Math.round(nav.domContentLoadedEventEnd) : null,
    transferKb: nav ? Math.round((nav.transferSize || 0) / 1024) : null,
    note: 'single lab load; Core Web Vitals thresholds apply to field p75 - treat as a lead',
  }

  return out
}
