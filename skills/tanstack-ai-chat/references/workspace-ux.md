# Workspace UX/UI

Use the application's existing tokens and primitives. The source proposes React, Tailwind CSS 4, Base UI and Motion; equivalent existing components can satisfy the same behavior. Numeric values below are starting specifications to validate, not framework requirements.

## Persistent runtime, adaptable presentation

Keep three state domains: local shell preferences, SDK live conversation state and durable server records. Derive presentation from open state, available space and saved desktop preference. Mobile sheet presentation must not overwrite a user's preferred desktop dock. Keep per-thread drafts and scroll state independent of panel lifetime.

| Presentation | Behavior |
|---|---|
| Closed | App fills workspace; active run/pending decision stays discoverable on launcher |
| Right dock | Both surfaces interactive; vertical keyboard/pointer separator |
| Bottom dock | Independent bounded scroll regions; horizontal separator |
| Mobile sheet | Modal, underlying app inert; focus management; safe areas and keyboard-aware height |
| Constrained height | Maximize/full-height treatment when minimum useful regions cannot fit |

Start with a 768px viewport threshold for mobile, but evaluate feasibility independently. For a side split, `innerWidth = workspaceWidth - 2 × inset`; require `innerWidth >= appMin + separator + chatMin`. Clamp chat width between `chatMin` and `innerWidth - separator - appMin`. Fall back to bottom/maximized when infeasible without erasing preference.

Source starting values: app/chat minimum 320px; preferred chat 420px; sidebar 250px; inset 16px; separator 8px; minimum bottom app/chat heights 240/280px; sheet up to 85dvh. Use actual workspace dimensions and zoom; never derive negative sizes. An existing product's useful content may need different minima.

## Containers, CSS and overlays

Use viewport queries for interaction mode and named inline-size containers for panel content. App navigation switches around 48rem of **app panel width**, not viewport width. Chat cards/toolbars stack below roughly 32rem of chat width. Named `app` and `chat` containers avoid nested generic containers capturing the wrong query.

Tailwind CSS 4 requires declared semantic theme tokens; utilities observed on another site do not appear automatically. Use static discoverable class strings, shrinkable grid/flex children (`min-width: 0`, `min-height: 0`) and `minmax(0, …)` tracks. Full size containment needs explicit dimensions and an actual height-query requirement.

The [CSS asset](../assets/workspace-reference.css) maps app tokens, named containers, mode geometry, layers, bounded transcript, safe areas and reduced-motion/forced-color behavior. Adapt tokens and compile through the project's Tailwind build; confirm generated variants rather than trusting raw CSS parsing. Inspect box sizing, viewport parent layout and theme inheritance in the target app.

Keep chat header/composer outside the transcript scroller. Confine overflow for code and tables locally, wrap long URLs/file names, and keep the app's scroll region separate. Portal menus escape clipped rounded panels but inherit the theme. Centralize overlay ordering and close the topmost transient surface first on Escape.

## Resize, focus and motion

Provide a labeled ARIA separator with orientation, controlled panel, current/min/max values and keyboard steps (Arrows, optionally Shift+Arrow and Home/End). Use pointer capture, cancel/unmount cleanup and a hit target wider than the visual line. Clamp on workspace resize/orientation; render drag geometry at most once per frame and avoid measurement feedback loops. Persist size on release/keyboard adjustment, not every pointer event.

Desktop chat is a labeled complementary region with no focus trap. Mobile is a modal dialog with inert underlying content. Restore focus to the invoker or stable launcher on dismissal. Keep retained exit-animation surfaces unreachable by keyboard. Honor reduced motion and forced colors; no token-by-token decorative animation.

## Transcript and composer

- Render typed parts through a shared registry: prose/Markdown, code, citations, attachment previews, domain cards, factual tool status and safe unknown-part fallback. Preserve order/IDs. Sanitize Markdown; do not execute model HTML/JS or show hidden reasoning as progress.
- Auto-follow only near the bottom (96px is an initial threshold). When reading older content, preserve anchor/offset and expose Jump to latest. Preserve anchors when prepending history or docking; streaming never moves focus.
- Use an autosizing bounded textarea. Enter sends outside IME composition, Shift+Enter inserts a newline; support a send-key preference when required. Start at 16px on mobile and verify actual devices.
- Freeze context/ready attachments on submit or explicit queue. Prevent duplicate submit. Do not silently start competing runs in one thread; label queued/disabled state and its reason.
- Preserve drafts, uploads and confirmed partial output on errors. Retry failed uploads separately. Delay attachment-dependent send until readiness; clear accepted input deliberately, not before failed admission can recover it.
- Distinguish Connecting, Streaming, Running tool, Awaiting decision, Reconnecting, Checking outcome and terminal states. Announce coarse changes politely, not every token.

## Controls and native context

Close dismisses; Stop cancels execution; Resume recovers delivery; Retry starts a failed/new attempt; New conversation preserves old history. Label each consequence correctly. Editing an earlier message starts an explicit retained branch. Show confirmed action receipts even when refresh or subsequent work fails.

Use one typed route registry for desktop/mobile navigation, docs links, suggestions and context chip. Show source label/revision on inspection. Context off removes future implicit context, while explaining earlier history. A native result uses actual record UI, authorized internal routing and targeted cache refresh. Keep raw SDK JSON out of primary decision flows.

Make the mobile entry discoverable with a label or navigation item and an accessible name; icon target starts at 44px. Provide visible close in addition to swipe. Protect text-selection/composer areas from drawer swipe gestures as required by the installed primitive. Avoid auto-opening the software keyboard merely to view history.

## Mobile and release evidence

Account for safe areas and keyboard/browser chrome. Use a tested VisualViewport adjustment only when target-browser behavior requires it, with symmetric listener cleanup. Test keyboard open, rotate, text selection and swipe on real hardware; emulator screenshots do not prove them.

Test 320/390/768/1024/1440px, threshold-adjacent app/chat panel widths, short landscape, 200% zoom, keyboard-only use, screen reader, contrast, forced colors and reduced motion. Verify all controls stay reachable and important table data stays inspectable. Human-help actions link to a real destination; integrated handoff previews included content before explicit submission.
