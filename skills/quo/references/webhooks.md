## Quo (formerly OpenPhone) — Webhooks v2 (Beta) Reference

> Source-cited from the live Quo beta webhook docs (`https://www.quo.com/docs/mdx/beta/*`) and the public OpenAPI specs. This is the **beta** webhook API (open beta), managed separately from legacy app-managed and legacy API-managed webhooks. Beta webhooks do **not** appear in Quo app settings during the beta.

### Base URL, versioning, and auth (read this first)

- **Base URL (verified):** `https://api.quo.com` — declared as the single `Production server` in *both* current OpenAPI specs (`servers[0].url = "https://api.quo.com"`). The beta webhook docs use `https://api.quo.com/webhooks` (**no `/v1` prefix**). Source: `openphone-public-api-2026-03-30-prod.json`, `webhooks-api-reference.md`.
  - **Host note:** Beta webhook paths are **un-prefixed** — `https://api.quo.com/webhooks` (no `/v1`). The OpenAPI `servers` block declares `https://api.quo.com` as the only production host; `https://api.openphone.com` is a legacy alias for the `/v1` REST API. Use `https://api.quo.com` for beta webhooks.
- **Auth header (verified):** Raw API key, NOT Bearer. OpenAPI `securitySchemes.apiKey = { "type": "apiKey", "in": "header", "name": "Authorization" }`, applied globally (`security: [{ "apiKey": [] }]`). Docs show `Authorization: YOUR_API_KEY`. There is **no** `Bearer ` prefix. Source: both specs + `webhooks-api-reference.md`.
- **API version header (required on every management call):** `x-quo-api-version: 2026-03-30`. The version is recorded **once** at webhook creation and pinned for every subsequent delivery of that subscription; it never changes for that webhook. Source: `webhooks-overview.md`, `webhooks-api-reference.md`.
- **Quota:** A workspace can have at most **50** webhooks created with the beta API. Source: `webhooks-overview.md`.

### Common delivery envelope

Every delivery (and every record returned by `requestBody` in delivery detail) uses the same top-level shape. The `type` field discriminates the schema of `data`.

```json
{
  "id": "EV123",
  "apiVersion": "2026-03-30",
  "createdAt": "2026-04-13T12:00:00.000Z",
  "type": "call.summary.completed",
  "data": {
    "resource": {},
    "context": {},
    "links": { "quo": "https://my.quo.com/..." }
  }
}
```

| Field | Meaning |
| --- | --- |
| `id` | Stable **event** id across retries and payload versions. NOT a delivery id — for delivery-level dedupe use the `webhook-id` **header**. |
| `apiVersion` | Payload version recorded when the webhook was created. |
| `createdAt` | When the underlying event occurred (send time is in the `webhook-timestamp` header). |
| `type` | Event name; discriminates the schema of `data`. |
| `data.resource` | Primary business object for the event. |
| `data.context` | Surrounding metadata (phone number, conversation, participants, contact lookup, sharing). |
| `data.links.quo` | Quo app deep link, or `null` when none is available. |

Treat all event/delivery/resource ids as **opaque strings**. Source: `webhooks-overview.md`, `webhooks-event-payloads.md`.

### Headers on every delivery

| Header | Format | Purpose |
| --- | --- | --- |
| `webhook-id` | string | Idempotency key. Stable across retries. |
| `webhook-timestamp` | unix seconds | When Quo signed the request. |
| `webhook-signature` | space-separated `v1,<base64sig>` entries | HMAC-SHA256 over `{webhook-id}.{webhook-timestamp}.{raw-body}`, base64-encoded. |

These are **Standard-Webhooks / Svix-compatible** headers. Source: `webhooks-overview.md`, `webhooks-signature-validation.md`.

---

## Signature validation (CRITICAL — get this exactly right)

Source: `webhooks-signature-validation.md`, corroborated by `webhooks-overview.md` and `webhooks-quickstart.md`.

- **Signed string:** `{webhook-id}.{webhook-timestamp}.{raw-body}` — the three values joined by literal `.` characters, where `raw-body` is the **exact raw request body bytes** Quo sent. If middleware parses/re-serializes the JSON first, verification fails.
- **Algorithm:** HMAC-SHA256.
- **Encoding of the signature:** **base64**.
- **Header carrying it:** `webhook-signature`, a **space-separated** list. Each entry is `v1,<base64-signature>`. Split on space, then split each entry on `,`; keep entries whose version is `v1`. Multiple signatures may be present (key rotation) — accept if **any** matches.
- **Signing secret:** Returned as the `key` field when you create a webhook (`POST /webhooks`) or rotate (`POST /webhooks/:id/rotate`), prefixed `whsec_`. For **manual** verification, strip the `whsec_` prefix and **base64-decode the remainder** to get the raw HMAC key bytes. For **SDK** verification (Svix), pass `whsec_…` as-is. Store the secret exactly as returned — do not trim, rewrap, or lowercase it.
- **Replay protection:** Reject any delivery whose `webhook-timestamp` is more than ~5 minutes (`MAX_AGE_SECONDS = 5 * 60`) off your server clock.
- **Constant-time compare:** Use `crypto.timingSafeEqual` (length-check first).

### Manual verification recipe (Node `crypto`, verbatim from docs)

```ts
import crypto from 'node:crypto'

const secret = process.env.QUO_WEBHOOK_KEY ?? '' // whsec_...
const MAX_AGE_SECONDS = 5 * 60

const secretBase64 = secret.startsWith('whsec_') ? secret.slice('whsec_'.length) : secret
const secretBytes = Buffer.from(secretBase64, 'base64')

const webhookId = request.headers['webhook-id']
const webhookTimestamp = request.headers['webhook-timestamp']
const webhookSignature = request.headers['webhook-signature']
if (!webhookId || !webhookTimestamp || !webhookSignature) {
  throw new Error('Missing required webhook headers')
}

const timestamp = Number(webhookTimestamp)
const now = Math.floor(Date.now() / 1000)
if (!Number.isFinite(timestamp) || Math.abs(now - timestamp) > MAX_AGE_SECONDS) {
  throw new Error('Invalid or stale webhook timestamp')
}

const signedContent = `${webhookId}.${webhookTimestamp}.${rawBody}`
const expectedSignature = crypto.createHmac('sha256', secretBytes).update(signedContent).digest('base64')

const providedSignatures = webhookSignature
  .split(' ')
  .map((entry) => entry.trim())
  .filter(Boolean)
  .map((entry) => {
    const [version, signature] = entry.split(',')
    return version === 'v1' ? signature : undefined
  })
  .filter((signature): signature is string => Boolean(signature))

const isValid = providedSignatures.some((signature) => {
  const left = Buffer.from(signature)
  const right = Buffer.from(expectedSignature)
  return left.length === right.length && crypto.timingSafeEqual(left, right)
})

if (!isValid) {
  throw new Error('Invalid webhook signature')
}
```

### SDK verification (recommended — Svix)

The Svix SDK accepts Quo's headers and the `whsec_…` key format unchanged.

```ts
import { Webhook } from 'svix'
const secret = process.env.QUO_WEBHOOK_KEY ?? '' // whsec_...
const headers = {
  'webhook-id': request.headers['webhook-id'],
  'webhook-timestamp': request.headers['webhook-timestamp'],
  'webhook-signature': request.headers['webhook-signature'],
}
const verified = new Webhook(secret).verify(rawBody, headers) // throws on failure
```

**Framework gotcha:** verification fails most often because a JSON body-parser ran before your handler saw the bytes. In Express use `express.raw({ type: "application/json" })`; in Flask use `request.get_data()` (NOT `request.get_json()`).

---

## Delivery semantics

Source: `webhooks-overview.md`.

- **Idempotency:** Quo retries on any non-`2xx`, so handlers must be idempotent. Use the `webhook-id` **header** as the key. Store processed ids for **at least 28 hours** (covers the full retry window).
- **Retries / backoff schedule** (8 attempts; any `2xx` accepts, non-`2xx` triggers next retry; after all fail the delivery is marked `failed`):

| Attempt | Delay from previous | Cumulative |
| --- | --- | --- |
| 1 | Immediate | 0 |
| 2 | 5 seconds | 5s |
| 3 | 5 minutes | 5m 5s |
| 4 | 30 minutes | 35m 5s |
| 5 | 2 hours | 2h 35m 5s |
| 6 | 5 hours | 7h 35m 5s |
| 7 | 10 hours | 17h 35m 5s |
| 8 | 10 hours | 27h 35m 5s |

  After ~27h 35m the delivery is marked `failed`. You can also force a manual retry via `POST /webhooks/:id/events/:eventId/retry`.
- **Ordering:** NOT guaranteed — across event families and occasionally within a single resource (e.g. `call.transcript.completed` may arrive before `call.summary.completed`). Design handlers to be order-independent: compare `data.resource.updatedAt` (or `createdAt` for terminal events) against stored state and ignore stale events.

### Subscription rules

- `message.*` and `call.*` events accept a `resourceIds` filter (phone-number ids, or `["*"]` for all). Defaults to `["*"]`.
- `contact.*` events are **workspace-wide**; omit `resourceIds` for contact-only webhooks. `resourceIds` does not filter contact events.
- Mixed subscriptions (message + call + contact in one webhook) are supported.

---

## Endpoints

All paths are relative to `https://api.quo.com`. Every request needs `Authorization: YOUR_API_KEY` and `x-quo-api-version: 2026-03-30`. Source: `webhooks-api-reference.md`.

### List webhooks

`GET https://api.quo.com/webhooks`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `Authorization` | header | string | Yes | Raw API key (no `Bearer`). |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

Request body: none. Not paginated — returns every beta webhook in the workspace.

```json
{
  "data": [
    {
      "id": "123",
      "orgId": "OR123",
      "label": "Production webhook",
      "status": "enabled",
      "url": "https://example.com/webhooks/quo",
      "createdAt": "2026-04-13T12:00:00.000Z",
      "updatedAt": "2026-04-13T12:00:00.000Z",
      "events": ["call.summary.completed", "contact.updated"],
      "resourceIds": ["PNabc123"],
      "apiVersion": "2026-03-30"
    }
  ]
}
```

**Gotchas**
- Returns only webhooks created via the **beta** endpoints; legacy app/API webhooks are not listed here.
- No `key` (signing secret) is returned on list/get — only on create and rotate.

### Create a webhook

`POST https://api.quo.com/webhooks`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `Authorization` | header | string | Yes | Raw API key. |
| `Content-Type` | header | string | Yes | `application/json`. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30` — pins the subscription's payload version forever. |
| `url` | body | string | **Yes** | Public HTTPS endpoint that receives deliveries. |
| `events` | body | string[] | **Yes** | One or more supported event types; message/call/contact may be mixed. |
| `resourceIds` | body | string[] | No | Phone-number ids to filter message/call events, or `["*"]` for all. Defaults to `["*"]`. Ignored for contact events. |
| `label` | body | string | No | Human-readable label. |
| `status` | body | `"enabled" \| "disabled"` | No | Defaults to `enabled`. Create with `disabled` to provision a secret without firing traffic (used in migration). |

Request body:

```json
{
  "url": "https://example.com/webhooks/quo",
  "events": ["call.completed", "message.received", "contact.updated"],
  "resourceIds": ["PNabc123"],
  "label": "Production webhook",
  "status": "enabled"
}
```

Response (the **only** create-time place you get the `whsec_…` secret — save it):

```json
{
  "data": {
    "id": "123",
    "orgId": "OR123",
    "label": "Production webhook",
    "status": "enabled",
    "url": "https://example.com/webhooks/quo",
    "key": "whsec_...",
    "createdAt": "2026-04-13T12:00:00.000Z",
    "updatedAt": "2026-04-13T12:00:00.000Z",
    "events": ["call.completed", "message.received", "contact.updated"],
    "resourceIds": ["PNabc123"],
    "apiVersion": "2026-03-30"
  }
}
```

curl (canonical Authorization header):

```bash
curl https://api.quo.com/webhooks \
  -X POST \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -H "x-quo-api-version: 2026-03-30" \
  -d '{
    "url": "https://example.com/webhooks/quo",
    "events": ["call.completed", "message.received", "contact.updated"],
    "resourceIds": ["PNabc123"],
    "label": "Production webhook",
    "status": "enabled"
  }'
```

**Gotchas**
- The `key` (`whsec_…`) is returned **only** here and on rotate. Lose it and you must rotate. Store it as an env var, never in source.
- `apiVersion` is locked at creation; to move to a newer payload version you must create a new subscription.
- Workspace cap is 50 beta webhooks.

### Get a webhook

`GET https://api.quo.com/webhooks/:id`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

```json
{
  "data": {
    "id": "123",
    "orgId": "OR123",
    "label": "Production webhook",
    "status": "enabled",
    "url": "https://example.com/webhooks/quo",
    "createdAt": "2026-04-13T12:00:00.000Z",
    "updatedAt": "2026-04-13T12:00:00.000Z",
    "events": ["call.summary.completed", "contact.updated"],
    "resourceIds": ["PNabc123"],
    "apiVersion": "2026-03-30"
  }
}
```

**Gotchas**
- No `key` in the response.

### Update a webhook

`PATCH https://api.quo.com/webhooks/:id`

All body fields optional — send only what you want to change.

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `Content-Type` | header | string | Yes | `application/json`. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |
| `url` | body | string | No | Replaces the webhook URL. |
| `events` | body | string[] | No | Replaces subscribed event types. |
| `resourceIds` | body | string[] \| null | No | Replaces phone-number filters. Send `null`, `[]`, or `["*"]` to clear filtering. |
| `label` | body | string \| null | No | Replaces label; `null` clears it. |
| `status` | body | `"enabled" \| "disabled"` | No | Enables/disables delivery. |

Request body:

```json
{
  "events": ["call.summary.completed", "contact.updated"],
  "resourceIds": ["PNabc123"],
  "label": "Updated webhook"
}
```

Response: same webhook object shape as Get (no `key`).

**Gotchas**
- `events` and `resourceIds` are **replace**, not merge — send the full desired array.
- You cannot change `apiVersion` via update (it's create-time only).

### Delete a webhook

`DELETE https://api.quo.com/webhooks/:id`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

Request body: none. Returns **`204 No Content`** on success.

```bash
curl https://api.quo.com/webhooks/123 \
  -X DELETE \
  -H "Authorization: YOUR_API_KEY" \
  -H "x-quo-api-version: 2026-03-30"
```

**Gotchas**
- Empty body / `204`; don't expect a JSON payload.

### Rotate the signing secret

`POST https://api.quo.com/webhooks/:id/rotate`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

Request body: none.

```json
{
  "data": { "key": "whsec_..." }
}
```

**Gotchas**
- Multiple `v1,<sig>` entries may appear in `webhook-signature` around a rotation — accept if any matches, so in-flight deliveries verify against the old or new key during cutover.

### Send a test event

`POST https://api.quo.com/webhooks/:id/events/test`

Sends a **real, signed** delivery to your webhook URL (identical to production) and returns the sample payload inline.

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `Content-Type` | header | string | Yes | `application/json`. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |
| `eventType` | body | string | Yes | One of the supported event types. |

Request body:

```json
{ "eventType": "message.received" }
```

Response (sample payload, full envelope):

```json
{
  "id": "EV-test-message-received",
  "apiVersion": "2026-03-30",
  "createdAt": "2026-03-30T18:00:00.000Z",
  "type": "message.received",
  "data": {
    "resource": {
      "id": "ACsampleactivity0000000000000000",
      "direction": "incoming",
      "text": "Hello from Quo! This is a sample message.",
      "status": "received",
      "createdAt": "2026-03-30T18:00:00.000Z"
    },
    "context": {
      "phoneNumberId": "PNsamplephonenumber000000000000",
      "conversationId": "CNsampleconversation000000000000",
      "userId": "USsampleus",
      "contacts": { "ids": ["CTsampleContact01234"], "lookupStatus": "matched" },
      "senderIdentifier": "+15555551234",
      "recipientIdentifiers": ["+15555555678"]
    },
    "links": { "quo": "https://my.quo.com/..." }
  }
}
```

**Gotchas**
- Delivery is **asynchronous** — the HTTP response returns the sample payload, but the actual signed POST to your URL lands separately. Use `GET /webhooks/:id/events` to find the delivery id and inspect what your endpoint returned.
- Great for verifying signature handling before any production traffic.

### List deliveries

`GET https://api.quo.com/webhooks/:id/events`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |
| `limit` | query | number | No | Page size. |
| `after` | query | string | No | Cursor from previous response's `nextCursor`. |
| `status` | query | `"success" \| "pending" \| "sending" \| "failed"` | No | Filter by delivery status. |
| `eventTypes` | query | string[] | No | Restrict to specific event types. |
| `createdBefore` | query | ISO-8601 string | No | Deliveries created before this time. |
| `createdAfter` | query | ISO-8601 string | No | Deliveries created after this time. |

Delivery status meanings: `success` = at least one attempt returned `2xx`; `pending` = queued, no attempt yet; `sending` = in progress or awaiting a retry; `failed` = all retries exhausted without `2xx`.

```json
{
  "data": [
    {
      "id": "msg_2abcDEFghiJKLmnoPQRstu",
      "eventType": "message.received",
      "status": "success",
      "nextAttemptAt": null,
      "createdAt": "2026-04-13T12:00:00.000Z"
    }
  ],
  "nextCursor": "eyJsYXN0SWQiOiJtc2dfMmFiY0RFRmdoaUpLTG1ub1BRUnN0dSJ9"
}
```

**Gotchas**
- This delivery-status enum (`success|pending|sending|failed`) differs from the message-resource `status` enum. Don't conflate them.
- Paginate with `after` = `nextCursor`.

### Get delivery detail

`GET https://api.quo.com/webhooks/:id/events/:eventId`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `eventId` | path | string | Yes | Delivery id (e.g. `msg_…`). |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

Returns the full request body and **all attempts**, ordered most-recent first.

```json
{
  "data": {
    "id": "msg_2abcDEFghiJKLmnoPQRstu",
    "eventType": "message.received",
    "createdAt": "2026-04-13T12:00:00.000Z",
    "requestBody": {
      "id": "EV123",
      "apiVersion": "2026-03-30",
      "createdAt": "2026-04-13T12:00:00.000Z",
      "type": "message.received",
      "data": {
        "resource": {
          "id": "AC-message",
          "direction": "incoming",
          "text": "hello",
          "status": "received",
          "createdAt": "2026-04-13T12:00:00.000Z"
        },
        "context": {
          "phoneNumberId": "PN123",
          "conversationId": "CN123",
          "userId": "US123",
          "contacts": { "ids": ["CT123"], "lookupStatus": "matched" },
          "senderIdentifier": "+15550001111",
          "recipientIdentifiers": ["+15550002222"]
        },
        "links": { "quo": "https://my.quo.com/inbox/..." }
      }
    },
    "attempts": [
      {
        "id": "atmpt_2abcDEFghiJKLmnoPQRstu",
        "timestamp": "2026-04-13T12:00:01.000Z",
        "status": "success",
        "responseStatusCode": 200,
        "responseBody": "{\"ok\":true}",
        "responseDurationMs": 123,
        "triggerType": "scheduled",
        "url": "https://example.com/webhooks/quo"
      }
    ]
  }
}
```

**Gotchas**
- `attempts[].triggerType` distinguishes `scheduled` (auto retry) from manual retries.

### Retry a delivery

`POST https://api.quo.com/webhooks/:id/events/:eventId/retry`

| Name | In | Type | Required | Notes |
| --- | --- | --- | --- | --- |
| `id` | path | string | Yes | Webhook id. |
| `eventId` | path | string | Yes | Delivery id. |
| `Authorization` | header | string | Yes | Raw API key. |
| `x-quo-api-version` | header | string | Yes | `2026-03-30`. |

Request body: none. Queued asynchronously; returns **`202 Accepted`**. Inspect the new attempt via Get delivery detail.

**Gotchas**
- `202`, not `200` — and the retry is async, so the attempt result is not in the response.

---

## Event payload catalog

Every event uses the common envelope; the sections below document only the per-event `data` wrapper. Source: `webhooks-event-payloads.md`.

### Reused context types

```ts
type MessageStatus =
  | 'queued' | 'sending' | 'sent' | 'delivered' | 'undelivered' | 'failed'
  | 'receiving' | 'received' | 'accepted' | 'scheduled' | 'read'
  | 'partially_delivered' | 'canceled'

interface MessageContext {
  phoneNumberId: string | null
  conversationId: string | null
  userId: string
  contacts: { ids: string[]; lookupStatus: 'matched' | 'none' | 'unavailable' }
  senderIdentifier: string
  recipientIdentifiers: string[]
}

interface CallContext {
  phoneNumberId: string | null
  conversationId: string | null
  phoneNumberType: 'shared' | 'private' | 'external' | null
  userId: string
  contacts: { ids: string[]; lookupStatus: 'matched' | 'none' | 'unavailable' }
  participants: { workspace: string[]; external: string[]; resolution: 'available' | 'unavailable' }
}

interface CallRingingContext {
  phoneNumberId: string | null
  conversationId: string | null
  userId: string
}

interface ContactContext {
  userId: string
  sharedWithIds: string[]
}
```

- `contacts.lookupStatus`: `matched` (ids populated) · `none` (checked, none found, `ids: []`) · `unavailable` (couldn't determine — treat `ids` as **unknown**, not empty).
- `participants.resolution`: `available` (populated) · `unavailable` (treat empty arrays as unknown, not "no participants").

### Event index

| Event type | When it fires |
| --- | --- |
| `message.received` | Inbound SMS/MMS/message received by a Quo number. |
| `message.delivered` | Outbound message delivered (NOT a read receipt). |
| `call.ringing` | Call started ringing (incoming + outgoing). Narrow context. |
| `call.answered` | Call connected. `answeredByUserId` = Quo-side user when known. Outgoing calls fire this on voicemail pickup too. |
| `call.completed` | Call ended (terminal) with final `status` + `duration`. |
| `call.forwarded` | Incoming call forwarded; includes forwarding numbers. |
| `call.missed` | Incoming call ended unanswered (outgoing calls do NOT fire this). |
| `call.recording.completed` | Recording finished processing; may arrive after `call.completed`. |
| `call.summary.completed` | Summary finished generating; may arrive long after the call. |
| `call.transcript.completed` | Transcript finished; order vs summary not guaranteed. |
| `call.voicemail.completed` | Voicemail left + processed; correlate via `resource.callId`. |
| `contact.updated` | Contact created or fields changed. |
| `contact.deleted` | Contact deleted (resource shape == `contact.updated`). |

### `message.received` / `message.delivered`

```json
{
  "data": {
    "resource": {
      "id": "AC-message",
      "direction": "incoming",
      "text": "hello",
      "status": "received",
      "createdAt": "2026-04-13T12:00:00.000Z"
    },
    "context": {
      "phoneNumberId": "PN123",
      "conversationId": "CN123",
      "userId": "US123",
      "contacts": { "ids": ["CT123"], "lookupStatus": "matched" },
      "senderIdentifier": "+15550001111",
      "recipientIdentifiers": ["+15550002222"]
    },
    "links": { "quo": "https://my.quo.com/inbox/..." }
  }
}
```

- `direction` is `'incoming'` for `message.received`, `'outgoing'` for `message.delivered`.
- `senderIdentifier`/`recipientIdentifiers` are usually E.164 but direct-number/internal flows can emit non-phone identifiers. For correlation key on `context.conversationId` + `context.phoneNumberId`, not `links.quo`.

### `call.ringing`

```json
{
  "data": {
    "resource": { "id": "AC-call", "direction": "incoming", "createdAt": "...", "updatedAt": "..." },
    "context": { "phoneNumberId": "PN123", "conversationId": "CN123", "userId": "US123" },
    "links": { "quo": "https://my.quo.com/inbox/..." }
  }
}
```
Lightweight: no `contacts`/`participants`/`phoneNumberType` yet (uses `CallRingingContext`).

### `call.answered`

`resource`: `id`, `direction`, `createdAt`, `answeredAt: string|null`, `answeredByUserId: string|null`, `updatedAt: string|null`. Context = `CallContext`.

```json
{
  "data": {
    "resource": { "id": "AC-call", "direction": "incoming", "createdAt": "...", "answeredAt": "...", "answeredByUserId": "US123", "updatedAt": "..." },
    "context": { "phoneNumberId": "PN123", "conversationId": "CN123", "phoneNumberType": "shared", "userId": "US123", "contacts": { "ids": ["CT123"], "lookupStatus": "matched" }, "participants": { "workspace": ["+15550000001"], "external": ["+15550000002"], "resolution": "available" } },
    "links": { "quo": "https://my.quo.com/inbox/..." }
  }
}
```
`answeredByUserId` is the Quo-side user, NOT the external party. Also fires on outgoing voicemail pickup — treat as "connected," not "human answered."

### `call.completed`

`resource`: `id`, `direction`, `status`, `createdAt`, `answeredAt: string|null`, `completedAt: string|null`, `updatedAt: string|null`, `duration: number|null` (seconds), `hasVoicemail: boolean`.

```ts
type CallCompletedStatus = 'answered' | 'unanswered' | 'failed' | 'forwarded' | 'abandoned' | 'ai-handled' | 'unknown'
```

```json
{
  "data": {
    "resource": { "id": "AC-call", "direction": "incoming", "status": "answered", "createdAt": "...", "answeredAt": "...", "completedAt": "...", "updatedAt": "...", "duration": 55, "hasVoicemail": false },
    "context": { "phoneNumberId": "PN123", "conversationId": "CN123", "phoneNumberType": "shared", "userId": "US123", "contacts": { "ids": ["CT123"], "lookupStatus": "matched" }, "participants": { "workspace": ["+15550000001"], "external": ["+15550000002"], "resolution": "available" } },
    "links": { "quo": "https://my.quo.com/inbox/..." }
  }
}
```
`duration` may be `null` for calls that never connected. `hasVoicemail: true` means a `call.voicemail.completed` arrives separately.

### `call.forwarded`

`resource`: `id`, `createdAt`, `updatedAt: string|null`, `forwardedFrom: string`, `forwardedTo: string`. Context = `CallContext`. Only this event carries `forwardedFrom`/`forwardedTo`.

### `call.missed`

`resource`: `id`, `createdAt`, `updatedAt` (minimal). Context = `CallContext`. Look up by `resource.id` for full call shape. Outgoing calls never fire this.

### `call.recording.completed`

```ts
interface CallRecording { id: string|null; duration: number|null; startTime: string|null; type: string|null; url: string|null }
```
`resource`: `id`, `direction`, `createdAt`, `answeredAt|null`, `completedAt|null`, `updatedAt|null`, `duration|null`, `recordings: CallRecording[]`.

```json
{
  "data": {
    "resource": { "id": "AC-call", "direction": "incoming", "createdAt": "...", "answeredAt": "...", "completedAt": "...", "updatedAt": "...", "duration": 55,
      "recordings": [ { "id": "REabc123", "duration": 55, "startTime": "...", "type": "audio/mpeg", "url": "https://recordings.example.com/REabc123.mp3" } ] },
    "context": { "...": "CallContext" },
    "links": { "quo": "..." }
  }
}
```
`recordings` is always an array; `[]` = no metadata in this payload. **Download/persist the file** — don't rely on `url` for long-term access.

### `call.summary.completed`

```ts
interface AgentCallSummaryJob { icon: string; name: string; result: { data: Array<{ name: string; value: string | number | boolean }> } }
```
`resource`: `callId`, `processingStatus: 'absent'|'in-progress'|'completed'|'failed'`, `summary: string[]|null`, `nextSteps: string[]|null`, `fromPhoneNumber: string|null`, `handledByAiAgent: boolean`, `answeredByUserId: string|null`, `jobs: AgentCallSummaryJob[]`.

```json
{
  "data": {
    "resource": { "callId": "AC-summary", "processingStatus": "completed", "summary": ["Customer asked for pricing details."], "nextSteps": ["Send follow-up email."], "fromPhoneNumber": null, "handledByAiAgent": false, "answeredByUserId": null, "jobs": [] },
    "context": { "...": "CallContext" },
    "links": { "quo": "..." }
  }
}
```
Readiness event, not call-ended. `summary`/`nextSteps` are arrays only when `processingStatus === 'completed'`, else `null`. Trust `processingStatus`, not arrival time. Correlate via `callId`.

### `call.transcript.completed`

```ts
interface DialogueEntry { userId: string|null; identifier: string|null; content: string; start: number; end: number }
```
`resource`: `callId`, `createdAt`, `duration: number`, `processingStatus: 'absent'|'in-progress'|'completed'|'failed'`, `dialogue: DialogueEntry[]|null`.

```json
{
  "data": {
    "resource": { "callId": "AC-transcript", "createdAt": "...", "duration": 42, "processingStatus": "completed",
      "dialogue": [ { "userId": "US123", "identifier": null, "content": "Thanks for calling, how can I help?", "start": 0, "end": 3 }, { "userId": null, "identifier": "+15550000002", "content": "Hi, I wanted to ask about pricing.", "start": 3, "end": 7 } ] },
    "context": { "...": "CallContext" },
    "links": { "quo": "..." }
  }
}
```
Independent of summary; may arrive before or after it. External speakers surface as `identifier` with `userId: null`; internal as `userId`.

### `call.voicemail.completed`

`resource`: `id` (voicemail activity id), `voicemailId: string|null`, `callId: string|null` (source call id, `null` if unresolved), `direction`, `duration: number`, `from: string`, `to: string`, `transcript: string|null`, `recordingUrl: string|null`, `createdAt`, `updatedAt`.

```json
{
  "data": {
    "resource": { "id": "AC-voicemail", "voicemailId": "VM123", "callId": "AC-source-call", "direction": "incoming", "duration": 18, "from": "+15550000002", "to": "+15550000001", "transcript": "Hi, leaving a quick message...", "recordingUrl": "https://recordings.example.com/VM123.mp3", "createdAt": "...", "updatedAt": "..." },
    "context": { "...": "CallContext" },
    "links": { "quo": "..." }
  }
}
```
`transcript` is `null` while processing or unavailable. Persist the recording. If source call unresolved: `callId` is `null` and `phoneNumberType` is `null`.

### `contact.updated` / `contact.deleted`

```ts
interface ContactResource {
  id: string; firstName: string|null; lastName: string|null; company: string|null; role: string|null
  location: string|null; source: string|null; externalId: string|null
  emails: Array<{ value: string; type: 'email' }>
  phoneNumbers: Array<{ value: string; type: 'phone-number' }>
  customFields: CustomField[]; createdAt: string; updatedAt: string
}
type CustomField =
  | { name: string; key: string; id?: string; type: 'string'|'url'|'address'; value: string|null }
  | { name: string; key: string; id?: string; type: 'number'; value: number|null }
  | { name: string; key: string; id?: string; type: 'boolean'; value: boolean }
  | { name: string; key: string; id?: string; type: 'date'; value: string|null }
  | { name: string; key: string; id?: string; type: 'multi-select'; value: string[] }
```

```json
{
  "data": {
    "resource": { "id": "CT123", "firstName": "Jane", "lastName": "Doe", "company": null, "role": null, "location": null, "source": null, "externalId": null,
      "emails": [{ "value": "jane@example.com", "type": "email" }],
      "phoneNumbers": [{ "value": "+15551234567", "type": "phone-number" }],
      "customFields": [ { "name": "Department", "key": "department", "id": "i1", "type": "multi-select", "value": ["sales"] } ],
      "createdAt": "2026-01-01T00:00:00.000Z", "updatedAt": "2026-04-13T12:00:00.000Z" },
    "context": { "userId": "US123", "sharedWithIds": ["US456"] },
    "links": { "quo": "https://my.quo.com/contacts/CT123" }
  }
}
```
`contact.*` are workspace-wide (no `resourceIds` filtering). `customFields[].id` omitted when absent. `contact.deleted` has the **identical** JSON shape — discriminate on the envelope `type`. Use `updatedAt` for freshness.

---

## Differences from legacy v1 webhooks (steer integrators)

Source: `webhooks-differences-from-current.md`, corroborated by `openphone-public-api-v1-prod.json`.

The beta API is **not** a drop-in replacement — management, signing, and payload shapes all change. The legacy and beta **signature schemes are not interchangeable**: code verifying the legacy `OpenPhone-Signature` header will reject every beta delivery.

| Area | Legacy (v1) | Beta |
| --- | --- | --- |
| Management | App settings + existing v1 API. | Beta endpoints only; not in app settings during beta. |
| Create endpoints | Four near-duplicate creates split by family: `POST /v1/webhooks/messages`, `/v1/webhooks/calls`, `/v1/webhooks/call-summaries`, `/v1/webhooks/call-transcripts` (confirmed in v1 OpenAPI spec). | One `POST /webhooks` with an `events` array; mix message/call/contact. |
| Event coverage | Calls, messages, contacts, transcripts. | Messages, call lifecycle, recordings, summaries, transcripts, voicemails, contacts. |
| Payload shape | `data.object` with object-specific fields. | `data.resource` + `data.context` + `data.links` envelope. |
| Filtering | Per-webhook subscription; per-phone-number for some types. | `resourceIds` filter for message/call; contact events workspace-wide. |
| Signature header | `OpenPhone-Signature`. | `webhook-id` + `webhook-timestamp` + `webhook-signature` (Standard-Webhooks-compatible). |
| Signing secret | OpenPhone-format secret. | `whsec_…` base64 secret, Svix-compatible. |
| Versioning | Single static version (`apiVersion: "v4"` in legacy payloads). | Date-versioned via `x-quo-api-version`; pinned per subscription at creation. |
| Delivery inspection | None. | Test events, delivery history, per-attempt detail, manual retry. |

Field remap: `data.object.id`→`data.resource.id`; `data.object.text`→`data.resource.text`; `data.object.phoneNumberId`→`data.context.phoneNumberId`; `data.object.userId`→`data.context.userId`; `data.object.contactIds`→`data.context.contacts.ids`; `data.deepLink`→`data.links.quo` (now explicitly nullable).

**Recommended migration (no downtime):** (1) add a *second* verifier for the new headers/secret while keeping the legacy verifier; (2) create the beta webhook with `status: "disabled"` (same URL) to pin `2026-03-30` and get a `whsec_…` secret without firing traffic; (3) add idempotency keyed on `webhook-id`; (4) flip beta to `enabled` (dual-run); (5) compare via `GET /webhooks/:id/events`; (6) disable legacy. Roll back by setting beta `status: "disabled"`. During dual-run, dedupe beta retries on `webhook-id` and dedupe across systems on stable business fields (message id, call id, contact id, type, timestamp).
