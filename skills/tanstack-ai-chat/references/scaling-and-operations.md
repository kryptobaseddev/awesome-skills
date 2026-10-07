# Scaling and operations

This guide extends the owner's specification with workload-driven engineering methods. Capacity examples are assumptions to measure, not vendor guarantees or universal production limits.

## Start with a workload model

Collect peak accepted turns/second, concurrent connected clients versus generating runs, mean/p95/p99 run duration, provider tokens/request, tool latency, attachment volume, replay frequency and tenant distribution. State whether figures are measured or projected. Include both burst and sustained workloads; long generations make connection counts diverge from ordinary request counts.

Estimate active runs with Little's Law: `concurrency ≈ accepted arrival rate × mean run duration` for a stable system. For example, 20 turns/s × 15s means about 300 active runs before headroom; 2,000 connected viewers do not imply 2,000 simultaneous generations. Percentile latency cannot be substituted mechanically for the mean. Validate with a measured traffic mix and host limits.

Estimate token throughput using actual input/output averages and multiple provider calls per tool loop. Provider RPM/TPM quotas, tool service limits, database connection pools, event-store bandwidth and runtime duration may constrain capacity before CPU. Do not quote a capacity number without its workload, environment and bottleneck assumptions.

## Architecture progression

| Stage | Fit | Required behavior |
|---|---|---|
| Request-bound development | One process, no recovery promise | Bounded runs, explicit failure, local/mocked dependencies |
| Production service | Multiple instances; reconnect required | Shared authoritative records/log, atomic admission, quotas, cancellation, producer-loss reconciliation |
| Durable runner | Work must outlive request/host | Queue/worker separation, leases/fencing, checkpoint policy, outcome reconciliation |
| Specialized infrastructure | Proven retrieval/realtime/isolation need | Add vector search, sockets or specialized workers only for that measured requirement |

Reuse supported SDK middleware/adapters before designing equivalents. Horizontal HTTP scaling requires shared state; sticky routing is insufficient for deployment/failure recovery. An event log is not a generator checkpoint. Confirm whether the chosen durable runner can actually recover provider/tool progress; do not advertise takeover for arbitrary chat runs based on sandbox-specific APIs.

## Admission, fairness and backpressure

- Admit at most one active producer per thread by default. Enforce user and tenant concurrency and token budgets in shared state; the source suggests four runs/user and eight tool steps as initial tunable policy.
- Separate connected replay subscribers from generation slots. Cap fanout and slow-consumer buffers so many viewers cannot create unbounded memory.
- Bound queue length, wait and request age. Use per-tenant fair scheduling or weighted quotas so one tenant cannot monopolize workers. Reserve capacity for manual app services.
- Reject or defer before expensive provider/tool work. Return meaningful 409/429/503 states and permitted retry guidance; do not loop client retries aggressively.
- Freeze queued context at queue time. Expose queued/cancellable state and revalidate permission/revision at execution.
- Apply backpressure to the producer where supported; otherwise disconnect slow viewers with an authorized replay path. Bound batching and preserve chunk order/terminal events.

For worker execution, persist admission/enqueue intent atomically, often through a transactional outbox. Use an expiring lease plus a monotonically increasing fencing token so stale workers cannot overwrite state after takeover. Lease ownership alone cannot fence an external provider; external actions still need idempotency and reconciliation.

## Retries, cancellation and failures

Use capped exponential backoff with jitter for safe transient delivery/store operations. Apply deadlines and total retry budgets. Retry provider generation only after classifying whether work started and whether restarting is allowed; do not automatically regenerate partial output under a delivery error. Never blindly replay an uncertain mutation.

| Failure | Recovery |
|---|---|
| Delivery drops | Replay same run/cursor, zero new provider invocation |
| Log expires | Load durable partial history; expose explicit retry if appropriate |
| Producer dies | Reconcile lease/status; preserve partial output; mark interrupted or invoke a verified takeover mechanism |
| Database/receipt store unavailable | Fail admission and consequential actions; preserve draft |
| Durability store unavailable | Fail or expose an explicit policy-approved non-resumable downgrade |
| Provider outage | Circuit-break new generation; preserve history/manual UI; reevaluate before reopening |
| Action timed out | Inspect downstream receipt/correlation ID before any retry |
| Cancellation requested | Abort supported provider/tool work; await confirmed terminal outcome |

Keep close, cancel-requested, cancelled, failed, interrupted and completed outcomes distinct. Drain active producers during deploys where possible; document hard runtime timeouts and graceful failure behavior. Stop remains available when the stream disconnects through an authenticated cancellation command.

## Cost and context efficiency

Track cost by tenant, turn, run, provider/model and tool cycle using actual reported usage; record incomplete usage as unknown. Reserve estimated spend/tokens at admission, reconcile actual usage and bound overruns. Price tables must be checked against the selected provider's current official source when estimating spend.

Choose model tiers using the task corpus, latency and verified action quality. Use routing and provider fallback only under server policy and compatible capability/data-processing requirements. A cheaper model that causes tool retries may cost more per completed task. Avoid speculative duplicate provider calls to improve perceived speed unless their cost and race semantics are explicitly intended.

Bound histories and retrieval output, summarize with provenance, deduplicate context and paginate tool reads. Keep unresolved decisions and authoritative tool outcomes. Cache safe deterministic reads or retrieval results with tenant/user authorization, policy/schema version, data revision and expiry in the key. Do not reuse private context across tenants or cache authorization decisions beyond their validity. Evaluate provider prompt caching separately and verify its current semantics.

## Frontend scaling

Profile before virtualizing. Keep token updates scoped to the active message, memoize stable registries, lazy-load heavy renderers and batch visual updates without delaying final outcomes. Measure long transcripts and simultaneous route interaction. Virtualization must preserve variable-height anchors, selection, keyboard focus and assistive reading. Avoid a full Markdown parse and layout measurement of the entire transcript on every token.

## Observability and release

Measure p50/p95/p99 submit-to-accept, first visible answer, queue wait, total run/tool time, replay success, provider invocation count, cancellation acknowledgment, uncertain action age, duplicate attempts, cache-refresh errors, token/cost per successful task, event-log lag/bytes and pool saturation. Track panel-open latency, resize frame times and long tasks separately from backend latency.

Correlate tenant-safe thread/turn/run/tool/action/receipt IDs. Instrument gateway admission, auth decisions, store writes, provider/tool calls and domain commits; SDK traces alone do not cover the app. Default telemetry excludes prompt bodies, selected text, credentials and private files. Redact content diagnostics and limit access.

Declare service objectives from product needs, then use dashboards and burn-rate alerts tied to those objectives. Run smoke, ramp, sustained, burst, slow-consumer and soak workloads with a realistic traffic mix; count duplicate calls/commits and test another-instance replay, store outage, worker death, quota exhaustion and deploy drain. Test transports behind the real proxy/CDN for buffering, compression and timeouts.

Roll out shell, reads, durability and writes independently with flags. Rollback must disable new actions while preserving old history/receipts. A scale proposal ends with the measured bottleneck, smallest justified intervention, proof criteria and recovery path.
