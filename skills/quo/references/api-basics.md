# Quo (formerly OpenPhone) API: the basics for both surfaces

Quo is the rebrand of OpenPhone. Its public REST API now has **two live surfaces on the same host**, and an integration usually needs both: the dated `2026-03-30` API for reads and new capability, and v1 for sending messages. This file covers how to choose a surface, auth, versioning, request and response conventions, pagination, filtering, errors, retries and rate limits, and lists every endpoint on both surfaces. It also gives the ground rules for agents (including LLM tool-calling integrations) that build on Quo.

## Contents

1. [The two surfaces at a glance](#the-two-surfaces-at-a-glance)
2. [Which surface to use](#which-surface-to-use)
3. [Host and base URL](#host-and-base-url)
4. [Authentication and key hygiene](#authentication-and-key-hygiene)
5. [Versioning](#versioning)
6. [Making requests: headers, envelopes, ids, timestamps](#making-requests-headers-envelopes-ids-timestamps)
7. [Pagination on both surfaces](#pagination-on-both-surfaces)
8. [Sorting and filtering (2026-03-30)](#sorting-and-filtering-2026-03-30)
9. [Errors](#errors)
10. [Retries](#retries)
11. [Rate limits](#rate-limits)
12. [Endpoint inventory (both specs)](#endpoint-inventory-both-specs)
13. [Migrating v1 to 2026-03-30](#migrating-v1-to-2026-03-30)
14. [Building with AI and agents](#building-with-ai-and-agents)
15. [Machine-readable sources](#machine-readable-sources)
16. [Sources](#sources-checked-2026-10-08)

---

## The two surfaces at a glance

| | v1 | 2026-03-30 (current dated version) |
|---|---|---|
| Host | `https://api.quo.com` | `https://api.quo.com` |
| Paths | prefixed: `/v1/messages`, `/v1/calls` … | unprefixed: `/messages`, `/calls` … |
| Version header | none | `Quo-Api-Version: 2026-03-30`, **required on every request** |
| Auth | `Authorization: YOUR_API_KEY` (raw key, no `Bearer`) | same |
| List envelope | `{ data, totalItems, nextPageToken }` | `{ data, nextCursor }` |
| Pagination | `maxResults` + `pageToken` | `limit` (1–50, default 10) + `after` |
| Filters | named params (`createdAfter`, `participants[]` …), often required | optional; `field`, `field[in]`, `field[gte]` … |
| Error body (spec) | `{ message, code, status, docs, title, trace?, errors? }` | `{ title, message, docs, trace?, errors? }` |
| Error body (live, observed) | `{ "error": { message, key, trace } }` | matches spec |
| Rate limit | 10 req/s per key | 10 req/s per key |
| Status | fully supported, no retirement announced | where **all new capability ships** |
| OperationIds | suffixed `_v1` (`sendMessage_v1`) | unsuffixed (`listCalls`, `tasks.create`) |

**Sending a message only exists on v1** (`POST /v1/messages`). The 2026-03-30 Messages surface is read-only, plus a retry for failed messages.

## Which surface to use

Default to **2026-03-30** wherever it covers the need. Quo's own guidance is to build new work there and to leave an existing v1 integration where it is until the new version covers its surface. Use v1 only for the operations below.

| Need | Use | Why |
|---|---|---|
| Send an SMS/MMS, including a group text to up to 10 numbers | **v1** `POST /v1/messages` | No send endpoint exists in 2026-03-30 |
| Retry a failed outbound message | 2026-03-30 `POST /messages/{messageId}/retry` | v1 has no retry |
| Read message history | 2026-03-30 `GET /messages` | Lists across the whole workspace; v1 needs `phoneNumberId` + `participants` |
| Calls, summaries, voicemails, recordings, transcripts | 2026-03-30 `GET /calls?include=summary,voicemail` etc. | One request instead of four |
| Contacts CRUD, notes, properties, shares | 2026-03-30 | Notes, properties and shares are new and exist only here |
| List workspace custom-field definitions | **v1** `GET /v1/contact-custom-fields` | 2026-03-30 has per-contact properties, not a workspace field catalogue |
| Conversations list / read / done / open | 2026-03-30 | Sort, time filters, `phoneNumberId[in]` |
| Phone numbers, number search, members | 2026-03-30 | `GET /phone-numbers/available` and `/phone-numbers/{id}/users` are new |
| Organization info | 2026-03-30 `GET /organization` | New |
| Tasks | 2026-03-30 | Same capability as v1, with REST-shaped sub-resources |
| Webhooks | 2026-03-30 `POST /webhooks` | One endpoint for all events, signed with `whsec_`, delivery logs, test and retry. v1 webhooks are per-event-type and use the legacy signature scheme |

**v1-only operations:** `sendMessage_v1`, `getContactCustomFields_v1`. Everything else in v1 has a 2026-03-30 counterpart (see [inventory](#endpoint-inventory-both-specs)).

## Host and base URL

```
https://api.quo.com            # both surfaces; the only server in both OpenAPI specs
https://api.quo.com/v1/...     # v1 paths
https://api.quo.com/...        # 2026-03-30 paths + Quo-Api-Version header
```

- Both specs declare exactly one server: `{"url": "https://api.quo.com", "description": "Production server"}`.
- **Legacy host `api.openphone.com` only serves v1.** A probe without credentials on 2026-10-08 returned:
  - `GET https://api.openphone.com/v1/phone-numbers` → `401`, the same body as `api.quo.com`
  - `GET https://api.openphone.com/users` → **`404 Not Found`** (the 2026-03-30 paths are not routed there)

  The current docs never mention `api.openphone.com`. Do not build on it. Keep the host in one constant set to `https://api.quo.com`.
- All traffic is HTTPS, with UTF-8 JSON bodies.

## Authentication and key hygiene

```
Authorization: YOUR_API_KEY        # the raw key, verbatim. NOT "Bearer YOUR_API_KEY"
```

Both specs declare the same scheme, `{"type": "apiKey", "in": "header", "name": "Authorization"}`, and apply it globally. v1 docs: *"The Quo API does not use a Bearer token for authentication."* A `Bearer x` value returns `401` (probed 2026-10-08).

**Getting a key**
1. Quo app → **Workspace Settings → API**. You need **owner or admin** rights to see the tab.
2. **Generate API key** and name it after the thing that will use it, for example `crm-sync`, `claude-agent` or `staging-tests`. **Spaces are not allowed** in key names.
3. Store it like a password, in a secrets manager or an environment variable.

**What a key can do:** it has full API access, with the same reach as an admin in the workspace. Keys have no scopes, so any isolation comes from using separate keys.

**Prerequisites:** an active Quo subscription and an owner/admin to create the key. Sending SMS to **US numbers** also requires completed US Carrier Registration (A2P 10DLC). Without it, send returns `400` code `0206400`.

**Hygiene (from both auth pages)**
- Use **one key per integration**. You can then delete a retired integration's key without guessing what else breaks, and each integration gets its own 10 req/s budget.
- **Rotate a key when someone who had access leaves.** Generate the new key, deploy it, then delete the old one. Rotate regularly anyway, and immediately if a key is compromised.
- **Never** commit keys, ship them in client-side code, or **paste them into a prompt**.
- Deleting a key is safe: only the integrations using that key stop working.

**Revoking:** Workspace Settings → API → find the key → ellipsis (⋯) → **Delete**. Access ends immediately.

## Versioning

**v1** is versioned only by its `/v1` path prefix. There is no version header, and `info.version` in both spec files is just `1.0.0`. Older v1 notes: `/v0` is deprecated, and `since` is deprecated in favour of `createdAfter`/`createdBefore` (`since` actually behaves as `createdBefore`).

**2026-03-30** uses date-based header versioning:

```
Quo-Api-Version: 2026-03-30
```

- The header is **required on every request and has no default**. The spec declares it as a required header parameter with `enum: ["2026-03-30"]`.
- If it is missing or wrong you get `400` with `"message": "Unsupported or missing Quo-Api-Version header. Supported versions: 2026-03-30"`. **The header is checked before auth**, so a request with neither header returns `400`, not `401` (probed 2026-10-08).
- A version is frozen once it ships. These can still arrive within a version: new endpoints, new optional request params, **new response fields**, and bug and security fixes. Removals, renames, type or format changes and observable behaviour changes all get a new date.
- **Ignore response fields you don't recognise.** Avoid strict response schemas (for example Zod `.strict()`) on Quo payloads.
- Retirement will be announced in the changelog (which has an RSS feed) with a migration window. Upgrading means changing the header and reading the changelog between the two dates.
- Do not confuse this with **`x-quo-api-version`**, which pinned the *webhook payload* version of a subscription in the earlier beta Webhook API. It is not a REST request header.

## Making requests: headers, envelopes, ids, timestamps

| Header | v1 | 2026-03-30 |
|---|---|---|
| `Authorization: YOUR_API_KEY` | required | required |
| `Quo-Api-Version: 2026-03-30` | not used | required |
| `Content-Type: application/json` | when sending a body | when sending a body |

**Envelopes.** Every successful body wraps its payload in `data`:

```json
{ "data": { "id": "USu3X8sIB9", "email": "renee@example.com", "role": "owner",
            "createdAt": "2024-08-02T17:31:08Z", "updatedAt": "2026-05-19T09:12:45Z" } }
```

```json
{ "data": [ { "id": "USu3X8sIB9" } ], "nextCursor": "Y3Vyc29yOjEwMjQ" }          // 2026-03-30 list
{ "data": [ { "id": "US123abc" } ], "totalItems": 42, "nextPageToken": "eyJ..." }  // v1 list
```

A few v1 lists are not paginated and return only `{ data }`: `GET /v1/phone-numbers`, `GET /v1/webhooks` and `GET /v1/contact-custom-fields`. Success codes are `200`, `201` (create), `202` (accepted: v1 send, 2026-03-30 message retry and webhook-delivery retry) and `204` (delete, no body).

**Identifiers** are strings with a resource prefix. Read the prefix, but otherwise treat ids as opaque: don't parse them and don't assume a length. Prefixes enforced by the spec patterns:

| Prefix | Resource | Notes |
|---|---|---|
| `US` | user | `userId`, `assignedTo`, `createdByUserId` … |
| `SYU` | system actor (e.g. a Quo AI agent) | accepted wherever an actor/user can be a system user: `actorId`, `answeredBy`, `initiatedBy` |
| `PN` | Quo phone number | `phoneNumberId`, `from` (v1 send accepts `PN…` or E.164) |
| `AC` | activity = **a call or a message** | calls and messages share the prefix; `messageId`, `callId`, `lastActivityId` |
| `CN` | conversation | |
| `TK` | task | |
| `WH` | webhook | |
| `OR` | organization | also appears in `sharedWith` |
| `GR` | group | `groupId`, `sharedWith` |
| `CR` | call recording | |
| `VM` | voicemail | |
| *(none)* | contact | contact ids have no prefix (`^(.*)$`) |

**Phone numbers** are E.164 (`^\+[1-9]\d{1,14}$`), e.g. `+15555555555`. Some fields also accept short codes (3–8 digits) or the literals `anonymous`/`blocked`/`restricted`. In query strings, **URL-encode `+` as `%2B`**, because a literal `+` is read as a space.

**Timestamps** are ISO 8601 strings in UTC, for example `"2026-05-19T09:12:45Z"`. Convert to local time only when displaying.

## Pagination on both surfaces

### 2026-03-30: cursor

| Param | Type | Behaviour |
|---|---|---|
| `limit` | integer 1–50, default `10` | page size; `>50` → `400` (`errors[].path: "/query/limit"`) |
| `after` | string | the previous page's `nextCursor`; omit for page one |

Walk pages until `nextCursor` is `null`. Cursors are opaque: pass them back unchanged and don't store them long-term. To resume a sync later, store a timestamp and filter on it (e.g. `updatedAt[gte]` on `/conversations`), not a cursor.

```ts
async function* quoList<T>(path: string, query: Record<string, string> = {}) {
  let after: string | null = null;
  do {
    const url = new URL(path, "https://api.quo.com");
    for (const [k, v] of Object.entries(query)) url.searchParams.set(k, v);
    url.searchParams.set("limit", "50");
    if (after) url.searchParams.set("after", after);
    const res = await fetch(url, {
      headers: { Authorization: process.env.QUO_API_KEY!, "Quo-Api-Version": "2026-03-30" },
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    const page = (await res.json()) as { data: T[]; nextCursor: string | null };
    yield* page.data;
    after = page.nextCursor;
  } while (after);
}
```

### v1: page token

| Param | Type | Behaviour |
|---|---|---|
| `maxResults` | integer, min 1 | **required** on calls, messages, contacts, conversations and tasks; optional on users |
| `pageToken` | string | the previous response's `nextPageToken`; omit for page one |

`maxResults` limits differ by endpoint (from the spec):

| Endpoint | max | default |
|---|---|---|
| `/v1/calls`, `/v1/messages`, `/v1/conversations` | 100 | 10 |
| `/v1/tasks` | 100 | **50** |
| `/v1/contacts`, `/v1/users` | **50** | 10 |

Response: `{ data, totalItems, nextPageToken }`. Stop when `nextPageToken` is `null` (a bug fixed in 1.1.2 used to return a string token on the last page).
**Never use `totalItems`.** The spec itself says: *"`totalItems` is not accurately returning the total number of items that can be paginated."* There is no offset/page-number paging on either surface.

## Sorting and filtering (2026-03-30)

v1 has no shared convention. Each endpoint has its own named params (`createdAfter`, `createdBefore`, `updatedAfter`, `participants[]`, `externalIds[]`, `excludeInactive`). In 2026-03-30 every list endpoint follows the rules below.

**Sorting.** A single `sort=field:direction` (`asc`|`desc`). Today only `GET /conversations` supports it, on `createdAt` or `updatedAt`. A missing or unknown direction, an unsupported field, or more than one pair → `400`. Every other list endpoint returns a fixed order (calls and messages are newest first).

**Filtering.** There is one query param per filterable field, named with the **singular** field name (`participant`, not `participants`). Equality is the default. Distinct params combine with **AND**. Operators go in brackets:

| Syntax | Meaning |
|---|---|
| `field[in]=a,b` | any of the comma-separated values (the only OR) |
| `field[gte]` / `field[lte]` | inclusive bounds |
| `field[gt]` / `field[lt]` | exclusive bounds |
| `field[all]=a,b` | exactly this set, any order |

Each filter accepts only some operators. A range filter accepts **either** the inclusive pair **or** the exclusive pair, never both. An unsupported operator → `400`. Cross-field OR is not possible, so make two calls.

Filters per endpoint, as the spec lists them:

| Endpoint | Filters |
|---|---|
| `GET /calls` | `phoneNumberId`, `actorId` (`US…`/`SYU…`), `participant` (+`[in]`), `direction` (`incoming`/`outgoing`), `status` (+`[in]`; `queued, initiated, ringing, in-progress, completed, busy, failed, no-answer, canceled, missed, answered, forwarded, abandoned`), `createdAt[gte\|lte]`, `include=summary,voicemail` |
| `GET /messages` | `from`, `to` (+`[all]` for exact group membership), `status` (`queued, sent, delivered, undelivered, received, failed`), `direction`, `phoneNumberId`, `userId`, `createdAt[gt\|lt]` (**exclusive** pair here) |
| `GET /conversations` | `phoneNumberId` (+`[in]`, max 100), `createdAt[gte\|lte]`, `updatedAt[gte\|lte]`, `sort` |
| `GET /contacts` | `externalId` (+`[in]`, max 50), `source` (+`[in]`, max 50) |
| `GET /contacts/{id}/properties` | `type` (e.g. `phone-number`, `email`) |
| `GET /phone-numbers` | `phoneNumber` (E.164), `include=restrictions` |
| `GET /phone-numbers/{id}` | `include=restrictions,businessHours` |
| `GET /users/{id}/phone-numbers` | `include=restrictions` |
| `GET /phone-numbers/available` | `countryCode`, `areaCode`, `inLocality`, `inRegion`, `contains`, `tollFree` |
| `GET /webhooks/{id}/events` | `status` (`success, pending, sending, failed`), `eventType`/`eventTypes`, `resourceId`, `createdAt[gt\|lt]` (`createdAfter`/`createdBefore` deprecated) |

Example: `GET /calls?status[in]=missed,no-answer&direction=incoming&createdAt[gte]=2026-07-01T00:00:00Z`.

## Errors

### Status codes (both surfaces)

| Code | Meaning | Retry? |
|---|---|---|
| `400` | Malformed request: missing/invalid `Quo-Api-Version`, bad body, param out of bounds, A2P not approved (v1 send) | No, fix it first |
| `401` | Missing or invalid `Authorization` (including a `Bearer` prefix) | No |
| `402` | v1 only: subscription expired (`0201402`), open-tasks limit reached (`0600402`) | No, fix billing or close tasks |
| `403` | Valid key, action not allowed: permissions, a workspace setting off (e.g. international messaging), not a member of that number, A2P daily cap reached (`0204403`) | No, not until something changes |
| `404` | Not found, **or the id belongs to another workspace** | No |
| `409` | v1 contacts: conflict | Only after resolving it |
| `422` | Well-formed but semantically impossible (e.g. retrying a message that isn't `failed`) | No |
| `429` | Over 10 req/s | **Yes**, with backoff |
| `500` | Quo-side failure | **Yes**, with backoff (see the POST caveat below) |

**4xx errors are yours, 5xx are Quo's.** Retrying a 4xx in a loop only uses up your rate limit.

### 2026-03-30 error envelope (spec and live agree)

```json
{
  "title": "Bad Request",
  "message": "Validation failed for 1 field.",
  "docs": "https://quo.com/docs",
  "trace": "6897907457496870895",
  "errors": [
    { "path": "/query/limit", "message": "must be <= 50", "value": 200, "schema": { "type": "integer" } }
  ]
}
```

`title`, `message` and `docs` are always present. `trace` and `errors[]` are optional, and `errors[]` holds one entry per invalid field, all in a single response. Branch on the **HTTP status first and `errors[].path` second**. `message` text may be reworded. **Log `trace`.** Support (support+developers@quo.com) can find the exact request from it. Webhook endpoints in this version also carry a `code` (e.g. `0303400` Invalid Id, `0304400` Invalid Input Format).

### v1 error bodies: spec vs live

The v1 spec documents a flat body with a 7-digit `code`:

```json
{ "message": "…", "code": "0206400", "status": 400, "docs": "https://quo.com/docs",
  "title": "A2P Registration Not Approved", "trace": "…", "errors": [ /* same shape as above */ ] }
```

The live v1 API (observed 2026-06-15 and again 2026-10-08) **wraps it instead**:

```json
{ "error": { "message": "Missing authorization header", "key": "Unauthorized", "trace": "6480612490142498014" } }
```

**Parse defensively across both surfaces:**

```ts
const err = body?.error ?? body;              // v1 live wraps, 2026-03-30 doesn't
const message = err?.message ?? res.statusText;
const trace = err?.trace;
const fieldErrors = body?.errors ?? err?.errors ?? [];
```

Named v1 codes from the spec (the generic `…400/401/403/404/500` codes per resource are omitted):

| Code | Status | Title | Where |
|---|---|---|---|
| `0206400` | 400 | A2P Registration Not Approved | messages |
| `0201402` | 402 | Subscription Expired | messages |
| `0204403` | 403 | A2P 10DLC Daily Message Cap Reached | messages |
| `0101400` | 400 | Too Many Participants | calls |
| `0101403` / `0801403` / `1001403` | 403 | Not Phone Number User | calls / contacts / conversations |
| `0801400` | 400 | Invalid Custom Field Item | contacts |
| `0800409` | 409 | Conflict | contacts |
| `0600402` | 402 | Open Tasks Limit Reached | tasks |
| `0305400` | 400 | Invalid Version | v1 webhooks |

The first two digits identify the resource (`01` calls, `02` messages, `03` webhooks, `04` phone numbers, `05` summaries, `06` tasks/transcripts, `07` custom fields, `08` contacts, `09` recordings, `10` conversations, `11` users, `12` voicemails). The rest is the HTTP status.

## Retries

- **Retry `429` and `5xx`** with exponential backoff and jitter. Start at about 1 s, double each time, and cap the number of attempts to suit the work. Neither surface documents `Retry-After` or `RateLimit-*` headers, so don't depend on them.
- **`GET` is always safe to retry.**
- **Never blindly retry `POST /v1/messages`.** Neither spec has an idempotency key. A timeout or `5xx` may already have sent the text, and a retry can send a duplicate SMS to a customer, billed per segment. Before re-sending, check `GET /messages?to=%2B1555…&createdAt[gt]=…` (2026-03-30) for the message. If you keep your own outbox, mark the attempt as "unknown" and reconcile it from the `message.delivered`/`message.failed` webhooks.
- For a message whose status is `failed`, use `POST /messages/{messageId}/retry` (2026-03-30, `202`). It re-attempts that same message and creates no new one. It returns `422` for `undelivered` messages and for `failed` messages that carry an error code (permanent failures).
- Other writes such as `POST /contacts` and `POST /tasks` can also repeat their effect. Look the record up (e.g. by `externalId`) before retrying a create.

## Rate limits

- **10 requests per second per API key.** The limit is per key, not per IP or workspace. Excess requests get `429` with the standard error envelope until the next second.
- There is **no daily quota**.
- Parallel workers on one key **share** the budget (five workers at 3 req/s each will hit `429` constantly).
- Stay under it by:
  1. using `limit=50` (2026-03-30), which cuts bulk reads 5×;
  2. caching slow-changing reads such as users, phone numbers and custom fields;
  3. running a client-side throttle or queue (e.g. a token bucket at roughly 8–9 req/s);
  4. backing off with jitter on `429`.
- Use webhooks instead of polling for new messages and calls.
- For more headroom, email support+developers@quo.com.

## Endpoint inventory (both specs)

All 2026-03-30 rows need `Quo-Api-Version: 2026-03-30`. "—" means there is no equivalent on that surface.

### Messages
| Operation | v1 (operationId) | 2026-03-30 (operationId) |
|---|---|---|
| **Send** (1–10 recipients; 2+ = one group message) | `POST /v1/messages` (`sendMessage_v1`) → `202` | — **v1 only** |
| List messages | `GET /v1/messages` (`listMessages_v1`): `phoneNumberId` + `participants` required | `GET /messages` (`listMessages`): workspace-wide, all filters optional |
| Get message | `GET /v1/messages/{id}` (`getMessageById_v1`) | `GET /messages/{messageId}` (`getMessageById`): includes `media[] {url, type}` (`type` is the MIME type) |
| Retry failed message | — | `POST /messages/{messageId}/retry` (`retryMessage`) → `202` |

### Calls
| Operation | v1 | 2026-03-30 |
|---|---|---|
| List calls | `GET /v1/calls` (`listCalls_v1`): `phoneNumberId` + `participants` required | `GET /calls` (`listCalls`) |
| Get call | `GET /v1/calls/{callId}` (`getCallById_v1`) | `GET /calls/{callId}` (`getCallById`) |
| Summary | `GET /v1/call-summaries/{callId}` (`getCallSummary_v1`) | `?include=summary` on list/get |
| Voicemail | `GET /v1/call-voicemails/{callId}` (`getCallVoicemails_v1`) | `?include=voicemail` on list/get |
| Recordings | `GET /v1/call-recordings/{callId}` (`getCallRecordings_v1`) | `GET /calls/{callId}/recordings` (`getCallRecordings`), paginated segments |
| Transcript | `GET /v1/call-transcripts/{id}` (`getCallTranscript_v1`) | `GET /calls/{callId}/transcripts` (`getCallTranscripts`), paginated segments |

Call summaries and transcripts are **Business and Scale plans only**. They are generated after the call ends, so a fresh call may not have them yet, and voicemail is processed asynchronously the same way. Subscribe to the `call.summary.completed`, `call.transcript.completed`, `call.recording.completed` and `call.voicemail.completed` webhook events rather than polling.

### Contacts
| Operation | v1 | 2026-03-30 |
|---|---|---|
| List | `GET /v1/contacts` (`listContacts_v1`) | `GET /contacts` (`listContacts`) |
| Get | `GET /v1/contacts/{id}` (`getContactById_v1`) | `GET /contacts/{contactId}` (`getContactById`) |
| Create | `POST /v1/contacts` (`createContact_v1`) → `201` | `POST /contacts` (`createContact`) → `201` |
| Update | `PATCH /v1/contacts/{id}` (`updateContactById_v1`) | `PATCH /contacts/{contactId}` (`updateContactById`) |
| Delete | `DELETE /v1/contacts/{id}` (`deleteContact_v1`) → `204` | `DELETE /contacts/{contactId}` (`deleteContact`) → `204` |
| Custom-field definitions | `GET /v1/contact-custom-fields` (`getContactCustomFields_v1`) | — **v1 only** |
| Shares | — | `GET /contacts/{contactId}/shares` (`listContactShares`) |
| Notes: list / create / get / update / delete | — | `GET`/`POST /contacts/{contactId}/notes`, `GET`/`PATCH`/`DELETE /contacts/{contactId}/notes/{noteId}` (`listContactNotes`, `createContactNote`, `getContactNote`, `updateContactNote`, `deleteContactNote`) |
| Properties: list / create / get / update / delete | — | `GET`/`POST /contacts/{contactId}/properties`, `GET`/`PATCH`/`DELETE /contacts/{contactId}/properties/{propertyId}` (`listContactProperties`, `createContactProperty`, `getContactProperty`, `updateContactProperty`, `deleteContactProperty`) |

### Conversations
| Operation | v1 | 2026-03-30 |
|---|---|---|
| List | `GET /v1/conversations` (`listConversations_v1`) | `GET /conversations` (`listConversationsHeaderVersioned`) |
| Mark read | `POST /v1/conversations/{conversationId}/mark-as-read` (`markConversationAsRead_v1`) | `POST /conversations/{conversationId}/mark-as-read` (`markConversationAsRead`) |
| Mark done | `POST /v1/conversations/{conversationId}/mark-as-done` (`markConversationAsDone_v1`) | `POST /conversations/{conversationId}/mark-as-done` (`markConversationAsDone`) |
| Mark open | `POST /v1/conversations/{conversationId}/mark-as-open` (`markConversationAsOpen_v1`) | `POST /conversations/{conversationId}/mark-as-open` (`markConversationAsOpen`) |

### Phone numbers, users, organization
| Operation | v1 | 2026-03-30 |
|---|---|---|
| List numbers | `GET /v1/phone-numbers` (`listPhoneNumbers_v1`), unpaginated, users embedded | `GET /phone-numbers` (`listPhoneNumbers`), paginated |
| Get number | `GET /v1/phone-numbers/{phoneNumberId}` (`getPhoneNumberById_v1`) | `GET /phone-numbers/{phoneNumberId}` (`getPhoneNumberById`) |
| Members of a number | embedded `users[]` | `GET /phone-numbers/{phoneNumberId}/users` (`listPhoneNumberUsers`) |
| Search purchasable numbers (no purchase) | — | `GET /phone-numbers/available` (`getAvailablePhoneNumbersBase`) |
| A user's numbers | `GET /v1/phone-numbers?userId=` | `GET /users/{userId}/phone-numbers` (`listUserPhoneNumbers`) |
| List users | `GET /v1/users` (`listUsers_v1`) | `GET /users` (`listUsers`) |
| Get user | `GET /v1/users/{userId}` (`getUserById_v1`) | `GET /users/{userId}` (`getUserById`) |
| Organization | — | `GET /organization` (`getOrganization`) |

### Tasks
| Operation | v1 | 2026-03-30 |
|---|---|---|
| List / create | `GET`, `POST /v1/tasks` (`listTasks_v1`, `createTask_v1`) | `GET`, `POST /tasks` (`tasks.list`, `tasks.create`) |
| Get / delete | `GET`, `DELETE /v1/tasks/{taskId}` (`getTaskById_v1`, `deleteTask_v1`) | `GET`, `DELETE /tasks/{taskId}` (`tasks.get`, `tasks.delete`) |
| Update title/description | `PUT /v1/tasks/{taskId}` (`updateTask_v1`) | `PATCH /tasks/{taskId}` (`tasks.update`) |
| Complete / reopen | `POST /v1/tasks/{taskId}/complete`, `/reopen` (`completeTask_v1`, `reopenTask_v1`) | `PATCH /tasks/{taskId}/status` (`tasks.updateStatus`) |
| Link / unlink conversation | `POST /v1/tasks/{taskId}/link-conversation`, `/unlink-conversation` | `POST`, `DELETE /tasks/{taskId}/conversations` (`tasks.linkConversation`, `tasks.unlinkConversation`) |
| Assign / unassign user | `POST /v1/tasks/{taskId}/assign`, `/unassign` | `POST`, `DELETE /tasks/{taskId}/users` (`tasks.assignUser`, `tasks.unassignUser`) |
| Set / remove due date | `POST /v1/tasks/{taskId}/change-due-date`, `/remove-due-date` | `PATCH`, `DELETE /tasks/{taskId}/due-date` (`tasks.updateDueDate`, `tasks.deleteDueDate`) |

The 2026-03-30 task operationIds contain a dot. Many LLM tool-name validators only allow `^[a-zA-Z0-9_-]{1,64}$`, so rename them when generating tool names (e.g. `tasks_create`).

### Webhooks
| Operation | v1 | 2026-03-30 |
|---|---|---|
| Create | per type: `POST /v1/webhooks/messages`, `/calls`, `/call-summaries`, `/call-transcripts` (`createMessageWebhook_v1` …) | `POST /webhooks` (`createHeaderVersionedWebhook`), any event mix, max 50 per workspace |
| List / get / delete | `GET /v1/webhooks`, `GET`/`DELETE /v1/webhooks/{id}` | `GET /webhooks`, `GET`/`DELETE /webhooks/{webhookId}` |
| Update | — | `PATCH /webhooks/{webhookId}` (`updateHeaderVersionedWebhookById`) |
| Rotate signing secret | — | `POST /webhooks/{webhookId}/rotate` (`rotateHeaderVersionedWebhookSecret`) |
| Delivery log / detail | — | `GET /webhooks/{webhookId}/events`, `GET /webhooks/{webhookId}/events/{deliveryId}` |
| Retry delivery | — | `POST /webhooks/{webhookId}/events/{deliveryId}/retry` → `202` |
| Send test event | — | `POST /webhooks/{webhookId}/events/test` |

The two webhook systems sign differently. 2026-03-30 uses Standard Webhooks (`webhook-id`, `webhook-timestamp`, `webhook-signature`, `whsec_…` secret). v1 uses the legacy `OpenPhone-Signature` header. The two schemes are not interchangeable.

## Migrating v1 to 2026-03-30

| v1 | 2026-03-30 |
|---|---|
| `/v1/...` path | unprefixed path + `Quo-Api-Version: 2026-03-30` |
| `maxResults` (max 50 or 100) / `pageToken` | `limit` (max **50**) / `after` |
| `nextPageToken`, `totalItems` | `nextCursor` (no total) |
| `createdAfter` / `createdBefore` | `createdAt[gte]`/`[lte]` (calls, conversations) or `createdAt[gt]`/`[lt]` (messages, webhook events) |
| `updatedAfter` / `updatedBefore` | `updatedAt[gte]`/`[lte]` |
| `participants[]` (required on calls/messages) | `participant` / `participant[in]` (calls), `to`/`from`/`to[all]` (messages), all optional |
| `phoneNumberId` (required on calls/messages) | optional filter |
| `phoneNumbers[]` / deprecated `phoneNumber` (conversations) | `phoneNumberId` / `phoneNumberId[in]` |
| `externalIds[]`, `sources[]` (contacts) | `externalId` / `externalId[in]`, `source` / `source[in]` |
| `userId` filter on calls | `actorId` (`US…` or `SYU…`) |
| phone number `number` field | `phoneNumber` |
| phone number `restrictions` always present | `include=restrictions` (and `businessHours` on get) |
| phone number `users[]` embedded | `GET /phone-numbers/{id}/users` |
| separate summary/voicemail endpoints | `include=summary,voicemail` |
| task verb routes (`/complete`, `/assign` …) | sub-resources (`/status`, `/users`, `/conversations`, `/due-date`) |
| per-type webhook create | single `POST /webhooks` |
| error `{ error: { message, key, trace } }` (live) | `{ title, message, docs, trace?, errors[]? }` |

You can migrate one resource at a time, because both surfaces share the host, key and IDs. The `AC…` id returned by `POST /v1/messages` is the same id that `GET /messages/{messageId}` and `POST /messages/{messageId}/retry` take.

## Building with AI and agents

There are two ways for an AI to work with Quo:

| You want to… | Use |
|---|---|
| Ask questions and take actions in plain language (Claude, ChatGPT, other MCP clients) | Quo's hosted **MCP connector**, on Starter, Business and Scale plans. It authenticates through the Quo account with OAuth (no API key) and can send messages, so trust it as you would a teammate who can text customers |
| Have your code (or code an agent writes) read and write on its own schedule, e.g. TanStack AI tool calls in your app | The **REST API** described in this file |

**Ground rules** (from the 2026-03-30 *Build with AI & agents* page and the v1 *Building with AI LLMs* guide):

1. **The key never enters the conversation.** Keep it in server-side env or connector config, never in a prompt, tool argument, tool result, or generated source. *"Anything an LLM reads, assume it may repeat."* In a TanStack AI app the tool's `server` implementation reads `process.env.QUO_API_KEY`, and the model only ever sees tool inputs and outputs.
2. **Give the agent its own key**, named after it (`claude-agent`, `gpt-ops`). You can then see its traffic, revoke it alone, and it gets its own rate budget.
3. **Tell it the budget.** State **10 req/s** up front. Left to itself, an agent will poll.
4. **Check generated code against the spec.** Code that compiles can still call endpoints that don't exist or send params the API ignores. Validate against the OpenAPI JSON, which wins over prose and over the model.
5. **Surface errors raw.** Return the status and the `errors[]` array (path, message, value, schema) to the model unchanged, so it can fix the request and try again. Don't swallow errors into "something went wrong". Remove nothing except the key.

The v1 guide also says to never share API keys or sensitive data with LLMs, to review all generated code and test it in a development environment, and to add error handling, logging and monitoring.

Tool-design notes for LLM tool calls:
- Expose **send** as a separate, approval-gated tool (`POST /v1/messages`). Every other tool should be a 2026-03-30 read or a reversible write.
- Do not let the model retry a send by itself after a timeout or `5xx` (see [Retries](#retries)).
- Default `limit` to 10–20 in tools so results fit in context, and return `nextCursor` so the model can ask for more.
- Validate E.164 and id prefixes (`PN`, `US`, `AC`, `CN`, `TK`) in the tool's input schema, so bad input fails before it costs a request.

## Machine-readable sources

| Resource | URL | Use |
|---|---|---|
| Docs index | `https://www.quo.com/docs/llms.txt` | the starting point for any agent |
| Full docs, one file | `https://www.quo.com/docs/llms-full.txt` | large-context ingestion |
| OpenAPI, 2026-03-30 | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-2026-03-30-prod.json` | ground truth for the dated version |
| OpenAPI, v1 | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-v1-prod.json` | ground truth for v1, including send |
| Docs bundle (zip) | `https://openphone-public-api-prod.s3.us-west-2.amazonaws.com/public/openphone-public-api-llm-ready-docs-prod.zip` | offline or air-gapped agents |
| Changelog (with RSS) | `https://www.quo.com/docs/changelog` | additions inside the current version |

Developer support: support+developers@quo.com.

## Sources (checked 2026-10-08)

- 2026-03-30 docs: `introduction`, `authentication`, `versioning`, `requests`, `sorting-and-filtering`, `errors`, `rate-limits`, `ai-agents`, `openapi`
- v1 docs: `mdx/api-reference/introduction`, `authentication`, `error-codes`, `rate-limits`, `messages/send-a-text-message`; `mdx/guides/building-with-ai-llms`; `mdx/pricing-support/pricing-overview`
- `changelog` (2026-03-30 initial release; June 15–16, 2026 mark-as-read, message retry and group messages; phone-number, call, contact, task and webhook additions; v1 1.1.2 pagination fix; v1 1.2.0)
- OpenAPI: `openphone-public-api-v1-prod.json` and `openphone-public-api-2026-03-30-prod.json`, used for every path, operationId, parameter bound, enum, id pattern and error code above
- Live probes without credentials, 2026-10-08: `api.quo.com` and `api.openphone.com` for `/v1/phone-numbers` and `/users`, with and without `Quo-Api-Version`, and with a `Bearer` value
