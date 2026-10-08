# Quo (formerly OpenPhone) API — Contacts

Contacts are the address book of a Quo workspace: a name/company/role record plus phone numbers, emails and workspace-defined fields, optionally linked to a record in your own system through `externalId`. Quo exposes contacts on **two live API surfaces** on the same host, `https://api.quo.com`. The two surfaces use different shapes and different update semantics:

| | v1 | 2026-03-30 |
|---|---|---|
| Paths | `/v1/contacts...` | `/contacts...` (no prefix) |
| Version header | none | **`Quo-Api-Version: 2026-03-30` required** (400 without it) |
| Contact shape | nested `defaultFields` + `customFields[]`, with emails/phones inline | flat `firstName`/`lastName`/`company`/`role`; phones, emails and custom values are separate **properties** |
| Pagination | `maxResults` (1–50, **required**) + `pageToken` → `nextPageToken`, `totalItems` | `limit` (1–50, default 10) + `after` → `nextCursor` |
| Errors | `{message, code, status, docs, title, trace?, errors[]}` with `08xxxxx` codes | `{title, message, docs, trace?, errors[{path,message,value,schema}]}` |

Auth on both surfaces is the **raw API key** in `Authorization` (no `Bearer`). The rate limit is 10 requests per second per key; 429 means back off and retry.

```bash
# v1
curl -H "Authorization: $QUO_API_KEY" "https://api.quo.com/v1/contacts?maxResults=10"
# 2026-03-30
curl -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" "https://api.quo.com/contacts?limit=10"
```

## Contents

- [Which surface to use](#which-surface-to-use)
- [Identifiers and source metadata](#identifiers-and-source-metadata)
- [2026-03-30 endpoints](#2026-03-30-endpoints): contacts · shares · notes · properties
- [v1 endpoints](#v1-endpoints): contacts · contact-custom-fields
- [Contact sync / upsert recipe](#contact-sync--upsert-recipe)
- [v1 → 2026-03-30 migration diffs](#v1--2026-03-30-migration-diffs)
- [Errors](#errors)
- [Sources](#sources-checked-2026-10-08)

---

## Which surface to use

| Need | Use | Why |
|---|---|---|
| Find a contact by your own ID | **2026** `GET /contacts?externalId=...` | Scalar or `[in]` filter; v1 `externalIds` also works |
| Create a contact (name/company/role) | **2026** `POST /contacts` | Flat body, no nesting |
| Change name/company/role/externalId/source | **2026** `PATCH /contacts/{contactId}` | Body has only scalar fields, so it cannot wipe phones/emails |
| Add/change/remove **one** phone, email or custom value | **2026** `/contacts/{contactId}/properties` | Per-item CRUD; no full-replace risk |
| Create a contact *with* phones/emails/custom fields in one call | v1 `POST /v1/contacts` | 2026 create has no phone/email fields (add them as properties after) |
| Read workspace custom-field **definitions** (key, type) | **v1 only** `GET /v1/contact-custom-fields` | No 2026 equivalent |
| Read a contact with phones/emails/custom fields inline in one call | v1 `GET /v1/contacts/{id}` | 2026 contact has no inline phones/emails; list its properties instead |
| Who a contact is shared with | **2026 only** `GET /contacts/{contactId}/shares` | |
| Contact notes (CRUD, @mentions) | **2026 only** `/contacts/{contactId}/notes` | |
| Delete a contact | either | Both return 204 |

Recommendation: default to 2026-03-30. Fall back to v1 only for custom-field definitions and single-call creates that include phones, emails and custom fields. **Never** use v1 `PATCH` for a partial change (see [v1 PATCH](#patch-v1contactsid--replaces-arrays)).

Contacts created by a **native integration** (CRM sync etc.) are read-only in Quo: "Any changes must be made in the source system and synced back to Quo." The MCP docs state the same for updates ("Contacts created by an integration cannot be updated — use get-contact to check a contact's source"). Read `source` before you write.

## Identifiers and source metadata

| ID / field | Format | Notes |
|---|---|---|
| contact `id` | opaque, e.g. `6a145ff26212a192852c856e` (no prefix) | Path param for get/patch/delete. **Not** your `externalId`. Save it when you create the contact. |
| user / actor | `US...` | `createdByUserId` (v1), `actorId` (2026; may also be system user `SYU...`) |
| share target | `US...` user, `GR...` group, `OR...` organization | `sharedWith` in shares |
| note / property `id` | opaque | |
| `externalId` | string, 1–75 chars (v1 constraint) | Your system's ID. In v1 it is "required for retrieving the contact later via the List Contacts endpoint". Keep it unique. |
| `source` | string, 1–72 chars on v1 create (75 on v1 patch/response) | v1 create defaults to `public-api` (UI-created contacts: `null`). **Reserved:** cannot be `openphone`, `device`, `csv`, `zapier`, `google-people`, `other`, nor start with `openphone` or `csv`. Use your own label, e.g. `acme-crm`. |
| `sourceUrl` | URI, 1–200 chars | Deep link back to the record in your system. |

An API-created contact appears in the Quo app (contact list, search, conversation list) **only once a conversation exists with a matching phone number**. Normalize phones to E.164 (`+15555550100`) before writing.

---

## 2026-03-30 endpoints

Every request in this section needs `Authorization: <key>` and `Quo-Api-Version: 2026-03-30`. List responses are `{ "data": [...], "nextCursor": "..." | null }`; pass `nextCursor` back as `after`.

### Contact object (2026)

```jsonc
{
  "id": "6a145ff26212a192852c856e",
  "externalId": "crm-001",            // string|null
  "source": "acme-crm",               // string|null
  "sourceUrl": "https://crm.example.com/contacts/001", // uri|null, ≤200
  "firstName": "John",                // string|null
  "lastName": "Doe",
  "company": "Quo",
  "role": "admin",
  "createdAt": "2026-01-01T00:00:00Z",
  "updatedAt": "2026-01-01T00:00:00Z",
  "actorId": "US123abc"               // ^US… or ^SYU…
}
```

Required in responses: `id`, `createdAt`, `updatedAt`, `actorId`. There are **no** `emails`, `phoneNumbers` or `customFields` here; use [properties](#properties).

### GET /contacts — list contacts

| Query | Type | Notes |
|---|---|---|
| `externalId` | string, or `externalId[in]=a,b` | Exact match; `[in]` = any of ≤50 comma-separated values |
| `source` | string, or `source[in]=a,b` | Same shape; ≤50 values |
| `limit` | int 1–50, default 10 | |
| `after` | string | cursor from `nextCursor` |

Filters on different fields combine with AND. Values inside one `[in]` combine with OR. There is no `sort` parameter on this endpoint.

```bash
curl -G https://api.quo.com/contacts \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" \
  --data-urlencode "externalId[in]=crm-001,crm-002" --data-urlencode "limit=50"
```

```json
{ "data": [ { "id": "6a14…", "externalId": "crm-001", "firstName": "John", "...": "..." } ],
  "nextCursor": null }
```

Gotchas: there is no phone-number or name filter. To find a contact by phone you need your own mapping or a full scan. An unsupported operator returns 400.

### POST /contacts — create (201)

| Body | Type | Notes |
|---|---|---|
| `firstName` | string | **required** |
| `lastName`, `company`, `role` | string\|null | |
| `externalId` | string\|null | set this for every synced contact |
| `source` | string\|null | the spec gives no default; set it explicitly |
| `sourceUrl` | uri\|null, 1–200 | |
| `actorId` | `^US…`\|null | user to attribute creation to; defaults to the org owner |

```jsonc
// request
{ "firstName": "Alice", "lastName": "Johnson", "company": "Acme Corp", "role": "CEO",
  "externalId": "crm-001", "source": "acme-crm", "sourceUrl": "https://crm.example.com/contacts/001" }
// 201
{ "data": { "id": "6a145ff26212a192852c856e", "firstName": "Alice", "externalId": "crm-001", "...": "..." } }
```

Gotchas: the body has no phone or email field. Create the contact, then `POST /contacts/{id}/properties` once for each phone or email. The spec defines no uniqueness rule for `externalId` and no 409 response. Look the contact up by `externalId` first to avoid duplicates.

### GET /contacts/{contactId} — get (200)

Returns `{ "data": <contact> }`, or 404 if the ID is unknown or belongs to another workspace.

### PATCH /contacts/{contactId} — update (200)

Body (all optional, each `string|null`): `firstName`, `lastName`, `company`, `role`, `externalId`, `source`, `sourceUrl`. Returns `{ "data": <contact> }`.

Semantics: the body only carries scalar fields, so a 2026 PATCH **cannot** delete phones, emails or custom values. Those live in properties. The REST spec does not say what happens to an omitted scalar. The MCP `update-contact` tool documents "omit a field to leave it unchanged; pass `null` to clear it", which is consistent with merge behaviour. Send only the fields you are changing, and send explicit `null` only when you mean to clear a field. Integration-sourced contacts are rejected.

### DELETE /contacts/{contactId} — delete (204, empty body)

---

### Shares

#### GET /contacts/{contactId}/shares

Query: `limit` 1–50 (default 10), `after`. The response is read-only, and there is no endpoint to create or delete a share.

```json
{ "data": [ { "contactId": "6a14…", "sharedWith": "GRabc123", "createdAt": "2026-01-01T00:00:00Z" } ],
  "nextCursor": null }
```

`sharedWith` is a user (`US…`), group (`GR…`) or organization (`OR…`) ID.

---

### Notes

Internal notes attached to a contact. Adding or editing a note **sends nothing to the contact**.

Note object: `{ id, text, media: [{ url, type|null, name|null }], createdAt, updatedAt, actorId: "US…" }`. The `media` array holds attachment URLs; the API cannot upload attachments.

| Method & path | Body | Success |
|---|---|---|
| `GET /contacts/{contactId}/notes` | query `limit` 1–50 (default 10), `after` | 200 `{data[], nextCursor}` |
| `POST /contacts/{contactId}/notes` | `{ "text": string 1–2000 }` (required) | **200** (not 201) `{data: note}` |
| `GET /contacts/{contactId}/notes/{noteId}` | — | 200 |
| `PATCH /contacts/{contactId}/notes/{noteId}` | `{ "text": string 1–2000 }` (required) | 200 |
| `DELETE /contacts/{contactId}/notes/{noteId}` | — | 204 |

```jsonc
// POST body — mention a teammate with @ + their ID
{ "text": "Called today, wants a quote by Friday. @USabc123 please follow up." }
```

Gotchas:
- **Mentions:** `@US…` (user), `@GR…` (group) and `@OR…` (organization) tags in `text` are detected and resolved automatically. Get user IDs from the users endpoint.
- **PATCH replaces the whole text.** To append, GET the note and send the old text plus the new text, staying within 2000 characters.
- `actorId` on a note is always a user (`US…`).

---

### Properties

Per-contact typed values: phone numbers, emails and custom-field-style data. **This is how the 2026 surface represents what v1 nests in `defaultFields.phoneNumbers`, `defaultFields.emails` and `customFields`.** Each item is its own resource with an `id`, so you add, edit or remove exactly one value at a time.

Property object:

```json
{ "id": "…", "type": "phone-number", "name": "Mobile", "value": "+15555550100",
  "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-01-01T00:00:00Z" }
```

- `type` (string, required on create). The spec gives **no enum**; its examples are `phone-number`, `email`, `string`, `date`, `boolean` and `number`. v1 custom-field types (`address`, `multi-select`, `url`) are probably valid too, but the spec does not list them. Read the existing `type` values before you write a new kind.
- `name` (string|null) is the label, e.g. `Mobile`, `Work`, or a custom field's display name.
- `value` is one of: string · boolean · number · string[] (e.g. multi-select) · string[][] · object.

| Method & path | Params / body | Success |
|---|---|---|
| `GET /contacts/{contactId}/properties` | query `limit` 1–50 (default 10), `after`, `type` (filter, e.g. `type=email`) | 200 `{data[], nextCursor}` |
| `POST /contacts/{contactId}/properties` | `{ type*, name?, value* }` | **200** `{data: property}` |
| `GET /contacts/{contactId}/properties/{propertyId}` | — | 200 |
| `PATCH /contacts/{contactId}/properties/{propertyId}` | `{ name?, value? }`; **`type` is immutable** | 200 |
| `DELETE /contacts/{contactId}/properties/{propertyId}` | — | 204 |

```bash
curl -X POST https://api.quo.com/contacts/6a14…/properties \
  -H "Authorization: $QUO_API_KEY" -H "Quo-Api-Version: 2026-03-30" -H "Content-Type: application/json" \
  -d '{"type":"phone-number","name":"Mobile","value":"+15555550100"}'
```

Relationship to v1 custom fields: v1 references a custom value by the workspace definition's `key`. A 2026 property carries only `type` and `name`, and the spec documents no `key` and no link to `GET /v1/contact-custom-fields`. Neither surface can create custom-field **definitions** ("can only be modified within the Quo app"). Whether creating a property with a custom field's `name` binds to that definition is not documented. To guarantee a value lands on an existing workspace custom field, write it through v1 with `key` (and use the full-replace body, see below), or verify the binding with one live GET before relying on it.

To change a type, DELETE the property and POST a new one.

---

## v1 endpoints

No version header. Errors use the `08xxxxx` code family (`07xxxxx` for custom fields).

### v1 contact object

```json
{
  "id": "664d0db69fcac7cf2e6ec",
  "externalId": "crm-001", "source": "public-api", "sourceUrl": "https://crm.example.com/c/001",
  "defaultFields": {
    "firstName": "John", "lastName": "Doe", "company": "Quo", "role": "Sales",
    "emails":       [ { "id": "acb123", "name": "work",   "value": "abc@example.com" } ],
    "phoneNumbers": [ { "id": "acb124", "name": "mobile", "value": "+12345678901" } ]
  },
  "customFields": [
    { "id": "66d0…", "key": "inbound-lead", "name": "Inbound Lead", "type": "string", "value": "123 Main St" }
  ],
  "createdAt": "2022-01-01T00:00:00Z", "updatedAt": "2022-01-01T00:00:00Z",
  "createdByUserId": "US123abc"
}
```

Custom field `type` is one of `address`, `boolean`, `date`, `multi-select`, `number`, `string` or `url`. `value` matches the type: string for address/string/url, boolean, an ISO date-time string for date, number, string[] for multi-select. Any value may be `null`.

### POST /v1/contacts — create (201)

| Body | Type | Notes |
|---|---|---|
| `defaultFields` | object | **required** |
| `defaultFields.firstName` | string\|null | **required key** |
| `defaultFields.lastName`, `company`, `role` | string\|null | |
| `defaultFields.emails[]` | `{ name*, value*: string\|null }` | |
| `defaultFields.phoneNumbers[]` | `{ name*, value*: string\|null }` | E.164 |
| `customFields[]` | `{ key, value }` | reference by definition `key` |
| `createdByUserId` | `^US…` | |
| `source` | string 1–72, default `public-api` | reserved words/prefixes rejected |
| `sourceUrl` | uri 1–200 | |
| `externalId` | string\|null 1–75 | |

```bash
curl -X POST https://api.quo.com/v1/contacts \
  -H "Authorization: $QUO_API_KEY" -H "Content-Type: application/json" \
  -d '{"defaultFields":{"firstName":"John","lastName":"Doe",
        "phoneNumbers":[{"name":"mobile","value":"+12345678901"}],
        "emails":[{"name":"work","value":"john@example.com"}]},
       "customFields":[{"key":"inbound-lead","value":"123 Main St"}],
       "source":"acme-crm","externalId":"crm-001"}'
```

Gotchas: everything nests under `defaultFields`; there is no root-level `firstName`. `customFields` is an **array** of `{key, value}`. The "External contacts" guide shows an object; that is wrong, so follow the spec. An invalid custom field returns 400 `0801400` "Invalid Custom Field Item".

### GET /v1/contacts — list

| Query | Type | Notes |
|---|---|---|
| `externalIds` | string[] (each 1–75) | repeat the key: `externalIds=a&externalIds=b` |
| `sources` | string[] | repeat the key |
| `maxResults` | int 1–50, default 10 | **marked required** |
| `pageToken` | string | from `nextPageToken` |

Response: `{ data: [contact], totalItems, nextPageToken|null }`. ⚠️ The spec itself warns that `totalItems` "is not accurately returning the total number of items". Loop on `nextPageToken` instead. With no filters, the endpoint returns every contact in the org.

### GET /v1/contacts/{id} — get (200)

Returns `{ data: contact }` with phones, emails and custom fields inline. Unknown ID → 404 `0800404`.

### PATCH /v1/contacts/{id} — REPLACES arrays

The spec's own description: "This endpoint replaces the contact rather than merging into it: any `defaultFields.emails`, `defaultFields.phoneNumbers` or `customFields` you omit from the request body is deleted on the contact. Always send the full set of fields, emails, and phone numbers you want the contact to have, not just the ones you're changing."

Body (all optional): `externalId`, `source` (≤75), `sourceUrl`, `defaultFields{firstName,lastName,company,role,emails[],phoneNumbers[]}`, `customFields[]`. Email and phone items are `{ id?, name*, value* }`. Custom items are `{ key? | id?, value }`, so on PATCH you may reference a custom item by `id` as well as `key`.

- Omitting `emails` deletes **all** emails. The same applies to `phoneNumbers` and to `customFields`.
- An item with `value: null` removes that one item.
- Safe pattern: **GET → modify in memory → PATCH the complete object** (keep item `id`s so they are updated in place rather than recreated).

```bash
# WRONG — silently deletes every email, phone and custom value:
curl -X PATCH https://api.quo.com/v1/contacts/664d… -H "Authorization: $QUO_API_KEY" \
  -H "Content-Type: application/json" -d '{"defaultFields":{"role":"VP Sales"}}'
# RIGHT on 2026 for a scalar change:
curl -X PATCH https://api.quo.com/contacts/664d… -H "Authorization: $QUO_API_KEY" \
  -H "Quo-Api-Version: 2026-03-30" -H "Content-Type: application/json" -d '{"role":"VP Sales"}'
```

The official Google-Sheets sync guide's `mapFields()` PATCHes `defaultFields` with no `customFields` and with `emails: undefined` when a cell is blank. Under replace semantics that **wipes** custom values and existing emails. Do not copy it as-is.

### DELETE /v1/contacts/{id} — 204, empty body

### GET /v1/contact-custom-fields — workspace definitions (v1 only)

No parameters. Response: `{ data: [ { name, key, type } ] }`, where `type` is one of the 7 types above. The endpoint is read-only: definitions are created and edited only in the Quo app. Call it before writing custom values so you send valid `key`s with correctly typed values. Errors use the `07xxxxx` codes.

---

## Contact sync / upsert recipe

Goal: mirror records from your system (CRM, sheet, DB) into Quo **idempotently and without destroying data**. Key each record on `externalId`, set your own `source` label, and never send a partial v1 PATCH.

```ts
const BASE = "https://api.quo.com";
const H = { Authorization: process.env.QUO_API_KEY!, "Quo-Api-Version": "2026-03-30",
            "Content-Type": "application/json" };            // raw key, no "Bearer"

async function quo(method: string, path: string, body?: unknown) {
  for (let attempt = 0; ; attempt++) {
    const r = await fetch(BASE + path, { method, headers: H, body: body && JSON.stringify(body) });
    if (r.status === 429 || r.status >= 500) {             // retryable
      if (attempt < 4) { await new Promise(s => setTimeout(s, 250 * 2 ** attempt)); continue; }
    }
    if (!r.ok) throw new Error(`${method} ${path} ${r.status} ${await r.text()}`);
    return r.status === 204 ? null : (await r.json()).data;
  }
}

async function upsertContact(rec: { id: string; first: string; last?: string;
                                    company?: string; phone?: string; email?: string }) {
  const q = new URLSearchParams({ externalId: rec.id, limit: "1" });
  const [existing] = await quo("GET", `/contacts?${q}`);
  const fields = { firstName: rec.first, lastName: rec.last ?? null, company: rec.company ?? null };

  if (!existing) {                                          // CREATE
    const c = await quo("POST", "/contacts",
      { ...fields, externalId: rec.id, source: "acme-crm" });
    if (rec.phone) await quo("POST", `/contacts/${c.id}/properties`,
      { type: "phone-number", name: "Mobile", value: rec.phone });     // E.164
    if (rec.email) await quo("POST", `/contacts/${c.id}/properties`,
      { type: "email", name: "Work", value: rec.email });
    return c;
  }
  if (existing.source && existing.source !== "acme-crm") return existing; // not ours / integration-owned
  const c = await quo("PATCH", `/contacts/${existing.id}`, fields);      // scalars only — safe
  await syncProp(existing.id, "phone-number", "Mobile", rec.phone);
  await syncProp(existing.id, "email", "Work", rec.email);
  return c;
}

// Add/update/remove exactly one typed value; never touches other properties.
async function syncProp(contactId: string, type: string, name: string, value?: string) {
  const props = await quo("GET", `/contacts/${contactId}/properties?type=${type}&limit=50`);
  const p = props.find((x: any) => x.name === name);
  if (!value) return p && quo("DELETE", `/contacts/${contactId}/properties/${p.id}`);
  if (!p) return quo("POST", `/contacts/${contactId}/properties`, { type, name, value });
  if (p.value !== value) return quo("PATCH", `/contacts/${contactId}/properties/${p.id}`, { value });
}
```

Rules for agents and tool-calling (e.g. TanStack AI tool definitions):

1. **Look up before you create.** Use `GET /contacts?externalId=X`; for batches, `externalId[in]=a,b,…` (≤50 per call). Neither surface rejects duplicate `externalId`s, so creating blind produces duplicates.
2. **Persist the mapping** `externalId ↔ Quo id` locally so you don't need a lookup on every run.
3. **Only touch contacts you own.** Skip a contact when its `source` isn't your label, and never write to integration-sourced contacts.
4. **Prefer per-property writes** over v1 PATCH. If you must use v1 (for example to set a value by custom-field `key`), GET the full contact, merge your change, and PATCH the **complete** `defaultFields.emails`, `phoneNumbers` and `customFields`.
5. **Expose narrow tools**, e.g. `find_contact_by_external_id`, `create_contact`, `update_contact_fields` (2026 PATCH), `set_contact_property` and `add_contact_note`, instead of a generic "update contact" that maps to v1 PATCH. An LLM filling a v1 PATCH from partial intent deletes data.
6. **Paginate** with `after`/`nextCursor` (2026) or `pageToken`/`nextPageToken` (v1). Stay under 10 req/s and retry 429/5xx with backoff.
7. **Deletes are permanent.** Only delete contacts whose `source` is yours and whose source record is gone.
8. Phones go in E.164. An API contact is invisible in the app until a conversation exists with that number.

---

## v1 → 2026-03-30 migration diffs

| v1 | 2026-03-30 |
|---|---|
| `/v1/contacts`, `/v1/contacts/{id}` | `/contacts`, `/contacts/{contactId}` + header `Quo-Api-Version: 2026-03-30` |
| `defaultFields.firstName` etc. (nested) | `firstName`, `lastName`, `company`, `role` at the top level |
| `defaultFields.phoneNumbers[] / emails[]` | properties with `type: "phone-number"` / `"email"` |
| `customFields[{key, value}]` | properties `{type, name, value}`; no `key` |
| `createdByUserId` (`US…`) | `actorId` (`US…` or system `SYU…`); on create, `actorId` defaults to the org owner |
| `externalIds=a&externalIds=b`, `sources=…` | `externalId=a` or `externalId[in]=a,b`; `source` / `source[in]` |
| `maxResults` (required), `pageToken` | `limit` (optional, default 10), `after` |
| `{data, totalItems, nextPageToken}` | `{data, nextCursor}` (no `totalItems`) |
| PATCH replaces arrays; omission deletes | PATCH scalars only; arrays are managed per property |
| `GET /v1/contact-custom-fields` | **none**; keep using v1 |
| — | shares, notes, properties (2026 only) |
| Create defaults `source` to `public-api` | no documented default; set it |
| Errors: `code` like `0800404` | Errors: `title`/`message`/`errors[].path`; branch on HTTP status |

Webhooks: `contact.updated` (fires on create too) and `contact.deleted` exist on the 2026 webhook API. See the webhooks reference.

## Errors

**2026-03-30:** `{ title, message, docs, trace?, errors?: [{ path, message, value, schema }] }`. Branch on HTTP status first, then on `errors[].path` (e.g. `/query/limit`). Statuses: 400 malformed (incl. missing version header or a bad filter operator), 401 bad key, 403 key valid but action not allowed (permissions or a workspace setting), 404 unknown or other-workspace ID, 422 semantically invalid, 429 rate-limited (retry), 500 (retry; quote `trace`).

**v1 contacts:** 400 `0801400` Invalid Custom Field Item · 401 `0800401` · 403 `0801403` Not Phone Number User · 404 `0800404` · 409 `0800409` Conflict · 500 `0801500`. **v1 contact-custom-fields:** `0700400`, `0700401`, `0700403`, `0700404`, `0701500`.

## Sources (checked 2026-10-08)

- OpenAPI: `openphone-public-api-2026-03-30-prod.json` (paths `/contacts*`), `openphone-public-api-v1-prod.json` (paths `/v1/contacts*`, `/v1/contact-custom-fields`). The spec wins where prose disagrees.
- 2026-03-30 pages: `contacts/{list-contacts, create-a-contact, get-a-contact-by-id, update-a-contact-by-id, delete-a-contact}`, `contact-shares/list-contact-shares`, `contact-notes/*`, `contact-properties/*`, `sorting-and-filtering`, `errors`, `mcp/tools` (Contacts, Contact notes), `changelog` (2026-09-28 contact management; 2026-09-28 filter conventions; 2026-10-01 MCP notes).
- v1 pages: `mdx/api-reference/contacts/*`, `mdx/api-reference/contact-custom-fields/get-contact-custom-fields`, `mdx/guides/contacts` (External contacts), `mdx/guides/sync-contacts`.
