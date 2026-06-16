## Quo (formerly OpenPhone) API — Conversations & Tasks

> All facts below are quoted verbatim from the live Quo docs (`https://www.quo.com/docs/mdx/api-reference/...`) and cross-checked against the live OpenAPI spec `openphone-public-api-v1-prod.json`. The OpenAPI `info.title` is **"Quo Public API"**, `version: 1.0.0`, `openapi: 3.1.0`.

### Base URL, host & auth (read this first)

| Item | Value (verbatim from spec) | Note |
|---|---|---|
| OpenAPI `servers[0].url` | `https://api.quo.com` | This is what the published spec declares. |
| Legacy host (still live) | `https://api.openphone.com` | Probed live: `GET https://api.quo.com/v1/conversations` returns **HTTP 401** (reachable, just needs auth) — the legacy OpenPhone host is still routing. Both `api.openphone.com` and `api.quo.com` answer identically. |
| Path prefix | `/v1` | All endpoints are under `/v1/...` in `openphone-public-api-v1-prod.json`. |
| Auth scheme | `securitySchemes.apiKey: { in: header, name: Authorization, type: apiKey }` | **RAW API key**, not Bearer. |

**Auth header:** `Authorization: <your-api-key>` — a raw key, **NOT** `Authorization: Bearer <key>`. Confirmed two ways: (1) the OpenAPI `securitySchemes` declares an `apiKey`-type scheme in the `Authorization` header (no `bearer` HTTP scheme anywhere in the spec); (2) live probe — with no header the API returns `{"error":{"message":"Missing authorization header",...}}`; with a raw `Authorization: <key>` header it advances to `{"error":{"message":"Unauthorized",...}}` (header accepted, key rejected). Do **not** prefix with `Bearer`.

> **Base-URL contradiction (flagged):** The integration target in this skill uses `https://api.quo.com/v1` but the current published OpenAPI spec advertises `https://api.quo.com`. Both hosts are live and behave identically today (rebrand alias). Recommendation: make the base URL configurable, default to `https://api.quo.com/v1` for backward compatibility, and treat `https://api.quo.com/v1` as the forward-looking canonical host.

---

### List Conversations

```
GET https://api.quo.com/v1/conversations
```

Fetch a paginated list of conversations. Can be filtered by user and/or phone numbers. Defaults to all conversations in the Quo organization. Results are returned in **descending order based on the most recent conversation**.

| name | in | type | required | notes |
|---|---|---|---|---|
| `phoneNumber` | query | string | no | **DEPRECATED — use `phoneNumbers` instead.** If both are provided, `phoneNumbers` wins. Quo phone number ID (`^PN.*`) or full E.164 number (`^\+[1-9]\d{1,14}$`). |
| `phoneNumbers` | query | array (1–100 items) | no | Each item is a phone number ID (`^PN.*`) or E.164 number. Filters to conversations with these Quo numbers. |
| `userId` | query | string (`^US.*`) | no | Filter to the requesting user's conversations. |
| `createdAfter` | query | string (date-time, ISO 8601) | no | e.g. `2022-01-01T00:00:00Z`. |
| `createdBefore` | query | string (date-time, ISO 8601) | no | |
| `updatedAfter` | query | string (date-time, ISO 8601) | no | |
| `updatedBefore` | query | string (date-time, ISO 8601) | no | |
| `excludeInactive` | query | boolean | no | Exclude inactive conversations. |
| `maxResults` | query | integer | **YES** | `default: 10`, `minimum: 1`, `maximum: 100`. Marked `required: true` in the spec. |
| `pageToken` | query | string | no | Opaque cursor from `nextPageToken`. |

Request body: none (GET).

Response `200` example:

```json
{
  "data": [
    {
      "assignedTo": "US123abc",
      "createdAt": "2022-01-01T00:00:00Z",
      "deletedAt": null,
      "id": "CN123abc",
      "lastActivityAt": "2022-01-01T00:00:00Z",
      "lastActivityId": "AC123abc",
      "mutedUntil": null,
      "name": "Chat with customer",
      "participants": ["+15555555555"],
      "phoneNumberId": "PN123abc",
      "snoozedUntil": null,
      "updatedAt": "2022-01-01T00:00:00Z"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```

The conversation object's required fields (per spec): `assignedTo`, `createdAt`, `deletedAt`, `id` (`^CN.*`), `lastActivityAt`, `lastActivityId` (`^AC.*` | null), `mutedUntil`, `name`, `participants` (E.164 strings), `phoneNumberId` (`^PN.*`), `snoozedUntil`, `updatedAt`. In **this** endpoint's schema `assignedTo` is typed `string | null`; in the mark-as-read endpoint it is `(^US.* | ^SYU.*) | null` (system-user-aware).

**Gotchas**
- `maxResults` is **required** despite having a default of 10 — always send it explicitly to be safe.
- `totalItems` is documented as unreliable: *"⚠️ Note: `totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue."* Paginate via `nextPageToken`, never via `totalItems`.
- `phoneNumber` (singular) is deprecated; prefer `phoneNumbers` (array). If both are sent, `phoneNumbers` is used.
- Sort is fixed: descending by most recent conversation activity. No sort parameter is exposed.
- `403` for this endpoint is specifically titled **"Not Phone Number User"** (code `1001403`) — the API key's user must be a member of the phone number.

---

### Mark conversation as read

```
POST https://api.quo.com/v1/conversations/{conversationId}/mark-as-read
```

Mark a conversation as read, clearing its unread indicator **without sending a message**. Returns the updated conversation.

| name | in | type | required | notes |
|---|---|---|---|---|
| `conversationId` | path | string (`^CN.*`) | **YES** | e.g. `CN123abc`. |

Request body: none.

Response `200` example:

```json
{
  "assignedTo": "US123abc",
  "createdAt": "2022-01-01T00:00:00Z",
  "deletedAt": null,
  "id": "CN123abc",
  "lastActivityAt": "2022-01-01T00:00:00Z",
  "lastActivityId": "AC123abc",
  "mutedUntil": null,
  "name": "Chat with customer",
  "participants": ["+15555555555"],
  "phoneNumberId": "PN123abc",
  "snoozedUntil": null,
  "updatedAt": "2022-01-01T00:00:00Z"
}
```

> `assignedTo` here is `(^US.* | ^SYU.*) | null` — it may be a regular user (`US…`) **or a system user** (`SYU…`).

**Gotchas**
- The 200 body is the **bare conversation object** (no `data` wrapper) — unlike List Conversations which wraps items in `data: [...]`.
- It does not send any message; it only clears the unread indicator.
- `403` is again **"Not Phone Number User"** (code `1001403`).

---

### List tasks

```
GET https://api.quo.com/v1/tasks
```

Retrieve a list of tasks.

| name | in | type | required | notes |
|---|---|---|---|---|
| `maxResults` | query | integer | **YES** | `default: 50`, `minimum: 1`, `maximum: 100`. (Default differs from conversations, which is 10.) |
| `pageToken` | query | string | no | Cursor from `nextPageToken`. |

Request body: none.

Response `200` example:

```json
{
  "data": [
    {
      "taskId": "TK123abc",
      "phoneNumberId": "PN123abc",
      "conversationId": "CN123abc",
      "activityId": null,
      "phoneNumberGroupId": null,
      "orgId": "OR123abc",
      "title": "Follow up with customer",
      "description": "Discuss pricing and onboarding next steps.",
      "dueDate": "2022-01-01T00:00:00Z",
      "assignedTo": "US123abc",
      "assignedBy": "US456def",
      "createdAt": "2022-01-01T00:00:00Z",
      "createdBy": "US456def",
      "completed": false,
      "isDeleted": false,
      "revision": "1"
    }
  ],
  "nextPageToken": "string",
  "totalItems": 1
}
```

Full task object — required fields (per spec): `taskId` (`^TK.*`), `phoneNumberId` (`^PN.*` | null), `conversationId` (`^CN.*` | null), `activityId` (`^AC.*` | null), `phoneNumberGroupId` (string | null), `orgId` (`^OR.*`), `title` (string | null), `description` (string | null), `dueDate` (date-time | null), `assignedTo` (`^US.* | ^SYU.*` | null), `assignedBy` (`^US.* | ^SYU.*` | null), `createdAt` (date-time), `createdBy` (string), `completed` (boolean), `isDeleted` (boolean), `revision` (string).

**Gotchas**
- There is **no task `status` enum**. Lifecycle state is two booleans: `completed` (true/false) and `isDeleted` (true/false). "Open" = `completed:false && isDeleted:false`.
- `maxResults` is **required** (default 50). The list-tasks response top-level requires `data` + `totalItems` (`nextPageToken` is optional and only present when more pages exist).
- No filter parameters are exposed for List tasks (no `assignedTo`, `conversationId`, `completed`, etc. query filters) — only pagination. Client-side filtering is required.
- `assignedTo`/`assignedBy`/`createdBy` may carry system-user IDs (`SYU…`), not just `US…`.

---

### Create a task

```
POST https://api.quo.com/v1/tasks
```

Create a task linked to a phone number, conversation, or conversation activity. **Provide exactly one of `phoneNumberId`, `conversationId`, or `activityId`.** (The request body is a 3-way `anyOf` — supplying more than one link, or none, is rejected.)

| name | in | type | required | notes |
|---|---|---|---|---|
| `title` | body | string | **YES** | The title of the task. |
| `description` | body | string | **YES** | The description of the task. |
| `dueDate` | body | string (date-time) | no | ISO 8601. |
| `assignedTo` | body | string (`^US.*`) | no | A user to assign on creation. On create this is `US…` only. |
| `phoneNumberId` | body | string (`^PN.*`) | one-of | Link to a phone number. |
| `conversationId` | body | string (`^CN.*`) | one-of | Link to a conversation. |
| `activityId` | body | string (`^AC.*`) | one-of | Link to a conversation activity. |

> The schema has `additionalProperties: false`, so unknown keys are rejected. Each `anyOf` branch requires `title`, `description`, and **exactly one** of the three link fields.

Request body example:

```json
{
  "title": "Follow up with customer",
  "description": "Discuss pricing and onboarding next steps.",
  "dueDate": "2022-01-01T00:00:00Z",
  "assignedTo": "US123abc",
  "conversationId": "CN123abc"
}
```

Response `201` example:

```json
{
  "data": {
    "taskId": "TK123abc",
    "revision": "1",
    "phoneNumberId": "PN123abc",
    "conversationId": "CN123abc",
    "activityId": "AC123abc"
  }
}
```

The 201 `data` requires `taskId`, `revision`, `phoneNumberId`; `conversationId` and `activityId` are included when applicable. (Even when you create via `conversationId`/`activityId`, the response resolves and returns the associated `phoneNumberId`.)

**Gotchas**
- Returns **201**, not 200.
- Exactly one link field — sending zero or two of `phoneNumberId`/`conversationId`/`activityId` fails validation (`anyOf` + `additionalProperties:false`).
- The response is a thin reference (`taskId` + `revision` + link IDs), **not** the full task object. Call `GET /v1/tasks/{taskId}` to read back the full task.
- Error codes for the tasks domain use the `06…` prefix (`0600400`, `0600401`, `0600403`, `0600404`, `0601500`) — different from the conversations domain (`1000400`, `1001403`, etc.).

---

### Gets a task by ID

```
GET https://api.quo.com/v1/tasks/{taskId}
```

Retrieve a single task by its ID.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |

Request body: none.

Response `200` example:

```json
{
  "data": {
    "taskId": "TK123abc",
    "phoneNumberId": "PN123abc",
    "conversationId": "CN123abc",
    "activityId": null,
    "phoneNumberGroupId": null,
    "orgId": "OR123abc",
    "title": "Follow up with customer",
    "description": "Discuss pricing and onboarding next steps.",
    "dueDate": "2022-01-01T00:00:00Z",
    "assignedTo": "US123abc",
    "assignedBy": "US456def",
    "createdAt": "2022-01-01T00:00:00Z",
    "createdBy": "US456def",
    "completed": false,
    "isDeleted": false,
    "revision": "1"
  }
}
```

**Gotchas**
- Returns the **full** task object wrapped in `data` (same shape as each item in List tasks). This is the canonical "read the full task" call after any mutation.
- Same nullable fields as List tasks; check `completed`/`isDeleted` for lifecycle state.

---

### Update a task

```
PUT https://api.quo.com/v1/tasks/{taskId}
```

Updates the task's **title and description** (only these two fields).

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `title` | body | string | **YES** | |
| `description` | body | string | **YES** | |

> `additionalProperties: false` — only `title` and `description` are accepted, and **both are required** (this is a PUT/replace of those fields, not a PATCH). To change `dueDate`, `assignedTo`, or completion, use the dedicated endpoints below.

Request body example:

```json
{
  "title": "Follow up with customer",
  "description": "Discuss pricing and onboarding next steps."
}
```

Response `200` example:

```json
{
  "data": {
    "taskId": "TK123abc",
    "revision": "2"
  }
}
```

**Gotchas**
- PUT requires **both** `title` and `description` — there is no partial update. Omitting either is a 400. Re-send the existing value for the field you don't want to change.
- This endpoint **cannot** set due date, assignment, completion, or links — use the dedicated action endpoints for those.
- Response is just `{taskId, revision}`; `revision` increments — use it for optimistic-concurrency tracking.

---

### Complete a task

```
POST https://api.quo.com/v1/tasks/{taskId}/complete
```

Marks the provided task as completed.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |

Request body: none.

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "3" } }
```

**Gotchas**
- No request body. This flips `completed` to `true` (there is no `status` field to set directly).
- Idempotency is not documented — completing an already-completed task is unspecified; check `completed` via GET if it matters.

---

### Reopen a task

```
POST https://api.quo.com/v1/tasks/{taskId}/reopen
```

Reopens the provided task (sets `completed` back to `false`).

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |

Request body: none.

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "4" } }
```

**Gotchas**
- The inverse of Complete; the only way to set `completed:false` on a completed task.
- No request body.

---

### Delete a task by ID

```
DELETE https://api.quo.com/v1/tasks/{taskId}
```

Deletes the task with the provided task ID.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |

Request body: none.

Response: **`204 No Content`** (empty body).

**Gotchas**
- Returns **204** with **no body** — do not try to parse JSON from a successful delete.
- Distinct from `isDeleted` on the task object (soft-delete flag seen in List/Get); this endpoint is the delete action.

---

### Assign a user to a task

```
POST https://api.quo.com/v1/tasks/{taskId}/assign
```

Assigns the provided user to the list of assignees for the task.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `userId` | body | string (`^US.*`) | **YES** | `additionalProperties: false`. |

Request body example:

```json
{ "userId": "US123abc" }
```

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "5" } }
```

**Gotchas**
- Body key is `userId` (not `assignedTo`). Must match `^US.*`.
- Description says "list of assignees", but the task object exposes a single `assignedTo` field — model assignment as effectively single-assignee when reading back.

---

### Unassign a user from a task

```
POST https://api.quo.com/v1/tasks/{taskId}/unassign
```

Removes the provided user from the assignee list of a task.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `userId` | body | string (`^US.*`) | **YES** | `additionalProperties: false`. |

Request body example:

```json
{ "userId": "US123abc" }
```

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "6" } }
```

**Gotchas**
- Requires the `userId` to remove (it is a targeted unassign, not "clear all").

---

### Change a task's due date

```
POST https://api.quo.com/v1/tasks/{taskId}/change-due-date
```

Sets the task's due date.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `dueDate` | body | string (date-time) | **YES** | ISO 8601. `additionalProperties: false`. |

Request body example:

```json
{ "dueDate": "2022-01-01T00:00:00Z" }
```

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "7" } }
```

**Gotchas**
- Setting/changing the due date is a **separate endpoint** from Update a task — `PUT /v1/tasks/{taskId}` cannot touch `dueDate`.
- To clear the due date, use the Remove endpoint (below); do not send `null` here.

---

### Remove a task's due date

```
POST https://api.quo.com/v1/tasks/{taskId}/remove-due-date
```

Clears the task's due date.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |

Request body: none.

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "8" } }
```

**Gotchas**
- No request body — the action itself clears `dueDate` (sets it to `null`).

---

### Link a task to a conversation

```
POST https://api.quo.com/v1/tasks/{taskId}/link-conversation
```

Links the task with the provided task ID to a conversation.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `conversationId` | body | string (`^CN.*`) | **YES** | (No `additionalProperties:false` on this body schema, unlike the assign/due-date bodies.) |

Request body example:

```json
{ "conversationId": "CN123abc" }
```

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "9" } }
```

**Gotchas**
- Body key is `conversationId` (`^CN.*`).
- A task may originally be linked via `phoneNumberId`/`conversationId`/`activityId` at create time; this endpoint links/relinks a conversation afterward.

---

### Unlink a task from a conversation

```
POST https://api.quo.com/v1/tasks/{taskId}/unlink-conversation
```

Unlinks the provided conversation from the task.

| name | in | type | required | notes |
|---|---|---|---|---|
| `taskId` | path | string (`^TK.*`) | **YES** | |
| `conversationId` | body | string (`^CN.*`) | **YES** | |

Request body example:

```json
{ "conversationId": "CN123abc" }
```

Response `200` example:

```json
{ "data": { "taskId": "TK123abc", "revision": "10" } }
```

**Gotchas**
- Requires the `conversationId` to unlink (targeted, not a blanket clear).

---

### curl examples (note the RAW Authorization header)

List conversations filtered by phone number and user:

```bash
curl -sS "https://api.quo.com/v1/conversations?phoneNumbers=PN123abc&userId=US123abc&maxResults=50" \
  -H "Authorization: YOUR_API_KEY"
```

Mark a conversation as read:

```bash
curl -sS -X POST "https://api.quo.com/v1/conversations/CN123abc/mark-as-read" \
  -H "Authorization: YOUR_API_KEY"
```

Create a task linked to a conversation, assigned, with a due date:

```bash
curl -sS -X POST "https://api.quo.com/v1/tasks" \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Follow up with customer",
        "description": "Discuss pricing and onboarding next steps.",
        "dueDate": "2026-07-01T00:00:00Z",
        "assignedTo": "US123abc",
        "conversationId": "CN123abc"
      }'
```

Complete a task, then read it back:

```bash
curl -sS -X POST "https://api.quo.com/v1/tasks/TK123abc/complete" \
  -H "Authorization: YOUR_API_KEY"

curl -sS "https://api.quo.com/v1/tasks/TK123abc" \
  -H "Authorization: YOUR_API_KEY"
```

> Do **not** write `-H "Authorization: Bearer YOUR_API_KEY"`. With no header the live API returns `{"error":{"message":"Missing authorization header",...}}`; with the raw key it advances to `{"error":{"message":"Unauthorized",...}}` if the key is wrong, or 200/201 if valid.

---

### Error model (all endpoints)

Documented (application-level) errors share this shape:

```json
{
  "message": "string",
  "code": "0600400",
  "status": 400,
  "docs": "https://quo.com/docs",
  "title": "Bad Request",
  "trace": "string",
  "errors": [
    { "path": "string", "message": "string", "value": {}, "schema": { "type": "string" } }
  ]
}
```

- Tasks domain status→code map: `400→0600400`, `401→0600401`, `403→0600403` ("Forbidden"), `404→0600404`, `500→0601500`.
- Conversations domain status→code map: `400→1000400`, `401→1000401`, `403→1001403` ("Not Phone Number User"), `404→1000404`, `500→1001500`.
- **Gateway-level** 401s (missing/invalid auth) return a *different, thinner* shape observed live: `{"error":{"message":"...","key":"Unauthorized","trace":"..."}}`. Handle both shapes defensively.