# Quo API — Conversations & Tasks

Conversations are Quo inbox threads (one per Quo number + participant set). Tasks are follow-up items a human works in the Quo app, optionally due on a date and linked to a conversation. Both resources exist on **both** API surfaces on `https://api.quo.com`:

- **v1** — paths under `/v1/...`, no version header, `maxResults` + `pageToken` pagination.
- **2026-03-30** — unprefixed paths, **required** header `Quo-Api-Version: 2026-03-30` (400 without it), `{data, nextCursor}` envelope, `limit` + `after` cursor pagination, bracket filters (`field[in|gte|lte]`).

Auth on both: the raw API key in `Authorization` — **no `Bearer` prefix**. Rate limit: 10 requests/second per key.

## Contents

- [Which surface to use](#which-surface-to-use)
- [ID prefixes](#id-prefixes)
- [Conversation object](#conversation-object)
- [Conversations — 2026-03-30](#conversations--2026-03-30)
- [Conversations — v1](#conversations--v1)
- [Incremental sync recipe](#incremental-sync-recipe)
- [Task object](#task-object)
- [Tasks — 2026-03-30](#tasks--2026-03-30)
- [Tasks — v1](#tasks--v1)
- [Task webhooks](#task-webhooks)
- [Scheduling and reminders recipe](#scheduling-and-reminders-recipe)
- [Errors](#errors)
- [v1 → 2026-03-30 migration](#v1--2026-03-30-migration)
- [Sources](#sources-checked-2026-10-08)

## Which surface to use

Default to **2026-03-30**. Drop to v1 only for the operations marked v1-only.

| Need | 2026-03-30 | v1 | Pick |
|---|---|---|---|
| List conversations | `GET /conversations` | `GET /v1/conversations` | 2026-03-30 (sortable, `updatedAt` range for sync) |
| Filter conversations by **user** scope | — | `userId` | **v1 only** |
| Filter by phone number as **E.164** | — (`PN…` IDs only) | `phoneNumbers` accepts E.164 or `PN…` | v1, or resolve the ID first |
| Exclude inactive conversations | — | `excludeInactive` | **v1 only** |
| Read `assignedTo` on a conversation | — (field absent) | present | **v1 only** |
| Sort conversations | `sort=createdAt\|updatedAt:asc\|desc` | fixed order | 2026-03-30 |
| Mark read / done / open | `POST /conversations/{id}/mark-as-*` | `POST /v1/conversations/{id}/mark-as-*` | either |
| List / get / delete tasks | `/tasks`, `/tasks/{id}` | `/v1/tasks`, `/v1/tasks/{id}` | 2026-03-30 |
| Create task linked to a conversation | `POST /tasks` | `POST /v1/tasks` | 2026-03-30 |
| Create task linked to a **phone number or activity** | — (`conversationId` required) | `phoneNumberId` / `activityId` | **v1 only** |
| Set task status (open / completed / deleted) | `PATCH /tasks/{id}/status` | `/complete`, `/reopen`, `DELETE` | 2026-03-30 |
| Assign / unassign, link / unlink, due date | REST sub-resources | action endpoints | 2026-03-30 |
| Task webhooks (`task.*`) | `/webhooks` | not offered on `/v1/webhooks/*` | 2026-03-30 |

Neither surface exposes conversation create/delete/rename, assignment of conversations, snooze/mute writes, or task filters (no `status`/`assignedTo`/`dueDate` query params on list tasks — filter client-side).

## ID prefixes

| Prefix | Resource |
|---|---|
| `CN` | conversation |
| `TK` | task |
| `PN` | Quo phone number |
| `AC` | activity (message/call) — `lastActivityId`, task `activityId` |
| `US` | user |
| `SYU` | system user (can appear in `assignedTo` / `assignedBy`) |
| `OR` | organization |

## Conversation object

Same fields on both surfaces, except `assignedTo`, which only v1 returns.

```json
{
  "id": "CN123abc",
  "phoneNumberId": "PN123abc",
  "participants": ["+15555555555"],
  "name": null,
  "assignedTo": "US123abc",
  "lastActivityAt": "2026-10-01T15:04:05Z",
  "lastActivityId": "AC123abc",
  "mutedUntil": null,
  "snoozedUntil": null,
  "createdAt": "2026-09-01T00:00:00Z",
  "updatedAt": "2026-10-01T15:04:05Z",
  "deletedAt": null
}
```

| Field | Type | Notes |
|---|---|---|
| `id` | string `^CN` | |
| `phoneNumberId` | string `^PN` | your Quo number |
| `participants` | string[] | excludes your Quo number. Each is E.164, a 5–6 digit short code, or `Anonymous` / `Blocked` / `Restricted` — do not assume E.164 |
| `name` | string \| null | custom name, null when unset |
| `assignedTo` | `US…` \| `SYU…` \| null | **v1 only** |
| `lastActivityAt`, `lastActivityId` | date-time / `^AC` \| null | |
| `mutedUntil`, `snoozedUntil` | date-time \| null | read-only through the API |
| `createdAt`, `updatedAt`, `deletedAt` | date-time \| null | all nullable |

There is no `status`/`isDone`/`unread` field: mark-as-done/open/read change inbox state you cannot read back through this object.

## Conversations — 2026-03-30

Every request needs `Authorization: YOUR_API_KEY` and `Quo-Api-Version: 2026-03-30`.

### GET /conversations

Lists the organization's conversations, most recently created first by default.

| Query param | Type | Notes |
|---|---|---|
| `phoneNumberId` | string `^PN` | one Quo number. Matches your Quo number only, not participant numbers |
| `phoneNumberId[in]` | comma-separated `PN…` list, max 100 | any of several numbers |
| `createdAt[gte]`, `createdAt[lte]` | ISO 8601 date-time | inclusive bounds |
| `updatedAt[gte]`, `updatedAt[lte]` | ISO 8601 date-time | inclusive bounds — the sync filter |
| `sort` | `createdAt:asc` \| `createdAt:desc` \| `updatedAt:asc` \| `updatedAt:desc` | exactly one pair |
| `limit` | integer 1–50, default 10 | |
| `after` | string | `nextCursor` from the previous page |

Only `[gte]`/`[lte]` are declared for the time ranges (the schema is `additionalProperties: false`), so `[gt]`/`[lt]` are rejected here.

```bash
curl -sS -G "https://api.quo.com/conversations" \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
  --data-urlencode "phoneNumberId[in]=PN123abc,PN456def" \
  --data-urlencode "updatedAt[gte]=2026-10-01T00:00:00Z" \
  --data-urlencode "sort=updatedAt:asc" \
  --data-urlencode "limit=50"
```

```json
{ "data": [ { "id": "CN123abc", "phoneNumberId": "PN123abc", "participants": ["+15555555555"], "updatedAt": "2026-10-01T15:04:05Z", "...": "..." } ],
  "nextCursor": "eyJ..." }
```

Gotchas:
- **This is the only endpoint in the whole API that accepts `sort`.** Other list endpoints have a fixed order. A missing/unknown direction, an unsupported field, or two pairs (`sort=updatedAt:desc,createdAt:asc`) is a 400.
- `nextCursor: null` means the last page. There is no `totalItems`.
- Keep the same filters and `sort` on every page of one traversal; only `after` changes.

### POST /conversations/{conversationId}/mark-as-read

Clears the unread indicator without sending a message. No body. Returns `{ "data": <conversation> }`.

### POST /conversations/{conversationId}/mark-as-done

Removes the conversation from the inbox (Done) without sending a message. No body. Returns `{ "data": <conversation> }`.

### POST /conversations/{conversationId}/mark-as-open

Returns a done conversation to the inbox without sending a message. No body. Returns `{ "data": <conversation> }`.

```bash
curl -sS -X POST "https://api.quo.com/conversations/CN123abc/mark-as-done" \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30"
```

All three: path param `conversationId` (`^CN`), 200 on success, the response is wrapped in `data` (v1 returns it bare).

## Conversations — v1

No version header. Response bodies follow v1 conventions.

### GET /v1/conversations

Results come back in descending order of the most recent conversation. No sort parameter.

| Query param | Type | Notes |
|---|---|---|
| `phoneNumbers` | array, 1–100 items | each `PN…` **or** E.164. Repeat the key (OpenAPI default form/explode): `phoneNumbers=PN1&phoneNumbers=PN2` |
| `phoneNumber` | `PN…` or E.164 | **deprecated** — `phoneNumbers` wins if both sent |
| `userId` | string `^US` | applies that user's access scope: only conversations the user can access |
| `createdAfter`, `createdBefore` | ISO 8601 date-time | |
| `updatedAfter`, `updatedBefore` | ISO 8601 date-time | |
| `excludeInactive` | boolean | |
| `maxResults` | integer 1–100, default 10, **required** | always send it |
| `pageToken` | string | from `nextPageToken` |

```json
{ "data": [ { "id": "CN123abc", "assignedTo": "US123abc", "...": "..." } ],
  "totalItems": 1,
  "nextPageToken": null }
```

Gotchas:
- `totalItems` is documented as inaccurate. Paginate on `nextPageToken` until it is null.
- 403 here is titled **"Not Phone Number User"** (code `1001403`): the key's user is not a member of that Quo number.

### POST /v1/conversations/{conversationId}/mark-as-read · /mark-as-done · /mark-as-open

Same semantics as the 2026-03-30 versions. No body. 200 returns the **bare** conversation object (no `data` wrapper), including `assignedTo`.

## Incremental sync recipe

Use 2026-03-30 `GET /conversations` to mirror the inbox into your database:

1. Store a high-water mark `lastSyncedAt` per org (start with the epoch or a backfill date).
2. Request `updatedAt[gte]=<lastSyncedAt>&sort=updatedAt:asc&limit=50`, add `phoneNumberId[in]=...` if you only track some numbers.
3. Upsert each conversation by `id`. Treat a non-null `deletedAt` as a tombstone.
4. Follow `nextCursor` until it is `null`.
5. Set `lastSyncedAt` to the largest `updatedAt` you saw (not wall-clock "now", which would skip rows written during the run). Because `[gte]` is inclusive, the next run re-reads the boundary rows; upserts make that harmless.
6. Then pull new messages per changed conversation from the messages endpoints, using `lastActivityAt`/`lastActivityId` to skip unchanged threads.

Combine with message/call webhooks for near-real-time updates and keep the poll as the repair path for missed deliveries. Stay under 10 req/s: one page of 50 per request is the cheapest sweep.

## Task object

The two surfaces return different task shapes. The key differences are `status` vs two booleans and `revision` as integer vs string.

2026-03-30:

```json
{
  "taskId": "TK123abc",
  "orgId": "OR123abc",
  "title": "Call back about quote",
  "description": "Customer asked for pricing on 3 seats.",
  "dueDate": "2026-10-10T16:00:00Z",
  "status": "open",
  "assignedTo": "US123abc",
  "assignedBy": "US456def",
  "createdBy": "US456def",
  "createdAt": "2026-10-08T12:00:00Z",
  "phoneNumberId": "PN123abc",
  "conversationId": "CN123abc",
  "activityId": null,
  "phoneNumberGroupId": null,
  "revision": 3
}
```

| Field | 2026-03-30 | v1 |
|---|---|---|
| `taskId` | `^TK`, required | same |
| `orgId` | `^OR`, required | same |
| `title`, `description` | string \| null | same |
| `dueDate` | date-time \| null | same |
| state | **`status`: `open` \| `completed` \| `deleted`** | **`completed: boolean` + `isDeleted: boolean`** |
| `assignedTo`, `assignedBy` | `US…` \| `SYU…` \| null | same |
| `createdBy` | string (actor ID) | same |
| `createdAt` | date-time | same |
| `phoneNumberId`, `conversationId`, `activityId`, `phoneNumberGroupId` | nullable links | same |
| `revision` | **integer** | **string** |

On 2026-03-30 only `taskId`, `orgId`, `createdBy`, `createdAt`, `status`, `revision` are required in the schema — code defensively for missing optional keys. v1 marks every field required (nullable).

`revision` increases on every mutation and every mutation response returns it. Neither surface accepts a revision/`If-Match` precondition, so there is **no optimistic concurrency**: last write wins. If two writers can collide, re-read with `GET` and compare `revision` before and after your write to detect a concurrent change.

Assignment is single-valued in the object (`assignedTo`), even though the assign endpoints talk about adding a user.

## Tasks — 2026-03-30

Every request needs `Authorization` and `Quo-Api-Version: 2026-03-30`. Mutations return `{ "data": { "taskId": "TK123abc", "revision": 4 } }` — call `GET /tasks/{taskId}` to read the full task back.

| Method & path | Body | Success |
|---|---|---|
| `GET /tasks` | — | 200 `{data: Task[], nextCursor}` |
| `POST /tasks` | create body (below) | **201** `{data: {taskId, revision}}` |
| `GET /tasks/{taskId}` | — | 200 `{data: Task}` |
| `PATCH /tasks/{taskId}` | `{title, description}` both required | 200 |
| `DELETE /tasks/{taskId}` | — | **204**, empty |
| `PATCH /tasks/{taskId}/status` | `{status: "open" \| "completed" \| "deleted"}` | 200 |
| `POST /tasks/{taskId}/conversations` | `{conversationId}` | 200 (link) |
| `DELETE /tasks/{taskId}/conversations` | `{conversationId}` | 200 (unlink) |
| `POST /tasks/{taskId}/users` | `{userId}` (`^US`) | 200 (assign) |
| `DELETE /tasks/{taskId}/users` | `{userId}` (`^US`) | 200 (unassign) |
| `PATCH /tasks/{taskId}/due-date` | `{dueDate}` ISO 8601 | 200 |
| `DELETE /tasks/{taskId}/due-date` | — | 200 (clears due date) |

### GET /tasks

| Query param | Type | Notes |
|---|---|---|
| `limit` | integer **1–100, default 50** | differs from most 2026-03-30 lists (1–50, default 10) |
| `after` | string | `nextCursor` from the previous page |

No filters and no `sort`. To find overdue open tasks, page through and filter `status == "open" && dueDate < now` yourself, or subscribe to `task.overdue`.

### POST /tasks

| Field | Type | Required |
|---|---|---|
| `title` | string | yes |
| `description` | string | yes (send `""` if you have none) |
| `conversationId` | string `^CN` | **yes** |
| `dueDate` | ISO 8601 date-time | no |
| `assignedTo` | string `^US` | no |

```bash
curl -sS -X POST "https://api.quo.com/tasks" \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
  -H "Content-Type: application/json" \
  -d '{"title":"Call back about quote","description":"Pricing for 3 seats","conversationId":"CN123abc","dueDate":"2026-10-10T16:00:00Z","assignedTo":"US123abc"}'
# 201 {"data":{"taskId":"TK123abc","revision":1}}
```

Gotchas:
- A conversation link is **mandatory** here. To hang a task off a phone number or a single activity, use v1 `POST /v1/tasks`.
- `PATCH /tasks/{taskId}` is named "title and/or description", but the schema requires **both** fields. Re-send the current value of the one you are not changing.
- Unlink and unassign are `DELETE` requests **with a JSON body**. Some HTTP clients and proxies drop DELETE bodies — set `Content-Type: application/json` and verify your client sends it.
- `status: "deleted"` and `DELETE /tasks/{taskId}` both remove the task; the first returns the new `revision`, the second returns 204 with no body. Use `status: "open"` to reopen a completed task.

## Tasks — v1

No version header. Mutations return `{ "data": { "taskId": "TK123abc", "revision": "4" } }` (revision is a **string**).

| Method & path | Body | Success |
|---|---|---|
| `GET /v1/tasks` | — (query: `maxResults` 1–100 default 50 **required**, `pageToken`) | 200 `{data, totalItems, nextPageToken?}` |
| `POST /v1/tasks` | create body (below) | **201** |
| `GET /v1/tasks/{taskId}` | — | 200 `{data: Task}` |
| `PUT /v1/tasks/{taskId}` | `{title, description}` both required | 200 |
| `DELETE /v1/tasks/{taskId}` | — | **204**, empty |
| `POST /v1/tasks/{taskId}/complete` | — | 200 |
| `POST /v1/tasks/{taskId}/reopen` | — | 200 |
| `POST /v1/tasks/{taskId}/assign` | `{userId}` (`^US`) | 200 |
| `POST /v1/tasks/{taskId}/unassign` | `{userId}` (`^US`) | 200 |
| `POST /v1/tasks/{taskId}/link-conversation` | `{conversationId}` | 200 |
| `POST /v1/tasks/{taskId}/unlink-conversation` | `{conversationId}` | 200 |
| `POST /v1/tasks/{taskId}/change-due-date` | `{dueDate}` ISO 8601 | 200 |
| `POST /v1/tasks/{taskId}/remove-due-date` | — | 200 |

### POST /v1/tasks

The body is an `anyOf` of three shapes, each `additionalProperties: false`. Send `title`, `description` and **exactly one** of the link fields; unknown keys are rejected.

| Field | Type | Required |
|---|---|---|
| `title` | string | yes |
| `description` | string | yes |
| `phoneNumberId` \| `conversationId` \| `activityId` | `^PN` \| `^CN` \| `^AC` | exactly one |
| `dueDate` | ISO 8601 date-time | no |
| `assignedTo` | string `^US` | no |

```json
// 201
{ "data": { "taskId": "TK123abc", "revision": "1", "phoneNumberId": "PN123abc", "conversationId": "CN123abc" } }
```

The 201 always includes the resolved `phoneNumberId`, plus `conversationId`/`activityId` when applicable.

Gotchas:
- Every v1 task operation can return **402 "Open Tasks Limit Reached"** (code `0600402`): the organization has hit its cap on open tasks. Complete or delete tasks, don't retry.
- The assign/unassign/change-due-date bodies are `additionalProperties: false`; link/unlink bodies are not.
- To clear a due date, call `remove-due-date`; don't send `null` to `change-due-date`.

## Task webhooks

Task events are available on 2026-03-30 webhooks (`/webhooks`), not on the v1 webhook endpoints. Events: `task.created`, `task.updated` (title/description), `task.deleted`, `task.completed`, `task.reopened`, `task.assigned`, `task.unassigned`, `task.overdue`, `task.linked`, `task.unlinked`, `task.duedate.updated`, `task.duedate.removed`.

```json
{ "type": "task.overdue",
  "data": {
    "resource": { "id": "TK123", "dueDate": "2026-04-20T18:00:00.000Z" },
    "context": { "orgId": "OR123", "actorId": "US123", "phoneNumberId": "PN123",
                 "conversationId": "CN123", "activityId": "AC123", "phoneNumberGroupId": null },
    "links": { "quo": "https://my.quo.com/inbox/PN123/c/CN123?taskId=TK123" } } }
```

`task.overdue` fires when a task passes its due date without being completed; `context.actorId` is the task owner when the check ran. The payload is thin — `GET /tasks/{id}` for the rest. Fire a test event with `POST /webhooks/{webhookId}/events/test`. Signature verification is covered in the webhooks reference.

## Scheduling and reminders recipe

**Quo has no scheduled-send endpoint.** Neither spec has a send-at/schedule field: v1 `POST /v1/messages` takes only `content`, `from`, `to`, `userId`, `setInboxStatus` (plus deprecated `phoneNumberId`), and 2026-03-30 has no message-create endpoint at all. The webhook `MessageStatus` type lists a `scheduled` value, but no API operation creates a scheduled message. Build reminders in your app:

1. **Outbound reminder SMS — your job queue.** Store `{to, from, content, sendAt, idempotencyKey}` in your database. A worker (cron, BullMQ, Cloudflare Queues/Cron Triggers, a Railway cron service, etc.) picks due rows and calls `POST /v1/messages`. Mark the row sent only after the 202, and record the returned `AC…` id so a retry after a crash can check `GET /v1/messages/{id}` instead of double-sending. Re-check opt-out/quiet hours at send time, not at schedule time. Throttle the worker to stay under 10 req/s.
2. **Human follow-up — a Quo task.** For anything a person should do, `POST /tasks` with `conversationId` + `dueDate` + `assignedTo`. It shows in the assignee's Quo app with the due date.
3. **Escalation — `task.overdue`.** Subscribe a 2026-03-30 webhook to `task.overdue` and, on receipt, notify the owner, reassign (`POST /tasks/{id}/users`), or send the customer a nudge through your queue.
4. **Close the loop.** Sending with `setInboxStatus: "done"` keeps automated reminders from reopening the thread in the inbox. When the customer replies, the inbound-message webhook can mark the task `completed` via `PATCH /tasks/{id}/status`.

| Want | Use |
|---|---|
| Send a text at 9:00 tomorrow | your queue → `POST /v1/messages` at 9:00 |
| Remind a teammate to call back Friday | `POST /tasks` with `dueDate` + `assignedTo` |
| Alert when a follow-up slips | `task.overdue` webhook |
| Recurring reminders | your scheduler; Quo has no recurrence |

## Errors

2026-03-30 errors (structured, no numeric `code`):

```json
{ "title": "Bad Request", "message": "...", "docs": "https://...", "trace": "...",
  "errors": [ { "path": "/status", "message": "...", "value": "done", "schema": {} } ] }
```

Titles: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Unknown. A missing `Quo-Api-Version` header is a 400.

v1 errors carry the same fields plus `code` and `status`:

| Domain | 400 | 401 | 402 | 403 | 404 | 500 |
|---|---|---|---|---|---|---|
| Conversations | `1000400` | `1000401` | — | `1001403` "Not Phone Number User" | `1000404` | `1001500` |
| Tasks | `0600400` | `0600401` | `0600402` "Open Tasks Limit Reached" | `0600403` | `0600404` | `0601500` |

A missing or malformed `Authorization` header can be rejected at the gateway with a thinner shape, `{"error": {"message": "...", "key": "Unauthorized", "trace": "..."}}`. Handle both shapes.

## v1 → 2026-03-30 migration

| Concern | v1 | 2026-03-30 |
|---|---|---|
| Path | `/v1/conversations`, `/v1/tasks` | `/conversations`, `/tasks` |
| Header | none | `Quo-Api-Version: 2026-03-30` |
| Page size | `maxResults` (required) | `limit` (conversations 1–50/10, tasks 1–100/50) |
| Cursor | `pageToken` / `nextPageToken`, plus unreliable `totalItems` | `after` / `nextCursor`, no total |
| Conversation number filter | `phoneNumbers` (`PN…` or E.164), deprecated `phoneNumber` | `phoneNumberId` / `phoneNumberId[in]` (`PN…` only) |
| Time filters | `createdAfter`/`createdBefore`, `updatedAfter`/`updatedBefore` | `createdAt[gte\|lte]`, `updatedAt[gte\|lte]` |
| `userId`, `excludeInactive` filters | supported | removed |
| Conversation `assignedTo` | present | removed |
| Sort | fixed | `sort=createdAt\|updatedAt:asc\|desc` |
| Single-conversation responses | bare object | wrapped in `data` |
| Task state | `completed` + `isDeleted` booleans | `status` enum `open\|completed\|deleted` |
| `revision` | string | integer |
| Create task links | one of `phoneNumberId` / `conversationId` / `activityId` | `conversationId` only |
| Create task response | `{taskId, revision, phoneNumberId, conversationId?, activityId?}` | `{taskId, revision}` |
| Update title/description | `PUT /v1/tasks/{id}` | `PATCH /tasks/{id}` (still both fields) |
| Complete / reopen | `POST .../complete`, `POST .../reopen` | `PATCH /tasks/{id}/status` |
| Assign / unassign | `POST .../assign`, `POST .../unassign` | `POST` / `DELETE /tasks/{id}/users` |
| Link / unlink conversation | `POST .../link-conversation`, `.../unlink-conversation` | `POST` / `DELETE /tasks/{id}/conversations` |
| Set / clear due date | `POST .../change-due-date`, `.../remove-due-date` | `PATCH` / `DELETE /tasks/{id}/due-date` |
| Error body | includes `code`, `status` | `title`, `message`, `docs`, `trace`, `errors[]` |

## Sources (checked 2026-10-08)

- OpenAPI: `openphone-public-api-v1-prod.json`, `openphone-public-api-2026-03-30-prod.json` (authoritative)
- v1 docs: api-reference/conversations (list-conversations, mark-conversation-as-read, -done, -open); api-reference/tasks (list-tasks, create-a-task, gets-a-task-by-id, update-a-task, delete-a-task-by-id, complete-a-task, reopen-a-task, assign-a-user-to-a-task, unassign-a-user-from-a-task, link-a-task-to-a-conversation, unlink-a-task-from-a-conversation, change-a-tasks-due-date, remove-a-tasks-due-date)
- 2026-03-30 docs: conversations/* (list, mark-as-read, -done, -open); tasks/* (list, create, get, update, delete, update-the-status, link, unlink, assign, unassign, update-the-due-date, delete-the-due-date); sorting-and-filtering; webhooks-event-payloads; mcp/tools
- changelog (2026-06-16 mark done/open; 2026-07-09 task webhook events; 2026-08-27 task endpoints on 2026-03-30; 2026-09-29 conversation discovery and sync)
