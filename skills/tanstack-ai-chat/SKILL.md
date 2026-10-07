---
name: tanstack-ai-chat
description: Build, debug, scale, and review production AI chat agents with TanStack AI. Use when integrating @tanstack/ai, useChat, streaming chat, tool calls or approval interrupts; building a persistent route-aware assistant workspace; fixing reconnect duplicates, lost drafts, chat resizing or mobile UX; or planning multi-tenant chat reliability, throughput, cost controls, persistence, and observability. Covers native React UX/UI, authorized domain actions, durable delivery, and measured scaling. Apply even when the request only says "add an assistant to our dashboard" or "make our AI chat production-ready". Preserve an explicitly chosen alternative SDK; use its APIs instead of mixing protocols. Do not use for ordinary non-AI messaging or unrelated TanStack tables, forms, or queries.
metadata:
  author: kryptobaseddev
  version: "1.0.0"
  last_updated: "2026-10-05 14:50:09"
  category: ai
---

# TanStack AI Chat

Build an assistant as a persistent application capability. Keep the conversation runtime independent of routes and panel geometry; keep authorization and side effects in existing application services. Deliver the requested working slice or evidence-based review, rather than stopping at a generic architecture proposal.

## Load only the relevant references

| Work | Read |
|---|---|
| SDK integration, migration, debugging | [TanStack integration](references/tanstack-integration.md) |
| Context, tools, approvals, records | [Application contracts](references/application-contracts.md) |
| Throughput, reliability, cost, deployment | [Scaling and operations](references/scaling-and-operations.md) |
| Shell, composer, responsive behavior, accessibility | [Workspace UX/UI](references/workspace-ux.md) |
| Testing, review, release | [Verification](references/verification.md) and [implementation checklist](references/implementation-checklist.md) |
| Origin or conflicting source claims | [Source notes](references/source-notes.md) |

Use [workspace-reference.css](assets/workspace-reference.css) as an optional Tailwind CSS 4 starting asset. It needs compilation, runtime size clamping, and product theme adaptation. It is not a ready-made chat component.

## 1. Establish the task and evidence

Inspect repository instructions, application shell, auth/services, package manifests and lockfile, chat routes, existing schemas, and relevant tests before editing. Separate observed behavior, documented SDK capability, application policy, and assumptions. Confirm the installed exports/types against version-matched official docs; `latest` is a moving reference, not a compatibility guarantee.

Infer these choices from the project before asking for missing information:

- Deliverable: implement, repair, review, or plan; existing application or new project.
- Framework and host; provider/model policy; personal versus shared threads.
- Required read/write tools, attachments, context, reconnect and producer-survival guarantees.
- Workload: concurrent generations, arrival rate, typical/long-tail duration, context size, tenant fairness, and provider quotas.
- UX requirements and design system; support destination; retention/privacy policy.

For a new project, default to TypeScript, React, TanStack Start/Router, Query for server records, app-owned UI, and same-origin SSE. Keep an existing framework and design system. Provider, database, production durability backend, hosting, sharing, and retention are adapter decisions; make reversible progress with mocks when those choices are unavailable. Ask only for decisions that materially block the requested work. Do not force a framework migration or install global tooling just because a documentation recipe suggests it.

## 2. Establish responsibility boundaries

Design this path: app shell and context registry → one persistent SDK client per active thread → authenticated chat gateway → bounded server orchestration → provider and authorized domain services → durable records and delivery log → validated UI/cache updates.

| Owner | Responsibility |
|---|---|
| Shell | Open/close, dock, geometry, preferences, focus |
| SDK client/controller | Live messages, connection, interrupts, send/stop/reattach |
| Query/repository | History lists and durable server/domain records |
| Context registry | Typed route/entity descriptors and selections |
| Gateway | Auth, validation, admission, replay/continuation routing |
| Policy and services | Provider allowlist, tool budgets, domain permissions, receipts |
| Stores and runner | Persistence, ordered delivery, cancellation, lease reconciliation |

Mount the controller above routed content and outside drawer/exit-animation lifetimes. Rehost views without creating a second client. Do not maintain another live-token reducer in Query. Clear tenant-scoped client state and subscriptions when identity changes.

## 3. Implement a complete vertical slice

For new implementations, work in this order with explicit exit evidence. For a repair, select the affected slice and inspect surrounding invariants instead of rebuilding everything.

1. **Shell:** shared tokens, labeled launcher, right/bottom/mobile presentation, bounded scroll regions, keyboard resizing. Use mock parts; verify container responsiveness and focus.
2. **Chat:** compatible pinned SDK packages, authenticated gateway, stable thread, streaming text, errors, Stop, accepted-turn and partial/terminal persistence. Compile wiring against installed types.
3. **Context/read tools:** visible route chips, immutable send/queue snapshots, scoped entity resolution, provenance, one registered domain result renderer.
4. **Recovery:** history hydration, shared stream durability, replay authorization, database duplicate guards, cancellation acknowledgment, producer-loss reconciliation.
5. **Mutations:** readable action review, bound interrupts, server approval receipts, revisions, idempotent service execution, confirmed outcomes, targeted cache refresh.
6. **Production:** load and fault testing, model quality corpus, responsive/device/accessibility evidence, telemetry redaction, staged rollout and rollback.

Use SDK persistence, middleware, and locking adapters when the selected version supplies the needed guarantees; extend application policy around them. Avoid parallel home-grown copies of the same authoritative state. A prototype can defer durable recovery or writes, but label that boundary accurately.

## 4. Preserve invariants through every change

- **Close ≠ Stop.** Close hides presentation. Stop requests server cancellation; report acknowledgment and any committed action.
- **Reconnect ≠ Retry ≠ continuation.** Replay retains the original run without a new provider call; retry starts an explicit new attempt; interrupt resolution starts a continuation linked to the interrupted run.
- **History ≠ delivery durability ≠ producer survival.** Test each promised guarantee separately. Shared stream storage alone cannot restart a dead generator.
- **Context is data.** Freeze at send/queue time, resolve references under server permissions, preserve retry snapshots, and keep already-sent context visible. Turning context off changes future payloads.
- **Approval is not authorization.** Bind server decisions to actor, tenant, thread/run, action, argument hash, entity revision, and expiry; recheck before writes.
- **Receipt is the outcome.** On unknown external results inspect first; on cache-refresh failure retry the refresh, not the action. Do not claim universal exactly-once external execution.
- **Scale follows measurement.** Bound concurrency, queue capacity, tools, tokens, payloads, and time. Enforce tenant fairness and provider quotas across instances.
- **Chat belongs to the app.** Use shared UI primitives, typed parts, named containers, stable scroll anchors, IME-safe sending, and modality-appropriate focus.

## 5. Verify what the task promises

Select relevant scenarios from the verification guide. Compile SDK code and generated CSS; test runtime identity, auth, idempotency, recovery, and UI interactions. Count provider invocations and domain commits during duplicate/reconnect tests. Screenshots cannot prove these backend invariants.

For scaling work, state the workload, bottleneck evidence, capacity assumptions, metrics, intervention, and rollback. Separate targets from measurements. For UI work, inspect rendered behavior including narrow panel widths, overflow, focus and streamed updates. Browser emulation cannot prove physical keyboard/swipe behavior or screen-reader usability.

Report unavailable checks and unassessed coverage explicitly. Never label an illustrative snippet, unexecuted scenario, or successful static check as a production release pass.

## 6. Return a concrete result

Match the requested output:

- **Implementation/repair:** changed artifacts, resulting behavior, checks run, material limitations.
- **Review:** severity, file/location, trigger, evidence, user impact, bounded correction, verification; mark uncertain findings as unverified.
- **Architecture/scaling plan:** responsibilities, lifecycle/data contracts, capacity assumptions, failure recovery, UX behaviors, phased work with exit checks, unresolved owner choices.

Keep product UI focused on meaningful user actions and outcomes. Keep internal SDK names, raw JSON, and infrastructure diagnostics in developer evidence unless they help the user decide.
