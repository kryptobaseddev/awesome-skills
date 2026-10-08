---
name: quo
description: "Build Quo (formerly OpenPhone) integrations and LLM agent tools on the Quo REST API, webhooks and MCP server: SMS send and receive, group texts, calls with AI summaries, transcripts and voicemails, contacts, conversations, tasks, users and phone numbers, on both API versions (v1, the only way to send, and header-versioned 2026-03-30). Ships a type-checked TanStack AI tool kit (Zod tools, approval-gated sends, inbox allowlists, 10 req/s limiter), a scaffolder, a webhook verifier and a client. Use when building an assistant or agent that texts customers, reads a phone inbox, triages missed calls, analyses calls, syncs contacts or schedules reminders; when adding SMS, inbound-text webhooks or call data to an app; or when fixing an app's texting, messages endpoint or call-data code, even if the user never says Quo or OpenPhone ('when someone texts our clinic line', 'our /api/messages refetches'). Not for Twilio, Vonage or WhatsApp APIs, email, or TanStack chat without phone data."
license: MIT
compatibility: >-
  Bundled scripts need Node 18+ (built-in fetch + node:crypto) and/or Python
  3.8+ stdlib, plus bash + curl for preflight. The TanStack AI kit in
  assets/tanstack-ai/ is TypeScript checked against @tanstack/ai 0.66,
  @tanstack/ai-react 0.30 and zod 4. Integrations target any stack that makes
  HTTPS calls. A Quo workspace owner/admin generates the API key; US SMS also
  requires A2P 10DLC registration.
inputs:
  - name: QUO_API_KEY
    description: "Quo (OpenPhone) API key, sent RAW in the Authorization header (no 'Bearer ' prefix). Generate at Quo workspace, Settings, API (owner/admin only). Keys have full workspace access and no scopes, so give each integration or agent its own named key. The legacy var OPENPHONE_API_KEY is also accepted by the bundled scripts."
    required: true
  - name: QUO_WEBHOOK_KEY
    description: "Webhook signing secret, prefixed 'whsec_'. Returned ONLY by POST https://api.quo.com/webhooks (data.key) and by rotate; store it immediately. Used solely to verify inbound webhook signatures."
    required: false
  - name: QUO_BASE_URL
    description: "Optional host override. Default https://api.quo.com (v1 under /v1, 2026-03-30 unprefixed). The legacy host api.openphone.com serves v1 only."
    required: false
metadata:
  author: github.com/kryptobaseddev
  version: "2.0.0"
  last_updated: "2026-10-08 16:25:00"
  category: communication
allowed-tools: Bash Read Write Edit Glob Grep WebFetch
---

# Quo (formerly OpenPhone): REST API, webhooks and agent tools

Quo is the rebranded OpenPhone business phone system. Its API lets software
send and read **SMS**, pull **calls** with AI **summaries, transcripts and
voicemails**, manage **contacts** (plus notes and properties),
**conversations**, **tasks**, **users** and **phone numbers**, and react to
**webhooks**. This skill covers three ways of building on it:

1. **App integrations:** server code that texts customers, syncs contacts or ingests call data.
2. **LLM agent tools:** an assistant that works the inbox through structured tool calls. A ready-made TanStack AI kit ships in `assets/tanstack-ai/`.
3. **Quo's hosted MCP server:** for Claude or ChatGPT acting as a Quo user, with no code.

## Two live API surfaces: pick per operation

Both are on host `https://api.quo.com` and use the same raw-key auth. The
OpenAPI specs are the ground truth: [v1](https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json) and
[2026-03-30](https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-2026-03-30-prod.json).

| | v1 | 2026-03-30 (current) |
|---|---|---|
| Paths | `/v1/messages`, `/v1/calls`, ... | `/messages`, `/calls`, ... (no prefix) |
| Version header | none | `Quo-Api-Version: 2026-03-30`, **required** (400 without it) |
| Lists | `maxResults` + `pageToken` → `nextPageToken` (`totalItems` unreliable); often require `phoneNumberId` + `participants` | `limit` 1–50 + `after` → `nextCursor`; workspace-wide, all filters optional |
| Filters | plain params; arrays as repeated keys | `field=value`, `field[in]=a,b`, range ops; AND across params. **Operators differ per endpoint**: `/calls` and `/conversations` take `createdAt[gte]/[lte]`, `/messages` only `createdAt[gt]/[lt]`. A wrong operator is a 400; check the endpoint's reference |
| Errors | `{ message, code, ... }` or gateway `{ error: { message, key, trace } }` | `{ title, message, docs, trace?, errors[{ path, message, value, schema }] }` |
| Only here | **send SMS** (`POST /v1/messages`), standalone call summary/transcript/voicemail routes, contact custom-field definitions, task create linked to a phone number or activity | message **retry**, `include=summary,voicemail` on calls, contact **notes/properties/shares**, organization, available-number search, webhook delivery log, retry and test, `task.*` webhooks |

**Default to 2026-03-30 for everything it covers; use v1 to send and for the
v1-only rows.** Version 2026-03-30 is frozen: new endpoints and fields arrive
without a version bump, so ignore unknown response fields. Details are in
`references/api-basics.md`.

## Facts that prevent broken work

| Fact | Consequence |
|---|---|
| Auth is the **raw key**: `Authorization: KEY`. Quo uses no Bearer token | `Bearer ...` → 401 |
| Sending is **v1 only** and returns **202 queued** | Delivery arrives later (`message.delivered` / `message.failed` / `message.undelivered` webhooks). Status `undelivered` is terminal; only `failed` messages can be retried (`POST /messages/{id}/retry`) |
| `to` takes **1–10** E.164 numbers, but **2+ creates ONE group thread** where everyone sees every number | For private bulk messages, send one at a time under the rate limit |
| **No idempotency key** on send | Never auto-retry a send after a timeout or 5xx. Look it up (`GET /messages?to=…&createdAt[gt]=…`) before resending |
| **10 requests/second per key**, across every process using it | One client (one limiter) per process, injected everywhere in that process: webhook handlers, workers and tools. A second client in the same process doubles the budget silently. Split `maxRps` across processes, inject a shared (Redis) limiter, or use one key per integration. Prefer `limit=50`, `include=` over N+1 and webhooks over polling |
| US SMS needs **A2P 10DLC** registration | `400 0206400` = not registered (not a bad body); `403 0204403` = daily cap reached |
| Summaries and transcripts need a **Business or Scale** plan and are **async** | Check `summary.status` / transcript `status` (`absent`, `in-progress`, `completed`, `failed`); prefer `call.summary.completed` / `call.transcript.completed` webhooks |
| **v1 `PATCH /v1/contacts/{id}` replaces** phones, emails and custom fields; anything omitted is deleted | Use 2026-03-30 `PATCH /contacts/{id}` (scalars only) plus per-item **properties**, or GET → merge → PATCH the full object |
| Contacts **cannot be searched by phone or name**, only by `externalId`/`source` | Store `externalId` on create and keep your own phone→contact index |
| Integration-synced contacts (CRM sources) are **read-only** via the API | Change them in the source system |
| **Webhooks**: 2026-03-30 uses Standard Webhooks (`webhook-id`, `webhook-timestamp`, `webhook-signature: v1,…`, `whsec_` secret); v1 uses a different `openphone-signature` header | Verify the **raw** body. Dedupe on the `webhook-id` header (not the envelope id) and keep ids ≥28h; deliveries retry and can arrive out of order |
| Ids are prefixed: `PN` number, `US` user, `SYU` AI/system actor, `CN` conversation, `AC` call or message, `TK` task, `VM` voicemail, `OR` org. Contact ids have **no** prefix | Validate prefixes in tool schemas and treat ids as opaque |
| No scheduled-send endpoint exists | Scheduling = your job queue calling `POST /v1/messages` at send time |
| "Missed" is not one status | An unanswered incoming call can be `missed`, `no-answer`, `abandoned`, `busy`, `canceled` or `completed`. Test incoming + no `answeredAt` + not `aiHandled` + not forwarded |

## Building agent tools (TanStack AI)

For an LLM agent that reads the inbox, triages calls, updates contacts or texts
customers, **start from the bundled kit** rather than writing tools from scratch.
It is compiled against `@tanstack/ai@0.66` and has an offline contract test.

```ts
// server only: the tools hold the API key
import { chat, maxIterations, toServerSentEventsResponse } from '@tanstack/ai'
import { createQuoClient } from './quo-client'     // copied from assets/tanstack-ai/
import { createQuoTools } from './quo-tools'

const quo = createQuoClient({ maxRps: 8 })          // module scope: one limiter per process

const stream = chat({
  adapter, messages, threadId, runId, resume,       // resume carries approval answers
  tools: createQuoTools(quo, { allowedInboxIds: ['PNsupport01'], maxRecipientsPerSend: 1 }),
  toolExecution: 'sequential',                      // keep under 10 req/s, predictable read→write
  agentLoopStrategy: maxIterations(8),
})
return toServerSentEventsResponse(stream)
```

What the kit enforces, and why:
- **Sends need human approval** (`needsApproval: true` on `quo_send_message` / `quo_schedule_message`). `execute` still re-checks the inbox allowlist and recipient cap, because approval is consent, not authorization.
- **Strict schemas**: E.164 and id-prefix regexes, discriminated unions for task actions and link targets. A bad call fails before reaching Quo, with a message the model can act on.
- **Errors return as data** (`{ ok: false, issues[{path}], hint, trace }`), so the model fixes the call. A send with an unknown outcome returns "do not resend, check first".
- **Compact outputs** with customer text labelled `untrusted*`, because SMS bodies and transcripts can carry prompt injection.
- **One approval, one send:** a send ledger keyed by tool-call id blocks replayed approvals. It is in memory by default; use a DB unique key in production.
- **No delete tools**, and no tool sends partial v1 contact arrays.

Read `references/agent-tools-tanstack.md` for the full catalog (18 tools, the
endpoint and surface each uses), approval UI, the four integration patterns
(message automation, contact management, call analytics, scheduling), how to
extend it, and evaluation. Copy files from `assets/tanstack-ai/`, or emit them
with `node scripts/scaffold-quo.mjs --agent-tools`. Verify a copy with
`npx tsx quo-tools.test.ts`.

For the chat gateway around it (persistence, reconnect, thread ownership,
durable delivery, chat UX), use the `tanstack-ai-chat` skill if it is installed.
If the user names another agent SDK, keep the same tool contracts (schemas,
approval, policy re-check, errors as data) and port the definitions to that SDK.

**MCP alternative:** if the goal is Claude or ChatGPT working one person's Quo
inbox, Quo hosts an MCP server at `https://mcp.quo.com/mcp` (OAuth, acts as that
user, 19 tools). TanStack apps can attach it via `chat({ mcp })` but must run
the OAuth flow themselves. See `references/mcp.md` for the decision table.

## Preflight

```bash
bash scripts/quo-preflight.sh            # node/curl, QUO_API_KEY, the Bearer mistake
bash scripts/quo-preflight.sh --probe    # live GET /organization with the version header (200 vs 401/400)
```

## Scaffold an app integration

`scripts/scaffold-quo.mjs` writes a runnable Express app: an API client, a
send-SMS route, a **signature-verified** webhook receiver, and a vanilla or React
frontend. The client and verifier are inlined, so the output has no dependency
on this skill.

```bash
node scripts/scaffold-quo.mjs --out ./quo-app                  # vanilla frontend
node scripts/scaffold-quo.mjs --out ./quo-app --frontend react
node scripts/scaffold-quo.mjs --out ./quo-app --agent-tools    # + server/quo-agent/ TanStack kit
```

## Quick start: send an SMS (v1)

```bash
curl -X POST https://api.quo.com/v1/messages \
  -H "Authorization: $QUO_API_KEY" -H "Content-Type: application/json" \
  -d '{"from":"PNabc123","to":["+15555550111"],"content":"Your order shipped."}'
# 202 → { data: { id: "AC…", conversationId: "CN…", status: "queued", ... } }
```

`from` is a `PN…` id or that number in E.164. `content` is 1–1600 characters
and not whitespace-only. `setInboxStatus: "done"` files the conversation as
done. Sending MMS is not supported. In Node, `scripts/quo-client.mjs` has
`sendMessage()`, which requires `group: true` before it sends to more than one
recipient.

## Quick start: read with 2026-03-30

```bash
curl "https://api.quo.com/calls?status%5Bin%5D=missed,no-answer&createdAt%5Bgte%5D=2026-10-07T00:00:00Z&include=summary,voicemail&limit=50" \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30"
# { data: [...], nextCursor: "…" | null }. Pass ?after=<nextCursor> for the next page.
```

URL-encode `+` in E.164 filter values as `%2B`.

## Quick start: receive a verified webhook

```ts
import express from 'express'
import { verifyQuoWebhook } from './verify-webhook.js'   // scripts/verify-webhook.js

app.post('/webhooks/quo', express.raw({ type: '*/*' }), (req, res) => {
  if (!verifyQuoWebhook(req.headers, req.body, process.env.QUO_WEBHOOK_KEY)) return res.status(400).end()
  const deliveryId = req.headers['webhook-id']            // idempotency key
  const event = JSON.parse(req.body.toString())           // { id, type, data: { resource, ... } }
  queue.add(event.type, event, { jobId: String(deliveryId) })   // ack fast, work async
  res.status(200).end()
})
```

Create the subscription with `POST https://api.quo.com/webhooks` (header
`Quo-Api-Version: 2026-03-30`, body `{ url, events: [...] }`) and save
`data.key` (`whsec_…`) immediately. Test without traffic using
`POST /webhooks/{id}/events/test`, and offline with
`node scripts/verify-webhook.js --selftest`. Event catalog, delivery log and
retries are in `references/webhooks.md`.

## Reference map

Read only what the task needs. Each file covers both surfaces, cites its
sources, and has a contents list.

| Task | Read |
|---|---|
| Agent tools, TanStack AI wiring, approvals, automation, contact, analytics and scheduling patterns | `references/agent-tools-tanstack.md` |
| Hosted MCP server, OAuth for custom clients, MCP vs own tools | `references/mcp.md` |
| Surfaces, auth, versioning, pagination, filters, errors and codes, rate limit, endpoint inventory | `references/api-basics.md` |
| Send, list and retry messages, group sends, phone numbers, available numbers, organization | `references/messages-and-numbers.md` |
| Calls, recordings, transcripts, summaries, voicemails, plan gating, analytics recipe | `references/calls.md` |
| Contacts, custom fields, notes, properties, shares, upsert-by-externalId sync | `references/contacts.md` |
| Conversations (sync, sort, mark read/done/open), tasks, reminders recipe | `references/conversations-and-tasks.md` |
| 2026-03-30 webhooks: events, payloads, signatures, deliveries, retries, test | `references/webhooks.md` |
| Legacy v1 webhooks, users | `references/webhooks-v1-and-users.md` |
| Pricing and segments, A2P 10DLC registration, cost control | `references/ai-cost-and-registration.md` |

## Bundled files

| Path | Purpose |
|---|---|
| `assets/tanstack-ai/` | TanStack AI kit: `quo-client.ts`, `quo-tool-defs.ts`, `quo-tools.ts`, `chat-route.example.ts`, `send-approval.example.tsx`, `quo-tools.test.ts` |
| `scripts/scaffold-quo.mjs` | Generate an Express + frontend integration; `--agent-tools` adds the kit |
| `scripts/quo-client.mjs` | Dependency-free JS client and CLI for both surfaces (`v2()`, `paginateV2()`, `sendMessage()`, `paginate()`); retries GETs only |
| `scripts/verify-webhook.js`, `scripts/verify_webhook.py` | Standard Webhooks verification (`whsec_`, raw body, 5-minute tolerance, rotation); `--selftest` |
| `scripts/quo-preflight.sh` | Tooling and key checks; `--probe` makes one live authenticated call |

## Common mistakes

| Mistake | Fix |
|---|---|
| `Authorization: Bearer KEY` | Send the raw key |
| Calling `/calls` without `Quo-Api-Version`, or `/v1/...` with it expecting new behaviour | Unprefixed paths need the header; `/v1` paths ignore it |
| Several numbers in one send for a "bulk" message | That creates a group thread; send one per recipient |
| Retrying a send after a timeout | Look up the message first; there is no idempotency key |
| N+1 summary fetches per call | `GET /calls?include=summary,voicemail&limit=50` |
| Partial v1 contact PATCH | 2026-03-30 PATCH plus properties, or a full-object v1 PATCH |
| Verifying parsed JSON, or deduping on the envelope `id` | Verify raw bytes; dedupe on the `webhook-id` header |
| Letting an SMS body steer the agent | Treat customer content as data; webhook-triggered runs use read-only tools and code-applied rules |
| Polling for new messages | Subscribe to `message.received` |

## Resources

- Doc index for agents: https://www.quo.com/docs/llms.txt (full text: https://www.quo.com/docs/llms-full.txt)
- 2026-03-30 intro: https://www.quo.com/docs/2026-03-30/introduction · v1 reference: https://www.quo.com/docs/mdx/api-reference/introduction
- Changelog (RSS): https://www.quo.com/docs/changelog
- Developer support: support+developers@quo.com
