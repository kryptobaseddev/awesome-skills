# Application contracts

These are application design requirements derived from the owner's Native Chat Workspace specification. They are not SDK type declarations.

## Identity and immutable turns

Keep tenant/user, thread, accepted turn, run, tool call, action and receipt identities distinct. One user-visible turn can contain an interrupted run followed by a continuation. A transport reconnect keeps the original run; a generation retry creates an explicit attempt. Bind all access to authenticated identity, never model arguments.

At Send or queue admission, freeze a versioned context snapshot and attachment IDs. Store the snapshot with the accepted turn; preserve it on retry. Route changes update only the next composer context. Use typed route IDs and entity references, source label/revision and selected text; omit implicit route/entity fields when context is off. Explain that prior context already sent remains in history.

Resolve references under the same permission system as ordinary UI actions. Do not scrape arbitrary DOM, inputs, route queries, browser history or entire tables. Bound client bytes before parsing and resolved tokens before generation. Source starting limits are five entity refs, 4KB selected text and 12KB client envelope; these are tunable product defaults, not SDK limits. Reserve output and tool capacity in the provider's token window.

Treat retrieved content, selected text, attachments and history as untrusted data. Keep policy in server-owned instruction layers. Record context provenance, omissions and freshness. Preserve unresolved decisions, user intent, recent tool outcomes and authoritative originals when compacting history. Evaluate retrieval quality before adding an index.

## Suggested durable records

| Record | Identity/invariant |
|---|---|
| Thread | Tenant + explicit owner/share policy; membership alone grants no blanket access |
| Turn | Unique `(threadId, clientTurnId)` with request fingerprint and frozen snapshot |
| Message/parts | Stable IDs and server order; schema version; partial/terminal status |
| Run | Turn + attempt/kind + parent run; bounded one-producer admission; terminal state |
| Tool execution | Stable execution key, arguments hash, outcome and receipt |
| Approval | Actor/tenant/thread/run/action + arguments hash + entity revision + expiry |
| Attachment | Private object ID, uploader/tenant, checksum/type/size, readiness/retention |
| Context | Immutable accepted snapshot and resolved provenance/revision |
| Delivery log | Ordered per-run chunks, cursor and expiry; replay never generates |

Map these invariants onto the installed SDK persistence stores where possible. Enforce unique constraints transactionally; browser click prevention and per-process maps cannot guard races across workers. Reject reuse of the same idempotency key with a different fingerprint. Persist accepted turns before generation, checkpoint partial output at bounded intervals, and finalize confirmed outcomes.

## Tools and trusted action outcomes

Classify tools as server domain read, client navigation/presentation, draft preparation or server mutation. Start with a small read/navigation set. Shared schemas define input/output; execution-time validation and authenticated service context define authority. A browser tool cannot grant record access or execute privileged service operations.

Every server tool invokes the existing authorized application service. Bind actor/tenant from the request, apply tool and run deadlines, bound pagination/output and recheck the target revision before mutation. Do not build separate agent business rules. Keep tool implementation, result schema, app renderer and invariant tests together.

Return a structured outcome with action ID, status, readable summary, validated entity reference/revision, affected-resource descriptors and durable receipt when applicable. Map resource descriptors to registered Query keys; reject arbitrary executable callbacks or model-supplied cache keys. Native result cards reuse actual app components. Assistant prose cannot establish that a change committed.

## Approval protocol

1. Prepare the action using validated arguments and record the target revision.
2. Show target, meaningful before/after fields and consequences in the app UI.
3. Accept the user's decision through the coordinated approval service and SDK interrupt flow.
4. Bind receipt to authenticated actor/scope, original proposal, final arguments hash, revision and expiry.
5. Before execution, recheck access, receipt binding, state and entity revision.
6. Reserve execution atomically; invoke the service with an idempotency key where supported.
7. Persist confirmed result and show the receipt; duplicate decisions/execution requests return it.

Editing reviewed arguments invalidates earlier approval binding. Expired/stale proposals need a fresh review. Denial is a normal outcome, not an automatic retry signal. Use review for consequential sends, deletion, permission changes and similar mutations; reads and local navigation should remain fluid.

Stateless SDK examples may reconstruct paused calls from browser history. Production application writes still require trusted server decisions and authorization. An `approved: true` flag or altered transcript is not a receipt.

## External side effects and uncertainty

Database admission can prevent duplicate local execution, but a crash after an external commit and before recording its receipt leaves an uncertain outcome. Use downstream idempotency support and/or a queryable correlation ID. Reconcile before retry. If reconciliation is unavailable, expose the uncertainty and pause automatic mutation retries; do not promise universal exactly-once effects.

Refresh affected app records only after confirmed success. If refresh fails, keep success visible and retry refresh only. Cancellation cannot undo an already committed change. Show known action outcomes even if later work fails.

## Attachments, transport and retention

Upload to private object storage via authorized IDs. Verify count, byte sizes, MIME signatures and readiness; scan relevant formats. Reject arbitrary backend-fetch URLs; avoid base64 payloads in chat requests. Suggested initial limits: five files, 10MB each, 25MB combined; product requirements can adjust them. Keep failed uploads removable/retryable.

Authenticate fresh POST, continuation, history, GET replay, cancellation and attachment access independently. Apply appropriate origin/CSRF checks to cookie-authenticated writes. Keep streaming responses private/non-cacheable. Bound request sizes before expensive parsing; return safe public errors and correlation IDs.

Define deletion/retention for history, replay, private files, logs and backups. Do not imply immediate backup deletion without support. Clear scoped client views/subscriptions on tenant changes and sign-out; choose separately whether server runs continue, cancel or reconcile under the old authorized owner.
