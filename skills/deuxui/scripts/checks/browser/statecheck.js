// R-STATE-ERROR / R-STATE-EMPTY / R-STATE-OFFLINE / R-STATE-SLOW.
// Run AFTER forcing a condition (aborted request, empty payload, offline,
// throttled). The question is never "did it crash" -- it is "does the interface
// tell the truth about what just happened, and offer a way out".
(() => {
  const visible = el => {
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' &&
           s.display !== 'none' && +s.opacity > 0.05;
  };
  const text = [...document.querySelectorAll('body *')]
    .filter(visible)
    .map(e => (e.childElementCount === 0 ? e.textContent : '') || '')
    .join(' ').replace(/\s+/g, ' ').trim();

  const spinners = [...document.querySelectorAll(
      '[class*=spin],[class*=Spin],[class*=loader],[class*=Loader],[class*=skeleton],' +
      '[class*=Skeleton],[role=progressbar],[aria-busy=true]')].filter(visible);

  const live = [...document.querySelectorAll(
      '[role=alert],[role=status],[aria-live=polite],[aria-live=assertive]')]
      .filter(visible)
      .map(e => e.textContent.trim().slice(0, 120)).filter(Boolean);

  const ERROR_WORDS = /\b(couldn.t|unable|failed|error|problem|went wrong|try again|retry|offline|no connection|reconnect)\b/i;
  const EMPTY_WORDS = /\b(no results|nothing here|no items|no data|empty|get started|add your first|create your first|none yet)\b/i;
  const ACTION = [...document.querySelectorAll('button,a[href],[role=button]')]
      .filter(visible)
      .filter(e => /\b(retry|try again|reload|refresh|add|create|new|back|contact)\b/i
                     .test(e.textContent || e.getAttribute('aria-label') || ''))
      .map(e => (e.textContent || '').trim().slice(0, 40));

  return {
    probe: 'state',
    visible_text_length: text.length,
    mentions_failure: ERROR_WORDS.test(text),
    mentions_empty: EMPTY_WORDS.test(text),
    live_region_messages: live,
    visible_spinners: spinners.length,
    recovery_actions: ACTION.slice(0, 8),
    looks_blank: text.length < 40 && spinners.length === 0,
    stuck_spinner: spinners.length > 0 && !ERROR_WORDS.test(text),
    excerpt: text.slice(0, 300)
  };
})()
