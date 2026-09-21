// R-MOTION -- with reduced motion requested, is anything still moving?
// LAY-010, A11Y-010. Emulate the preference first (agent-browser set media).
(() => {
  const moving = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    const animated = s.animationName !== 'none' &&
                     parseFloat(s.animationDuration) > 0.01;
    const transitioned = parseFloat(s.transitionDuration) > 0.15;
    if (animated || transitioned) {
      moving.push({ tag: el.tagName.toLowerCase(),
                    cls: (el.className || '').toString().slice(0, 50),
                    animation: s.animationName, duration: s.animationDuration,
                    transition: s.transitionDuration });
    }
    if (moving.length >= 30) break;
  }
  return { probe: 'motion',
           honours_reduced_motion: matchMedia('(prefers-reduced-motion: reduce)').matches,
           still_moving: moving };
})()
