## Quo (formerly OpenPhone) Public API — Foundation Reference

> Sourced verbatim from the live Quo docs (`https://www.quo.com/docs/mdx/api-reference/*.md`) and the OpenPhone/Quo OpenAPI 3.1.0 specs. Quo is the rebrand of OpenPhone; the two share one API. The docs and OpenAPI spec now use the `api.quo.com` host, but `api.openphone.com` remains a live alias for the same service.

### Base URL & Host

```
https://api.quo.com/v1     (alias — still live)
https://api.quo.com/v1           (canonical host in current docs + OpenAPI `servers`)
```

- The OpenAPI `servers` block declares exactly one server: `{"url": "https://api.quo.com", "description": "Production server"}`. All paths are prefixed with `/v1` (e.g. `/v1/messages`).
- The current quickstart curl example uses `https://api.quo.com/v1/...`.
- Verified live (2026-06-15): an unauthenticated `GET` to both `https://api.quo.com/v1/phone-numbers` and `https://api.quo.com/v1/phone-numbers` returns the same `401` with body `{"error":{"message":"Unauthorized","key":"Unauthorized","trace":"..."}}`. **Both hosts are interchangeable.** Pick one host and use it consistently.
- API design: REST, JSON request/response bodies, API-key auth. (Source: introduction.md)

**Gotchas**
- `https://api.quo.com/v1` is the canonical host (the OpenAPI `servers` block declares `https://api.quo.com`); `https://api.openphone.com/v1` is a live legacy alias that returns identical responses (verified). Keep the host in one configurable constant; prefer `api.quo.com` to match current docs.

---

### Authentication

```
Header on every request:  Authorization: YOUR_API_KEY
```

| name | in | type | required | notes |
| --- | --- | --- | --- | --- |
| `Authorization` | header | string (raw API key) | yes | The **raw API key**, verbatim. NOT a Bearer token. |

Verbatim from authentication.md: *"Include your API key in the Authorization header of each request: `Authorization: YOUR_API_KEY`. The Quo API does not use a Bearer token for authentication."*

OpenAPI `securitySchemes` confirms: `{"apiKey": {"type": "apiKey", "in": "header", "name": "Authorization"}}`, applied globally via `security: [{"apiKey": []}]`.

**API key generation (verbatim steps):**
1. Access your Quo account.
2. Navigate to the **"API"** tab under workspace settings. You need **workspace owner or admin** privileges to access this tab.
3. Click **"Generate API key"** and provide a descriptive label. Each key provides **full API access** (same privileges as your Quo account).
4. Name the key based on intended use (e.g. `production-environment`). **Spaces are not allowed in the API key name.**

**Prerequisites:** a Quo/OpenPhone account, owner or admin privileges, and — to send SMS to US numbers — completed **US Carrier Registration (A2P)**.

**Revoking a key:** API tab → locate key → ellipsis (⋯) → **Delete** (immediate revoke). Deleting one key only affects integrations using that key; others keep working.

**Request example (raw key, NOT Bearer):**
```bash
curl --request GET \
  --url https://api.quo.com/v1/phone-numbers \
  --header 'Authorization: YOUR_API_KEY'
```

**Gotchas**
- Do NOT prefix with `Bearer ` — the header value is the raw key. A `Bearer <key>` value will fail auth.
- A key carries full account privileges; treat it like a password. Rotate regularly; never commit to git or client-side code.
- Generating a key requires workspace **owner/admin**. No self-serve key without admin rights.

---

### API Versioning

- The core REST API is unversioned beyond the `/v1` path segment. There is **no `OpenPhone-API-Version` header** and no dated version header on core REST endpoints (confirmed: no such header appears anywhere in the v1 OpenAPI spec; `info.version` is `1.0.0`).
- Two OpenAPI documents are published and are byte-for-byte equivalent in `info` (`title: "Quo Public API"`, `version: "1.0.0"`, server `https://api.quo.com`):
  - `openphone-public-api-v1-prod.json` — the full v1 surface (Calls, Call Summaries, Call Transcripts, Contacts, Conversations, Messages, Phone Numbers, Users, Webhooks, Tasks).
  - `openphone-public-api-2026-03-30-prod.json` — a dated snapshot containing only `/conversations/{conversationId}/mark-as-read`, `/messages/{messageId}/retry`, `/users`, `/users/{userId}` (note: paths here are NOT `/v1`-prefixed in this dated file).
- The ONLY versioning header in Quo is `x-quo-api-version`, and it applies **only to the beta Webhook API payload versioning** (each webhook subscription pins a payload version at creation). It does NOT apply to core REST endpoints. (Source: changelog.md)

**Gotchas**
- Do not send `OpenPhone-API-Version` / `Quo-API-Version` on core REST calls — it is not a recognized header.
- `x-quo-api-version` is webhook-payload-only; don't confuse it with REST API versioning.

---

### Rate Limits

```
Limit: 10 requests per second, per API key.
```

- Verbatim from rate-limits.md: *"Each API key may make up to **10 requests per second.** Exceeding this limit may result in `429` status code errors."*
- On `429`, the docs advise **exponential backoff** / request throttling (error-codes.md: *"For 429 errors, implement exponential backoff in your requests."*).

| name | in | type | required | notes |
| --- | --- | --- | --- | --- |
| `429 Too Many Requests` | response status | — | — | Rate limit exceeded. Back off and retry. |

**Gotchas**
- The published docs do **not** document any `RateLimit-*` / `Retry-After` response headers. Do not rely on `Retry-After`; implement client-side exponential backoff with jitter and cap concurrency to stay under 10 req/s per key.
- The limit is per API key, not per workspace — multiple keys get independent buckets.

---

### Global Error / Response Codes

Quo uses standard HTTP response codes. `2xx` success, `4xx` client error, `5xx` server error. Some `4xx` errors include a machine-readable `code`.

| Code | Status | Meaning | Retry guidance |
| --- | --- | --- | --- |
| `200` | OK | Request successful | — |
| `201` | Created | Resource successfully created | — |
| `202` | Accepted | Request accepted for processing (returned by send-message) | — |
| `204` | No Content | Successful, no body | — |
| `400` | Bad Request | Invalid parameters / semantic body error (e.g. A2P not approved, invalid custom field, whitespace-only message, bad E.164) | Do not retry blindly — fix the request |
| `401` | Unauthorized | Missing or invalid API key | Fix auth; do not retry |
| `402` | Payment Required | Subscription Expired (`code 0201402`) | Resolve billing; do not retry |
| `403` | Forbidden | Insufficient permissions or an account setting not enabled (e.g. "Not Phone Number User", international messaging disabled) | Fix config/permissions; do not retry |
| `404` | Not Found | Resource doesn't exist | Do not retry |
| `409` | Conflict | Conflict with another request | Resolve conflict, then retry |
| `422` | Unprocessable Entity | Well-formed but semantically invalid | Fix the request |
| `429` | Too Many Requests | Rate limit exceeded | Exponential backoff, then retry |
| `500` | Server Error | Quo-side issue (`code 0201500`) | Retry with backoff |

**Error response envelope (from OpenAPI — structured form):**
```json
{
  "message": "Unauthorized",
  "code": "0200401",
  "status": 401,
  "docs": "https://quo.com/docs",
  "title": "Unauthorized",
  "trace": "1234567890",
  "errors": [
    {
      "path": "to",
      "message": "Invalid phone number",
      "value": "555",
      "schema": { "type": "string" }
    }
  ]
}
```

**Error response envelope (observed LIVE on 2026-06-15 — simpler form):**
```json
{
  "error": {
    "message": "Unauthorized",
    "key": "Unauthorized",
    "trace": "4128582783457776981"
  }
}
```

Documented `code` constants observed in the OpenAPI spec for the send-message path: `0206400` (A2P Registration Not Approved), `0200401` (Unauthorized), `0201402` (Subscription Expired), `0202403` (Not Phone Number User), `0200404` (Not Found), `0201500` (Unknown Error).

**Gotchas**
- The error body shape is **not stable between the spec and the live API**. The OpenAPI spec documents a flat `{message, code, status, docs, title, trace, errors[]}` object; the live API (observed) wraps it as `{"error": {"message", "key", "trace"}}`. **Parse defensively** — check `body.error?.message ?? body.message` and don't hard-depend on `code`.
- A `403` can mean "account setting not enabled" (e.g. international messaging off) rather than a permissions problem — read the message.
- Sending an SMS without approved US A2P registration returns `400` (`code 0206400`), not `403`.

---

### Pagination Model (list endpoints)

List endpoints use **cursor/token pagination** via `maxResults` + `pageToken`, and return `nextPageToken` in the response.

| name | in | type | required | notes |
| --- | --- | --- | --- | --- |
| `maxResults` | query | integer | yes (default `10`) | Page size. `minimum: 1`, `maximum: 100`. |
| `pageToken` | query | string | no | Opaque cursor for the next page. Omit/empty for the first page; pass the previous response's `nextPageToken`. |

**Response envelope:**
```json
{
  "data": [ /* array of resource objects */ ],
  "totalItems": 42,
  "nextPageToken": "eyJ...="
}
```
- `nextPageToken` is `string | null`. When it is `null`, you have reached the last page (stop paginating).
- `totalItems` is **known-broken**: the spec itself warns *"`totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue."* (changelog.md also documents this.)

**Gotchas**
- Do NOT trust `totalItems` for loop control or progress bars — it is documented as inaccurate. Loop until `nextPageToken === null` instead.
- A historical bug returned a stringified token at the end of results; this was fixed so the terminal token is correctly `null`. Code defensively for `null`.
- `maxResults` is required and capped at 100 — requesting more is rejected.
- Cursor pagination has no `offset`/`page` number params — only `pageToken`.

---

### POST /v1/messages — Send a text message

```
POST https://api.quo.com/v1/messages
```

Sends a text message from your Quo number to a recipient. Returns **`202 Accepted`** on success.

| name | in | type | required | notes |
| --- | --- | --- | --- | --- |
| `content` | body | string | yes | Message text. `minLength: 1`, `maxLength: 1600`, must contain a non-whitespace char (`pattern: .*\S.*`). |
| `from` | body | string | yes | Sender. Either a Quo phone-number ID (`^PN...`) OR a full E.164 number (`^\+[1-9]\d{1,14}$`). |
| `to` | body | string[] | yes | Recipients array. `minItems: 1`, `maxItems: 1` (exactly one recipient). E.164 strings. |
| `userId` | body | string (`^US...`) | no | Quo user sending the message. Defaults to the phone number owner if omitted. |
| `setInboxStatus` | body | string enum | no | Only value: `"done"` — moves the conversation to the Done inbox view. Default leaves it open. |
| `phoneNumberId` | body | string (`^PN...`) | no | **DEPRECATED** — use `from` instead. |

**Request body example:**
```json
{
  "content": "Hello, world!",
  "from": "+15555555555",
  "to": ["+15555555555"],
  "userId": "US123abc"
}
```

**Response example (`202 Accepted`):**
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

- `direction` enum: `incoming` | `outgoing`.
- `status` enum: `queued` | `sent` | `delivered` | `undelivered` | `received`.

**curl:**
```bash
curl --request POST \
  --url https://api.quo.com/v1/messages \
  --header 'Authorization: YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{
    "content": "Hello, world!",
    "from": "+15555555555",
    "to": ["+15555555555"],
    "userId": ""
  }'
```

**Gotchas**
- `to` accepts exactly ONE recipient (`maxItems: 1`). It is an array, but you cannot fan out to multiple numbers in one call.
- All phone numbers MUST be E.164 (`+15555555555`). E.164 validation is now enforced (a changelog patch fixed loose validation).
- A whitespace-only `content` (`" "`, `"\n"`) now returns `400` with a validation error (previously `500`).
- Sending to a US number requires approved A2P registration, else `400` (`code 0206400`, "A2P Registration Not Approved").
- Sending to an international number with international messaging disabled returns `403` (changelog: changed from `500`→`403`).
- Use `from`, not the deprecated `phoneNumberId`, to specify the sender.
- Success status is `202`, not `200` — assert on `202`.

---

### GET /v1/phone-numbers — List phone numbers

```
GET https://api.quo.com/v1/phone-numbers
```

Retrieves the phone numbers and users in your workspace. Used in step 1 of the quickstart to discover `userId` and the sending number's `id`/`number`.

| name | in | type | required | notes |
| --- | --- | --- | --- | --- |
| `userId` | query | string (`^US...`) | no | Filter to phone numbers associated with this user. |

**Response example (`200 OK`):**
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

- `users[].role` enum: `owner` | `admin` | `member`.
- `restrictions.{calling,messaging}.{CA,Intl,US}` enum: `restricted` | `unrestricted`.

**curl:**
```bash
curl --request GET \
  --url https://api.quo.com/v1/phone-numbers \
  --header 'Authorization: YOUR_API_KEY'
```

**Gotchas**
- This list response is NOT paginated — it returns only `{ "data": [...] }` (no `nextPageToken`/`totalItems`). Unlike `GET /v1/messages`, there's no `maxResults`/`pageToken`.
- The phone number's own ID field is `id` (`PN...`); use it as `from` when sending. The human number string is `number`/`formattedNumber`.
- Check `restrictions` before sending — a `restricted` region for `messaging.US` means outbound US SMS will fail.
- `restrictions` was added in API minor version 1.1.0; older integrations may not expect it.

---

### Send Your First Message — Quickstart (verbatim)

1. **Get phone numbers (optional).** `GET /v1/phone-numbers` to retrieve the `userId` and the sending number (`from`). Skip if you already know them.
2. **Specify user ID (optional).** Include `userId` in the request body to send as a specific workspace member; otherwise the sender defaults to the phone number owner.
3. **Send your message.** `POST /v1/messages` with `content`, `from`, `to` (and optional `userId`). On success you receive a **`202`**. Phone numbers must be E.164 (`+1234567890`).

```bash
curl --request POST \
  --url https://api.quo.com/v1/messages \
  --header 'Authorization: YOUR_API_KEY' \
  --header 'Content-Type: application/json' \
  --data '{ "content": "", "from": "", "to": [ "+15555555555" ], "userId": "" }'
```

**Gotchas**
- If sending to US numbers, US Carrier Registration (A2P) must be completed first.
- The quickstart works for US and Canada out of the box; international requires it enabled on the workspace.

---

### Partner Directory / Getting Help

- Partner directory: browse Quo Experts at `https://www.openphone.com/experts`; project matchmaking at `https://www.openphone.com/experts/matchmaking`.
- API keys are NOT obtained through the partner directory — they are self-generated in Workspace Settings → API tab (owner/admin only). The partner directory is for implementation help, not key provisioning or plan gating.

**Gotchas**
- No "apply for API access" gate — any workspace with an owner/admin can generate keys immediately. The only true gate for SMS to US numbers is A2P Carrier Registration.

---

### Changelog highlights (foundation-relevant)

- **1.0.0 (Public API v1 launch):** `since` query param deprecated (use `createdAfter`/`createdBefore`); `phoneNumberId` body field deprecated for send-message (use `from`); `/v0` deprecated (use `/v1`).
- **1.1.0:** added `restrictions` to `GET /phone-numbers` items; international-send error changed `500`→`403`; assorted `500`→`400`/`404` fixes (whitespace-only message, contact-not-found).
- Pagination fix: terminal `nextPageToken` now correctly `null`; `totalItems` flagged as inaccurate.
- Beta Webhook API (separate domain): unified `POST /webhooks`, Standard-Webhooks signing (`webhook-id`/`webhook-timestamp`/`webhook-signature`, `whsec_...` secret) — NOT interchangeable with the legacy `OpenPhone-Signature` header. Payload version pinned via `x-quo-api-version`.