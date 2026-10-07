# TanStack AI integration

## Version-first implementation

Inspect the lockfile and installed declarations for `@tanstack/ai`, the framework client, direct `@tanstack/ai-client` use, provider adapters, and any persistence/durability packages. Record exact resolved versions. Match release-specific docs and changelogs; a matching version number across packages is not itself proof of compatibility. Compile a minimal end-to-end slice using the project's TypeScript configuration and runtime.

Check current official sources when changing SDK wiring. If offline, use installed source/types and identify unresolved API assumptions. Do not install `latest` into an established project just to match a snippet. Keep secrets and provider factories in server-only modules.

## API map, checked 2026-10-05

These names are navigation aids, not a pinned compatibility matrix:

| Concern | Documented surface | Application work |
|---|---|---|
| Generation | `chat`, provider adapter, `modelOptions` | Allowlisted model policy, limits, credentials |
| HTTP parsing | `chatParamsFromRequest` | Preserve parser error Responses; validate scope before execution |
| Server delivery | `toServerSentEventsResponse` | Host streaming, durability, private response policy |
| React | `useChat`, `fetchServerSentEvents` | Persistent owner, draft state, thread switching |
| Tools | `toolDefinition`, `.server()`, `.client()` | Service permissions and registered result UI |
| Decisions | `interrupts`, bound `resolveInterrupt`, `canResolve`, `resuming` | Action review and trusted server receipts |
| History | `withPersistence` in `@tanstack/ai-persistence` | Authorized store adapter and migrations |
| Replay | Durability adapter and replay response helper | Scope checks and guarded one-time side effects |

The [streaming guide](https://tanstack.com/ai/latest/docs/chat/streaming) pairs the request parser, server stream response and client adapter. Keep that protocol end to end. Do not introduce Vercel `DefaultChatTransport` or substitute another SDK's message/stream schema into TanStack endpoints.

## Gateway algorithm — application pseudocode

This is a contract to implement, not a compilable SDK snippet:

```text
authenticate actor; bound request bytes and enforce origin policy
parse installed SDK request protocol; preserve 400 Responses
authorize thread, run, attachments and every entity reference
classify fresh turn / replay / interrupt continuation / explicit retry
if replay: authorize stored run and replay log; skip fresh side effects
if continuation: validate persisted paused decision set and admission key
if fresh/retry: reserve unique turn/attempt under thread concurrency policy
resolve bounded trusted context; reconcile history against server records
construct allowlisted provider and tools bound to actor scope
run installed SDK, persistence and delivery adapters
checkpoint output; record terminal outcome or reconcile producer loss
```

Explicitly forward the installed protocol's resume payload on continuation. Blindly spreading all parsed browser parameters into `chat()` would allow client values to influence policy. Reconcile client-supplied assistant/tool history before consequential execution.

## Persistent client and UI parts

Keep one controller for a thread above the route outlet. A stable connection object and thread identity should survive view dismissal, docking and portals. Hydrate authorized history before activating a restored controller; prevent a background query from overwriting live messages. Coordinate thread switches and reattachment explicitly.

Render SDK discriminated message parts, preserving IDs, versions, order and tool results. Inspect installed part unions instead of inventing `content` or `text` fields. Unknown parts get a safe visible fallback. Keep server tool definitions free of secret imports when sharing schemas with the browser.

The [connection adapter guide](https://tanstack.com/ai/latest/docs/chat/connection-adapters) documents transports and per-call forwarded data. Freeze context and ready attachment IDs before sending; confirm the selected release's per-call body mapping through a round-trip test. Do not assume a generic reload helper resends earlier per-call context. Default to same-origin SSE; consider NDJSON, native transports or WebSockets only for the target runtime's actual needs.

## Interrupts and mutations

The [tool approval guide](https://tanstack.com/ai/latest/docs/tools/tool-approval) uses bound interrupts and deprecates `addToolApprovalResponse`. Narrow by interrupt kind and disable decisions while unbound or resuming. Render readable action consequences rather than raw arguments. Current docs distinguish result output from the tool-call lifecycle; do not wait for an assumed tool-call `complete` state without checking the installed model.

The [interrupt lifecycle](https://tanstack.com/ai/latest/docs/interrupts/overview) separates interrupted execution from continuation. Preserve pending decision lineage. Verify multiple-interrupt batching and edited arguments against the installed API. Rebind app approval receipts to the final validated arguments before a mutation executes.

## Persistence and delivery choices

The [chat persistence guide](https://tanstack.com/ai/latest/docs/persistence/chat-persistence) documents `withPersistence`: a messages store plus optional run and interrupt stores, with interrupts depending on runs. Evaluate that surface before writing a separate conversation engine. Keep tenant access, action receipts, context snapshots, quotas and retention in application contracts. Follow the selected adapter's full-overwrite and insert-if-absent requirements; test contention and migrations.

The [client persistence guide](https://tanstack.com/ai/latest/docs/persistence/client-persistence) covers server-authoritative hydration and client storage modes. Choose one authority for history. Do not silently cache sensitive transcripts in local storage; namespace and clear any permitted local data by user/tenant.

The [resumable stream guide](https://tanstack.com/ai/latest/docs/resumable-streams/overview) separates event replay from saved conversation history. In-process memory is development-only for cross-instance recovery. Use a shared supported adapter or verify a custom adapter. Build it once per request, detect reconnect before one-time writes, and reuse it for delivery. GET replay does not normally restart a dead producer; producer recovery is a separate runner contract.

## Upgrade procedure

Capture baseline fixture transcripts, tool/interrupt states, persistence migrations, transport behavior and runtime checks. Change a compatible package set together, compile, replay fixtures, test recovery/auth boundaries and deploy behind a reversible flag. Record API conflicts and the installed-source resolution. Avoid asserting a docs example is production-ready until the app's integration points and tests exist.
