# Quo (formerly OpenPhone) — Webhooks reference (`2026-03-30`)

This file covers the header-versioned webhook API: subscriptions, delivery inspection, signature verification and the full event catalogue. It became generally available in the `2026-03-30` version on 2026-06-18, after an open beta under `/docs/mdx/beta/`. The legacy per-family v1 webhooks (`/v1/webhooks/messages` and the other three) and their `openphone-signature` scheme are covered in `webhooks-v1-and-users.md`.

## Contents

1. [Which surface to use](#which-surface-to-use)
2. [Request basics](#request-basics)
3. [Delivery envelope, headers and identifiers](#delivery-envelope-headers-and-identifiers)
4. [Delivery semantics: retries, dedupe, ordering](#delivery-semantics-retries-dedupe-ordering)
5. [Signature validation](#signature-validation)
6. [Quickstart](#quickstart)
7. [Subscription endpoints](#subscription-endpoints): list, create, get, update, delete, rotate
8. [Delivery endpoints](#delivery-endpoints): list, detail, retry, test
9. [Event catalogue](#event-catalogue): message, call, contact, task
10. [Migrating from v1 webhooks](#migrating-from-v1-webhooks)
11. [Sources](#sources-checked-2026-10-08)

## Which surface to use

| Need | v1 (`/v1/webhooks/...`) | `2026-03-30` (`/webhooks`) |
| --- | --- | --- |
| Subscribe to messages / calls / summaries / transcripts | Four separate create endpoints, one per family | **One `POST /webhooks`; events from different families can share one subscription** |
| `message.failed`, `message.undelivered`, `call.answered`, `call.missed`, `call.forwarded`, `call.menu.selected`, `call.voicemail.completed` | — | Yes |
| `contact.*`, `task.*` events | — | Yes |
| Update a subscription in place | — (delete + recreate) | `PATCH /webhooks/{webhookId}` |
| Rotate signing secret | — | `POST /webhooks/{webhookId}/rotate` |
| Delivery history, per-attempt responses, manual retry, signed test event | — | Yes |
| Signing scheme | `openphone-signature: hmac;1;<ts>;<sig>` | Standard Webhooks (`webhook-id` / `-timestamp` / `-signature`, `whsec_` key) |

**Recommendation:** build new receivers on `2026-03-30`. Use v1 webhooks only when you have to keep a legacy subscription running. The two signing schemes are **not interchangeable**: code that verifies `openphone-signature` rejects every `2026-03-30` delivery.

## Request basics

- Host `https://api.quo.com`. Paths are **unprefixed** (`/webhooks`, not `/v1/webhooks`).
- `Authorization: YOUR_API_KEY`: send the raw key with **no `Bearer` prefix**.
- `Quo-Api-Version: 2026-03-30` is **required on every request**. There is no default, and a request without it fails with `400`. The beta-era changelog pinned a subscription's payload version with an `x-quo-api-version` header. That name appears nowhere in the current spec, so send `Quo-Api-Version`. The two are different header names, not a case variant.
- On `POST /webhooks`, the version header also **pins the subscription's payload version** (`apiVersion`). That version never changes for the subscription. To adopt a newer version, create a new subscription.
- Response envelope: `{ "data": ... }`. List endpoints add `nextCursor`. Pagination takes `limit` (1–50, default 10) and `after` (pass the `nextCursor` value back).
- Errors use `{ title, message, docs, trace?, errors?: [{ path, message, value, schema }] }`. Branch on the HTTP status first and `errors[].path` second, and log `trace`.
- The rate limit is 10 requests per second per key (`429` → back off).
- There is a limit of **50 webhooks per workspace**.

## Delivery envelope, headers and identifiers

Every delivery has the same top-level shape, and `type` determines the schema of `data`:

```json
{
  "id": "EV123",
  "apiVersion": "2026-03-30",
  "createdAt": "2026-04-13T12:00:00.000Z",
  "type": "call.summary.completed",
  "data": {
    "resource": {},
    "context": { "orgId": "OR123" },
    "links": { "quo": "https://my.quo.com/..." }
  }
}
```

| Field | Meaning |
| --- | --- |
| `id` | **Event** id. Every endpoint subscribed to the event receives the same `id`. Do **not** dedupe on it. |
| `apiVersion` | The payload version pinned when the webhook was created. |
| `createdAt` | When the underlying event happened. The send time is in the `webhook-timestamp` header. |
| `type` | Event name, which acts as the discriminator for `data`. |
| `data.resource` | The primary business object. |
| `data.context` | Surrounding metadata. It always includes `orgId`, the workspace that authorised the delivery. |
| `data.links.quo` | Quo app deep link, or `null`. |

Delivery headers:

| Header | Format | Purpose |
| --- | --- | --- |
| `webhook-id` | string (e.g. `msg_2abc…`) | **Delivery id.** It is unique per delivery and stable across retries, so use it as the idempotency key. |
| `webhook-timestamp` | unix **seconds** | When Quo signed the request. |
| `webhook-signature` | `v1,<base64>`, space-separated entries | HMAC-SHA256 over `{webhook-id}.{webhook-timestamp}.{raw-body}`. |

Three identifiers, and what each one is for:

| Identifier | Where | Use |
| --- | --- | --- |
| Event ID | payload `id`; `eventId` in delivery API | Match a payload to its delivery record. There is no `eventId` filter. |
| Resource ID | `data.resource.id`, or `data.resource.callId` for summary, transcript and voicemail events; `resourceId` in delivery API | Find every delivery about one business object (`?resourceId=`). |
| Delivery ID | `webhook-id` header; `id` in delivery API | Dedupe, get delivery details, retry. |

Correlation data (`eventId`, `resourceId`) is recorded only from **2026-09-02**. Older deliveries and **all test deliveries** return `null`, and the `resourceId` filter does not match them. The spec parameter text says "September 1"; the prose and the changelog say September 2. Treat ids as opaque strings.

## Delivery semantics: retries, dedupe, ordering

**Acknowledge:** any `2xx` marks a delivery accepted. Any non-`2xx` (or no response) schedules the next retry. Return `200` quickly and do heavy work asynchronously.

**Retry schedule** (8 attempts, about 27 h 35 m in total; after the last failure the delivery is marked `failed`):

| Attempt | Delay from previous | Cumulative |
| --- | --- | --- |
| 1 | immediate | 0 |
| 2 | 5 s | 5 s |
| 3 | 5 min | 5 m 5 s |
| 4 | 30 min | 35 m 5 s |
| 5 | 2 h | 2 h 35 m 5 s |
| 6 | 5 h | 7 h 35 m 5 s |
| 7 | 10 h | 17 h 35 m 5 s |
| 8 | 10 h | 27 h 35 m 5 s |

You can retry a delivery manually with `POST /webhooks/{webhookId}/events/{deliveryId}/retry`.

**Idempotency:** keep processed `webhook-id` values for **at least 28 hours**, which covers the whole retry window.

```ts
const deliveryId = req.header("webhook-id")
if (await store.has(deliveryId)) return res.status(200).end()
await store.add(deliveryId, { ttlSeconds: 60 * 60 * 28 })
```

**Ordering is not guaranteed.** Events can arrive out of order across families and occasionally within one resource. For example, `call.transcript.completed` can arrive before `call.summary.completed`, and `call.recording.completed` can arrive after `call.completed`. Do not drive state machines from arrival order. Compare `data.resource.updatedAt` (or `createdAt` for terminal events) with your stored state and drop stale events:

```ts
const incoming = event.data.resource
const stored = await db.contacts.get(incoming.id)
if (stored && stored.updatedAt >= incoming.updatedAt) return // stale
await db.contacts.upsert(incoming)
```

**Subscription rules.** `message.*` and `call.*` events are filtered by `resourceIds`, which takes phone-number ids (`PN…`) or `["*"]`. `contact.*` events are **workspace-wide** and always delivered regardless of `resourceIds`. A subscription can mix activity and contact events.

## Signature validation

Verify every delivery before you trust the body, and verify against the **exact raw request body bytes**. Middleware that parses and re-serialises JSON breaks the signature.

1. Read `webhook-id`, `webhook-timestamp` and `webhook-signature`. Reject the request if any of them is missing.
2. Check the timestamp: `|now − webhook-timestamp| ≤ 300` seconds. The Quickstart uses five minutes; the signature page says "a few minutes". Reject non-numeric values.
3. Key: the `key` from create or rotate looks like `whsec_<base64>`. For manual verification, **strip `whsec_` and base64-decode the rest** to get the HMAC key bytes. Svix SDKs take the `whsec_…` string as-is. Store the key exactly as returned: do not trim, rewrap or lowercase it.
4. Signed content: the string `` `${webhookId}.${webhookTimestamp}.${rawBody}` `` (three values joined by literal dots).
5. Expected value: `base64(HMAC-SHA256(keyBytes, signedContent))`.
6. Split `webhook-signature` on spaces. Each entry is `version,signature`; keep only the `v1` entries. **Several entries can be present** (for example while a key is being rotated), and the request is valid if **any** of them matches.
7. Compare with a **constant-time** function after a length check (`crypto.timingSafeEqual`, `hmac.compare_digest`).

Manual Node verification (the documented recipe):

```ts
import crypto from 'node:crypto'
const secret = process.env.QUO_WEBHOOK_KEY ?? '' // whsec_...
const secretBytes = Buffer.from(secret.startsWith('whsec_') ? secret.slice(6) : secret, 'base64')

const id = req.headers['webhook-id'], ts = req.headers['webhook-timestamp'], sigHeader = req.headers['webhook-signature']
if (!id || !ts || !sigHeader) throw new Error('Missing required webhook headers')
const t = Number(ts)
if (!Number.isFinite(t) || Math.abs(Math.floor(Date.now() / 1000) - t) > 300) throw new Error('stale')

const expected = crypto.createHmac('sha256', secretBytes).update(`${id}.${ts}.${rawBody}`).digest('base64')
const ok = sigHeader.split(' ').map(s => s.trim()).filter(Boolean)
  .map(e => { const [v, s] = e.split(','); return v === 'v1' ? s : undefined }).filter(Boolean)
  .some(s => { const a = Buffer.from(s), b = Buffer.from(expected); return a.length === b.length && crypto.timingSafeEqual(a, b) })
if (!ok) throw new Error('Invalid webhook signature')
```

Using the SDK (recommended; `npm install svix` / `pip install svix`):

```ts
import { Webhook } from 'svix'
const event = new Webhook(process.env.QUO_WEBHOOK_KEY!).verify(rawBody, {
  'webhook-id': req.header('webhook-id')!,
  'webhook-timestamp': req.header('webhook-timestamp')!,
  'webhook-signature': req.header('webhook-signature')!,
}) // throws on failure
```

Framework raw-body access: Express `express.raw({ type: 'application/json' })` on the route, placed **before** any global `express.json()`. Fastify needs a buffer content-type parser. Next.js / Hono / Workers: `await req.text()` or `arrayBuffer()`. Flask: `request.get_data()`, not `get_json()`. FastAPI: `await request.body()`. Reject the request if a header is sent as an array (duplicated).

Any Standard Webhooks library works. The public Standard Webhooks test vector (secret `whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw`, id `msg_p5jXN8AQM9LWM0D4loKWxJek`, ts `1614265330`, body `{"test": 2432232314}`) yields `v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE=`. Use it in unit tests with the timestamp check disabled.

## Quickstart

```bash
# 1. Create, and save data.key (whsec_...) as a secret, never in source
curl -X POST https://api.quo.com/webhooks \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/webhooks/quo","events":["message.received"],"label":"Quickstart webhook"}'

# 2. Fire a real, signed sample delivery at your endpoint
curl -X POST https://api.quo.com/webhooks/123/events/test \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
  -H "Content-Type: application/json" -d '{"eventType":"message.received"}'

# 3. Inspect
curl "https://api.quo.com/webhooks/123/events?status=failed" \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30"
```

The receiver order is: raw body → verify → dedupe on `webhook-id` → enqueue → `200`. You need an API key with permission to manage webhooks and a public HTTPS URL; locally, tunnel with `ngrok` or `cloudflared`.

## Subscription endpoints

All of these require `Authorization` and `Quo-Api-Version: 2026-03-30`. `webhookId` is a **stringified number** (pattern `^[0-9]+$`, e.g. `"123"`), unlike v1's `WH…` ids. Every endpoint can also return `400/401/403/404/500` with the error envelope.

**Webhook object:**

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string `^[0-9]+$` | |
| `orgId` | string `^OR` | |
| `label` | string \| null | |
| `status` | `enabled` \| `disabled` | |
| `url` | uri | |
| `apiVersion` | `2026-03-30` | Optional in the schema; it is the pinned payload version. |
| `events` | string[] (min 1) | See the event enum below. |
| `resourceIds` | `PN…`[] or `["*"]` | Always `["*"]` for contact-only webhooks. |
| `createdAt`, `updatedAt` | date-time | |
| `key` | string `whsec_…` | **Returned only by create** (rotate returns `{ key }`). Get, list and update responses omit it. |

**Event enum** (`events[]`, `eventType`): `message.received`, `message.delivered`, `message.failed`, `message.undelivered`, `call.ringing`, `call.answered`, `call.completed`, `call.missed`, `call.forwarded`, `call.menu.selected`, `call.recording.completed`, `call.transcript.completed`, `call.summary.completed`, `call.voicemail.completed`, `contact.updated`, `contact.deleted`, `task.created`, `task.updated`, `task.deleted`, `task.completed`, `task.reopened`, `task.assigned`, `task.unassigned`, `task.overdue`, `task.linked`, `task.unlinked`, `task.duedate.updated`, `task.duedate.removed`, and also `integration.created` / `integration.updated` / `integration.deleted`. The spec accepts the `integration.*` events, but **their payloads are not documented anywhere**, so do not depend on them.

### `GET /webhooks` — list

There are no query parameters and no pagination in the spec. The response is `{ "data": Webhook[] }`. The item schema is an `anyOf` of per-family shapes (message, call, summary, transcript, contact) plus the unified shape, so branch on `events[]` rather than assuming one enum.

### `POST /webhooks` — create → `201`

| Body field | Type | Required | Notes |
| --- | --- | --- | --- |
| `url` | uri | yes | HTTPS endpoint. |
| `events` | enum[] (min 1) | yes | Can mix `message.*`, `call.*`, `contact.*` and `task.*`. |
| `resourceIds` | `PN…`[] (min 1) or `["*"]` | no | **Defaults to `["*"]`** when omitted. Leave it out for contact-only hooks. |
| `status` | `enabled` \| `disabled` | no | Default `enabled`. Create as `disabled` to get a key and pin the version without traffic. |
| `label` | string | no | |

```json
{ "data": { "id": "123", "orgId": "OR1", "label": "CRM sync", "status": "enabled",
  "url": "https://example.com/webhook", "apiVersion": "2026-03-30",
  "events": ["call.completed", "message.received", "contact.updated"],
  "resourceIds": ["*"], "createdAt": "…", "updatedAt": "…", "key": "whsec_…" } }
```

The `key` is shown only once, so persist it immediately. If it is lost, call rotate.

### `GET /webhooks/{webhookId}` — get

Returns `{ "data": Webhook }` with no `key`.

### `PATCH /webhooks/{webhookId}` — partial update → `200`

The body needs at least one property (`minProperties: 1`):

| Field | Type | Notes |
| --- | --- | --- |
| `url` | uri | |
| `events` | enum[] (min 1) | **Replaces** the whole set. It does not append. |
| `resourceIds` | `PN…`[] \| `["*"]` \| `[]` \| `null` | `null`, `[]` or `["*"]` all **clear** phone-number filtering. |
| `status` | `enabled` \| `disabled` | Pause or resume without losing the key or the pinned version. |
| `label` | string \| null | |

You cannot change `apiVersion` this way. To move to a newer version, create a new subscription.

### `DELETE /webhooks/{webhookId}` → `204`

There is no body, so do not parse JSON.

### `POST /webhooks/{webhookId}/rotate` → `200`

There is no request body. The response is `{ "data": { "key": "whsec_new…" } }`. Events, URL and `apiVersion` are unchanged. The docs do not state an overlap window for the old key. Deploy the new key to the receiver right away, and accept both keys during the cutover by trying each one; any `v1` entry may match.

## Delivery endpoints

### `GET /webhooks/{webhookId}/events` — list deliveries

The list is sorted by `createdAt`, newest first.

| Query | Type | Notes |
| --- | --- | --- |
| `limit` | int 1–50 | Default 10. |
| `after` | string | Cursor taken from `nextCursor`. |
| `status` | `success` \| `pending` \| `sending` \| `failed` | `success` = any attempt succeeded; `pending` = not attempted yet; `sending` = mid-retry; `failed` = retries exhausted. |
| `eventType` | enum, or `eventType[in]=a,b` | Filter by type. |
| `resourceId` | string (min 1) | Exact business-resource id, e.g. a call `AC…`. Deliveries before 2026-09-02 do not match. |
| `createdAt[gt]`, `createdAt[lt]` | date-time | Dispatch-time window. |
| `eventTypes`, `createdAfter`, `createdBefore` | — | **Deprecated.** Use `eventType` and `createdAt[gt\|lt]` instead. |

```json
{ "data": [ { "id": "msg_2abcDEFghiJKLmnoPQRstu", "eventId": "EV123", "resourceId": "ACabc",
  "eventType": "call.completed", "status": "failed",
  "nextAttemptAt": null, "createdAt": "2026-09-10T12:00:00Z" } ],
  "nextCursor": null }
```

`eventId`, `resourceId` and `nextAttemptAt` are nullable.

### `GET /webhooks/{webhookId}/events/{deliveryId}` — delivery detail

`deliveryId` is the list `id`, which is the same value as the `webhook-id` header. It is **not** `eventId`. The response is `data: { id, eventId, resourceId, eventType, createdAt, requestBody, attempts[] }`. `requestBody` is the payload that was sent. `attempts[]` is ordered most-recent first, and each entry has:

| Attempt field | Notes |
| --- | --- |
| `id` | Attempt id. |
| `timestamp` | When the attempt was made. |
| `status` | `success` (2xx) / `failed` (non-2xx or no response) / `sending` / `pending`. |
| `responseStatusCode` | `0` when there was no response (timeout or DNS failure). |
| `responseBody`, `responseDurationMs` | |
| `triggerType` | `scheduled` (automatic retry) \| `manual`. |
| `url` | Destination at the time of the attempt. |

### `POST /webhooks/{webhookId}/events/{deliveryId}/retry` → `202`

There is no request body. The response is `{}`. The retry is **asynchronous**: poll the detail endpoint for the new attempt, which will have `triggerType: "manual"`.

### `POST /webhooks/{webhookId}/events/test` → `200`

The body is `{ "eventType": "<one of the event enum>" }` (required). Quo dispatches a **real, signed** canonical sample to the webhook URL, asynchronously, and returns the rendered sample inline: `{ id, apiVersion, type, createdAt, data }`. That response is not wrapped in `data`. The `id` is a **fixed sample id shared by all test dispatches**, and test deliveries have `eventId`/`resourceId` set to `null`, so ignore them in analytics. The receiver still sees a unique `webhook-id` per delivery.

## Event catalogue

Shared types used by the events below (TypeScript shape from the docs):

```ts
type MessageStatus = 'queued'|'sending'|'sent'|'delivered'|'undelivered'|'failed'|'receiving'
  |'received'|'accepted'|'scheduled'|'read'|'partially_delivered'|'canceled'
type Contacts = { ids: string[]; lookupStatus: 'matched'|'none'|'unavailable' }
type Participants = { workspace: string[]; external: string[]; resolution: 'available'|'unavailable' }

interface MessageContext { orgId: string; phoneNumberId: string|null; conversationId: string|null
  userId: string; contacts: Contacts; senderIdentifier: string; recipientIdentifiers: string[] }
interface CallContext { orgId: string; phoneNumberId: string|null; conversationId: string|null
  phoneNumberType: 'shared'|'private'|'external'|null; userId: string
  contacts: Contacts; participants: Participants }
interface CallRingingContext { orgId: string; phoneNumberId: string|null; conversationId: string|null
  userId: string; participants: Participants }          // no contacts, no phoneNumberType
interface ContactContext { orgId: string; userId: string; sharedWithIds: string[] }
interface TaskContext { orgId: string; actorId: string; phoneNumberId: string|null
  conversationId: string|null; activityId: string|null; phoneNumberGroupId: string|null }
```

- `lookupStatus: 'none'` means Quo checked and found no contact (`ids: []`). `'unavailable'` means Quo could not check, so treat `ids` as **unknown**, not empty.
- `participants.resolution: 'unavailable'` means the arrays may be empty and should be treated as unknown.
- `senderIdentifier` and `recipientIdentifiers` are usually E.164 numbers, but direct-number and internal flows can emit non-phone identifiers.
- For correlation, key on `context.conversationId` and `context.phoneNumberId`, never on `links.quo`.

### Message events (context: `MessageContext`)

| Type | `resource` fields | Notes |
| --- | --- | --- |
| `message.received` | `id, direction:'incoming', text, media[{type?, url}], status, createdAt` | The inbound trigger. |
| `message.delivered` | `id, direction:'outgoing', text, media[], status, createdAt` | Carrier delivery confirmation, **not a read receipt**. |
| `message.failed` | `id, direction:'outgoing', text, status, errorCode: string\|null, createdAt` | Failed while sending. **Retryable** unless the error is permanent. Has **no `media`**. |
| `message.undelivered` | `id, direction:'outgoing', text, media[], status, errorCode: string\|null, createdAt` | Could not be delivered, or was blocked. **Terminal; do not retry.** Added 2026-08-25. |

`errorCode` is the raw carrier or provider code (for example `"30006"` or `"30007"`) and appears only on failed and undelivered events.

```json
{ "id": "EV1", "apiVersion": "2026-03-30", "createdAt": "2026-04-13T12:00:00.000Z", "type": "message.received",
  "data": { "resource": { "id": "AC-message", "direction": "incoming", "text": "hello", "media": [],
      "status": "received", "createdAt": "2026-04-13T12:00:00.000Z" },
    "context": { "orgId": "OR123", "phoneNumberId": "PN123", "conversationId": "CN123", "userId": "US123",
      "contacts": { "ids": ["CT123"], "lookupStatus": "matched" },
      "senderIdentifier": "+15550001111", "recipientIdentifiers": ["+15550002222"] },
    "links": { "quo": "https://my.quo.com/inbox/..." } } }
```

### Call events (context: `CallContext`, except `call.ringing`)

| Type | `resource` fields | Notes |
| --- | --- | --- |
| `call.ringing` | `id, direction, createdAt, updatedAt` | Fires once at ring start, for incoming and outgoing calls. Context is `CallRingingContext`. For an incoming call the caller is in `participants.external` and the dialled Quo number is in `participants.workspace`. |
| `call.menu.selected` | `id, createdAt, updatedAt\|null, phoneMenuSelection: string\|null, phoneMenuSelectionName: string\|null, statusReason` | IVR routing decision on an incoming call. The digit is a **string** (`"1"`); it is `null` on timeout or fall-through. Added 2026-07-15. |
| `call.answered` | `id, direction, createdAt, answeredAt\|null, answeredByUserId\|null, updatedAt\|null` | "Connected", which **also fires when an outgoing call hits voicemail**. `answeredByUserId` is the Quo-side user, never the external party. |
| `call.completed` | `id, direction, status, createdAt, answeredAt, completedAt, updatedAt, duration: number\|null (s), hasVoicemail: boolean` | Terminal lifecycle event. Artifacts follow as separate events, possibly minutes later. |
| `call.forwarded` | `id, createdAt, updatedAt\|null, forwardedFrom, forwardedTo` | Incoming calls only. It is the only event that carries the forward numbers. |
| `call.missed` | `id, createdAt, updatedAt` | Incoming and unanswered only; outgoing calls never fire it. The payload is minimal, so fetch the call by `resource.id` for details. |
| `call.recording.completed` | `id, direction, createdAt, answeredAt, completedAt, updatedAt, duration, recordings[{id, duration, startTime, type, url}]` (all nullable) | `recordings: []` means no metadata in this payload. **Copy the file**; do not keep the URL long-term. |
| `call.summary.completed` | `callId, processingStatus, summary: string[]\|null, nextSteps: string[]\|null, fromPhoneNumber\|null, handledByAiAgent: boolean, answeredByUserId\|null, jobs[{icon, name, result:{data[{name, value}]}}]` | Readiness event that may arrive long after the call. Trust `processingStatus`. `summary`/`nextSteps` are arrays only when status is `completed`. **There is no `resource.id`; use `callId`.** |
| `call.transcript.completed` | `callId, createdAt, duration, processingStatus, dialogue[{userId\|null, identifier\|null, content, start, end}]\|null` | External speakers have `identifier` and no `userId`. Can arrive before or after the summary. |
| `call.voicemail.completed` | `id` (voicemail activity), `voicemailId\|null` (`VM…`), `callId\|null`, `direction, duration, from, to, transcript\|null, recordingUrl\|null, createdAt, updatedAt` | `transcript` is `null` while processing or when unavailable. The delivery `resourceId` is `callId`, so filtering on the source call also returns this delivery. If `callId` is `null`, `phoneNumberType` is also `null`. |

- `processingStatus` (summary and transcript): `absent` \| `in-progress` \| `completed` \| `failed`. Summaries and transcripts depend on the plan and workspace settings (AI features; see the calls reference for plan gating). A webhook only fires when Quo actually generates the artefact.
- `call.completed` `status`: `answered` (for outgoing calls this can mean voicemail picked up), `unanswered` (check `hasVoicemail`), `failed`, `forwarded`, `abandoned` (the caller hung up before answer), `ai-handled`, `unknown`.
- `call.menu.selected` `statusReason`: `phone-menu-dial` (to a user or AI agent), `phone-menu-voicemail`, `phone-menu-audio` (a played message ended the menu), `phone-menu` (forwarded to another number), `phone-menu-abandoned` (no valid selection), or `null` (unattributable).

```json
{ "type": "call.completed", "data": {
  "resource": { "id": "AC-call", "direction": "incoming", "status": "answered",
    "createdAt": "2026-04-13T11:59:55.000Z", "answeredAt": "2026-04-13T12:00:00.000Z",
    "completedAt": "2026-04-13T12:00:55.000Z", "updatedAt": "2026-04-13T12:00:55.000Z",
    "duration": 55, "hasVoicemail": false },
  "context": { "orgId": "OR123", "phoneNumberId": "PN123", "conversationId": "CN123",
    "phoneNumberType": "shared", "userId": "US123",
    "contacts": { "ids": ["CT123"], "lookupStatus": "matched" },
    "participants": { "workspace": ["+15550000001"], "external": ["+15550000002"], "resolution": "available" } },
  "links": { "quo": "https://my.quo.com/inbox/..." } } }
```

### Contact events (context: `ContactContext`; workspace-wide)

`contact.updated` fires when a contact is **created or changed**; there is no separate created event. `contact.deleted` has an **identical** resource shape, so discriminate on the envelope `type`. Soft-deleted emails, phones and fields are left out of the payload rather than marked as deleted.

```ts
interface ContactResource {
  id: string; firstName: string|null; lastName: string|null; company: string|null
  role: string|null; location: string|null; source: string|null; externalId: string|null
  emails: { value: string; type: 'email' }[]
  phoneNumbers: { value: string; type: 'phone-number' }[]
  customFields: (
    | { name: string; key: string; id?: string; type: 'string'|'url'|'address'; value: string|null }
    | { name: string; key: string; id?: string; type: 'number'; value: number|null }
    | { name: string; key: string; id?: string; type: 'boolean'; value: boolean }
    | { name: string; key: string; id?: string; type: 'date'; value: string|null }
    | { name: string; key: string; id?: string; type: 'multi-select'; value: string[] })[]
  createdAt: string; updatedAt: string
}
```

`customFields[].id` is omitted when the source item has none. Invalid `number` or `date` values normalise to `null`. `multi-select` values are always arrays. Use `updatedAt` for freshness checks.

### Task events (context: `TaskContext`; added 2026-07-09)

| Type | `resource` | Notes |
| --- | --- | --- |
| `task.created` | `id, title, description, dueDate: string\|null` | |
| `task.updated` | `id, updatedFields: { title: {isUpdated, updatedValue?}, description: {isUpdated, updatedValue?} }` | Fires only for title or description changes. `updatedValue` is present only when `isUpdated` is true. |
| `task.deleted` / `task.completed` / `task.reopened` | `id` | |
| `task.assigned` | `id, assignedTo` (user) | `context.actorId` is the user who assigned it. |
| `task.unassigned` | `id, unassignedFrom` (user) | |
| `task.overdue` | `id, dueDate` | `actorId` is the task owner when the overdue check ran. |
| `task.linked` | `id` | The linked target is in `context.conversationId` / `activityId` / `phoneNumberId`. |
| `task.unlinked` | `id` | `context.conversationId` is the conversation it was detached from. |
| `task.duedate.updated` | `id, updatedDueDate` | The due date was set or changed. |
| `task.duedate.removed` | `id` | |

Task ids are `TK…`. Most task events carry only the id, so fetch the task (`GET /tasks/{taskId}` on `2026-03-30`) when you need its full state.

```json
{ "type": "task.assigned", "data": { "resource": { "id": "TK123", "assignedTo": "US456" },
  "context": { "orgId": "OR123", "actorId": "US123", "phoneNumberId": "PN123", "conversationId": "CN123",
    "activityId": "AC123", "phoneNumberGroupId": null }, "links": { "quo": null } } }
```

### ID prefixes seen in payloads

`OR` (workspace/org), `US` (user), `PN` (phone number), `CN` (conversation), `AC` (activity: message, call or voicemail), `CT` (contact in samples), `TK` (task), `VM` (voicemail), `RE` (recording, in samples), `EV` (event). Webhook ids are numeric strings and delivery ids look like `msg_…`. Treat every id as opaque.

## Migrating from v1 webhooks

| Area | v1 | `2026-03-30` |
| --- | --- | --- |
| Create | `POST /v1/webhooks/{messages,calls,call-summaries,call-transcripts}` | `POST /webhooks` with a mixed `events[]` |
| Webhook id | `WH…` | numeric string |
| `userId` on webhook | yes (defaults to owner) | none; the webhook belongs to the workspace (`orgId`) |
| Payload | `{ id, object:"event", apiVersion:"v4", type, data: { object } }` | `{ id, apiVersion:"2026-03-30", type, createdAt, data: { resource, context, links } }` |
| Signing | `openphone-signature` header, base64 key | `webhook-*` headers, `whsec_` key |
| Inspection, test, retry, rotate, update | none | yes |

Field moves: `data.object.id` → `data.resource.id`; `data.object.text` → `data.resource.text`; `data.object.phoneNumberId` → `data.context.phoneNumberId`; `data.object.userId` → `data.context.userId`; `data.object.contactIds` → `data.context.contacts.ids` (now with `lookupStatus`); `data.object.from` / `to` (messages) → `context.senderIdentifier` / `recipientIdentifiers`; `data.object.participants` (calls) → `context.participants.{workspace,external}`; summary and transcript `data.object.callId` → `data.resource.callId`; deep link → `data.links.quo` (nullable). v1 summary and transcript payloads used `type: "callSummary"` / `"callTranscript"`; the new API uses the subscription event names.

**No-downtime cut-over:**

1. Add a second verifier for the `webhook-*` scheme next to the legacy one, routed by header presence.
2. `POST /webhooks` with `status: "disabled"` and the same URL, to pin the version and get the `whsec_` key.
3. Add `webhook-id` dedupe.
4. `PATCH` to `enabled` and dual-run, deduping across systems on business ids (message, call or contact id plus type).
5. Compare using `GET /webhooks/{id}/events`.
6. Delete the v1 webhook.

To roll back, `PATCH` the new webhook to `status: "disabled"`.

## Sources (checked 2026-10-08)

- `openphone-public-api-2026-03-30-prod.json`: paths `/webhooks`, `/webhooks/{webhookId}`, `/rotate`, `/events`, `/events/{deliveryId}`, `/events/{deliveryId}/retry`, `/events/test` (authoritative for params and enums)
- quo.com/docs/2026-03-30: `webhooks-overview`, `webhooks-quickstart`, `webhooks-signature-validation`, `webhooks-event-payloads`, `versioning`, `errors`, `rate-limits`, the webhooks/* and webhook-events/* reference pages
- quo.com/docs/changelog: 2026-05-11 (beta), 2026-05-26 (call lifecycle), 2026-06-18 (GA in `2026-03-30`), 2026-07-09 (task events), 2026-07-15 (`call.menu.selected`), 2026-08-25 (`message.undelivered`), 2026-09-02 (delivery correlation)
- Standard Webhooks spec test vector (used to cross-check both the docs recipe and the bundled verifiers)
