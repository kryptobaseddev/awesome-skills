# Browser walkthrough — see the real app, mobile first

Static analysis tells you what the code says. The walk tells you what users get. Do it on the running app,
narrowest viewport first, because a layout that works at 320px usually scales up cleanly, while a desktop
layout squeezed down usually doesn't.

## Contents
1. Widths and why
2. Pick a browser tool
3. The per-route protocol
4. Force the states nobody tests
5. Keyboard and focus pass
6. Mobile-specific checks
7. Desktop scaling checks
8. Before/after comparison

---

## 1. Widths and why
| Width | Represents | Must hold |
|---|---|---|
| **320** | small phones; WCAG 1.4.10 reflow width (1280px at 400% zoom) | no horizontal scroll, no clipped text, no overlap |
| **390** | the typical modern phone (390×844) | thumb-reachable primary action, ≥44px targets, readable type |
| 768 | tablets, large phones landscape, split screen | layout transition is deliberate, not accidental |
| 1024 | small laptops, tablet landscape | navigation pattern switch (tab bar → sidebar/top nav) works |
| **1440** | the common desktop | line length ≤ ~75ch, content doesn't stretch edge to edge, density earns the space |

Bold widths are the minimum set. Phone widths must be emulated as **touch** (pointer: coarse, hover: none),
or hover-only bugs won't show.

## 2. Pick a browser tool
Use whatever the environment has; the procedure is the same. `probe.js` is a function, `async () => {...}`.

**Batch, Node + Playwright (fastest for many routes):**
```bash
# playwright is looked up in the project, then in ~/.cache/ux-laws; add --install once to set up that cache
node <skill>/scripts/walk.mjs --install --base http://localhost:5173 \
  --routes / /products /products/123 /cart /checkout /account \
  --widths 320,390,768,1024,1440 --out ux-audit/captures
# authenticated routes: save a storage state from a logged-in test session, then --storage-state auth.json
```

**Playwright MCP** (`browser_resize`, `browser_navigate`, `browser_evaluate`, `browser_take_screenshot`):
1. `browser_resize` 390×844 → `browser_navigate` to the route.
2. `browser_evaluate` with the full text of `probe.js` as the function. On a localhost app you can serve the
   skill's scripts folder with any static server that sends CORS headers and evaluate
   `async () => { const s = await (await fetch('http://127.0.0.1:<port>/probe.js')).text(); return (0, eval)('(' + s + ')')() }`
   instead of pasting 12KB. Pass `filename` to save the result as `ux-audit/captures/<route>@390.json`.
3. `browser_take_screenshot` (fullPage) → `ux-audit/captures/<route>@390.png`. Repeat at each width.
Resizing a desktop window does **not** emulate touch. Note in the report that the hover and pointer checks
came from a mouse context, or use walk.mjs for phone widths.

**Claude in Chrome** (`resize_window`, `navigate`, `javascript_tool`, `computer` screenshot): same steps;
`javascript_tool` takes an expression, so wrap it as `(<probe.js source>)()`. It runs in the user's real
profile: stay on the app under audit and don't submit forms with real data.

**agent-browser CLI / Playwright CLI:** `open <url>`, set the viewport or device, `eval "(<probe source>)()"`,
`screenshot`. Check `--help` for the exact viewport/device flag of the installed version.

**No browser available:** say so in the report. Every runtime metric is then NOT_MEASURED, which is not a
pass. Do the static audit and list the walk as the first follow-up.

## 3. The per-route protocol
For each route in `flows.md` (critical paths first), at each width:
1. Navigate and wait for network idle plus a beat for client rendering.
2. Run the probe and save the JSON.
3. Screenshot the first viewport, and the full page if it's long.
4. **Look** at the screenshot; don't just read numbers. Check the 5-second read: what is this screen for, and what's the one thing to do? If you can't tell, that's a Hick's/Von Restorff finding.
5. Walk the critical path by actually doing it: fill the form with realistic input (including a pasted, messy value), submit invalid, submit valid, go Back, refresh mid-flow (Zeigarnik), and time how long feedback takes (Doherty 400ms).
6. Note every place the path breaks at this width: hidden actions, keyboard covering fields, sticky bars overlapping content, modals taller than the screen, horizontal scroll.

Then run the scorecard over the folder:
```bash
python3 <skill>/scripts/scorecard.py --inventory ux-audit/inventory.json --probes ux-audit/captures --out ux-audit
```

## 4. Force the states nobody tests
The four states (empty, loading, error, success) are where generated and rushed UIs fail. Force each one,
and count them in `manual.json` (`states_verified` / `states_total`):
- **Loading:** throttle the network (DevTools "Slow 4G"; Playwright `page.route('**/api/**', r => setTimeout(() => r.continue(), 3000))`). Is there a skeleton or progress that matches the final layout, or a blank screen, or a layout jump (CLS)?
- **Error:** fail the request (`page.route('**/api/products', r => r.fulfill({ status: 500 }))` or block it in DevTools). Is the error typed, human, recoverable (retry), and on the right surface?
- **Offline:** `context.setOffline(true)` or DevTools offline. Does the app say so and recover when the connection is back?
- **Empty:** use a fresh test account, or intercept with `r.fulfill({ json: [] })`. Does the empty state teach the next action (Paradox of the Active User)?
- **Success:** complete the action. Does the confirmation name the specific thing and offer a next step (Peak-End)?
- **Permission / not found:** visit a route without access and a bad id.
Only intercept requests on a local or staging app you were asked to audit.

## 5. Keyboard and focus pass
At 1440, with a mouse untouched:
- Tab through the critical path. Every interactive element is reachable, in a sensible order, with a **visible** focus ring (WCAG 2.4.7) that isn't hidden under sticky headers (2.4.11).
- Enter/Space activate; Escape closes dialogs, menus and tooltips; focus returns to the trigger after a dialog closes; focus is trapped inside an open modal.
- Search and combobox: arrow keys move the highlight; Enter selects.
Record `focus_visible` and `keyboard_complete` in `manual.json`.

## 6. Mobile-specific checks
- **Thumb zone:** primary actions in the lower half or a sticky bottom bar; destructive actions away from the primary; nothing essential only in the top corners.
- **Navigation:** 3–5 destinations in a bottom tab bar, or a clear menu. A desktop mega-menu squeezed into a hamburger with 30 links is a Hick's failure.
- **Forms:** one column; the right keyboard per field (`inputmode`, `type`); `autocomplete` set; inputs ≥16px; the error is visible above the keyboard; a sticky submit on long forms.
- **Overlays:** dialogs become bottom sheets or full-screen on phones; nothing taller than the viewport without internal scroll; close is reachable.
- **Hover:** nothing essential appears only on hover (row actions, card buttons, tooltips holding required info).
- **Viewport meta:** `width=device-width, initial-scale=1`, and zoom is not disabled (`user-scalable=no` and `maximum-scale=1` block zoom; WCAG 1.4.4). If it's missing, phones render a shrunken ~980px page that hides the real layout bugs, so **re-measure with it injected** before judging mobile (Playwright: `await page.addInitScript(() => document.addEventListener('DOMContentLoaded', () => { const m = document.createElement('meta'); m.name = 'viewport'; m.content = 'width=device-width, initial-scale=1'; document.head.append(m) }))`). The true overflow is often several times worse, which changes the fix order.
- **Safe areas:** fixed bars use `env(safe-area-inset-bottom)`; nothing hides behind the home indicator.
- **Tables:** become cards below the table's own container width (component-systems.md → Data tables, mobile).
- **Media:** images sized to the slot (`srcset`/`sizes`), not 2000px downloads at 390.

## 7. Desktop scaling checks
Mobile-first doesn't mean a stretched phone layout:
- Content width is capped (~1200–1440 for apps, ~65–75ch for reading) with intentional side space or a second column.
- Density rises where experts work (tables, dashboards): compact row heights and more columns, because the space is there.
- Hover and keyboard shortcuts add speed for pointer users without being the only path.
- Navigation switches pattern deliberately (bottom tabs → sidebar or top nav) at a breakpoint defined in tokens.
- Prefer container queries for components (they adapt to their slot, e.g. a card in a sidebar vs a grid) and media queries for page layout.

## 8. Before/after comparison
Every iteration repeats the same walk with the same routes, widths and test data:
```bash
python3 <skill>/scripts/scorecard.py --inventory ux-audit/inventory.json --probes ux-audit/captures \
  --baseline ux-audit/iteration-1/scorecard.json --out ux-audit/iteration-2
```
Keep each iteration's captures in its own folder (`ux-audit/iteration-N/`) so screenshots can be put side
by side. The Δ column shows movement; a FAIL that turned into a PASS is a result, and a new FAIL is a
regression to fix before shipping.
