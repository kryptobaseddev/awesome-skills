## Quo (formerly OpenPhone) REST API — Messages & Phone Numbers

> Source of truth: the per-endpoint doc "markdown twins" under `https://www.quo.com/docs/mdx/api-reference/...`, each of which embeds the verbatim OpenAPI fragment from `openphone-public-api-v1-prod.json` (`openapi: 3.1.0`, `info.version: 1.0.0`). All field names, types, enums, patterns, and required flags below are quoted directly from those sources.

### Authentication & Base URL (read first — there is a contradiction to resolve)

- **Auth scheme (verbatim from the spec's `components.securitySchemes`):**
  ```yaml
  securitySchemes:
    apiKey:
      in: header
      name: Authorization
      type: apiKey
  ```
  This is a **raw API key sent in the `Authorization` header — NOT a `Bearer` token.** `type: apiKey` (not `http`/`bearer`) means you send the key value directly: `Authorization: <YOUR_API_KEY>`. Do **not** prefix with `Bearer`.
- **Base URL — CONTRADICTION FLAGGED:** The OpenAPI spec's `servers` block is verbatim:
  ```yaml
  servers:
    - description: Production server
      url: https://api.quo.com
  ```
  The OpenAPI spec declares the base host as **`https://api.quo.com`** (with `/v1` baked into each path, e.g. `/v1/messages`). `https://api.openphone.com/v1` is a live legacy alias returning identical responses. Keep the host in one configurable constant; prefer `https://api.quo.com/v1` to match the current docs and OpenAPI `servers`. The `/v1/...` path suffix is identical on both hosts.

All endpoints in this domain require `security: - apiKey: []` (i.e., the `Authorization` API-key header).

---

### Send a text message

`POST https://api.quo.com/v1/messages`

Send a text message from your Quo number to a recipient. (`operationId: sendMessage_v1`)

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `content` | body | string | **yes** | The text content of the message. Constraints: `minLength: 1`, `maxLength: 1600`, `pattern: .*\S.*` (must contain a non-whitespace char). |
| `from` | body | string (`anyOf`) | **yes** | The sender's phone number. Either your Quo **phone number ID** (`pattern: ^PN(.*)$`) **or** the full number in **E.164** (`pattern: ^\+[1-9]\d{1,14}$`). |
| `to` | body | array | **yes** | Recipients. `minItems: 1`, **`maxItems: 1`** — exactly ONE recipient per call. Each item is `anyOf` an E.164 string (`^\+[1-9]\d{1,14}$`) or a string `maxLength: 15`. |
| `phoneNumberId` | body | string | no | **DEPRECATED — use `from` instead.** `pattern: ^PN(.*)$`. "Quo phone number ID to send a message from." |
| `userId` | body | string | no | `pattern: ^US(.*)$`. The Quo user sending the message. "If not provided, defaults to the phone number owner." |
| `setInboxStatus` | body | string (enum) | no | Only valid value: `"done"`. Default behavior (omit it) leaves the conversation OPEN in the user's inbox. Setting `"done"` moves the conversation to the Done inbox view. |

**Request body example:**
```json
{
  "content": "Hello, world!",
  "from": "+15555555555",
  "to": ["+15555555555"],
  "userId": "US123abc",
  "setInboxStatus": "done"
}
```

**Response — `202` Success** (note: **202 Accepted**, not 200):
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
Response `data` required fields: `id, to, from, text, phoneNumberId, direction, userId, status, createdAt, updatedAt`. `direction` enum: `incoming | outgoing`. `status` enum: `queued | sent | delivered | undelivered | received`. `id` matches `^AC(.*)$`. `phoneNumberId` is `anyOf` a `^PN(.*)$` string or `null`.

**curl:**
```bash
curl -X POST "https://api.quo.com/v1/messages" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, world!",
    "from": "+15555555555",
    "to": ["+15555555555"]
  }'
```

**Gotchas:**
- `Authorization` header is the **raw key** — no `Bearer ` prefix (`type: apiKey`).
- `to` is an **array** but capped at **one** recipient (`maxItems: 1`). Sending to multiple numbers in one call is not supported here.
- Success status is **`202`**, not `200`. The returned `status` is the initial state (`queued`/`sent`); delivery is async — poll Get-a-message or use webhooks for `delivered`/`undelivered`.
- `from` accepts **either** a `PN...` phone-number ID **or** an E.164 number; `phoneNumberId` still works but is **deprecated**.
- `content` must contain at least one non-whitespace character and be ≤ 1600 chars.
- **`400 A2P Registration Not Approved`** (`code: "0206400"`) is returned when US A2P 10DLC registration isn't approved — a hard gate for sending to US numbers, independent of auth.
- Other documented errors: `401 Unauthorized` (`0200401`), `402 Subscription Expired` (`0201402`), `403 Not Phone Number User` (`0202403` — the API key's user isn't a member of that phone number), `404 Not Found` (`0200404`), `500 Unknown` (`0201500`).

---

### List messages

`GET https://api.quo.com/v1/messages`

Retrieve a chronological list of messages exchanged between your Quo number and specified participants, with filtering and pagination. (`operationId: listMessages_v1`)

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `phoneNumberId` | query | string | **yes** | The Quo number used to send/receive. `pattern: ^PN(.*)$` (example shown as `OP123abc` in docs, but the pattern is `PN`). Retrieve it via List Phone Numbers. |
| `participants` | query | array of string | **yes** | Phone numbers in the conversation, **excluding your Quo number**, in E.164 (`^\+[1-9]\d{1,14}$`). |
| `maxResults` | query | integer | **yes** | Page size. `default: 10`, `minimum: 1`, `maximum: 100`. |
| `userId` | query | string | no | The user the message was sent from. `pattern: ^US(.*)$`. |
| `createdAfter` | query | string (date-time) | no | ISO 8601. Only messages created after this time. |
| `createdBefore` | query | string (date-time) | no | ISO 8601. Only messages created before this time. |
| `since` | query | string (date-time) | no | **DEPRECATED** — use `createdAfter`/`createdBefore`. Currently behaves as `createdBefore`; will be removed. |
| `pageToken` | query | string | no | Cursor from a previous response's `nextPageToken`. |

**Request example (curl):**
```bash
curl -X GET "https://api.quo.com/v1/messages?phoneNumberId=PN123abc&participants=%2B15555555555&maxResults=10" \
  -H "Authorization: YOUR_API_KEY"
```

**Response — `200` Success:**
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
      "status": "sent",
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```
Top-level required fields: `data`, `totalItems`, `nextPageToken`. Each `data` item has required fields `id, to, from, text, phoneNumberId, direction, userId, status, createdAt, updatedAt` (same shapes/enums as Send). `nextPageToken` is `anyOf` string or `null`.

**Gotchas:**
- **Both `phoneNumberId` AND `participants` are REQUIRED**, plus `maxResults`. You cannot list "all messages" globally — you must scope to one Quo number and a specific conversation's participant(s).
- `participants` must be E.164 and must **exclude** your own Quo number.
- `maxResults` caps at **100** per page.
- **`totalItems` is documented as unreliable:** the spec literally warns "⚠️ Note: `totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue." Drive pagination off `nextPageToken` (loop until it is `null`), never off `totalItems`.
- `since` is deprecated; prefer `createdAfter`/`createdBefore`.

---

### Get a message by ID

`GET https://api.quo.com/v1/messages/{id}`

Get a message by its unique identifier. (`operationId: getMessageById_v1`)

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | The message ID. `pattern: ^AC(.*)$` (e.g. `AC123abc`). |

**Request (curl):**
```bash
curl -X GET "https://api.quo.com/v1/messages/AC123abc" \
  -H "Authorization: YOUR_API_KEY"
```

**Response — `200` Success:**
```json
{
  "data": {
    "id": "AC123abc",
    "to": ["+15555555555"],
    "from": "+15555555555",
    "text": "Hello, world!",
    "phoneNumberId": "PN123abc",
    "direction": "incoming",
    "userId": "US123abc",
    "status": "sent",
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z"
  }
}
```
`data` required fields: `id, to, from, text, phoneNumberId, direction, userId, status, createdAt, updatedAt`. `direction`: `incoming | outgoing`. `status`: `queued | sent | delivered | undelivered | received`. `userId` is "Null for incoming messages."

**Gotchas:**
- Message IDs start with `AC` (`^AC(.*)$`), NOT `PN`/`US`. Don't confuse with phone-number or user IDs.
- Use this (or webhooks) to poll for final delivery `status` after a `202` send.
- Same error gates as send: `400 A2P Registration Not Approved` (`0206400`), `401`, `402 Subscription Expired`, `403 Not Phone Number User`, `404`, `500`.

---

### List phone numbers

`GET https://api.quo.com/v1/phone-numbers`

Retrieve the list of phone numbers and users associated with your Quo workspace. (`operationId: listPhoneNumbers_v1`)

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `userId` | query | string | no | Filter to numbers associated with this user. `pattern: ^US(.*)$`. |

**Request (curl):**
```bash
curl -X GET "https://api.quo.com/v1/phone-numbers" \
  -H "Authorization: YOUR_API_KEY"
```

**Response — `200` Success** (`ListPhoneNumbersResponse`, top-level required: `data`):
```json
{
  "data": [
    {
      "id": "PN123bc",
      "groupId": "1234",
      "portRequestId": null,
      "formattedNumber": "+15555555555",
      "forward": null,
      "name": "My phone number",
      "number": "+15555555555",
      "portingStatus": null,
      "symbol": "🏡",
      "users": [
        {
          "email": "johndoe@example.com",
          "firstName": "John",
          "lastName": "Doe",
          "id": "US123abc",
          "role": "owner",
          "groupId": "GRcei8k90o"
        }
      ],
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z",
      "restrictions": {
        "calling":   { "CA": "unrestricted", "Intl": "unrestricted", "US": "unrestricted" },
        "messaging": { "CA": "unrestricted", "Intl": "unrestricted", "US": "unrestricted" }
      }
    }
  ]
}
```
Each phone-number object required fields: `id, groupId, portRequestId, formattedNumber, forward, name, number, portingStatus, symbol, users, createdAt, updatedAt, restrictions`.
- `id` (`^PN(.*)$`) — **this is the value you pass as `from` (or the deprecated `phoneNumberId`) when sending, and as `phoneNumberId` when listing messages.**
- `number` / `formattedNumber` — the E.164 number itself (you may also use `number` directly as `from`).
- `users[]` — `allOf` merge of: `{email, firstName, lastName, id (^US...), role}` and `{groupId (^GR...)}`. `role` enum: `owner | admin | member`. `firstName`/`lastName` may be `null`.
- `restrictions.calling` and `restrictions.messaging` each have required keys `CA`, `Intl`, `US`, each enum `restricted | unrestricted`.
- Nullable: `portRequestId`, `formattedNumber`, `forward`, `portingStatus`, `symbol`.

**Gotchas:**
- This is the canonical way to discover the `id` (`PN...`) used as the message sender and the `phoneNumberId` filter for List Messages — call it first during setup.
- Check `restrictions.messaging.US == "unrestricted"` (and `restrictions.calling`) before relying on a number; a `restricted` value means sends/calls to that region will be blocked even though the number exists.
- `users[]` tells you which Quo users (`US...`) and roles can act on a number — relevant to the `403 Not Phone Number User` send error and to choosing a valid `userId`.
- Errors here use a different code family: `400 Bad Request` (`0400400`), `401` (`0400401`), `403 Forbidden` (`0400403`), `404` (`0400404`), `500` (`0401500`).

---

### Get a phone number by ID

`GET https://api.quo.com/v1/phone-numbers/{phoneNumberId}`

Get a phone number by its unique identifier. (`operationId: getPhoneNumberById_v1`)

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `phoneNumberId` | path | string | **yes** | `pattern: ^PN(.*)$` (e.g. `PNlja6rrtI`). |

**Request (curl):**
```bash
curl -X GET "https://api.quo.com/v1/phone-numbers/PNlja6rrtI" \
  -H "Authorization: YOUR_API_KEY"
```

**Response — `200` Success** (single object under `data`, required: `data`):
```json
{
  "data": {
    "id": "PN123bc",
    "groupId": "1234",
    "portRequestId": null,
    "formattedNumber": "+15555555555",
    "forward": null,
    "name": "My phone number",
    "number": "+15555555555",
    "portingStatus": null,
    "symbol": "🏡",
    "users": [
      {
        "email": "johndoe@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "id": "US123abc",
        "role": "owner",
        "groupId": "GRcei8k90o"
      }
    ],
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "restrictions": {
      "calling":   { "CA": "unrestricted", "Intl": "unrestricted", "US": "unrestricted" },
      "messaging": { "CA": "unrestricted", "Intl": "unrestricted", "US": "unrestricted" }
    }
  }
}
```
Identical object shape to the items in List Phone Numbers (same required fields, same `users`/`restrictions`/nullable rules).

**Gotchas:**
- Path param `pattern: ^PN(.*)$` — passing an E.164 number or `US...` id will not resolve.
- Same per-number `restrictions` and `users` semantics as the list endpoint; this is the targeted lookup when you already hold a `PN` id.
- Errors: `400` (`0400400`), `401` (`0400401`), `403 Forbidden` (`0400403`), `404 Not Found` (`0400404`), `500` (`0401500`).

---

### Cross-endpoint ID & enum cheat-sheet (verbatim patterns)

| Entity | ID pattern | Where it appears |
|--------|-----------|------------------|
| Message | `^AC(.*)$` | `messages.data[].id`, path `{id}` for Get message |
| Phone number | `^PN(.*)$` | `phone-numbers.data[].id`; message `from`/`phoneNumberId`; List Messages `phoneNumberId` query |
| User | `^US(.*)$` | `users[].id`, message `userId`, query `userId` |
| Group | `^GR(.*)$` | `users[].groupId` |
| E.164 phone | `^\+[1-9]\d{1,14}$` | `to`, `from`, `number`, `participants` |

- `direction` enum: `incoming | outgoing`
- message `status` enum: `queued | sent | delivered | undelivered | received`
- user `role` enum: `owner | admin | member`
- `restrictions.*.{CA,Intl,US}` enum: `restricted | unrestricted`
- `setInboxStatus` enum: `done` (only value)
