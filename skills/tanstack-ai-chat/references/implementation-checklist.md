# Native Chat Workspace — implementation checklist

Use with the [verification guide](verification.md). Items are release evidence to collect, not checks already completed. TanStack AI is the chosen runtime; the shell and domain infrastructure remain application-owned.

## Architecture and package baseline

- [ ] Pin compatible TanStack AI/core/client/React/provider packages and record versions.
- [ ] Compile current SDK examples; use interrupts/resolveInterrupt rather than deprecated approval APIs.
- [ ] Keep the conversation controller above route content and outside drawer/animation lifetime.
- [ ] Assign one mounted SDK client per active thread; separate layout preferences and server state.
- [ ] Keep model policy, tools, credentials, and tenant authorization on the server.

## Shell and CSS

- [ ] Configure Tailwind CSS 4 semantic tokens; verify generated custom utilities.
- [ ] Use named app/chat inline-size containers; test nested container behavior.
- [ ] Distinguish viewport mode selection from panel-content breakpoints.
- [ ] Implement closed, right, bottom, mobile-sheet, and constrained-height behavior.
- [ ] Clamp sizes against actual available space and preserve desktop dock preference on mobile.
- [ ] Implement pointer and keyboard resizing with labeled ARIA separators.
- [ ] Bound app/transcript scroll regions with min-height:0 and min-width:0.
- [ ] Keep header/composer reachable and menus outside clipped panels.
- [ ] Reuse route metadata for navigation, docs footer, suggestions, and context chips.
- [ ] Restore focus and retain draft/scroll position through docking and dismissal.

## Chat UX

- [ ] Render typed message parts through shared app components.
- [ ] Freeze context/attachments at send or queue time; preserve retry snapshots.
- [ ] Distinguish Close, Stop, Retry, Resume, and New conversation.
- [ ] Implement IME-safe Enter/Shift+Enter behavior and mobile textarea sizing.
- [ ] Preserve drafts, uploads, and partial output on recoverable errors.
- [ ] Follow streaming only near bottom; preserve reading anchors and expose Jump to latest.
- [ ] Show accurate tool/progress outcomes and safe unsupported-part fallbacks.
- [ ] Provide discoverable mobile entry and explicit human-help destination.

## Context and domain actions

- [ ] Register typed route/entity context; avoid arbitrary DOM/page scraping.
- [ ] Make context off affect future payloads and explain already-sent history.
- [ ] Resolve entity references under authenticated permissions and record provenance/revision.
- [ ] Reuse normal application services for every server tool.
- [ ] Review action arguments and bind approval receipts server-side before mutation.
- [ ] Validate stale revision, approval input hash, expiry, and actor scope.
- [ ] Execute actions idempotently; inspect uncertain outcomes before retry.
- [ ] Refresh only validated affected domain resources after confirmed success.

## Records and transport

- [ ] Persist accepted turns, ordered/versioned parts, partial/terminal outputs, and run state.
- [ ] Enforce unique thread/clientTurn IDs and run/action execution identities.
- [ ] Adopt shared production stream durability; keep message history separate from event replay.
- [ ] Authenticate GET replay and POST continuation against stored scope.
- [ ] Guard one-time writes, title generation, and usage records from reconnect duplication.
- [ ] Add cancellation acknowledgment and producer-loss reconciliation.
- [ ] Use private attachment IDs, upload readiness, size/type limits, and defined retention.
- [ ] Verify proxy/host streaming, timeouts, deployment behavior, and feature-flag rollback.

## Release evidence

- [ ] Run A01–A25 from the verification guide with recorded outcomes.
- [ ] Test 320/390/768/1024/1440px, threshold-adjacent panel widths, and 200% zoom.
- [ ] Test physical mobile keyboard, orientation, touch selection, and swipe dismissal.
- [ ] Test keyboard-only, screen reader, reduced motion, contrast, and forced colors.
- [ ] Prove reconnect creates no duplicate provider invocation or domain mutation.
- [ ] Prove malicious context/history/approval changes cannot grant authority.
- [ ] Measure stream latency, replay success, cancellation, and frontend responsiveness.
- [ ] Record provider/model, hosting, durability store, sharing policy, retention, and support decisions.
- [ ] Publish evidence and limitations; keep private screenshot/account content out of public examples.
