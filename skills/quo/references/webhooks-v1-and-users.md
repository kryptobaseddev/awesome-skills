## Quo (formerly OpenPhone) REST API — Users & Webhooks (v1)

> Source of truth: the live `*.md` doc twins under `https://www.quo.com/docs/mdx/...` and the live OpenAPI spec `openphone-public-api-v1-prod.json`. All field names, enums, and examples below are quoted verbatim from those sources (fetched 2026-06-15). Where the rendered doc pages and the OpenAPI JSON disagree, the disagreement is flagged in **Gotchas**.

### Base URL, auth, and versioning (read first)

- **Server (per live OpenAPI spec):** `https://api.quo.com`. Every doc page's embedded OpenAPI declares `servers: [{ url: https://api.quo.com }]` — EXCEPT the *Delete a webhook by ID* page, whose embedded spec renders `url: https://api.openphone.com`. The legacy/canonical host most integrations still use is `https://api.quo.com/v1`; both resolve to the same API. Treat the host as configurable and prefer whatever the workspace's existing integration already uses. (Source: `openphone-public-api-v1-prod.json` `servers`; `delete-a-webhook-by-id.md`.)
- **Auth header:** RAW API key in `Authorization` — **NOT** `Bearer`. The spec's only security scheme is `apiKey: { type: apiKey, in: header, name: Authorization }`, and `security: [{ apiKey: [] }]` is global. So the literal header is `Authorization: <YOUR_API_KEY>`. (Source: `openphone-public-api-v1-prod.json` `components.securitySchemes.apiKey`.) The string `Bearer` appears 0 times in the v1 spec.
- **Path version:** all endpoints in this domain are under `/v1/...`. (The separate dated spec `openphone-public-api-2026-03-30-prod.json` uses UN-prefixed paths like `/users` and contains NO webhook endpoints — do not mix the two.)
- **Webhook event payloads carry `"apiVersion": "v4"`** even though the management endpoints live under `/v1`. The version on the delivered event object is unrelated to the `/v1` of the create API. (Source: `guides/webhooks.md` sample payloads.)
- **No webhook signing secret in v1.** The v1 spec and the webhooks guide contain ZERO references to `signature`, `signing`, `secret`, HMAC, or svix. The webhook object returns a `key` field ("Webhook key", example `"example-key"`) but the docs never describe how to use it to verify authenticity, nor do they document retries or delivery guarantees. v1 has no documented signature-verification story. (Source: `guides/webhooks.md`; absence in `openphone-public-api-v1-prod.json`.)

---

### List users

```
GET https://api.quo.com/v1/users
```

`operationId: listUsers_v1`. Retrieve a paginated list of users in your Quo workspace.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `maxResults` | query | integer | **yes** | Max results per page. `default: 10`, `minimum: 1`, `maximum: 50`. (Marked `required: true` in the spec despite having a default.) |
| `pageToken` | query | string | no | Opaque cursor for the next page; pass back the `nextPageToken` from the previous response. |
| `Authorization` | header | string | **yes** | Raw API key (global security). |

Request body: none (GET).

Response `200` (`data[]` items — each user object; `firstName`, `lastName`, `pictureUrl` are nullable via `anyOf [string, null]`):

```json
{
  "data": [
    {
      "id": "US123abc",
      "email": "johndoe@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "pictureUrl": "https://example.com/picture.jpg",
      "role": "owner",
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```

curl:

```bash
curl -s "https://api.quo.com/v1/users?maxResults=50" \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- `maxResults` is **required** even though it has `default: 10`. Always send it; cap is 50.
- `totalItems` is documented as unreliable: ⚠️ "`totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue." Do NOT use it to compute page counts — paginate until `nextPageToken` is `null`.
- `nextPageToken` is `string | null`; loop until it is `null`.
- `role` enum is `owner | admin | member`. `firstName`/`lastName`/`pictureUrl` can be `null`.

---

### Get a user by ID

```
GET https://api.quo.com/v1/users/{userId}
```

`operationId: getUserById_v1`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `userId` | path | string | **yes** | Pattern `^US(.*)$`, e.g. `US123abc`. |
| `Authorization` | header | string | **yes** | Raw API key. |

Request body: none (GET).

Response `200` (single user object — same shape as list items):

```json
{
  "data": {
    "id": "US123abc",
    "email": "johndoe@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "pictureUrl": "https://example.com/picture.jpg",
    "role": "owner",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z"
  }
}
```

curl:

```bash
curl -s "https://api.quo.com/v1/users/US123abc" \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- `userId` must match `^US(.*)$`. There is no `groupId` field on the user object — the only fields are `id, email, firstName, lastName, pictureUrl, role, createdAt, updatedAt`. (Note: there is no `groupId` field in the live v1 user schema.)
- Error responses (`400/401/403/404/500`) share an envelope: `{ message, code, status, docs, title, trace?, errors[] }` where `code` is a per-status constant (e.g. `1100404` for 404, `1100401` for 401).

---

### List all webhooks

```
GET https://api.quo.com/v1/webhooks
```

`operationId: listWebhooks_v1`. List all webhooks for a user.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `userId` | query | string | no | Pattern `^US(.*)$`. "Defaults to the workspace owner." |
| `Authorization` | header | string | **yes** | Raw API key. |

Response `200` — `data[]` is a polymorphic `anyOf` union; each item is a webhook object whose `events[]` enum depends on the resource it was created for:

```json
{
  "data": [
    {
      "id": "WHabcd1234",
      "userId": "US123abc",
      "orgId": "OR1223abc",
      "label": "my webhook label",
      "status": "enabled",
      "url": "https://example.com/",
      "key": "example-key",
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z",
      "deletedAt": null,
      "events": ["message.received", "message.delivered"],
      "resourceIds": ["PN1234"]
    }
  ]
}
```

The webhook object is the SAME for every endpoint that returns one (list, get, and all four create endpoints). Required fields: `id, userId, orgId, label, status, url, key, createdAt, updatedAt, deletedAt, events, resourceIds`.

Field reference for the webhook object:

| field | type | notes |
|-------|------|-------|
| `id` | string | Pattern `^WH(.*)$`, e.g. `WHabcd1234`. |
| `userId` | string | `^US(.*)$` — creator of the webhook. |
| `orgId` | string | `^OR(.*)$` — owning organization. |
| `label` | string \| null | Optional human label. |
| `status` | enum | `enabled \| disabled` (default `enabled`). |
| `url` | string(uri) | Endpoint that receives events. |
| `key` | string | "Webhook key" (example `example-key`). Not documented as a signing secret. |
| `createdAt` | string(date-time) | ISO 8601. |
| `updatedAt` | string(date-time) | ISO 8601 (description erroneously says "created at"). |
| `deletedAt` | string(date-time) \| null | ISO 8601 when soft-deleted. |
| `events` | string[] | Enum depends on resource (see below). |
| `resourceIds` | array | Either `^PN(.*)$` phone-number IDs OR a single `["*"]` wildcard. |

**`events` enum by webhook resource** (from the list/get `anyOf` variants — verbatim):
- Messages: `message.received`, `message.delivered`
- Calls: `call.completed`, `call.ringing`, `call.recording.completed`
- Call summaries: `call.summary.completed`
- Call transcripts: `call.transcript.completed`
- (Also present in the response union, though not createable via the four documented endpoints: Contacts `contact.updated` / `contact.deleted`, and `task.assigned` — these last two require `resourceIds` to be exactly `["*"]`.)

curl:

```bash
curl -s "https://api.quo.com/v1/webhooks?userId=US123abc" \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- The response `data[]` is an `anyOf` union; a generic JSON consumer should branch on the resource by inspecting `events` rather than assuming a fixed enum.
- Omit `userId` and you only get the workspace owner's webhooks, not every webhook in the org.

---

### Get a webhook by ID

```
GET https://api.quo.com/v1/webhooks/{id}
```

`operationId: getWebhookById_v1`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | Pattern `^WH(.*)$`, e.g. `WH12345`. |
| `Authorization` | header | string | **yes** | Raw API key. |

Response `200` — `data` is the single webhook object (same `anyOf` union as list):

```json
{
  "data": {
    "id": "WHabcd1234",
    "userId": "US123abc",
    "orgId": "OR1223abc",
    "label": "my webhook label",
    "status": "enabled",
    "url": "https://example.com/",
    "key": "example-key",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "deletedAt": null,
    "events": ["call.completed", "call.ringing", "call.recording.completed"],
    "resourceIds": ["PN1234"]
  }
}
```

curl:

```bash
curl -s "https://api.quo.com/v1/webhooks/WH12345" \
  -H "Authorization: YOUR_API_KEY"
```

---

### Delete a webhook by ID

```
DELETE https://api.quo.com/v1/webhooks/{id}
```

`operationId: deleteWebhookById_v1`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | Pattern `^WH(.*)$`, e.g. `WH12345`. |
| `Authorization` | header | string | **yes** | Raw API key. |

Response `204`: Success — **no body**. (Other codes: `400` "Invalid Version" with `code: 0305400`, `401`, `403`, `404`, `500`.)

curl:

```bash
curl -s -X DELETE "https://api.quo.com/v1/webhooks/WH12345" \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- Success is `204 No Content` — do not try to parse a JSON body.
- This page is the one whose embedded spec shows `url: https://api.openphone.com` (vs `api.quo.com` on every other page).

---

### Create a new webhook for messages

```
POST https://api.quo.com/v1/webhooks/messages
```

`operationId: createMessageWebhook_v1`. Required body fields: `events`, `url`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `url` | body | string(uri) | **yes** | Endpoint that receives events. |
| `events` | body | string[] | **yes** | Items enum: `message.received`, `message.delivered`. |
| `resourceIds` | body | array | no | `^PN(.*)$` phone-number IDs, or `["*"]` for all. |
| `label` | body | string | no | Webhook label. |
| `status` | body | enum | no | `enabled \| disabled` (default `enabled`). |
| `userId` | body | string | no | `^US(.*)$`. "If not provided, default to workspace owner." |
| `Authorization` | header | string | **yes** | Raw API key. |

Request body:

```json
{
  "url": "https://example.com",
  "events": ["message.received", "message.delivered"],
  "resourceIds": ["PN1234"],
  "label": "my webhook label",
  "status": "enabled",
  "userId": "US123abc"
}
```

Response `201` (webhook object):

```json
{
  "data": {
    "id": "WHabcd1234",
    "userId": "US123abc",
    "orgId": "OR1223abc",
    "label": "my webhook label",
    "status": "enabled",
    "url": "https://example.com",
    "key": "example-key",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "deletedAt": null,
    "events": ["message.received", "message.delivered"],
    "resourceIds": ["PN1234"]
  }
}
```

curl:

```bash
curl -s -X POST "https://api.quo.com/v1/webhooks/messages" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","events":["message.received","message.delivered"],"resourceIds":["PN1234"],"label":"my webhook label","status":"enabled"}'
```

---

### Create a new webhook for calls

```
POST https://api.quo.com/v1/webhooks/calls
```

`operationId: createCallWebhook_v1`. Required body fields: `url`, `events`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `url` | body | string(uri) | **yes** | Endpoint that receives events. |
| `events` | body | string[] | **yes** | Items enum: `call.completed`, `call.ringing`, `call.recording.completed`. |
| `resourceIds` | body | array | no | `^PN(.*)$` IDs or `["*"]`. |
| `userId` | body | string | no | `^US(.*)$`; defaults to workspace owner. |
| `label` | body | string | no | Webhook label. |
| `status` | body | enum | no | `enabled \| disabled` (default `enabled`). |
| `Authorization` | header | string | **yes** | Raw API key. |

Request body:

```json
{
  "url": "https://example.com/",
  "events": ["call.completed", "call.ringing", "call.recording.completed"],
  "resourceIds": ["PN1234"],
  "userId": "US123abc",
  "label": "my webhook label",
  "status": "enabled"
}
```

Response `201` (webhook object — `events` echoes the call enum):

```json
{
  "data": {
    "id": "WHabcd1234",
    "userId": "US123abc",
    "orgId": "OR1223abc",
    "label": "my webhook label",
    "status": "enabled",
    "url": "https://example.com/",
    "key": "example-key",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "deletedAt": null,
    "events": ["call.completed", "call.ringing", "call.recording.completed"],
    "resourceIds": ["PN1234"]
  }
}
```

curl:

```bash
curl -s -X POST "https://api.quo.com/v1/webhooks/calls" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/","events":["call.completed","call.ringing","call.recording.completed"],"resourceIds":["PN1234"]}'
```

---

### Create a new webhook for call summaries

```
POST https://api.quo.com/v1/webhooks/call-summaries
```

`operationId: createCallSummaryWebhook_v1`. Required body fields: `events`, `url`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `events` | body | string[] | **yes** | `minItems: 1`. Only enum value: `call.summary.completed`. |
| `url` | body | string(uri) | **yes** | Endpoint that receives events. |
| `resourceIds` | body | array | no | `^PN(.*)$` IDs or `["*"]`. |
| `label` | body | string | no | Webhook label. |
| `status` | body | enum | no | `enabled \| disabled` (default `enabled`). |
| `userId` | body | string | no | `^US(.*)$`; defaults to workspace owner. |
| `Authorization` | header | string | **yes** | Raw API key. |

Request body:

```json
{
  "events": ["call.summary.completed"],
  "url": "https://example.com",
  "resourceIds": ["PN1234"],
  "label": "my webhook label",
  "status": "enabled",
  "userId": "US123abc"
}
```

Response `201`: webhook object with `events: ["call.summary.completed"]` (same shape as the others).

curl:

```bash
curl -s -X POST "https://api.quo.com/v1/webhooks/call-summaries" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"events":["call.summary.completed"],"url":"https://example.com","resourceIds":["PN1234"]}'
```

**Gotchas**
- `events` has `minItems: 1` and a single legal value here.
- Requires AI/call-summary capability on the workspace plan; summaries only fire when Quo generates them.

---

### Create a new webhook for call transcripts

```
POST https://api.quo.com/v1/webhooks/call-transcripts
```

`operationId: createCallTranscriptWebhook_v1`. Required body fields: `events`, `url`.

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `events` | body | string[] | **yes** | `minItems: 1`. Only enum value: `call.transcript.completed`. |
| `url` | body | string(uri) | **yes** | Endpoint that receives events. |
| `label` | body | string | no | Webhook label. |
| `resourceIds` | body | array | no | `^PN(.*)$` IDs or `["*"]`. Note: the transcripts page renders the example as a bare `PN1234` (the other three render `["PN1234"]`); the type is still an array. |
| `status` | body | enum | no | `enabled \| disabled`. |
| `userId` | body | string | no | `^US(.*)$`; defaults to workspace owner. |
| `Authorization` | header | string | **yes** | Raw API key. |

Request body:

```json
{
  "events": ["call.transcript.completed"],
  "url": "https://example.com",
  "resourceIds": ["PN1234"],
  "label": "my webhook label",
  "status": "enabled",
  "userId": "US123abc"
}
```

Response `201`: webhook object with `events: ["call.transcript.completed"]`.

curl:

```bash
curl -s -X POST "https://api.quo.com/v1/webhooks/call-transcripts" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"events":["call.transcript.completed"],"url":"https://example.com","resourceIds":["PN1234"]}'
```

---

### Webhook payload reference (delivered event envelope)

Every delivered event is wrapped in a common envelope. From `guides/webhooks.md`:

```json
{
  "id": "EVsampleEvent01",
  "object": "event",
  "apiVersion": "v4",
  "createdAt": "2022-01-23T16:55:52.557Z",
  "type": "message.received",
  "data": { "object": { /* resource-specific */ } }
}
```

- **Message** (`message.received` / `message.delivered`): `data.object` is a `message` with `id, object, from, to[], direction, text, status, createdAt, userId, phoneNumberId, contactIds[]`.
- **Call** (`call.ringing` / `call.completed` / `call.recording.completed`): `data.object` is a `call` with `id, object, answeredAt, answeredBy, initiatedBy, direction, status, completedAt, createdAt, duration, forwardedFrom, forwardedTo, phoneNumberId, participants[], updatedAt, userId, contactIds[]`.
- **Call summary** (`call.summary.completed`): `type` is `"callSummary"` (NOT the event name); `data.object` = `callId, object, status, summary[], nextSteps[], contactIds[]`.
- **Call transcript** (`call.transcript.completed`): `type` is `"callTranscript"`; `data.object` = `callId, object, createdAt, dialogue[ {content, start, end, identifier, userId} ], duration, status, contactIds[]`.

**Delivery / retries / authenticity:** the v1 webhooks guide documents ONLY the payload shapes. It says NOTHING about retry policy, delivery guarantees, or how to verify a payload's authenticity. There is no signing secret, HMAC header, or signature field anywhere in the v1 spec or guide. The webhook object's `key` field exists but is undocumented as a verification mechanism. If you need signature verification, that is a beta-API concern, not v1.

**Gotchas (whole domain)**
- The delivered event's `type` for summaries/transcripts is `callSummary` / `callTranscript`, which does NOT match the subscription event names `call.summary.completed` / `call.transcript.completed`. Switch on both forms.
- Payload `apiVersion` is `v4` even though management is `/v1`.
- App-created webhooks and API-created webhooks are mutually invisible: "Webhooks created in the Quo app are not compatible with those created via the API."