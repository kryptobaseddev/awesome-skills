// R-ZOOM (NUM-008, 200% text) and R-TEXTSPACING (NUM-010, SC 1.4.12 overrides).
// Both criteria are about surviving a user's own settings. Apply the override,
// then look for content that got clipped or pushed off screen.
(() => {
  const mode = window.__uxMode;           // "zoom" | "spacing"
  const style = document.createElement('style');
  style.id = '__ux_probe_style';
  style.textContent = mode === 'zoom'
    ? ':root{font-size:200% !important}'
    : `*,*::before,*::after{line-height:1.5 !important;letter-spacing:0.12em !important;
       word-spacing:0.16em !important} p{margin-bottom:2em !important}`;
  document.getElementById('__ux_probe_style')?.remove();
  document.head.appendChild(style);
  void document.body.offsetHeight;        // force reflow

  const vw = document.documentElement.clientWidth;
  const clipped = [], off = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const s = getComputedStyle(el);
    const hidesOverflow = /hidden|clip/.test(s.overflow + s.overflowX + s.overflowY);
    if (hidesOverflow && (el.scrollHeight > el.clientHeight + 2 ||
                          el.scrollWidth > el.clientWidth + 2)) {
      clipped.push({ tag: el.tagName.toLowerCase(),
                     cls: (el.className || '').toString().slice(0, 50),
                     text: (el.textContent || '').trim().slice(0, 40) });
    }
    if (r.right > vw + 1) {
      off.push({ tag: el.tagName.toLowerCase(),
                 cls: (el.className || '').toString().slice(0, 50) });
    }
  }
  style.remove();
  return { probe: mode === 'zoom' ? 'zoom' : 'textspacing',
           viewport: vw, clipped: clipped.slice(0, 20), overflowing: off.slice(0, 20) };
})()
