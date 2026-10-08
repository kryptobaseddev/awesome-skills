# Quo (formerly OpenPhone) API: Messages, Phone Numbers & Organization

Quo serves two live REST surfaces from one host, `https://api.quo.com`, and this resource straddles both of them:

- **v1**: paths start with `/v1/...` and take no version header. It is still the **only way to send a message** (`POST /v1/messages`).
- **2026-03-30**: unprefixed paths (`/messages`, `/phone-numbers`, `/organization`). The header `Quo-Api-Version: 2026-03-30` is **required**; without it you get a 400. List responses come back as `{ data, nextCursor }` with cursor pagination (`limit` 1-50, default 10, plus `after`). Errors use the structured envelope `{ title, message, docs, trace, errors[{path,message,value,schema}] }`. New features ship only here.

Both surfaces use the same auth: send the raw API key in the `Authorization` header, with **no `Bearer` prefix**. The rate limit is 10 requests per second per key. `https://api.openphone.com` is a legacy alias for v1; keep the host in one config constant.

## Contents

1. [Which surface to use](#which-surface-to-use)
2. [ID prefixes and shared enums](#id-prefixes-and-shared-enums)
3. [Send a message (v1 only)](#send-a-message--post-v1messages-v1-only)
4. [Idempotency and safe retries](#idempotency-and-safe-retries)
5. [List messages (2026-03-30)](#list-messages--get-messages-2026-03-30)
6. [Get a message (2026-03-30)](#get-a-message--get-messagesmessageid-2026-03-30)
7. [Retry a failed message (2026-03-30)](#retry-a-failed-message--post-messagesmessageidretry-2026-03-30)
8. [v1 list and get messages](#v1-list-and-get-messages)
9. [Phone numbers (2026-03-30)](#phone-numbers-2026-03-30)
10. [Phone numbers (v1)](#phone-numbers-v1)
11. [Get the organization (2026-03-30)](#get-the-organization--get-organization-2026-03-30)
12. [Send your first message: the walkthrough](#send-your-first-message-the-walkthrough)
13. [Segments, cost and registration](#segments-cost-and-registration)
14. [v1 to 2026-03-30 migration diffs](#v1-to-2026-03-30-migration-diffs)
15. [Sources](#sources-checked-2026-10-08)

---

## Which surface to use

| Need | Use | Why |
|---|---|---|
| Send an SMS/MMS, 1:1 or group (up to 10) | **v1** `POST /v1/messages` | Only v1 has a send endpoint. 2026-03-30 has no `POST /messages`. |
| Read message history across the whole workspace | **2026-03-30** `GET /messages` | No required scoping; filter by from/to/status/direction/number/user/time. |
| Read one conversation's thread | 2026-03-30 `GET /messages?phoneNumberId=…&to=…` (or v1 `GET /v1/messages`) | v1 *requires* `phoneNumberId` + `participants` + `maxResults`. |
| Find failed or undelivered sends | **2026-03-30** `GET /messages?status=failed` | v1's status enum has no `failed`; it has no status filter at all. |
| Retry a failed send | **2026-03-30** `POST /messages/{messageId}/retry` | 2026-03-30 only. |
| Get one message (with `media`) | 2026-03-30 `GET /messages/{messageId}` | v1 `GET /v1/messages/{id}` also works. |
| List workspace numbers | **2026-03-30** `GET /phone-numbers` | Paginated, filter by E.164; `include=restrictions`. |
| Who is assigned to a number | **2026-03-30** `GET /phone-numbers/{id}/users` | v1 embeds `users[]` in every number instead. |
| A user's numbers | 2026-03-30 `GET /users/{userId}/phone-numbers` (or v1 `GET /v1/phone-numbers?userId=`) | |
| Business hours of a number | **2026-03-30** `GET /phone-numbers/{id}?include=businessHours` | 2026-03-30 only, and only on the get-by-id endpoint. |
| Search purchasable numbers | **2026-03-30** `GET /phone-numbers/available` | 2026-03-30 only. Search only; it does not buy or provision. |
| Workspace name and subscription status | **2026-03-30** `GET /organization` | 2026-03-30 only; v1 has no `/v1/organization`. |

**Default:** read with 2026-03-30 and send with v1. A typical integration therefore uses both: it sends with `POST /v1/messages`, then uses `GET /messages/{id}` (or webhooks) to track the status of the returned `AC…` id.

---

## ID prefixes and shared enums

| Entity | Pattern | Seen in |
|---|---|---|
| Message | `^AC(.*)$` | message `id`, path `{id}` / `{messageId}` |
| Phone number | `^PN(.*)$` | number `id`, message `phoneNumberId`, send `from` |
| User | `^US(.*)$` | `userId`, `users[].id` |
| System actor (e.g. Sona AI) | `^SYU(.*)$` | 2026-03-30 message `userId` only |
| Conversation | `^CN(.*)$` | message `conversationId` |
| Group | `^GR(.*)$` | number `groupId` (2026-03-30), `users[].groupId` |
| Organization | `^OR(.*)$` | `GET /organization` `id` |
| E.164 number | `^\+[1-9]\d{1,14}$` | `to`, `from`, `phoneNumber`/`number` |
| Short code | `^[0-9]{3,8}$` | 2026-03-30 message `from`/`to` |
| Caller-ID token | `Anonymous`, `Restricted`, `Blocked` (case-insensitive) | 2026-03-30 message `from`/`to` |

- Message `direction`: `incoming | outgoing`.
- Message `status`: **v1** has `queued | sent | delivered | undelivered | received`. **2026-03-30** has the same values **plus `failed`**.
- User `role`: `owner | admin | member`.
- `restrictions.{calling,messaging}.{CA,Intl,US}`: `restricted | unrestricted`.

---

## Send a message: `POST /v1/messages` (v1 only)

`operationId: sendMessage_v1`. Headers: `Authorization: YOUR_API_KEY`, `Content-Type: application/json`. Do not send `Quo-Api-Version`.

| Field | Type | Req | Constraints / notes |
|---|---|---|---|
| `content` | string | **yes** | `minLength 1`, `maxLength 1600`, `pattern .*\S.*`. The text must contain at least one non-whitespace character; whitespace-only content gets a 400. |
| `from` | string | **yes** | `anyOf`: a Quo phone-number ID (`^PN(.*)$`) **or** the number in E.164 (`^\+[1-9]\d{1,14}$`). |
| `to` | string[] | **yes** | `minItems 1`, **`maxItems 10`**. Each item is E.164, or any string of at most 15 characters. **More than one recipient sends ONE group message**, not separate 1:1 texts. |
| `userId` | string | no | `^US(.*)$`. Attributes the message to this user. It defaults to the **owner of the sending number**. The user **must be a member** of the sending number. |
| `setInboxStatus` | string | no | enum `["done"]` only. If you omit it, the conversation shows as **open** in the inbox. `"done"` moves it to Done. |
| `phoneNumberId` | string | no | **Deprecated**: use `from`. `^PN(.*)$`. |

The spec defines no media or attachment field on send. The body accepts text only; `media[]` appears only in responses.

```bash
curl -X POST https://api.quo.com/v1/messages \
  -H "Authorization: $QUO_API_KEY" -H "Content-Type: application/json" \
  -d '{"content":"Your order shipped.","from":"PN123abc","to":["+15555550123"],"setInboxStatus":"done"}'
```

**Response: `202 Accepted`**, not 200. The send is accepted, not yet delivered:

```json
{
  "data": {
    "id": "AC123abc",
    "to": ["+15555550123"],
    "from": "+15555555555",
    "text": "Your order shipped.",
    "phoneNumberId": "PN123abc",
    "conversationId": "CN123abc",
    "direction": "outgoing",
    "userId": "US123abc",
    "status": "queued",
    "createdAt": "2026-10-08T15:00:00Z",
    "updatedAt": "2026-10-08T15:00:00Z",
    "media": []
  }
}
```

Required in `data`: `id, to, from, text, phoneNumberId (PN… | null), conversationId (CN…), direction, userId (US… | null), status, createdAt, updatedAt`. `media[]` (`{url, type: string|null}`) is optional on v1. Note that the request field is `content` but the response field is `text`.

**Errors (v1 envelope `{message, code, status, docs, title, trace?, errors?}`):**

| HTTP | `code` | `title` | Meaning / action |
|---|---|---|---|
| 400 | `0206400` | A2P Registration Not Approved | US A2P 10DLC registration is not approved. Do not retry; finish registration first. |
| 401 | `0200401` | Unauthorized | Bad key, or the key was sent with `Bearer`. |
| 402 | `0201402` | Subscription Expired | Billing lapsed. Check `GET /organization` → `subscriptionStatus`. |
| 403 | `0204403` | A2P 10DLC Daily Message Cap Reached | The carrier's daily cap was hit. Back off until tomorrow; do not tight-loop. |
| 404 | `0200404` | Not Found | Unknown `from` number or user. |
| 500 | `0201500` | Unknown | Server error. **This outcome is ambiguous**: see [safe retries](#idempotency-and-safe-retries). |

A 403 can also come back when you send to an international number and international messaging is not enabled in the workspace. Check `restrictions.messaging.Intl` before sending.

**Gotchas**

- The returned `status` is the initial state, usually `queued` or `sent`. Final delivery is asynchronous. Track it with webhooks (`message.delivered`, `message.failed`, `message.undelivered` on 2026-03-30 webhooks) or by polling `GET /messages/{id}`.
- A group send (`to.length > 1`) produces a single group conversation. To reach N people separately, call the endpoint N times with one recipient each. Stay under 10 req/s.
- Every recipient must be in E.164 with the leading `+`. A number without a country code (for example `5555550123`) fits the second schema branch (a string of at most 15 characters) and is not rejected locally, so normalize numbers yourself.
- The sending user (`userId`, or the number's owner) must be assigned to the `from` number. List the assignees with `GET /phone-numbers/{id}/users`.

---

## Idempotency and safe retries

**`POST /v1/messages` has no idempotency key.** The spec defines no `Idempotency-Key` header and no client-reference body field; the only "idempotency" in the docs is webhook-delivery deduplication. Re-sending after a timeout, a dropped connection or a 5xx can therefore **double-text the customer**.

Use this pattern for safe retries:

1. Before sending, record `sentAt = now()` (minus a few seconds for clock skew) and your intended `(from, to[], content)`.
2. **Retry automatically only when the request provably never reached Quo:** a DNS or connect failure, or a 429. Do not retry on 400, 402 or 403; those are terminal until a human acts.
3. On a timeout or 5xx, **look the message up before resending**:
   ```bash
   curl -G https://api.quo.com/messages \
     -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
     --data-urlencode "phoneNumberId=PN123abc" \
     --data-urlencode "to=+15555550123" \
     --data-urlencode "direction=outgoing" \
     --data-urlencode "createdAt[gt]=2026-10-08T14:59:55Z"
   ```
   If a message comes back with matching `text`, treat it as sent and keep its `id`. Only resend when nothing matches. For a group send, use `to[all]=+1555…,+1666…` (the exact recipient set). The v1 equivalent is `GET /v1/messages?phoneNumberId=…&participants=…&createdAfter=…&maxResults=…`.
4. Store your own dedupe key (for example an order id mapped to the message id `AC…`) so the same business event never sends twice.
5. After a send is accepted, a failure to *deliver* is a separate problem. Use `POST /messages/{id}/retry` on `failed` messages; never resend through `POST /v1/messages`, which creates a duplicate message.

---

## List messages: `GET /messages` (2026-03-30)

`operationId: listMessages`. It returns the organization's messages **across all conversations, newest first**. No parameters are required. Header: `Quo-Api-Version: 2026-03-30`.

| Query | Type | Notes |
|---|---|---|
| `from` | E.164 \| short code \| `Anonymous`/`Restricted`/`Blocked` | Matches the sender exactly. |
| `to` | same value types, **or** `to[all]=a,b,c` | A bare `to=+1…` matches that recipient. `to[all]` (deepObject) is a comma-separated list that matches messages whose recipients are **exactly** that set, in any order; subsets and supersets do not match. |
| `status` | enum `queued \| sent \| delivered \| undelivered \| received \| failed` | Takes a single value. |
| `direction` | `incoming \| outgoing` | |
| `phoneNumberId` | `^PN(.*)$` | Restricts results to one Quo number. |
| `userId` | `^US(.*)$` | The sending user. |
| `createdAt[gt]` / `createdAt[lt]` | date-time | deepObject. **Only `gt` and `lt` exist**; this endpoint has no `gte`/`lte`. |
| `limit` | int 1-50, default 10 | |
| `after` | string | Pass the previous response's `nextCursor`. |

URL-encode `+` as `%2B` (or use `--data-urlencode`). A raw `+` in a query string decodes to a space, so the E.164 match fails.

```json
{
  "data": [{
    "id": "AC123abc",
    "to": ["+15555555555"],
    "from": "+15555550123",
    "text": "Is my order ready?",
    "phoneNumberId": "PN123abc",
    "conversationId": "CN123abc",
    "direction": "incoming",
    "userId": null,
    "status": "received",
    "createdAt": "2026-10-08T15:00:00Z",
    "updatedAt": "2026-10-08T15:00:00Z",
    "media": [{ "url": "https://…/image.jpg", "type": "image/jpeg" }]
  }],
  "nextCursor": "eyJsYXN0SWQiOiJBQzEyMyJ9"
}
```

- Required item fields: `id, to, from, text, conversationId, direction, status, createdAt, updatedAt, media`. **`media` is always present** (possibly `[]`). `phoneNumberId` and `userId` are optional and nullable.
- `userId` can be `US…` (a person) or `SYU…` (a system actor such as Sona, the AI agent), or `null` for incoming messages.
- On incoming messages, `to` contains your Quo number.
- Paginate until `nextCursor` is `null`. There is no `totalItems`.
- Errors: 400, 401, 403, 404, **422** (validation, for example a bad filter value), and 500, all in the structured envelope.

**Typical queries for tool calls**

| Goal | Query |
|---|---|
| Recent failures to retry | `status=failed&direction=outgoing&createdAt[gt]=…` |
| Undelivered (terminal; do not retry) | `status=undelivered` |
| Thread with one contact on one line | `phoneNumberId=PN…&to=%2B1555…` plus a separate query with `from=%2B1555…`, or use the conversation's `CN…` id via the conversations endpoints |
| Exact group thread | `to[all]=%2B1555…,%2B1666…` |

---

## Get a message: `GET /messages/{messageId}` (2026-03-30)

`operationId: getMessageById`. The path parameter `messageId` must match `^AC(.*)$`. Header: `Quo-Api-Version: 2026-03-30`. It returns `{ "data": Message }`, with the same object as the list items, including `media[]`. Errors: 400/401/403/404/422/500. Use it to poll the final `status` after a send.

---

## Retry a failed message: `POST /messages/{messageId}/retry` (2026-03-30)

`operationId: retryMessage`. Path: `messageId` (`^AC(.*)$`). No body. Header: `Quo-Api-Version: 2026-03-30`. Response: **`202`** with an empty object `{}`. Errors: 400/401/403/404/422/500.

**Retryable rules (spec verbatim):** "Only messages with a `failed` status can be retried. Messages that have permanently failed (a `failed` status with an error code) and messages with an `undelivered` status cannot be retried."

- `failed` is a transient send failure, and the only retryable state.
- A `failed` message that carries an error code has failed permanently. It is not retryable; expect a 4xx such as 422.
- `undelivered` is **terminal**: the carrier could not deliver the message or blocked it. Do not retry it, and do not resend it blindly. Check the number, the opt-out status and registration first.
- After a 202, the retry runs asynchronously. Re-read the message, or wait for the `message.delivered` or `message.failed` webhook.

---

## v1 list and get messages

### `GET /v1/messages`

`operationId: listMessages_v1`. This endpoint is scoped to **one conversation**.

| Query | Type | Req | Notes |
|---|---|---|---|
| `phoneNumberId` | `^PN(.*)$` | **yes** | Your Quo number. |
| `participants` | E.164[] | **yes** | `maxItems 10`. Excludes your own number. Repeat the parameter for each value (`participants=%2B1…&participants=%2B1…`). One value returns that 1:1 thread; several values return the **group** thread. |
| `maxResults` | int 1-100, default 10 | **yes** | |
| `userId` | `^US(.*)$` | no | |
| `createdAfter` / `createdBefore` | date-time | no | |
| `since` | date-time | no | **Deprecated**. It behaves as `createdBefore`. |
| `pageToken` | string | no | Pass the previous `nextPageToken`. |

The response is `{ data: Message[], totalItems, nextPageToken: string|null }`. **`totalItems` is inaccurate** according to the spec's own warning; paginate on `nextPageToken`. Message items carry `conversationId` (`CN…`, added 2026-06) and an optional `media[]` (added 2026-08).

### `GET /v1/messages/{id}`

`operationId: getMessageById_v1`. The path `id` must match `^AC(.*)$`. It returns `{ data: Message }`.

Both v1 read endpoints document the same error set as send (0206400, 0200401, 0201402, 0204403, 0200404, 0201500).

---

## Phone numbers (2026-03-30)

All endpoints in this section require `Quo-Api-Version: 2026-03-30`. The phone-number object looks like this:

```json
{
  "id": "PN123abc",
  "groupId": "GR123abc",
  "name": "Support line",
  "phoneNumber": "+15555555555",
  "formattedNumber": "(555) 555-5555",
  "forward": null,
  "portRequestId": null,
  "portingStatus": null,
  "symbol": "📞",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "restrictions": {
    "calling":   { "CA": "unrestricted", "Intl": "restricted", "US": "unrestricted" },
    "messaging": { "CA": "unrestricted", "Intl": "restricted", "US": "unrestricted" }
  }
}
```

The object always includes `id, groupId (GR…), name, phoneNumber, formattedNumber, forward, portRequestId, portingStatus, symbol, createdAt, updatedAt`; the five fields after `phoneNumber` are nullable. **`restrictions` (and `businessHours`) appear only when requested with `include`**; otherwise they are left out entirely. **There is no `users` array**; use the members endpoint.

### `GET /phone-numbers`

`operationId: listPhoneNumbers`. Query parameters: `limit` (1-50, default 10), `after`, `phoneNumber` (an E.164 exact-match filter, URL-encoded), and `include` (`restrictions` is the only value). Response: `{ data: PhoneNumber[], nextCursor }`. Errors: 400/401/403/500.

To resolve an E.164 number to its `PN…` id, call `GET /phone-numbers?phoneNumber=%2B15555555555`.

### `GET /phone-numbers/{phoneNumberId}`

`operationId: getPhoneNumberById`. Query: `include`, a comma list drawn from `restrictions` and `businessHours` (at most 2 values). **`businessHours` is available only on this endpoint.**

```json
"businessHours": {
  "enabled": true,
  "timezone": "America/New_York",
  "schedule": {
    "monday": { "start": "0900", "end": "1700" },
    "saturday": null,
    "sunday": null
  }
}
```

The schedule above is trimmed; the full schedule always lists all seven days. Times use 24-hour `HHMM` local time, and a day is `null` when the number is closed. If no business hours are stored, the response has `enabled: false`, `timezone: "America/Los_Angeles"` and `schedule: null`. Errors: 400/401/403/404/500.

### `GET /phone-numbers/{phoneNumberId}/users`

`operationId: listPhoneNumberUsers`. It returns the members assigned to a number, **ordered by user id**; assignments carry no timestamp. Query: `limit` (1-50), `after`. Each item is `{ id (US…), email, firstName|null, lastName|null, role (owner|admin|member), groupId (GR…) }`, and the response is `{ data, nextCursor }`. Errors: 400/401/403/404/500. Use it to choose a valid send `userId`.

### `GET /users/{userId}/phone-numbers`

`operationId: listUserPhoneNumbers`. It returns the numbers assigned to a user. Query: `limit`, `after`, `include=restrictions`. The response is the same PhoneNumber object in `{ data, nextCursor }`. Errors: 400/401/403/500.

### `GET /phone-numbers/available`

`operationId: getAvailablePhoneNumbersBase`. It searches inventory and **does not buy or provision** a number; the API has no purchase endpoint. All query parameters are optional strings: `areaCode`, `contains` (a substring), `countryCode`, `inLocality` (city), `inRegion` (state or province), plus the boolean `tollFree`.

```json
{ "data": { "phoneNumbers": ["+14155550100", "+14155550101"] } }
```

The response is **not paginated** and returns bare E.164 strings under `data.phoneNumbers`. Errors: 400/401/403/404/500.

---

## Phone numbers (v1)

### `GET /v1/phone-numbers`

`operationId: listPhoneNumbers_v1`. The only query parameter is `userId` (`^US(.*)$`). The endpoint is **not paginated**: it returns `{ data: PhoneNumber[] }` with every number at once.

### `GET /v1/phone-numbers/{phoneNumberId}`

`operationId: getPhoneNumberById_v1`. The path parameter must match `^PN(.*)$`. It returns `{ data: PhoneNumber }`.

The v1 object differs from 2026-03-30 in four ways. It uses **`number`** (E.164) instead of `phoneNumber`. It **always** embeds `restrictions`. It **always** embeds `users[]`, each item `{id, email, firstName, lastName, role, groupId}`. And its `groupId` is a free-form string, while 2026-03-30 enforces the `GR…` pattern.

Errors use a separate code family: 400 `0400400`, 401 `0400401`, 403 `0400403`, 404 `0400404`, 500 `0401500`.

---

## Get the organization: `GET /organization` (2026-03-30)

`operationId: getOrganization`. Header: `Quo-Api-Version: 2026-03-30`. The endpoint takes no parameters.

```json
{ "data": { "id": "OR123abc", "name": "Acme Dental", "subscriptionStatus": "active",
            "createdAt": "2025-01-01T00:00:00Z", "updatedAt": "2026-09-03T00:00:00Z" } }
```

`subscriptionStatus` is `active | expired`; `expired` covers both a lapsed billing period and no subscription at all. `name` is nullable. Errors: 401, 500. This is a cheap **preflight and auth check**: if it returns 401, the key is bad, and if it returns `expired`, sends will fail with 402.

---

## Send your first message: the walkthrough

This is the official guide, corrected for the current spec:

1. **Complete US carrier registration (A2P 10DLC)** before texting US numbers. Without it, sends return `400 0206400`.
2. **Find the sending number.** Call `GET /phone-numbers` (2026-03-30) or `GET /v1/phone-numbers`. Use the `id` (`PN…`) or the E.164 number as `from`. Check that `restrictions.messaging.US` (or `CA`/`Intl`) is `unrestricted` for the destination.
3. **Choose `userId` (optional).** Pick a member from `GET /phone-numbers/{id}/users`. If you omit it, the message is attributed to the number's owner.
4. **Send** with `POST /v1/messages` `{content, from, to:[E.164…]}` and expect a **202**. Persist `data.id`.
5. **Track delivery** with webhooks or `GET /messages/{id}`. Retry `failed` messages; treat `undelivered` as terminal.

According to the guide, you can then text anyone in the US or Canada. International destinations depend on the workspace setting and on `restrictions.messaging.Intl`.

---

## Segments, cost and registration

SMS is billed per **segment**. A segment holds 160 characters in GSM-7; a single non-GSM character (an emoji, a curly quote, `é`) drops the whole message to 70 characters per segment. At the 1600-character maximum, one `content` value can span many segments (whether a group send is billed per recipient is not stated in the docs; assume it is when estimating). Plans, segment rates, smart encoding, the A2P 10DLC requirement and the daily cap (`403 0204403`) are covered in **ai-cost-and-registration.md**. For LLM-generated messages, cap the length and strip emoji and smart quotes before calling send.

---

## v1 to 2026-03-30 migration diffs

| Area | v1 | 2026-03-30 |
|---|---|---|
| Send | `POST /v1/messages` | **none**: keep using v1 |
| Version header | none | `Quo-Api-Version: 2026-03-30` required |
| List messages scope | `phoneNumberId` + `participants` + `maxResults` all required | all filters optional, workspace-wide, newest first |
| Recipient filter | `participants[]` (repeat the parameter) | `to=` (contains) or `to[all]=a,b` (exact set); `from=` |
| Time filter | `createdAfter` / `createdBefore` (`since` deprecated) | `createdAt[gt]` / `createdAt[lt]` |
| Pagination | `maxResults` ≤100, `pageToken` → `nextPageToken`, unreliable `totalItems` | `limit` ≤50, `after` → `nextCursor`, no total |
| Message `status` | no `failed` | adds `failed`; filterable |
| Message `userId` | `US…` or `null` | `US…`, `SYU…` (system actor), or `null`; optional |
| Message `from` / `to` | string / E.164[] | E.164, short code, or `Anonymous`/`Restricted`/`Blocked` |
| `media` | optional | always present (`[]` when there is none) |
| Retry | none | `POST /messages/{id}/retry` |
| Phone number field | `number` | **`phoneNumber`** |
| Number restrictions | always embedded | opt-in: `include=restrictions` |
| Number members | embedded `users[]` | `GET /phone-numbers/{id}/users` |
| Business hours | none | `include=businessHours` (get-by-id only) |
| Number lookup by E.164 | filter client-side | `?phoneNumber=%2B1…` |
| Available-number search | none | `GET /phone-numbers/available` |
| Organization | none | `GET /organization` |
| Error body | `{message, code, status, docs, title, …}` with numeric `code` strings | `{title, message, docs, trace, errors[]}`; branch on HTTP status and `title` |

---

## Sources (checked 2026-10-08)

- OpenAPI `openphone-public-api-v1-prod.json` (paths `/v1/messages`, `/v1/messages/{id}`, `/v1/phone-numbers`, `/v1/phone-numbers/{phoneNumberId}`) and `openphone-public-api-2026-03-30-prod.json` (paths `/messages`, `/messages/{messageId}`, `/messages/{messageId}/retry`, `/phone-numbers`, `/phone-numbers/{phoneNumberId}`, `/phone-numbers/available`, `/phone-numbers/{phoneNumberId}/users`, `/users/{userId}/phone-numbers`, `/organization`). Where the prose and the spec disagree, the spec wins.
- Doc pages: `mdx/api-reference/messages/send-a-text-message`, `mdx/api-reference/messages/list-messages`, `mdx/api-reference/messages/get-a-message-by-id`, `mdx/api-reference/send-your-first-message`, `mdx/api-reference/phone-numbers/list-phone-numbers`, `mdx/api-reference/phone-numbers/get-a-phone-number-by-id`, `2026-03-30/messages/list-messages`, `2026-03-30/messages/get-a-message-by-id`, `2026-03-30/messages/retry-a-failed-message`, `2026-03-30/phone-numbers/list-phone-numbers`, `2026-03-30/phone-numbers/get-a-phone-number-by-id`, `2026-03-30/phone-numbers/get-available-phone-numbers`, `2026-03-30/phone-numbers/list-the-members-assigned-to-a-phone-number`, `2026-03-30/user-phone-numbers/list-a-users-phone-numbers`, `2026-03-30/organization/get-the-organization`, `changelog` (entries 2026-06-15 through 2026-09-30).
