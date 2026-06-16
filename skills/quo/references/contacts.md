## Quo (formerly OpenPhone) API — Contacts

> All facts below are quoted verbatim from the live Quo docs (`https://www.quo.com/docs/mdx/...`) and the authoritative OpenAPI spec (`openphone-public-api-v1-prod.json`). Do not trust training data for this API — Quo rebranded from OpenPhone and field/host details changed.

### Base URL & Authentication (CRITICAL — read first)

- **Base URL (per live spec + guide):** `https://api.quo.com/v1`
  - The OpenAPI `servers[0].url` is `https://api.quo.com` (Production server); the official Sync guide hard-codes `const API_BASE_URL = "https://api.quo.com/v1"`.
  - ⚠️ **Host note:** The canonical, currently-documented host is `https://api.quo.com/v1` (OpenAPI `servers` = `https://api.quo.com`). `https://api.openphone.com/v1` is a live legacy alias serving the same API. Use either; prefer `api.quo.com`.
- **Auth scheme (confirmed):** RAW API key in the `Authorization` header — **NOT** `Bearer`.
  - OpenAPI `components.securitySchemes.apiKey` = `{ "in": "header", "name": "Authorization", "type": "apiKey" }`, applied globally via `security: [{ apiKey: [] }]`.
  - The Sync guide sets the header literally: `headers: { Authorization: process.env.QUO_API_KEY, "Content-Type": "application/json" }` — no `Bearer ` prefix.

```bash
# Canonical auth header — RAW key, no "Bearer"
curl -H "Authorization: YOUR_API_KEY" -H "Content-Type: application/json" \
  https://api.quo.com/v1/contacts?maxResults=10
```

### Contact data model (verbatim field structure)

A contact splits into three top-level concerns plus metadata:

- **`defaultFields`** (object) — predefined fields present on every contact: `firstName`, `lastName`, `role`, `company`, `emails[]`, `phoneNumbers[]`. (Guide: "Every contact in Quo includes these predefined fields: First Name, Last Name, Role, Company, Emails, Phone Numbers".)
  - `emails[]` and `phoneNumbers[]` items are objects with **required** `name` and `value`. Responses additionally include a server-assigned `id` per email/phone item.
- **`customFields`** (array) — user-defined fields. Supported `type` values: `address`, `boolean`, `date`, `multi-select`, `number`, `string`, `url`.
  - **Reference a custom field by `key`** (its identifying handle, e.g. `inbound-lead`) when writing. Responses also echo `name` (human label, e.g. `Inbound Lead`), `id`, and `type`.
  - **Custom field *definitions* can only be created/edited inside the Quo app — the API cannot create or modify custom field definitions**, only set their values on a contact.
- **Identity / source metadata:** `externalId`, `source`, `sourceUrl`, plus read-only `id`, `createdAt`, `updatedAt`, `createdByUserId`.

`externalId` / `source` / `sourceUrl` semantics:
- **`externalId`** — "A unique identifier from an external system that can optionally be supplied when creating a contact... **required for retrieving the contact later via the 'List Contacts' endpoint**. Ensure the `externalId` is unique and consistent across systems." (`minLength:1`, `maxLength:75`).
- **`source`** — "how the contact was created or where it originated from." On create: **defaults to `public-api`** (defaults to `null` for UI-created contacts). **Cannot be one of the reserved words** `openphone`, `device`, `csv`, `zapier`, `google-people`, `other`, and **cannot start with reserved prefixes** `openphone`, `csv`. (`minLength:1`, `maxLength:72`.)
- **`sourceUrl`** — "A link to the contact in the source system" (`format: uri`, `maxLength:200`).

---

### Create a contact
Source: https://www.quo.com/docs/mdx/api-reference/contacts/create-a-contact.md

`POST https://api.quo.com/v1/contacts`

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `defaultFields` | body | object | **yes** | The only top-level required property. |
| `defaultFields.firstName` | body | string \| null | **yes** | Only required field inside `defaultFields`. |
| `defaultFields.lastName` | body | string \| null | no | |
| `defaultFields.company` | body | string \| null | no | |
| `defaultFields.role` | body | string \| null | no | |
| `defaultFields.emails` | body | array | no | Each item requires `name` + `value`. |
| `defaultFields.phoneNumbers` | body | array | no | Each item requires `name` + `value`; value should be E.164 (`+12345678901`). |
| `customFields` | body | array | no | Each item: `{ key, value }`. Reference field by `key`. |
| `source` | body | string | no | Defaults to `public-api`. Reserved words/prefixes rejected (see above). `maxLength:72`. |
| `sourceUrl` | body | string (uri) | no | `maxLength:200`. |
| `externalId` | body | string \| null | no | `maxLength:75`. Needed to fetch via List Contacts later. |
| `createdByUserId` | body | string | no | Pattern `^US(.*)$`, e.g. `US123abc`. |

Request body:
```json
{
  "defaultFields": {
    "company": "Quo",
    "emails": [
      { "name": "company email", "value": "abc@example.com" }
    ],
    "firstName": "John",
    "lastName": "Doe",
    "phoneNumbers": [
      { "name": "company phone", "value": "+12345678901" }
    ],
    "role": "Sales"
  },
  "customFields": [
    { "key": "inbound-lead", "value": "123 Main St" }
  ],
  "createdByUserId": "US123abc",
  "source": "public-api",
  "sourceUrl": "https://openphone.co/contacts/664d0db69fcac7cf2e6ec",
  "externalId": "664d0db69fcac7cf2e6ec"
}
```

Response `201 Success`:
```json
{
  "data": {
    "id": "664d0db69fcac7cf2e6ec",
    "externalId": "664d0db69fcac7cf2e6ec",
    "source": "public-api",
    "sourceUrl": "https://openphone.co/contacts/664d0db69fcac7cf2e6ec",
    "defaultFields": {
      "company": "Quo",
      "emails": [
        { "name": "company email", "value": "abc@example.com", "id": "acb123" }
      ],
      "firstName": "John",
      "lastName": "Doe",
      "phoneNumbers": [
        { "name": "company phone", "value": "+12345678901", "id": "acb123" }
      ],
      "role": "Sales"
    },
    "customFields": [
      {
        "name": "Inbound Lead",
        "key": "inbound-lead",
        "id": "66d0d87d534de8fd1c433cec3",
        "type": "string",
        "value": "123 Main St"
      }
    ],
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "createdByUserId": "US123abc"
  }
}
```

curl:
```bash
curl -X POST https://api.quo.com/v1/contacts \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "defaultFields": { "firstName": "John", "lastName": "Doe",
      "phoneNumbers": [{ "name": "primary", "value": "+12345678901" }] },
    "source": "custom-hubspot",
    "externalId": "664d0db69fcac7cf2e6ec"
  }'
```

**Gotchas**
- The whole payload nests under `defaultFields` — there is **no** flat `firstName` at the request root (the *create* request body has no top-level `name` field; only `defaultFields`, `customFields`, `createdByUserId`, `source`, `sourceUrl`, `externalId`).
- `firstName` is the single mandatory contact field; everything else is optional.
- On create, request `customFields` items take `{ key, value }` (no `type`); the **response** adds `name`, `id`, and `type`. The Guide example shows `customFields` as an *object* (`"customFields": { ... }`), but the spec/POST body defines it as an **array** of `{ key, value }` — follow the spec (array).
- Save the returned `id` — it is required for all future GET/PATCH/DELETE on that contact.
- An API-created contact only shows up in the Quo app (conversation/contact list, search) once there's an associated conversation with a matching phone number.
- Validate phone numbers are E.164 (`+12345678901`) before sending.

---

### List contacts
Source: https://www.quo.com/docs/mdx/api-reference/contacts/list-contacts.md

`GET https://api.quo.com/v1/contacts`

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `externalIds` | query | string[] | no | Filter to contacts created with these `externalId`s. Must match values supplied at creation. **Omit → returns all contacts for the org.** |
| `sources` | query | string[] | no | Filter by `source` value(s), e.g. `public-api`. |
| `maxResults` | query | integer | **yes** | `default:10`, `min:1`, `max:50`. Marked `required: true` in the spec despite having a default. |
| `pageToken` | query | string | no | Cursor for the next page (from `nextPageToken`). |

Request: query-string only (no body).

Response `200 Success`:
```json
{
  "data": [
    {
      "id": "664d0db69fcac7cf2e6ec",
      "externalId": "664d0db69fcac7cf2e6ec",
      "source": "public-api",
      "sourceUrl": "https://openphone.co/contacts/664d0db69fcac7cf2e6ec",
      "defaultFields": {
        "company": "Quo",
        "emails": [{ "name": "company email", "value": "abc@example.com", "id": "acb123" }],
        "firstName": "John",
        "lastName": "Doe",
        "phoneNumbers": [{ "name": "company phone", "value": "+12345678901", "id": "acb123" }],
        "role": "Sales"
      },
      "customFields": [
        { "name": "Inbound Lead", "key": "inbound-lead", "id": "66d0d87d534de8fd1c433cec3", "type": "string", "value": "123 Main St" }
      ],
      "createdAt": "2022-01-01T00:00:00Z",
      "updatedAt": "2022-01-01T00:00:00Z",
      "createdByUserId": "US123abc"
    }
  ],
  "totalItems": 1,
  "nextPageToken": null
}
```

curl:
```bash
curl -G https://api.quo.com/v1/contacts \
  -H "Authorization: YOUR_API_KEY" \
  --data-urlencode "maxResults=50" \
  --data-urlencode "externalIds=664d0db69fcac7cf2e6ec" \
  --data-urlencode "sources=public-api"
```

**Gotchas**
- `maxResults` is **required** and capped at **50** (default 10). Requesting more than 50 is rejected.
- Paginate via `nextPageToken` → pass back as `pageToken`. `nextPageToken` is `null` on the last page.
- ⚠️ **`totalItems` is unreliable** — the spec literally warns: "`totalItems` is not accurately returning the total number of items that can be paginated. We are working on fixing this issue." Do not rely on it; loop on `nextPageToken` instead.
- You can only fetch a contact back by `externalId` if you supplied one at creation — contacts created without an `externalId` are not addressable through the `externalIds` filter.
- `externalIds` and `sources` are array query params (repeat the key per value).

---

### Get a contact by ID
Source: https://www.quo.com/docs/mdx/api-reference/contacts/get-a-contact-by-id.md

`GET https://api.quo.com/v1/contacts/{id}`

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | The Quo contact `id` (e.g. `66d0d87e8dc1211467372303`), pattern `^(.*)$`. This is the `id` returned from create — **not** your `externalId`. |

Response `200 Success`:
```json
{
  "data": {
    "id": "664d0db69fcac7cf2e6ec",
    "externalId": "664d0db69fcac7cf2e6ec",
    "source": "public-api",
    "sourceUrl": "https://openphone.co/contacts/664d0db69fcac7cf2e6ec",
    "defaultFields": {
      "company": "Quo",
      "emails": [{ "name": "company email", "value": "abc@example.com", "id": "acb123" }],
      "firstName": "John",
      "lastName": "Doe",
      "phoneNumbers": [{ "name": "company phone", "value": "+12345678901", "id": "acb123" }],
      "role": "Sales"
    },
    "customFields": [
      { "name": "Inbound Lead", "key": "inbound-lead", "id": "66d0d87d534de8fd1c433cec3", "type": "string", "value": "123 Main St" }
    ],
    "createdAt": "2022-01-01T00:00:00Z",
    "updatedAt": "2022-01-01T00:00:00Z",
    "createdByUserId": "US123abc"
  }
}
```

curl:
```bash
curl https://api.quo.com/v1/contacts/66d0d87e8dc1211467372303 \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- `{id}` is the Quo contact `id`, not your `externalId`. To look up by `externalId` you must use `GET /contacts?externalIds=...`.
- Returns `404 Not Found` (code `0800404`) for unknown ids.

---

### Update a contact by ID
Source: https://www.quo.com/docs/mdx/api-reference/contacts/update-a-contact-by-id.md

`PATCH https://api.quo.com/v1/contacts/{id}`

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | Quo contact `id`. |
| `externalId` | body | string \| null | no | `maxLength:75`. |
| `source` | body | string \| null | no | `maxLength:75`. |
| `sourceUrl` | body | string \| null | no | `format:uri`, `maxLength:200`. |
| `defaultFields` | body | object | no | **No required sub-fields on PATCH** (unlike create). Partial update. |
| `defaultFields.emails[]` | body | array | no | Item `{ name, value, id? }`. Set `value: null` to **remove** that email item. |
| `defaultFields.phoneNumbers[]` | body | array | no | Item `{ name, value, id? }`. Set `value: null` to **remove** that phone item. |
| `customFields` | body | array | no | Items `{ key?, id?, value }`. On PATCH you may reference by **`key` OR `id`**. |

Request body:
```json
{
  "externalId": "664d0db69fcac7cf2e6ec",
  "source": "public-api",
  "sourceUrl": "https://openphone.co/contacts/664d0db69fcac7cf2e6ec",
  "defaultFields": {
    "company": "Quo",
    "emails": [
      { "name": "company email", "value": "info@openphone.com", "id": "acb123" }
    ],
    "firstName": "John",
    "lastName": "Doe",
    "phoneNumbers": [
      { "name": "company phone", "value": "+15555555555", "id": "acb123" }
    ],
    "role": "Sales"
  },
  "customFields": [
    { "key": "inbound-lead", "id": "66d0d87d534de8fd1c433cec3", "value": "123 Main St" }
  ]
}
```

Response `200 Success`: same shape as Get-by-ID (full contact object under `data`, with response `customFields` echoing `name`, `key`, `type`, `value`).

curl:
```bash
curl -X PATCH https://api.quo.com/v1/contacts/66d0d87e8dc1211467372303 \
  -H "Authorization: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "defaultFields": { "role": "VP Sales" } }'
```

**Gotchas**
- PATCH is partial — no body field is required (`firstName` is mandatory only on create).
- **Deleting an email/phone item:** set its `value` to `null` — "If set to null during a patch operation, it will remove the [email/phone number] item from the contact."
- On PATCH, `customFields` items may carry **`id` in addition to `key`** (create only allows `key`).
- Contacts created via the Quo API can be updated by API or in the app; contacts synced from **native integrations are read-only in Quo** and cannot be edited via this endpoint.

---

### Delete a contact
Source: https://www.quo.com/docs/mdx/api-reference/contacts/delete-a-contact.md

`DELETE https://api.quo.com/v1/contacts/{id}`

| name | in | type | required | notes |
|------|----|------|----------|-------|
| `id` | path | string | **yes** | Quo contact `id`, e.g. `66d0d87e8dc1211467372303`. |

Request: no body. Response: **`204` Success** (empty body — no JSON envelope).

curl:
```bash
curl -X DELETE https://api.quo.com/v1/contacts/66d0d87e8dc1211467372303 \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- Success is `204 No Content` — there is no response body to parse.
- `404 Not Found` for unknown ids; `403 Not Phone Number User` if the API key's user lacks phone-number access.

---

### Get contact custom fields
Source: https://www.quo.com/docs/mdx/api-reference/contact-custom-fields/get-contact-custom-fields.md

`GET https://api.quo.com/v1/contact-custom-fields`

No parameters. Returns the workspace's custom-field **definitions** so you can map `key`/`type` correctly before writing contacts.

Response `200 Success`:
```json
{
  "data": [
    {
      "name": "Inbound Lead",
      "key": "inbound-lead",
      "type": "boolean"
    }
  ]
}
```

Each item: `name` (UI label, required), `key` (identifier used when writing custom values, required), `type` (one of `address`, `boolean`, `date`, `multi-select`, `number`, `string`, `url`, required).

curl:
```bash
curl https://api.quo.com/v1/contact-custom-fields \
  -H "Authorization: YOUR_API_KEY"
```

**Gotchas**
- This endpoint is **read-only** — the API "does not currently support creating or editing custom field definitions"; create/modify field definitions only inside the Quo app.
- Call this **first** when building a create/update flow to learn the valid `key`s and `type`s, then send `{ key, value }` in `customFields`.
- Note the distinct error code namespace here: `400` = `0700400` (Bad Request), `401` = `0700401`, vs. the `08xxxx` codes used by the `/contacts` endpoints.

---

### Sync pattern — upsert by externalId
Sources: https://www.quo.com/docs/mdx/guides/sync-contacts.md, https://www.quo.com/docs/mdx/guides/contacts.md

The official one-way sync guide (Google Sheets → Quo) encodes the recommended **upsert** pattern, keyed on a stored Quo contact `id` (the guide stores it back into the sheet as `contactId`):

```js
const API_BASE_URL = "https://api.quo.com/v1";
const quo = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    Authorization: process.env.QUO_API_KEY,   // RAW key, no "Bearer"
    "Content-Type": "application/json",
  },
});

async function createQuoContact(contactData) {
  const response = await quo.post("/contacts", contactData);
  return response.data.data;            // unwrap { data: {...} }
}
async function updateQuoContact(contactId, contactData) {
  const response = await quo.patch(`/contacts/${contactId}`, contactData);
  return response.data.data;
}

function mapFields(sheetRow) {
  if (!sheetRow.firstName) return;       // firstName is required
  return {
    defaultFields: {
      firstName: sheetRow.firstName,
      lastName: sheetRow.lastName,
      phoneNumbers: sheetRow.phone ? [{ name: "primary", value: sheetRow.phone }] : undefined,
      emails: sheetRow.email ? [{ name: "primary", value: sheetRow.email }] : undefined,
    },
  };
}

// Upsert: if we already stored the Quo id, PATCH; else POST and persist the new id.
if (sheetRow.contactId) {
  await updateQuoContact(sheetRow.contactId, mappedContact);
} else {
  const { id } = await createQuoContact(mappedContact);
  await updateSheetWithContactId(rowNumber, id);   // store id for next sync
}
```

The guide's "Considerations and Optimizations" recommend: implement deletion logic for rows removed from source, **paginate** when fetching many contacts, add retry/error handling, persist sync state in a database, and use incremental sync + rate-limiting to cut API calls.

**Upsert notes**
- The shipped guide keys the upsert on the **Quo `id`** it stores back into the source row. For a system you don't control round-trips on, the durable alternative is to set a unique **`externalId`** at create time and resolve via `GET /contacts?externalIds=<id>` before deciding POST vs PATCH — `externalId` is explicitly "required for retrieving the contact later via the List Contacts endpoint."
- Either way: store a stable mapping (source record ↔ Quo contact). Don't re-create on every sync.

---

### Error model (all `/contacts` endpoints)

Errors return a JSON object with `message`, `code` (string), `status` (number), `docs`, `title`, optional `trace`, and `errors[]`. Documented statuses: `400` Invalid Custom Field Item (`0801400`), `401` Unauthorized (`0800401`), `403` Not Phone Number User (`0801403`), `404` Not Found (`0800404`), `409` Conflict (`0800409`), `500` Unknown (`0801500`). The `contact-custom-fields` endpoint uses the `07xxxxx` code family instead.
