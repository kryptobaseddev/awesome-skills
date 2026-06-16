## Quo (formerly OpenPhone) API — Building with AI/LLMs, Cost & Carrier Registration

> Source-grounded against the live `quo.com` docs (June 2026) and the public OpenAPI spec. **Quo is the rebrand of OpenPhone** — docs, the API host, and support email all now use `quo.com`, while the public OpenAPI JSON files are still hosted on the legacy `openphone-public-api-prod` S3 bucket.

### Base URL & Auth (read this first)

- **Base URL:** `https://api.quo.com/v1` — the OpenAPI `servers[0].url` is `https://api.quo.com` and every live curl example uses `https://api.quo.com/v1/...`. (The legacy `https://api.quo.com/v1` host is **not** what the current docs publish — use `api.quo.com`.)
  Source: <https://www.quo.com/docs/mdx/api-reference/send-your-first-message.md>, <https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json>
- **Auth header:** raw API key, **not** a Bearer token. The docs state verbatim: *"Include your API key in the Authorization header of each request: `Authorization: YOUR_API_KEY` The Quo API does not use a Bearer token for authentication."* The OpenAPI `securityScheme` is `{ type: apiKey, in: header, name: Authorization }`.
  Source: <https://www.quo.com/docs/mdx/api-reference/authentication.md>
- **Get a key:** Workspace Settings → "API" tab → "Generate API key" (requires workspace **owner or admin** privileges). Each key grants full API access; spaces are not allowed in the key name.
  Source: <https://www.quo.com/docs/mdx/api-reference/authentication.md>
- **Rate limit:** **10 requests/second per API key**. Exceeding it returns `429`. Implement throttling / exponential backoff.
  Source: <https://www.quo.com/docs/mdx/api-reference/rate-limits.md>

---

### Building with AI/LLMs — recommended patterns

The "Building with AI LLMs" guide is a workflow guide (no endpoints of its own). Verbatim guidance from <https://www.quo.com/docs/mdx/guides/building-with-ai-llms.md>:

- **Feed the LLM the spec, not your keys.** Provide the LLM with two artifacts:
  - OpenAPI spec: `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json`
  - The "complete documentation package" (llm-ready docs zip): `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-llm-ready-docs-prod.zip`
  - The docs index (`llms.txt`) for page discovery: `https://www.quo.com/docs/llms.txt`
- **Security (verbatim):** *"Never share API keys with LLMs · Keep sensitive data out of prompts · Validate all generated code · Follow security best practices."*
- **API usage (verbatim):** *"Follow Quo API rate limits · Implement proper error handling · Monitor API usage · Optimize API calls."*
- **Documented integration patterns:** automated message handling/responses, contact sync/management, processing call summaries & recording data, and scheduling/reminders (Tasks).
- The guide uses Claude in its examples but states the principles apply to any capable LLM.

**Polling vs. webhooks (grounded in the API surface):** For AI/agent workflows that react to inbound activity (new SMS, completed call, ready transcript/summary), **register a webhook** rather than polling `GET /v1/messages` / `GET /v1/calls`. Polling burns your 10 req/s budget and adds latency; webhooks push the event the moment it occurs. Quo exposes dedicated webhook-creation endpoints for exactly the AI-relevant events: inbound messages, call lifecycle, **AI call summaries**, and **AI call transcripts**. Note: *"Webhooks created in the Quo app are not compatible with those created via the API. You cannot access or modify app webhooks through the API, or API webhooks in the app."*
Source: <https://www.quo.com/docs/mdx/guides/webhooks.md>

---

### `POST /v1/messages` — Send a text message

```
POST https://api.quo.com/v1/messages
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `content` | body | string | **yes** | `minLength: 1`, `maxLength: 1600`, must contain a non-whitespace char (`pattern: .*\S.*`). |
| `from` | body | string | **yes** | Sender. Either a Quo phone number ID (`^PN(.*)$`) **or** an E.164 number (`^\+[1-9]\d{1,14}$`). |
| `to` | body | string[] | **yes** | Array with `minItems: 1`, `maxItems: 1` — **exactly one recipient**. E.164 (`+15555555555`). |
| `userId` | body | string | no | `^US(.*)$`. Quo user sending the message. Defaults to the phone number owner if omitted. |
| `setInboxStatus` | body | string (enum) | no | Only allowed value: `"done"`. Moves the resulting conversation to the Done inbox view. Default leaves it open. |
| `phoneNumberId` | body | string | no | **DEPRECATED** — use `from` instead. `^PN(.*)$`. |

Request body:

```json
{
  "content": "Hello, world!",
  "from": "+15555555555",
  "to": ["+15555555555"],
  "userId": "US123abc",
  "setInboxStatus": "done"
}
```

Response — `202 Accepted`:

```json
{
  "data": {
    "id": "AC123abc",
    "to": ["+15555555555"],
    "from": "+15555555555",
    "text": "Hello, world!",
    "phoneNumberId": "PN123abc",
    "direction": "outgoing",
    "userId": "US123abc",
    "status": "sent",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z"
  }
}
```

`status` enum: `queued | sent | delivered | undelivered | received`. `direction` enum: `incoming | outgoing`.

curl:

```bash
curl --request POST \
  --url https://api.quo.com/v1/messages \
  --header 'Authorization: YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "content": "Hello, world!",
    "from": "+15555555555",
    "to": ["+15555555555"],
    "userId": "US123abc"
  }'
```

**Gotchas:**
- Success is **`202`, not `200`** — the send is accepted asynchronously; poll `GET /v1/messages/{id}` (or use a `message.delivered` webhook) for terminal delivery state.
- `to` accepts **only one** recipient (`maxItems: 1`). No bulk/fan-out in a single call.
- **MMS is not supported** in the current API version — text only.
- `400` here means **A2P Registration Not Approved** (code `0206400`), not a malformed body — see registration gate below.
- Insufficient credit → the API returns an error and the message is **not** sent. Partial credits can't be used.
- `phoneNumberId` in the request body is deprecated; use `from`.

---

### `GET /v1/messages` — List messages

```
GET https://api.quo.com/v1/messages
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `phoneNumberId` | query | string | **yes** | Your Quo phone number ID. |
| `participants` | query | string[] | **yes** | The other party/parties (E.164). |
| `maxResults` | query | integer | **yes** | Page size. |
| `userId` | query | string | no | Filter by sending user. |
| `since` | query | string (date-time) | no | ISO 8601. |
| `createdAfter` | query | string (date-time) | no | ISO 8601. |
| `createdBefore` | query | string (date-time) | no | ISO 8601. |
| `pageToken` | query | string | no | Cursor from `nextPageToken`. |

Response — `200`:

```json
{
  "data": [
    {
      "id": "AC123abc",
      "to": ["+15555555555"],
      "from": "+15555555555",
      "text": "Hello, world!",
      "phoneNumberId": "PN123abc",
      "direction": "incoming",
      "userId": "US123abc",
      "status": "received",
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```

**Gotchas:**
- `phoneNumberId`, `participants`, and `maxResults` are **all required** — a bare `GET /v1/messages` will 4xx.
- This is a polling surface. For AI agents reacting to inbound SMS, prefer a `message.received` webhook over a poll loop to respect the 10 req/s ceiling.

---

### `GET /v1/messages/{id}` — Get a message by ID

```
GET https://api.quo.com/v1/messages/{id}
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | Message ID (`^AC(.*)$`). |

Response — `200`: same single-object `{ "data": { ... } }` shape as the send response above. Use this to resolve final `status` after a `202` send.

**Gotchas:** Message IDs are prefixed `AC` (same prefix family as call IDs in webhook payloads — match on the full ID, not the prefix).

---

### `POST /v1/webhooks/messages` — Create a message webhook

```
POST https://api.quo.com/v1/webhooks/messages
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `events` | body | string[] (enum) | **yes** | Allowed: `message.received`, `message.delivered`. |
| `url` | body | string | **yes** | HTTPS endpoint that receives events. |
| `label` | body | string | no | Human label, e.g. `my webhook label`. |
| `resourceIds` | body | string[] | no | Phone number IDs to scope to, e.g. `["PN1234"]`. |
| `status` | body | string (enum) | no | `enabled` (default) or `disabled`. |
| `userId` | body | string | no | `^US(.*)$`. Creator; defaults to workspace owner. |

Request body:

```json
{
  "events": ["message.received", "message.delivered"],
  "url": "https://example.com/webhooks/quo",
  "label": "inbound-sms-to-agent",
  "resourceIds": ["PN1234"],
  "status": "enabled",
  "userId": "US123abc"
}
```

Response — `201`:

```json
{
  "data": {
    "id": "WH123abc",
    "userId": "US123abc",
    "orgId": "OR123abc",
    "label": "inbound-sms-to-agent",
    "status": "enabled",
    "url": "https://example.com/webhooks/quo",
    "key": "whsec_...",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "deletedAt": null,
    "events": ["message.received", "message.delivered"],
    "resourceIds": ["PN1234"]
  }
}
```

Inbound event payload (`message.received`):

```json
{
  "id": "EVsampleEvent01",
  "object": "event",
  "apiVersion": "v4",
  "createdAt": "2022-01-23T16:55:52.557Z",
  "type": "message.received",
  "data": {
    "object": {
      "id": "ACsampleActivity01",
      "object": "message",
      "from": "+19876543210",
      "to": ["+15555555555"],
      "direction": "incoming",
      "text": "Hello, world!",
      "status": "delivered",
      "createdAt": "2022-01-23T16:55:52.420Z",
      "userId": "USu5AsEHuQ",
      "phoneNumberId": "PNtoDbDhuz",
      "contactIds": ["6824dfb69aee85c132b7dg65"]
    }
  }
}
```

**Gotchas:**
- The create response returns a `key` — the signing secret used to **verify webhook signatures**; persist it and validate every delivery.
- API-created webhooks and app-created webhooks are **mutually invisible** — you can't manage one from the other surface.
- The actual event payload is nested under `data.object`, with the `event` envelope (`id`, `type`, `apiVersion`, `createdAt`) at the top — don't read `data` as the message directly.

---

### `POST /v1/webhooks/calls` — Create a call webhook

```
POST https://api.quo.com/v1/webhooks/calls
```

Same body schema as the message webhook (`url` + `events` required; optional `label`, `resourceIds`, `status`, `userId`).

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `url` | body | string | **yes** | HTTPS receiver. |
| `events` | body | string[] (enum) | **yes** | Allowed: `call.completed`, `call.ringing`, `call.recording.completed`. |
| `resourceIds` | body | string[] | no | Phone number IDs. |
| `label` / `status` / `userId` | body | — | no | As above (`status`: `enabled`/`disabled`). |

`call.ringing` payload (top-level envelope + `data.object`):

```json
{
  "id": "EVsampleEvent02",
  "object": "event",
  "apiVersion": "v4",
  "createdAt": "2022-06-24T19:35:46.825Z",
  "type": "call.ringing",
  "data": {
    "object": {
      "id": "ACsXlF0",
      "object": "call",
      "direction": "outgoing",
      "status": "ringing",
      "duration": 60,
      "phoneNumberId": "PN1ZmRMzlx",
      "participants": ["+15555555555"],
      "userId": "USlHhXmRMz",
      "contactIds": ["6824dfb69aee85c132b7dg65"]
    }
  }
}
```

**Gotchas:** `call.recording.completed` fires only after the recording is processed — your AI pipeline should treat recording/transcript availability as eventually-consistent, not synchronous with `call.completed`.

---

### `POST /v1/webhooks/call-summaries` — AI call-summary webhook

```
POST https://api.quo.com/v1/webhooks/call-summaries
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `events` | body | string[] (enum) | **yes** | Only allowed: `call.summary.completed`. |
| `url` | body | string | **yes** | HTTPS receiver. |
| `resourceIds` / `label` / `status` / `userId` | body | — | no | As above. |

`call.summary.completed` payload (note `type` is `callSummary`):

```json
{
  "id": "EVsampleEvent02",
  "object": "event",
  "apiVersion": "v4",
  "createdAt": "2022-06-24T19:35:46.825Z",
  "type": "callSummary",
  "data": {
    "object": {
      "callId": "ACsampleActivity02",
      "object": "callSummary",
      "status": "completed",
      "summary": ["You talked about the weather."],
      "nextSteps": ["Bring an umbrella."],
      "contactIds": ["6824dfb69aee85c132b7dg65"]
    }
  }
}
```

**Gotchas:** Call summaries/transcripts are **only available on business and scale plans** — the corresponding `GET` endpoints and these webhooks will not produce data on lower plans. The webhook event enum is `call.summary.completed`, but the payload `type` field is `callSummary` — match on `type`, not the registered event name.

---

### `POST /v1/webhooks/call-transcripts` — AI call-transcript webhook

```
POST https://api.quo.com/v1/webhooks/call-transcripts
```

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `events` | body | string[] (enum) | **yes** | Only allowed: `call.transcript.completed`. |
| `url` | body | string | **yes** | HTTPS receiver. |
| `resourceIds` / `label` / `status` / `userId` | body | — | no | As above. |

`call.transcript.completed` payload (`type` is `callTranscript`):

```json
{
  "id": "EVsampleEvent02",
  "object": "event",
  "apiVersion": "v4",
  "createdAt": "2022-06-24T19:35:46.825Z",
  "type": "callTranscript",
  "data": {
    "object": {
      "callId": "ACsampleActivity02",
      "object": "callTranscript",
      "createdAt": "2022-06-24T19:34:50.279Z",
      "dialogue": [
        {
          "content": "Hello, world!",
          "start": 5.123456,
          "end": 10.123456,
          "identifier": "+19876543210",
          "userId": "USlHhXmRMz"
        }
      ],
      "duration": 5,
      "status": "completed",
      "contactIds": ["6824dfb69aee85c132b7dg65"]
    }
  }
}
```

**Gotchas:** Transcripts are business/scale-plan only. Each `dialogue` entry has float `start`/`end` seconds and an `identifier` (E.164 of the speaker).

---

### Cost & US Carrier Registration (A2P 10DLC)

#### HARD requirement: register before sending US SMS

> **US Messaging Registration Required:** *"To send text messages to US numbers via the API, you must complete US Carrier Registration."*
> Source: <https://www.quo.com/docs/mdx/api-reference/authentication.md>, <https://www.quo.com/docs/mdx/api-reference/send-your-first-message.md>
> Registration guide: <https://support.openphone.com/hc/en-us/articles/15519949741463-Guide-to-US-carrier-registration-for-OpenPhone-customers>

If you call `POST /v1/messages` to a US number before registration is approved, the API returns:

```json
{
  "title": "A2P Registration Not Approved",
  "description": "A2P Registration Not Approved",
  "code": "0206400",
  "status": 400,
  "docs": "https://quo.com/docs",
  "message": "...",
  "errors": []
}
```

(`code` const `0206400`, `status` const `400`, `title`/`description` const `A2P Registration Not Approved`.)
Source: <https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json>

#### Plan & account gating
- An **active Quo subscription is required** for API access. Expired subscription → `402` (`code 0201402`, title "Subscription Expired").
- Credit-based billing: add funds under "Plans & Billing"; credits are deducted automatically on send. **Insufficient credit → error, message not sent.** Partial credits cannot be used.
- **Call summaries & transcripts require business or scale plans** (Source: <https://www.quo.com/docs/llms.txt>).
Source: <https://www.quo.com/docs/mdx/pricing-support/pricing-overview.md>

#### Pricing model (segment-based)
- **$0.01 per segment** for standard (e.g. US/Canada) destinations.
- **$0.01 + country-specific rate per segment** for international destinations (rates vary by country; see <https://www.openphone.com/rates>).
- You are charged **only for outgoing API-powered messages** (direct API calls or apps built on the API). **MMS is not supported.**

#### What a "segment" is
- A segment is the SMS billing unit. Messages are split into segments by **(1) length** and **(2) character type**.
- **Standard GSM-7** (A–Z, a–z, 0–9, spaces, basic punctuation): **up to 160 characters/segment**.
- **Special/non-GSM** characters: capacity drops to **70 characters/segment** — and critically, *"If your message contains even one special character, the entire message is billed at the 70-character limit — not just the portion with special characters."* Special chars include accented letters (é, ñ, ü), curly/smart quotes (" " ' '), emojis, and many international chars.
- Quo's API **automatically enables "smart encoding"** to minimize segments where possible.
Source: <https://www.quo.com/docs/mdx/pricing-support/pricing-overview.md>

#### Cost-minimization tactics (verbatim from the minimizing-costs guide)
- Stick to standard Latin alphabet, numbers, and basic punctuation (160 chars/segment).
- Avoid special characters (é, ñ, ß) — they cut capacity to 70 chars/segment.
- Avoid emojis — most count as **two** characters; heavy use inflates segment count fast.
- Each **line break counts as a character**.
- **Shorten long URLs** — long URLs can span multiple segments; shortened links save space.
- Use widely understood abbreviations to cut character count.
- Estimate before sending with the [Segment Calculator](https://twiliodeved.github.io/message-segment-calculator/).
Source: <https://www.quo.com/docs/mdx/pricing-support/minimizing-costs.md>

#### Cost tactics derived from the API surface
- **Webhooks over polling.** Don't poll `GET /v1/messages` / `GET /v1/calls` in a loop to detect activity — register `message.received` / `call.*` webhooks. Polling wastes your 10 req/s budget and risks `429`s.
- **Batch and throttle outbound sends** to stay under 10 req/s; on `429`, back off exponentially.
- **One recipient per `POST /v1/messages`** — plan fan-out client-side under the rate limit.

---

### API response codes (reference)

| Code | Status | Meaning |
|------|--------|---------|
| 200 | OK | Request successful |
| 201 | Created | Resource created (e.g. webhook) |
| 202 | Accepted | Request accepted for processing (message send) |
| 204 | No Content | Success, no body |
| 400 | Bad Request | Invalid parameters — **or A2P Registration Not Approved (`0206400`) on `POST /v1/messages`** |
| 401 | Unauthorized | Missing/invalid API key (`0200401`) |
| 402 | (Payment Required) | Subscription Expired (`0201402`) — message endpoints |
| 403 | Forbidden | Insufficient permissions / account setting not enabled (`0202403` "Not Phone Number User") |
| 404 | Not Found | Resource doesn't exist (`0200404`) |
| 409 | Conflict | Conflict with another request |
| 422 | Unprocessable Entity | Well-formed but semantically invalid |
| 429 | Too Many Requests | Rate limit exceeded — use exponential backoff |
| 500 | Server Error | Quo-side issue (`0201500`) |

Source: <https://www.quo.com/docs/mdx/api-reference/error-codes.md>, <https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json>
