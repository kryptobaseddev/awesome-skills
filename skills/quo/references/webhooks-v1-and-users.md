# Quo (formerly OpenPhone) — v1 webhooks and Users (both surfaces)

This file covers two things: the **legacy v1 webhook endpoints** (`/v1/webhooks/...`, with one create endpoint per event family and the `openphone-signature` signing scheme), and the **Users** resource on both the v1 surface and the `2026-03-30` surface. For new webhook work, use the `2026-03-30` webhook API in `webhooks.md`. Read this file when you have to maintain or migrate a v1 subscription.

## Contents

1. [Which surface to use](#which-surface-to-use)
2. [Request basics](#request-basics)
3. [Users — 2026-03-30](#users--2026-03-30)
4. [Users — v1](#users--v1)
5. [v1 webhooks: endpoints](#v1-webhooks-endpoints)
6. [v1 webhooks: delivered payloads](#v1-webhooks-delivered-payloads)
7. [v1 webhooks: signature (`openphone-signature`)](#v1-webhooks-signature-openphone-signature)
8. [Migration diffs](#migration-diffs)
9. [Sources](#sources-checked-2026-10-08)

## Which surface to use

| Need | v1 | `2026-03-30` | Use |
| --- | --- | --- | --- |
| List users | `GET /v1/users` (`maxResults`, `pageToken`) | `GET /users` (`limit`, `after`) | **2026-03-30** |
| Get a user | `GET /v1/users/{userId}` | `GET /users/{userId}` | **2026-03-30** |
| A user's phone numbers | — | `GET /users/{userId}/phone-numbers` | 2026-03-30 only |
| Members assigned to a number (with `groupId`) | — | `GET /phone-numbers/{phoneNumberId}/users` | 2026-03-30 only |
| Create a webhook for messages, calls, summaries or transcripts | four `POST /v1/webhooks/{family}` | `POST /webhooks` | **2026-03-30** (see `webhooks.md`) |
| List, get or delete a v1 webhook | `/v1/webhooks`, `/v1/webhooks/{id}` | n/a for `WH…` ids | v1, only to manage legacy subscriptions |
| Update a webhook, rotate the secret, delivery logs, test events, contact/task events | — | yes | 2026-03-30 only |

User data is the same on both surfaces. The real differences are the pagination style, the envelope (`totalItems` / `nextPageToken` on v1 versus `nextCursor` on `2026-03-30`), and the required version header.

## Request basics

| | v1 | 2026-03-30 |
| --- | --- | --- |
| Host | `https://api.quo.com` | `https://api.quo.com` |
| Path | `/v1/...` | unprefixed (`/users`) |
| Version header | none | **`Quo-Api-Version: 2026-03-30` required** (`400` without it) |
| Auth | `Authorization: YOUR_API_KEY` (raw key, **no `Bearer`**) | same |
| Pagination | `maxResults` 1–50 (default 10, **optional**) + `pageToken`; response `totalItems`, `nextPageToken` | `limit` 1–50 (default 10) + `after`; response `nextCursor` |
| Errors | `{ message, code, status, docs, title, trace?, errors? }`. `code` is a string constant per error (e.g. `"0305400"` = Invalid Version) | `{ title, message, docs, trace?, errors?: [{path, message, value, schema}] }` |

Both surfaces allow 10 requests per second per key. The old host `api.openphone.com` is a legacy alias; use `api.quo.com`.

## Users — 2026-03-30

User object (all fields required; nullable where marked):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string `^US` | e.g. `US123abc` |
| `email` | string (email) | |
| `firstName`, `lastName`, `pictureUrl` | string \| null | |
| `role` | **`owner` \| `admin` \| `member`** | Workspace role. |
| `createdAt`, `updatedAt` | date-time | |

The user object has **no `groupId`**. `groupId` (`GR…`) appears only on the phone-number-members endpoint below.

### `GET /users` — list users

| Query | Type | Notes |
| --- | --- | --- |
| `limit` | int 1–50 | Default 10. |
| `after` | string | `nextCursor` from the previous page. |

There are no filters. Required header: `Quo-Api-Version: 2026-03-30`.

```json
{ "data": [ { "id": "US123abc", "email": "johndoe@example.com", "firstName": "John", "lastName": "Doe",
  "pictureUrl": null, "role": "owner", "createdAt": "2022-01-01T00:00:00Z", "updatedAt": "2022-01-01T00:00:00Z" } ],
  "nextCursor": "eyJsYXN0SWQiOiJVU211a09NaXBhIn0" }
```

Keep paging until `nextCursor` is `null`.

```bash
curl "https://api.quo.com/users?limit=50" -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30"
```

### `GET /users/{userId}` — get a user

`userId` must match `^US(.*)$`. The response is `{ "data": User }`. A `404` also covers an id that belongs to a different workspace.

### `GET /users/{userId}/phone-numbers` — numbers assigned to a user

| Query | Type | Notes |
| --- | --- | --- |
| `limit`, `after` | | Standard cursor paging. |
| `include` | `restrictions`[] (comma-separated) | Adds the `restrictions` section. When omitted, the section is **absent**, not `null`. |

Each item has `id` (`PN…`), `groupId` (`GR…`), `name`, `phoneNumber` (E.164), `formattedNumber|null`, `forward|null`, `portRequestId|null`, `portingStatus|null`, `symbol|null`, `createdAt`, `updatedAt`, and optionally `restrictions: { calling: {US, CA, Intl}, messaging: {US, CA, Intl} }`, where each value is `restricted` or `unrestricted`. Member lists are **not** embedded; use the endpoint below. The full phone-number schema is in the messages and numbers reference.

### `GET /phone-numbers/{phoneNumberId}/users` — members of a number

The path takes `phoneNumberId` (`^PN`), with `limit`/`after` for paging. Results are ordered by user id, because assignments have no timestamp. Items are a **slimmer user**: `id, email, firstName|null, lastName|null, role, groupId` (`GR…`). This variant has no `pictureUrl` or timestamps.

### Users in tasks (2026-03-30)

`POST /tasks/{taskId}/users` with `{ "userId": "US…" }` assigns a task, and `DELETE /tasks/{taskId}/users` unassigns it. Both return `{ data: { taskId, revision } }`. Details are in the conversations and tasks reference. These calls fire the `task.assigned` / `task.unassigned` webhooks.

## Users — v1

The fields and the `role` enum (`owner | admin | member`) are identical to `2026-03-30`. Only paging and the envelope differ.

### `GET /v1/users`

| Query | Type | Notes |
| --- | --- | --- |
| `maxResults` | int 1–50 | Default 10. **Optional** in the current spec; v1.0.0 of this skill wrongly said it was required. |
| `pageToken` | string | `nextPageToken` from the previous page. |

```json
{ "data": [ { "id": "US123abc", "email": "johndoe@example.com", "firstName": "John", "lastName": "Doe",
  "pictureUrl": "https://example.com/picture.jpg", "role": "owner",
  "createdAt": "2022-01-01T00:00:00Z", "updatedAt": "2022-01-01T00:00:00Z" } ],
  "totalItems": 1, "nextPageToken": null }
```

The spec itself warns that `totalItems` is **not accurate**, so never compute page counts from it. Loop until `nextPageToken` is `null`.

### `GET /v1/users/{userId}`

`userId` must match `^US(.*)$`. The response is `{ "data": User }`.

## v1 webhooks: endpoints

These require `Authorization` only, with no version header. v1 webhook ids are `WH…`.

**v1 webhook object** (returned by list, get and every create; all fields required):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | `^WH` | |
| `userId` | `^US` | The creator, which defaults to the workspace owner. |
| `orgId` | `^OR` | |
| `label` | string \| null | |
| `status` | `enabled` \| `disabled` | Default `enabled`. |
| `url` | uri | |
| `key` | string | The **signing key** (base64). In the app it is shown as "Reveal signing secret". The spec only describes it as "Webhook key". |
| `createdAt`, `updatedAt` | date-time | |
| `deletedAt` | date-time \| null | |
| `events` | string[] | The allowed values depend on the family (table below). |
| `resourceIds` | `PN…`[] or `["*"]` | Always `["*"]` for contact webhooks. |

**Events per family** (taken from the create bodies and the list/get `anyOf` variants):

| Family | Create endpoint | `events` enum |
| --- | --- | --- |
| Messages | `POST /v1/webhooks/messages` | `message.received`, `message.delivered` |
| Calls | `POST /v1/webhooks/calls` | `call.completed`, `call.ringing`, `call.recording.completed` |
| Call summaries | `POST /v1/webhooks/call-summaries` | `call.summary.completed` (`minItems: 1`) |
| Call transcripts | `POST /v1/webhooks/call-transcripts` | `call.transcript.completed` (`minItems: 1`) |
| Contacts | **no v1 create endpoint** (appears only in list/get responses, e.g. app-created) | `contact.updated`, `contact.deleted` |

v1 has **no** `message.failed`/`undelivered` events, no `call.answered`/`missed`/`forwarded`/`menu.selected`/`voicemail.completed`, and no task events. Those exist only on `2026-03-30`.

### `GET /v1/webhooks` — list

| Query | Type | Notes |
| --- | --- | --- |
| `userId` | `^US` | **Defaults to the workspace owner.** To see every webhook, call once per user. |

The response is `{ "data": V1Webhook[] }`, with no pagination. Branch on `events[]`, because the item schema is a union of the families.

### `GET /v1/webhooks/{id}` — get

The response is `{ "data": V1Webhook }`.

### `DELETE /v1/webhooks/{id}` → `204`

There is no body. This is also how you "update" a v1 webhook, because v1 has no PATCH: delete it and recreate it, which issues a **new `key`**.

### `POST /v1/webhooks/{messages|calls|call-summaries|call-transcripts}` — create → `201`

| Body field | Type | Required | Notes |
| --- | --- | --- | --- |
| `url` | uri | yes | |
| `events` | enum[] for that family | yes | |
| `resourceIds` | `PN…`[] or `["*"]` | no | |
| `label` | string | no | |
| `status` | `enabled` \| `disabled` | no | Default `enabled`. |
| `userId` | `^US` | no | Defaults to the workspace owner. |

```bash
curl -X POST https://api.quo.com/v1/webhooks/calls -H "Authorization: $QUO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/hook","events":["call.completed","call.recording.completed"],"resourceIds":["*"]}'
```

```json
{ "data": { "id": "WHabcd1234", "userId": "US123abc", "orgId": "OR1223abc", "label": null, "status": "enabled",
  "url": "https://example.com/hook", "key": "…base64…", "createdAt": "2022-01-01T00:00:00Z",
  "updatedAt": "2022-01-01T00:00:00Z", "deletedAt": null,
  "events": ["call.completed", "call.recording.completed"], "resourceIds": ["*"] } }
```

Gotchas:

- Summary and transcript webhooks fire only when the workspace plan and settings actually produce summaries or transcripts (these are AI features on Business/Scale-tier plans; see the calls reference).
- Webhooks created in the Quo app and webhooks created through the API are managed separately. The docs say app-created webhooks "are not compatible with those created via the API".
- Retry policy, ordering and delivery logs are **not documented** for v1. Assume at-least-once delivery, dedupe on the event `id`, and return `2xx` quickly.

## v1 webhooks: delivered payloads

> These shapes come from the v1 webhooks guide as captured in this skill's v1.0.0 (fetched 2026-06-15). That guide was not part of the 2026-10-08 fetch, so they were not re-verified.

```json
{ "id": "EVsampleEvent01", "object": "event", "apiVersion": "v4",
  "createdAt": "2022-01-23T16:55:52.557Z", "type": "message.received",
  "data": { "object": { "id": "AC…", "object": "message", "from": "+1555…", "to": ["+1555…"],
    "direction": "incoming", "text": "hi", "status": "received", "createdAt": "…",
    "userId": "US…", "phoneNumberId": "PN…", "contactIds": [] } } }
```

- **Message** (`message.received`/`delivered`): `data.object` = `id, object, from, to[], direction, text, status, createdAt, userId, phoneNumberId, contactIds[]`.
- **Call** (`call.ringing`/`completed`/`recording.completed`): `id, object, answeredAt, answeredBy, initiatedBy, direction, status, completedAt, createdAt, duration, forwardedFrom, forwardedTo, phoneNumberId, participants[], updatedAt, userId, contactIds[]`.
- **Summary**: the envelope `type` is **`"callSummary"`**, not the subscription name. `data.object` = `callId, object, status, summary[], nextSteps[], contactIds[]`.
- **Transcript**: the envelope `type` is **`"callTranscript"`**. `data.object` = `callId, object, createdAt, dialogue[{content, start, end, identifier, userId}], duration, status, contactIds[]`.
- `apiVersion` on the payload is `"v4"` even though management lives under `/v1`. Switch on both forms of `type`.

## v1 webhooks: signature (`openphone-signature`)

The v1 OpenAPI spec says nothing about signing. The scheme below comes from the Quo Resource Center (support.quo.com, "Webhooks"). The 2026-03-30 changelog confirms that the header is named `OpenPhone-Signature` and that it is **not interchangeable** with the `webhook-*` scheme.

```
openphone-signature: hmac;1;1639710054089;mw1K4fvh5m9XzsGon4C5N3KvL0bkmPZSAyb/9Vms2Qo=
                     ^scheme ^version ^timestamp ^base64 HMAC-SHA256 digest
```

1. Split the header on `;` into `[scheme="hmac", version="1", timestamp, digest]`.
2. Signed data = `timestamp + "." + payload`. The doc says the JSON payload must have **all whitespace and newlines removed**. Its Node sample uses `JSON.stringify(req.body)`, and its Python sample uses the raw `request.data` bytes. Prefer the raw bytes, and fall back to compact re-serialisation only if raw-byte verification fails.
3. Key = **base64-decode** the webhook's signing key (the `key` field or the app's "Reveal signing secret"). There is **no `whsec_` prefix**.
4. `base64(HMAC-SHA256(keyBytes, signedData))` must equal `digest`. Compare in constant time; the doc's sample uses `==`, which is not safe.
5. The sample timestamp has 13 digits, so it appears to be in **milliseconds**, unlike the `webhook-timestamp` seconds in the new scheme. The doc gives no tolerance. If you add a replay window, normalise the units first.

The bundled `verify-webhook.js` / `verify_webhook.py` implement **only** the `2026-03-30` `webhook-*` scheme. They cannot verify v1 deliveries.

## Migration diffs

| v1 | 2026-03-30 |
| --- | --- |
| `GET /v1/users?maxResults=&pageToken=` | `GET /users?limit=&after=` + `Quo-Api-Version` |
| `totalItems`, `nextPageToken` | `nextCursor` (no total) |
| four `POST /v1/webhooks/{family}` | one `POST /webhooks` with mixed `events[]` |
| webhook `id` `WH…`, has `userId`, `deletedAt` | numeric string id, no `userId`; `apiVersion` pinned |
| `key` = base64 signing key, `openphone-signature` | `key` = `whsec_…`, `webhook-id`/`-timestamp`/`-signature` |
| no update, rotate, delivery log or test | `PATCH`, `/rotate`, `/events`, `/events/test`, retry |
| `data.object.*` payload, `apiVersion: "v4"` | `data.resource` / `data.context` / `data.links`, `apiVersion: "2026-03-30"` |
| `data.object.contactIds` | `data.context.contacts.ids` + `lookupStatus` |
| `data.object.from` / `to` | `context.senderIdentifier` / `recipientIdentifiers` |

The `role` enum (`owner | admin | member`) and the user fields are unchanged.

## Sources (checked 2026-10-08)

- `openphone-public-api-v1-prod.json`: `/v1/users`, `/v1/users/{userId}`, `/v1/webhooks`, `/v1/webhooks/{id}`, `/v1/webhooks/{messages,calls,call-summaries,call-transcripts}`
- `openphone-public-api-2026-03-30-prod.json`: `/users`, `/users/{userId}`, `/users/{userId}/phone-numbers`, `/phone-numbers/{phoneNumberId}/users`, `/tasks/{taskId}/users`
- quo.com/docs/mdx/api-reference: users/list-users, users/get-a-user-by-id, webhooks/* (four create pages, list, get, delete), authentication, rate-limits, error-codes
- quo.com/docs/2026-03-30: users/*, user-phone-numbers/list-a-users-phone-numbers, versioning, errors
- quo.com/docs/changelog: 2026-05-11 entry (legacy `OpenPhone-Signature` versus the new scheme)
- support.quo.com/core-concepts/integrations/webhooks: `openphone-signature` format (web, outside the local fetch)
