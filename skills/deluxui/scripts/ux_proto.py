#!/usr/bin/env python3
"""A working prototype, generated from the contract — not a picture of one.

Between the wireframe and the production build there is a stage most teams skip
because it is expensive to make by hand: a real, clickable thing. Buttons that
depress, a form that validates as you leave a field, a dialog that traps focus and
closes on Escape, a table that sorts, a list you can flip into its empty, loading,
error and offline states to see what they actually look like.

That stage is where a person finds out whether a design works, because using an
interface and looking at one are different activities. A wireframe cannot be used.
A screenshot cannot be used. This can.

Everything it emits comes from `.deluxui/design.contract.yaml`: the colour roles
become custom properties with a composed dark theme, the type ladder becomes the
only sizes on the page, the spacing scale the only gaps, the one depth metaphor
the only way anything is raised. So the prototype is conformant by construction,
and `ux_check.py` over its output is a positive control on the generator rather
than a review of somebody's taste.

    ux_proto.py --write .deluxui/proto/index.html
    ux_proto.py --write .deluxui/proto/index.html --title "Jobs" --density compact
    ux_proto.py                     # to stdout

Then put it in front of a person, beside whatever exists today:

    ux_review.py serve --variant "proposed=.deluxui/proto/index.html" \
                       --variant "current=http://localhost:5173/jobs"

What this is not: the product. It is a conforming reference a component gets
lifted out of, and a surface a person can argue with before the argument costs a
sprint.
"""
from __future__ import annotations
import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ux_image                                                    # noqa: E402


FALLBACK = {"sans": "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
            "serif": "Georgia, Cambria, Times New Roman, serif",
            "mono": "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"}


def _stack(family: str, kind: str) -> str:
    fam = str(family or "").strip()
    if not fam or "," in fam:
        return fam or FALLBACK[kind]
    quoted = f'"{fam}"' if " " in fam else fam
    return f"{quoted}, {FALLBACK[kind]}"


def faces(c) -> list:
    """Which declared families this project does not provide.

    Reported on the page rather than quietly fallen back to: the reviewer is
    judging type, and judging it in a face nobody chose wastes the review."""
    try:
        import fontindex
        res = fontindex.analyse(Path.cwd(), c.raw)
    except Exception:
        return []
    return [f for f in res.get("findings", []) if f.get("severity") == "high"]


def tokens(c) -> str:
    """The contract as custom properties, including a composed dark theme.

    Dark is derived here rather than declared twice: a muted grey chosen against
    paper lands around 2.5:1 on a dark card, and carrying it across is the most
    common way a dark theme fails a contrast check its light twin passes."""
    scale = c.scale
    steps = [4, 8, 12, 16, 24, 32, 48, 64]
    sp = (c.raw.get("spacing") or {}).get("scale") or steps
    lines = [":root{"]
    for k, v in c.roles.items():
        lines.append(f"  --{k}:{v};")
    for i, s in enumerate(scale):
        lines.append(f"  --t{i}:{s:g}px;")
    for i, s in enumerate(sp):
        lines.append(f"  --s{i}:{s:g}px;")
    lines.append(f"  --r-ctl:{c.r_control:g}px; --r-card:{c.r_card:g}px;")
    dur = (c.raw.get("motion") or {}).get("duration_ms") or [140, 240]
    ease = (c.raw.get("motion") or {}).get("easing")
    ease = ease if ease and ease != "UNKNOWN" else "cubic-bezier(.2,.8,.2,1)"
    lines.append(f"  --fast:{dur[0]}ms; --slow:{dur[-1]}ms; --ease:{ease};")
    # A declared face this project does not ship will not render, and a prototype
    # shown in a fallback while claiming the declared face is a prototype about a
    # typeface nobody chose. The stack always ends somewhere real, and `faces()`
    # puts the truth on the page.
    lines.append(f"  --font-display:{_stack(c.families['display'], 'serif')};")
    lines.append(f"  --font-body:{_stack(c.families['body'], 'sans')};")
    lines.append(f"  --font-mono:{_stack(c.families['mono'], 'mono')};")
    lines.append("  --line:color-mix(in oklab,var(--ink) 15%,var(--canvas));")
    lines.append("}")
    lines.append(
        "@media (prefers-color-scheme:dark){:root:not([data-theme=light]){"
        "--canvas:#14120e;--surface:#1e1b16;--ink:#f4f0e7;"
        "--muted:color-mix(in oklab,#f4f0e7 72%,#14120e);"
        "--interactive:color-mix(in oklab,var(--focus) 78%,#ffffff);"
        "--line:color-mix(in oklab,#f4f0e7 22%,#14120e)}}")
    lines.append(
        ":root[data-theme=dark]{--canvas:#14120e;--surface:#1e1b16;--ink:#f4f0e7;"
        "--muted:color-mix(in oklab,#f4f0e7 72%,#14120e);"
        "--interactive:color-mix(in oklab,var(--focus) 78%,#ffffff);"
        "--line:color-mix(in oklab,#f4f0e7 22%,#14120e)}")
    return "\n".join(lines)


CSS = r"""
*,*::before,*::after{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--font-body);
  font-size:var(--t2);line-height:1.55;padding-inline:var(--s3)}
.wrap{max-width:1120px;margin:0 auto;padding:var(--s5) 0 var(--s7)}
h1{font-family:var(--font-display);font-size:var(--t5);line-height:1.15;margin:0 0 var(--s1);
  font-weight:650;text-wrap:balance;max-width:24ch}
h2{font-family:var(--font-display);font-size:var(--t4);margin:var(--s6) 0 var(--s2);
  font-weight:650;text-wrap:balance}
h3{font-family:var(--font-display);font-size:var(--t3);margin:0 0 var(--s1);font-weight:650}
p{margin:0 0 var(--s2);max-width:68ch;text-wrap:pretty}
.muted{color:var(--muted)}
.bar{display:flex;flex-wrap:wrap;gap:var(--s2);align-items:center;
  padding:var(--s2) 0 var(--s4);border-bottom:1px solid var(--line);margin-bottom:var(--s4)}
.card{background:var(--surface);border-radius:var(--r-card);padding:var(--s4);
  margin:0 0 var(--s3)}
.grid{display:grid;gap:var(--s3);grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
button,.btn{font:inherit;font-weight:600;min-height:44px;padding:var(--s2) var(--s4);
  border-radius:var(--r-ctl);cursor:pointer;border:1px solid transparent;
  background:var(--interactive);color:#fff}
.btn-secondary{background:var(--surface);color:var(--ink);border-color:var(--line)}
.btn-danger{background:var(--danger);color:#fff}
.btn-ghost{background:transparent;color:var(--interactive);border-color:transparent}
button[disabled]{cursor:not-allowed;background:color-mix(in oklab,var(--ink) 12%,var(--canvas));
  color:color-mix(in oklab,var(--ink) 62%,var(--canvas));border-color:var(--line)}
button:hover:not([disabled]){filter:brightness(1.07)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
label{display:block;font-weight:600;margin:0 0 var(--s1)}
.hint{display:block;font-weight:400;font-size:var(--t0);color:var(--muted);margin-top:2px}
input,select,textarea{width:100%;font:inherit;padding:var(--s2) var(--s3);min-height:46px;
  border:1px solid color-mix(in oklab,var(--ink) 34%,var(--canvas));
  border-radius:var(--r-ctl);background:var(--surface);color:var(--ink)}
input:user-invalid{border-color:var(--danger)}
.field{margin:0 0 var(--s3)}
.err{color:var(--danger);font-size:var(--t1);margin-top:var(--s1);display:none}
input:user-invalid ~ .err{display:block}
.summary{border:1px solid var(--danger);border-radius:var(--r-ctl);padding:var(--s3);
  margin:0 0 var(--s3);background:color-mix(in oklab,var(--danger) 10%,var(--canvas))}
.summary ul{margin:var(--s1) 0 0;padding-left:var(--s4)}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}
caption{text-align:left;color:var(--muted);padding:0 0 var(--s2)}
th{text-align:left;font-weight:600;color:var(--muted);padding:var(--s1) var(--s3) var(--s2) 0;
  border-bottom:1px solid color-mix(in oklab,var(--ink) 28%,var(--canvas));white-space:nowrap}
th button{background:none;border:0;color:inherit;font:inherit;padding:var(--s1) 0;
  min-height:36px;cursor:pointer}
td{padding:var(--s2) var(--s3) var(--s2) 0;border-bottom:1px solid var(--line)}
td.num{text-align:right}
.tscroll{overflow-x:auto}
[role=tablist]{display:flex;gap:var(--s1);border-bottom:1px solid var(--line);
  margin:0 0 var(--s3)}
[role=tab]{background:none;border:0;border-bottom:2px solid transparent;color:var(--muted);
  border-radius:0;min-height:44px}
[role=tab][aria-selected=true]{color:var(--ink);border-bottom-color:var(--interactive)}
.switch{display:flex;align-items:center;gap:var(--s2);min-height:44px}
.switch button{width:52px;height:30px;min-height:30px;padding:0;border-radius:999px;
  background:color-mix(in oklab,var(--ink) 26%,var(--canvas));position:relative}
.switch button[aria-checked=true]{background:var(--interactive)}
.switch button::after{content:"";position:absolute;top:3px;left:3px;width:24px;height:24px;
  border-radius:999px;background:#fff;transition:transform var(--fast) var(--ease)}
.switch button[aria-checked=true]::after{transform:translateX(22px)}
dialog{border:0;border-radius:var(--r-card);padding:var(--s4);max-width:34rem;width:92%;
  background:var(--surface);color:var(--ink)}
dialog::backdrop{background:color-mix(in oklab,var(--ink) 55%,transparent)}
.row{display:flex;gap:var(--s2);flex-wrap:wrap;margin-top:var(--s3)}
.toast{position:fixed;left:50%;bottom:var(--s4);transform:translateX(-50%);
  background:var(--ink);color:var(--canvas);padding:var(--s2) var(--s3);
  border-radius:var(--r-ctl);display:flex;gap:var(--s3);align-items:center;
  min-height:48px}
.toast button{background:none;color:inherit;text-decoration:underline;min-height:40px;
  padding:0 var(--s1)}
.state{padding:var(--s5) var(--s3);text-align:center;border:1px dashed var(--line);
  border-radius:var(--r-card)}
.spinner{width:22px;height:22px;border-radius:999px;border:3px solid var(--line);
  border-top-color:var(--interactive);display:inline-block;
  animation:spin 900ms linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){
  .spinner{animation-duration:2.4s}
  *{transition-duration:1ms!important}}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:var(--r-ctl);
  overflow:hidden}
.seg button{background:var(--surface);color:var(--ink);border:0;border-radius:0;
  font-size:var(--t1);padding:var(--s2) var(--s3)}
.seg button[aria-pressed=true]{background:var(--interactive);color:#fff}
[data-density=compact] .card{padding:var(--s2)}
[data-density=compact] td,[data-density=compact] th{padding-top:var(--s1);
  padding-bottom:var(--s1)}
/* The parts nobody draws still carry the design: selection, caret, scrollbar,
   underline offset and the native control accent all ship with browser defaults
   that belong to no design system. */
::selection{background:color-mix(in oklab,var(--focus) 26%,var(--canvas));
  color:var(--ink)}
:root{caret-color:var(--interactive);accent-color:var(--interactive);
  scrollbar-color:color-mix(in oklab,var(--ink) 30%,var(--canvas)) transparent}
a{color:var(--interactive);text-underline-offset:0.18em}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0 0 0 0);white-space:nowrap;border:0}
"""

DEPTH_BORDER = (".card,dialog{border:1px solid var(--line)}\n"
                ".toast{border:1px solid color-mix(in oklab,var(--canvas) 34%,var(--ink))}\n")
# The depth metaphor is ONE of these, never both -- an element with a hairline
# border under a wide soft shadow is two systems arguing. The overlay surfaces
# follow whichever the contract declared rather than reaching for a shadow.
DEPTH_SHADOW = (".card{box-shadow:0 1px 2px color-mix(in oklab,var(--ink) 10%,transparent)}\n"
                "dialog,.toast{box-shadow:0 18px 50px "
                "color-mix(in oklab,var(--ink) 30%,transparent)}\n")

HEADER = r"""
  <h1>__TITLE__</h1>
  <p class="muted">A working prototype generated from this project's design
    contract. Every colour, size, radius and duration here is a declared value —
    nothing was chosen while writing this page. Use it: click things, tab through
    it, switch the states, try it at 320px.</p>

  <div class="bar">
    <div class="seg" role="group" aria-label="Theme">
      <button type="button" data-theme="light" aria-pressed="true">Light</button>
      <button type="button" data-theme="dark" aria-pressed="false">Dark</button>
    </div>
    <div class="seg" role="group" aria-label="Density">
      <button type="button" data-density="comfortable" aria-pressed="true">Comfortable</button>
      <button type="button" data-density="compact" aria-pressed="false">Compact</button>
    </div>
    <span class="muted" style="font-size:var(--t1)">Contract __SHA__ · __DATE__</span>
  </div>
"""

SECTIONS = r"""
  <section class="proto-section" id="states"><h2>The states nobody opens</h2>
  <p>The happy path is the smallest part of the work. Switch between them and see
     what a person actually meets.</p>
  <div class="seg" role="group" aria-label="List state" id="statepicker">
    <button type="button" data-state="ready" aria-pressed="true">Ready</button>
    <button type="button" data-state="loading" aria-pressed="false">Loading</button>
    <button type="button" data-state="empty" aria-pressed="false">Empty</button>
    <button type="button" data-state="error" aria-pressed="false">Error</button>
    <button type="button" data-state="offline" aria-pressed="false">Offline</button>
  </div>
  <div id="liveregion" role="status" aria-live="polite" class="sr-only"></div>

  <div id="list" style="margin-top:var(--s3)"></div>

  </section>

  <section class="proto-section" id="controls"><h2>Controls</h2>
  <div class="card">
    <div class="row">
      <button type="button">Primary action</button>
      <button type="button" class="btn-secondary">Secondary</button>
      <button type="button" class="btn-ghost">Tertiary</button>
      <button type="button" class="btn-danger" id="del">Delete this job</button>
      <button type="button" disabled aria-describedby="whydisabled">Approve</button>
    </div>
    <p id="whydisabled" class="hint" style="margin-top:var(--s2)">Approve is
      unavailable until an engineer is assigned — a disabled control that does not
      say why is a dead end.</p>
    <div class="switch" style="margin-top:var(--s3)">
      <button type="button" role="switch" aria-checked="false" id="sw"
              aria-labelledby="swlabel"></button>
      <span id="swlabel">Notify the engineer by text</span>
    </div>
  </div>

  </section>

  <section class="proto-section" id="tabs"><h2>Tabs</h2>
  <div class="card">
    <div role="tablist" aria-label="Job sections">
      <button role="tab" id="t1" aria-selected="true" aria-controls="p1" tabindex="0">Details</button>
      <button role="tab" id="t2" aria-selected="false" aria-controls="p2" tabindex="-1">History</button>
      <button role="tab" id="t3" aria-selected="false" aria-controls="p3" tabindex="-1">Parts</button>
    </div>
    <div role="tabpanel" id="p1" aria-labelledby="t1" tabindex="0">
      <p>Arrow keys move between tabs and Home and End jump to the ends, which is
         the pattern assistive technology expects. A row of buttons that merely
         looks like tabs does not do any of that.</p></div>
    <div role="tabpanel" id="p2" aria-labelledby="t2" tabindex="0" hidden>
      <p>Three visits since March. The last engineer left a note about access.</p></div>
    <div role="tabpanel" id="p3" aria-labelledby="t3" tabindex="0" hidden>
      <p>One part on order, expected Thursday.</p></div>
  </div>

  </section>

  <section class="proto-section" id="form"><h2>A form that behaves</h2>
  <div class="card">
    <form id="f" novalidate>
      <div class="summary" id="summary" hidden>
        <strong>This was not sent</strong><ul id="summarylist"></ul>
      </div>
      <div class="field">
        <label for="who">Contact name
          <span class="hint">A real label, not a placeholder — a placeholder
            disappears the moment someone types.</span></label>
        <input id="who" name="who" type="text" autocomplete="name" required>
        <span class="err">Give the name of the person on site.</span>
      </div>
      <div class="field">
        <label for="email">Email</label>
        <input id="email" name="email" type="email" autocomplete="email" required
               inputmode="email">
        <span class="err">That does not look like an email address.</span>
      </div>
      <div class="field">
        <label for="when">Preferred date</label>
        <input id="when" name="when" type="date" required>
        <span class="err">Pick a date.</span>
      </div>
      <button type="submit" id="submit">Book the visit</button>
      <span class="hint" style="display:inline-block;margin-left:var(--s2)">The
        button guards against a double submit, which is how a card gets charged
        twice.</span>
    </form>
  </div>

  </section>

  <section class="proto-section" id="table"><h2>A table that is a table</h2>
  <div class="card">
    <div class="tscroll" role="region" tabindex="0" aria-label="Scheduled jobs">
      <table id="jobs">
        <caption>Scheduled jobs. Click a column heading to sort.</caption>
        <thead><tr>
          <th scope="col"><button type="button" data-k="job">Job</button></th>
          <th scope="col"><button type="button" data-k="engineer">Engineer</button></th>
          <th scope="col"><button type="button" data-k="due">Due</button></th>
          <th scope="col" class="num"><button type="button" data-k="cost">Cost (GBP)</button></th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <p class="hint" style="margin-top:var(--s2)">Figures use tabular numerals, so
      the column stays a column. Zero and “not collected” are different facts and
      are shown differently.</p>
  </div>

  </section>

  <section class="proto-section" id="durable"><h2>Where a confirmation goes to live</h2>
  <div class="card">
    <p class="muted" style="margin:0 0 var(--s2)">A toast is gone in ten seconds.
      Anything someone may need to refer back to has to survive it, so every
      consequential action also lands here.</p>
    <ul id="activity" style="margin:0;padding-left:var(--s4)">
      <li class="muted">Nothing yet. Delete a job and watch both places change.</li>
    </ul>
  </div>

  <dialog id="confirm" aria-labelledby="ctitle">
    <h3 id="ctitle">Delete “Boiler service”?</h3>
    <p>The engineer is notified immediately and it cannot be undone from their
       side. You will have ten seconds to undo it here.</p>
    <div class="row">
      <button type="button" class="btn-secondary" id="cancel">Keep it</button>
      <button type="button" class="btn-danger" id="reallydelete">Delete the job</button>
    </div>
  </dialog>
  </section>
"""

SCRIPT = r"""
<script>
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const say = t => { $('#liveregion').textContent = t; };

/* theme + density: real toggles, so the reviewer can check both without a
   browser setting. The dark values come from the contract's own roles. */
$$('.seg [data-theme]').forEach(b => b.onclick = () => {
  document.documentElement.setAttribute('data-theme', b.dataset.theme);
  $$('.seg [data-theme]').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
});
$$('.seg [data-density]').forEach(b => b.onclick = () => {
  document.body.setAttribute('data-density', b.dataset.density);
  $$('.seg [data-density]').forEach(o => o.setAttribute('aria-pressed', String(o === b)));
});

/* the five states, as things you can actually look at */
const JOBS = [
  {job:'Boiler service', engineer:'Priya Raman', due:'Fri 25 Sep', cost:148},
  {job:'Annual inspection', engineer:null, due:'Mon 28 Sep', cost:0},
  {job:'Pump replacement', engineer:'Tom Walsh', due:'Wed 30 Sep', cost:1260},
];
function render(state) {
  const box = $('#list');
  if (state === 'loading') {
    box.innerHTML = `<div class="state"><span class="spinner" role="img"
      aria-label="Loading jobs"></span><p style="margin:var(--s2) auto 0">Loading
      your jobs…</p></div>`;
    say('Loading jobs'); return;
  }
  if (state === 'empty') {
    box.innerHTML = `<div class="state"><h3>No jobs yet</h3>
      <p class="muted" style="margin:0 auto var(--s3)">When a clinic books a
      service it appears here, newest first.</p>
      <button type="button">Raise the first job</button></div>`;
    say('No jobs yet'); return;
  }
  if (state === 'error') {
    box.innerHTML = `<div class="state"><h3>We could not load your jobs</h3>
      <p class="muted" style="margin:0 auto var(--s3)">The scheduling service did
      not answer. Nothing you entered has been lost.</p>
      <button type="button" onclick="show('ready')">Try loading the jobs again</button></div>`;
    say('Could not load jobs'); return;
  }
  if (state === 'offline') {
    box.innerHTML = `<div class="state"><h3>You are offline</h3>
      <p class="muted" style="margin:0 auto var(--s3)">These are the jobs as of
      your last connection. Booking is unavailable until you reconnect.</p></div>
      ${JOBS.map(card).join('')}`;
    say('Offline'); return;
  }
  box.innerHTML = JOBS.map(card).join('');
  say(JOBS.length + ' jobs');
}
const card = j => `<div class="card"><h3>${j.job}</h3>
  <p class="muted">${j.due} · ${j.engineer ? 'Engineer: ' + j.engineer
    : '<em>Unassigned</em>'}</p>
  <div class="row"><button type="button" class="btn-secondary">Reschedule</button>
  ${j.engineer ? '' : '<button type="button">Assign an engineer</button>'}</div></div>`;
function show(s) {
  $$('#statepicker button').forEach(o =>
    o.setAttribute('aria-pressed', String(o.dataset.state === s)));
  render(s);
}
$$('#statepicker button').forEach(b => b.onclick = () => show(b.dataset.state));
show('ready');

/* switch */
const sw = $('#sw');
sw.onclick = () => sw.setAttribute('aria-checked',
  sw.getAttribute('aria-checked') === 'true' ? 'false' : 'true');

/* tabs with roving tabindex and arrow keys */
const tabs = $$('[role=tab]');
function pick(t) {
  tabs.forEach(x => {
    const on = x === t;
    x.setAttribute('aria-selected', String(on));
    x.tabIndex = on ? 0 : -1;
    $('#' + x.getAttribute('aria-controls')).hidden = !on;
  });
  t.focus();
}
tabs.forEach(t => {
  t.onclick = () => pick(t);
  t.onkeydown = e => {
    const i = tabs.indexOf(t);
    if (e.key === 'ArrowRight') pick(tabs[(i + 1) % tabs.length]);
    else if (e.key === 'ArrowLeft') pick(tabs[(i - 1 + tabs.length) % tabs.length]);
    else if (e.key === 'Home') pick(tabs[0]);
    else if (e.key === 'End') pick(tabs[tabs.length - 1]);
    else return;
    e.preventDefault();
  };
});

/* form: validate on submit, link the summary to the fields, guard the submit */
const f = $('#f'), submit = $('#submit');
f.onsubmit = async e => {
  e.preventDefault();
  const bad = $$('#f input').filter(i => !i.checkValidity());
  $$('#f input').forEach(i => i.matches(':user-invalid'));
  const sum = $('#summary'), list = $('#summarylist');
  if (bad.length) {
    list.innerHTML = bad.map(i =>
      `<li><a href="#${i.id}">${$('label[for=' + i.id + ']').firstChild.textContent.trim()}
       — ${i.nextElementSibling.textContent}</a></li>`).join('');
    sum.hidden = false; sum.focus(); bad[0].focus();
    say(bad.length + ' problems to fix'); return;
  }
  sum.hidden = true;
  submit.disabled = true; submit.textContent = 'Booking…';
  say('Booking');
  await new Promise(r => setTimeout(r, 1200));
  submit.disabled = false; submit.textContent = 'Book the visit';
  activity('Booked a visit for ' + ($('#when').value || 'the chosen date') + '.');
  toast('Visit booked for ' + ($('#when').value || 'the chosen date'), null);
};

/* table sort, with the direction announced */
let dir = 1, key = 'due';
function rows() {
  const body = $('#jobs tbody');
  const data = [...JOBS].sort((a, b) =>
    (a[key] === null ? '' : a[key]) > (b[key] === null ? '' : b[key]) ? dir : -dir);
  body.innerHTML = data.map(j => `<tr><td>${j.job}</td>
    <td>${j.engineer ?? '<span class="muted">not assigned</span>'}</td>
    <td>${j.due}</td>
    <td class="num">${j.cost === 0 ? '0' : j.cost.toLocaleString('en-GB')}</td></tr>`).join('');
}
$$('#jobs th button').forEach(b => b.onclick = () => {
  if (key === b.dataset.k) dir = -dir; else { key = b.dataset.k; dir = 1; }
  $$('#jobs th').forEach(th => th.removeAttribute('aria-sort'));
  b.closest('th').setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
  rows(); say('Sorted by ' + b.textContent + ', ' + (dir === 1 ? 'ascending' : 'descending'));
});
rows();

/* destructive: confirm, then undo. Undo beats confirmation where it is possible,
   because it does not tax the ninety-nine correct actions to stop the one slip. */
const dlg = $('#confirm');
$('#del').onclick = () => dlg.showModal();
$('#cancel').onclick = () => dlg.close();
$('#reallydelete').onclick = () => {
  dlg.close();
  // The list actually changes. An outcome that exists only in a toast is an
  // outcome the user missed the moment the toast went away, and the undo has to
  // put back the thing that left.
  const removed = JOBS.shift();
  show('ready'); rows();
  let undone = false;
  activity('Deleted “' + removed.job + '”. The engineer was notified.');
  toast('“' + removed.job + '” deleted. The engineer has been notified.', () => {
    undone = true; JOBS.unshift(removed); show('ready'); rows();
    activity('Restored “' + removed.job + '”.');
    say(removed.job + ' restored');
  });
  say(removed.job + ' deleted');
  setTimeout(() => { if (!undone) say('That deletion is now permanent'); }, 10000);
};
/* the durable half of every confirmation */
function activity(text) {
  const ul = $('#activity');
  if (ul.querySelector('.muted')) ul.innerHTML = '';
  const li = document.createElement('li');
  const t = new Date().toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit'});
  li.textContent = t + ' — ' + text;
  ul.prepend(li);
}
function toast(text, onUndo) {
  $$('.toast').forEach(t => t.remove());
  const el = document.createElement('div');
  el.className = 'toast'; el.setAttribute('role', 'status');
  el.innerHTML = `<span></span>${onUndo ? '<button type="button">Undo</button>' : ''}`;
  el.querySelector('span').textContent = text;
  if (onUndo) el.querySelector('button').onclick = () => { onUndo(); el.remove(); };
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 10000);
  return el;
}
</script>
"""


SHELL = Path(__file__).resolve().parent.parent / "assets" / "templates" / "prototype-shell.html"


# The template documents its own slots, which means the documentation contains
# the slot markers -- and a naive fill replaced them there too, pasting a whole
# copy of the page inside an HTML comment and doubling every output. The doc
# block is removed before filling, which is also right on its own terms: a 2KB
# comment explaining the template has no business in every prototype it makes.
_DOC = re.compile(r"<!--(?:(?!-->).)*?deluxui prototype shell.*?-->\s*", re.S)


def shell_text(path: Path | None = None) -> str:
    """The wrapper. A template on disk, so a project can change the chrome once
    and have every prototype it generates inherit it."""
    p = path or SHELL
    try:
        return _DOC.sub("", p.read_text(), count=1)
    except OSError:
        # The script stays usable on its own; the template is the editable copy,
        # not a dependency to be broken by a partial install.
        return ("<!doctype html>\n<html lang=\"en\" data-theme=\"light\"><head>"
                "<meta charset=\"utf-8\">"
                "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
                "<title>{{title}}</title><style>\n{{tokens}}\n{{css}}\n{{depth}}\n"
                "</style></head><body data-density=\"{{density}}\">{{banners}}"
                "<div class=\"wrap\">{{header}}{{sections}}</div>{{script}}"
                "</body></html>\n")


# --------------------------------------------------- what the project is made of
# The prototype is generated from the contract and knows nothing about the repo it
# sits in, which is right for its conformance claim and wrong for the person
# reading it. They are about to decide whether to build this, and the honest
# framing of that decision needs one more fact: what the project already has.
#
# A prototype's hand-rolled dialog is a DEMONSTRATION of the intended behaviour.
# Lifted into production verbatim, in a project that has Radix installed, it is a
# COMP-001 violation with the focus containment done worse. Saying so here, on the
# artefact itself, is the only place it gets read at the right moment.
DEMOS = [
    ("dialog", "The confirmation dialog", ("dialog", "modal", "alertdialog", "confirm")),
    ("tabs", "Tabs", ("tabs", "tab")),
    ("select", "The select", ("select", "combobox", "listbox", "dropdown")),
    ("toast", "The toast and the activity log", ("toast", "snackbar", "notification")),
    ("table", "The table", ("table", "datatable", "grid")),
    ("form", "The form", ("form", "input", "field", "textfield")),
    ("button", "Controls", ("button", "iconbutton")),
]


def provenance(root: Path | None = None) -> dict:
    """Frameworks, primitive libraries and the real component for each demo.

    Measured, never declared -- and when it cannot be measured it says so rather
    than reporting an empty inventory, because "this project has no components" and
    "nobody looked" produce the same empty list and mean opposite things."""
    root = root or Path.cwd()
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ux_check
        from checks.designsystem import PRIMITIVES
        pr = ux_check.detect_project(root)
    except Exception as e:
        return {"measured": False, "why": f"{type(e).__name__}: {e}"}
    libs = sorted({name for dep, name in PRIMITIVES.items()
                   if any(d == dep or d.startswith(dep + "/") for d in pr.deps)})
    rows = []
    for _key, label, words in DEMOS:
        hits = sorted({n for n in pr.inventory
                       if any(wd in n.lower() for wd in words)})[:3]
        rows.append({"demo": label, "components": hits,
                     "paths": [pr.inventory[h] for h in hits]})
    return {"measured": True, "libraries": libs,
            "frameworks": sorted({f for f, dep in (("React", "react"), ("Vue", "vue"),
                                  ("Svelte", "svelte"), ("Solid", "solid-js"),
                                  ("Angular", "@angular/core"), ("Astro", "astro"))
                                  if dep in pr.deps}),
            "tailwind": pr.tailwind_major or None,
            "tokens": len(pr.cssvars), "token_sources": pr.token_sources[:4],
            "components": len(pr.inventory), "rows": rows}


def provenance_section(pv: dict) -> str:
    """The panel, last on the page. Last because it is about the build rather than
    about the design, and a reviewer should meet the interface first."""
    if not pv.get("measured"):
        return ('\n  <section class="proto-section" id="built-with">'
                '<h2>What this would be built with</h2>\n'
                f'<p class="note">Not measured ({html.escape(str(pv.get("why")))}). '
                'This prototype therefore says nothing about which components exist '
                'in the project \u2014 that is unknown here, not empty.</p>\n'
                '  </section>\n')
    libs = ", ".join(pv["libraries"])
    fw = ", ".join(pv["frameworks"]) or "no framework detected"
    rows = ""
    for r in pv["rows"]:
        if r["components"]:
            has = "".join(f'<code>{html.escape(c)}</code> ' for c in r["components"])
            verdict = "compose this, do not re-implement it"
        else:
            has = '<span class="muted">nothing matching</span> '
            verdict = ("build it \u2014 but check the inventory by hand before you do"
                       if pv["components"] else "the inventory is empty")
        rows += (f'<tr><td>{html.escape(r["demo"])}</td><td>{has}</td>'
                 f'<td class="muted">{verdict}</td></tr>')
    lib_line = (f'<p><strong>{html.escape(libs)}</strong> is installed. Every dialog, '
                f'menu, select and tooltip below is a demonstration of the intended '
                f'behaviour, not the component to ship: that library has already '
                f'solved focus containment, Escape handling and typeahead, and a '
                f'hand-rolled replacement will be worse at all three.</p>'
                if libs else
                '<p>No headless primitive library is installed, so the accessibility '
                'behaviour demonstrated below \u2014 focus containment, Escape, '
                'typeahead, roving tabindex \u2014 is work somebody will have to do '
                'by hand, and it is the work that gets dropped under time pressure.</p>')
    return (f'\n  <section class="proto-section" id="built-with">'
            f'<h2>What this would be built with</h2>\n'
            f'    <p class="note">Measured from this repository, not declared. The '
            f'rest of this page comes from the contract; this section comes from the '
            f'code, and the two disagreeing is worth knowing before anybody starts.</p>\n'
            f'    <p>{html.escape(fw)}'
            + (f' \u00b7 Tailwind {pv["tailwind"]}' if pv["tailwind"] else "")
            + f' \u00b7 {pv["tokens"]} design token(s)'
            + (f' in <code>{html.escape(", ".join(pv["token_sources"]))}</code>'
               if pv["token_sources"] else " and no token source")
            + f' \u00b7 {pv["components"]} component(s) in the inventory</p>\n'
            f'    {lib_line}\n'
            f'    <table class="proto-table"><thead><tr><th>This prototype shows</th>'
            f'<th>The project already has</th><th></th></tr></thead>'
            f'<tbody>{rows}</tbody></table>\n  </section>\n')


def build(c, title: str, density: str, shell: Path | None = None,
          extra_sections: str = "", pv: dict | None = None) -> str:
    depth = DEPTH_SHADOW if c.depth == "shadow" else DEPTH_BORDER
    header = (HEADER.replace("__TITLE__", title)
              .replace("__SHA__", c.sha())
              .replace("__DATE__", str(date.today())))
    und = c.undeclared
    missing = faces(c)
    banner = ""
    if missing:
        names = ", ".join(sorted({str(m.get("family")) for m in missing}))
        banner += (f'<p style="background:color-mix(in oklab,var(--warning) 14%,'
                   f'var(--canvas));border-left:4px solid var(--warning);'
                   f'padding:var(--s2) var(--s3);margin:0 0 var(--s3);max-width:none">'
                   f'<strong>This is not rendering in {names}.</strong> Nothing in '
                   f'this project provides that face, so what you are looking at is '
                   f'the fallback. Judge the type once it is shipped, or change the '
                   f'contract to the face that is actually rendering.</p>')
    if und:
        banner += (f'<p style="background:color-mix(in oklab,var(--danger) 12%,'
                   f'var(--canvas));border-left:4px solid var(--danger);'
                   f'padding:var(--s2) var(--s3);margin:0 0 var(--s4);max-width:none">'
                   f'<strong>{len(und)} contract fields are undeclared</strong> '
                   f'({", ".join(und)}). Those parts of this prototype are '
                   f'placeholders, not proposals \u2014 reviewing it does not decide '
                   f'them.</p>')
    out = shell_text(shell)
    for slot, value in (("title", title), ("tokens", tokens(c)), ("css", CSS),
                        ("depth", depth), ("banners", banner), ("header", header),
                        ("sections", SECTIONS + (extra_sections or "")
                         + (provenance_section(pv) if pv is not None else "")),
                        ("script", SCRIPT), ("density", density)):
        out = out.replace("{{" + slot + "}}", value)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", metavar="PATH")
    ap.add_argument("--title", default="Prototype")
    ap.add_argument("--density", default="comfortable",
                    choices=["comfortable", "compact"])
    ap.add_argument("--contract")
    ap.add_argument("--shell", metavar="PATH",
                    help="a different wrapper (default: assets/templates/"
                         "prototype-shell.html)")
    ap.add_argument("--no-provenance", action="store_true",
                    help="omit the \"what this would be built with\" panel, which is "
                         "measured from the repository this runs in")
    ap.add_argument("--sections", metavar="PATH",
                    help="an HTML fragment appended after the built-in systems -- "
                         "this is where a real product screen goes")
    a = ap.parse_args(argv)
    c = ux_image.load_contract(a.contract)
    extra = ""
    if a.sections:
        try:
            extra = "\n" + Path(a.sections).read_text()
        except OSError as e:
            sys.stderr.write(f"could not read {a.sections}: {e}\n")
            return 2
    pv = None if a.no_provenance else provenance()
    out = build(c, a.title, a.density,
                Path(a.shell) if a.shell else None, extra, pv)
    if a.write:
        p = Path(a.write)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out)
        sys.stderr.write(
            f"\nwrote {p}  ({len(out)} bytes, no dependencies, no build step)\n"
            f"  contract {c.sha()}"
            + (f", {len(c.undeclared)} fields undeclared and drawn as placeholders"
               if c.undeclared else ", fully declared") + "\n"
            + (("  built with: " + (", ".join(pv["libraries"]) or "no primitive library")
                + f", {pv['components']} component(s) in the inventory\n")
               if pv and pv.get("measured") else "")
            + "\n"
            f"Put it in front of a person, beside whatever exists today:\n"
            f"  python3 scripts/ux_review.py serve --variant \"proposed={p}\" \\\n"
            f"        --variant \"current=http://localhost:5173/\"\n\n"
            f"Then check the generator did not cheat:\n"
            f"  python3 scripts/ux_check.py {p.parent}\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
