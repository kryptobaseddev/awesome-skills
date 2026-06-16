# Organizations, Admin & RBAC — Better Auth

Multi-tenant **organizations**, an **admin** panel, and **role-based access control** via the access-control engine — the server plugins, their client twins, and the one wiring pattern that makes permission checks work on both sides.

## Contents

- [The shape of it](#the-shape-of-it)
- [Imports (load-bearing)](#imports-load-bearing)
- [Organization plugin](#organization-plugin)
- [Admin plugin](#admin-plugin)
- [Access control / RBAC](#access-control--rbac)
- [Wiring ac + roles into both halves](#wiring-ac--roles-into-both-halves)
- [Permission checks: which method, where](#permission-checks-which-method-where)
- [Common mistakes](#common-mistakes)

## The shape of it

Three plugins, each a **server + client pair** (see [the skill overview](../SKILL.md) — "Server plugin + client plugin come in pairs"). `organization()` adds multi-tenancy (orgs, members, invitations, teams); `admin()` adds a god-mode user-management surface (list/create/ban/impersonate, app-wide roles). The **access-control engine** (`createAccessControl`) is shared plumbing both plugins consume to turn role strings into permission checks.

All three add schema, so after configuring them **re-run the CLI** (`npx @better-auth/cli@latest generate`, then your ORM's migrate — Kysely/raw can `migrate` directly). Forgetting this is the #1 plugin error. See [database-adapters.md](database-adapters.md).

## Imports (load-bearing)

Copy these verbatim — the access-control helpers live in dedicated subpaths, not in `better-auth/plugins`.

```ts
import { betterAuth } from "better-auth";
import { organization, admin } from "better-auth/plugins";           // SERVER plugins
import { createAuthClient } from "better-auth/client";               // or /react, /svelte, /vue, /solid
import { organizationClient, adminClient } from "better-auth/client/plugins"; // CLIENT twins

// Access control — generic primitive, also re-exported by each plugin's /access subpath
import { createAccessControl } from "better-auth/plugins/access";

// ADMIN default statements + default-role helpers
import { defaultStatements, adminAc, userAc } from "better-auth/plugins/admin/access";

// ORGANIZATION default statements + default-role helpers (note the per-plugin subpath)
import {
  defaultStatements as orgDefaultStatements,
  adminAc as orgAdminAc,
  ownerAc,
  memberAc,
} from "better-auth/plugins/organization/access";
```

**Org and admin each ship their OWN `defaultStatements` and `adminAc`** — different permission universes (org covers `organization`/`member`/`invitation`/`team`; admin covers `user`/`session`). Import each from its matching `/access` subpath and never spread admin's `adminAc` into an org role or vice versa, or you'll grant nonsense permissions or drop the real ones.

---

## Organization plugin

### Server `organization(options)`

```ts
organization({
  allowUserToCreateOrganization: true, // boolean | ((user) => Awaitable<boolean>), default true
  organizationLimit: 5,                // number | ((user) => Awaitable<boolean>), default unlimited
  creatorRole: "owner",                // role the creator gets, default "owner"
  membershipLimit: 100,                // number | ((user, org) => number | Promise), default 100
  invitationExpiresIn: 60 * 60 * 48,   // seconds, default 48h
  invitationLimit: 100,                // number | ((user) => Promise<boolean>)
  cancelPendingInvitationsOnReInvite: false,
  requireEmailVerificationOnInvitation: false,
  disableOrganizationDeletion: false,
  sendInvitationEmail: async (data) => {
    // data: { id, email, role, organization, inviter, invitation }
    // build a link to /accept-invitation/{data.id} and send it
  },
  teams: {
    enabled: true,
    maximumTeams: 10,                  // number | async fn
    maximumMembersPerTeam: 50,         // number | async fn
    allowRemovingAllTeams: false,
  },
  dynamicAccessControl: { enabled: false, maximumRolesPerOrganization: 10 }, // v1.3+ DB-stored runtime roles
  ac,                                  // AccessControl instance (see RBAC below)
  roles: { owner, admin, member /* + custom */ },
  // organizationHooks: before/after pairs for org / member / invitation / team / teamMember
  // e.g. beforeCreateOrganization, afterAddMember, beforeUpdateMemberRole, beforeAcceptInvitation, ...
  organizationHooks: { beforeAddMember, afterAddMember /* ... */ },
})
```

### Client `organizationClient(options)`

```ts
organizationClient({
  ac,                              // SAME ac instance as the server
  roles: { owner, admin, member }, // SAME roles object as the server
  teams: { enabled: true },        // MUST mirror the server when teams are enabled
})
```

### Client methods — namespaced under `authClient.organization.*`

Accessed off your client instance (`authClient.organization.create(...)`), **not** as a bare `organization` import (you *can* `export const { organization } = authClient`, but the namespaced form is unambiguous). Every call returns `{ data, error }`.

**Org management**

| Method | Notes |
|---|---|
| `organization.create({ name, slug, logo?, metadata?, userId?, keepCurrentActiveOrganization? })` | |
| `organization.update({ organizationId?, data: { name?, slug?, logo?, metadata? } })` | |
| `organization.delete({ organizationId })` | |
| `organization.checkSlug({ slug })` | availability probe |
| `organization.setActive({ organizationId?, organizationSlug? })` | **sets `session.activeOrganizationId`**; pass `organizationId: null` to UNSET |
| `organization.list()` | user's orgs · reactive: `useListOrganizations()` |
| `organization.getFullOrganization({ query: { organizationId?, organizationSlug?, membersLimit? } })` | org + members + invitations |
| `useActiveOrganization()` (top-level, **not** namespaced) | reactive active-org hook (framework client bundles) |
| `organization.leave({ organizationId })` | |

**Members**

| Method | Notes |
|---|---|
| `organization.listMembers({ query: { organizationId?, limit?, offset?, sortBy?, sortDirection?, filterField?, filterOperator?, filterValue? } })` | |
| `organization.addMember({ userId, role, organizationId?, teamId? })` | primarily **server-side** (`auth.api.addMember`); prefer the server for direct adds |
| `organization.removeMember({ memberIdOrEmail, organizationId? })` | param key is `memberIdOrEmail` |
| `organization.updateMemberRole({ memberId, role, organizationId? })` | `role: string \| string[]` |
| `organization.getActiveMember()` | current user's membership in active org |
| `organization.getActiveMemberRole()` | → `{ role }` |

**Invitations** — the invite method is **`inviteMember`**, not `invite`:

| Method | Notes |
|---|---|
| `organization.inviteMember({ email, role, organizationId?, resend?, teamId? })` | `role: string \| string[]`; fires `sendInvitationEmail` |
| `organization.acceptInvitation({ invitationId })` | |
| `organization.rejectInvitation({ invitationId })` | |
| `organization.cancelInvitation({ invitationId })` | |
| `organization.getInvitation({ query: { id } })` | for the accept page |
| `organization.listInvitations({ query: { organizationId? } })` | |
| `organization.listUserInvitations()` | client-side requires a verified email |

**Teams** — require `teams.enabled` on **both** server and client:

| Method | Notes |
|---|---|
| `organization.createTeam({ name, organizationId? })` | |
| `organization.listTeams({ query: { organizationId? } })` | |
| `organization.updateTeam({ teamId, data: { name?, ... } })` | |
| `organization.removeTeam({ teamId, organizationId? })` | |
| `organization.setActiveTeam({ teamId })` | sets `session.activeTeamId`; `teamId: null` to unset |
| `organization.listUserTeams()` | |
| `organization.listTeamMembers({ query: { teamId? } })` | |
| `organization.addTeamMember({ teamId, userId })` | |
| `organization.removeTeamMember({ teamId, userId })` | |

REST equivalents exist for every method (`POST /organization/create`, `/organization/set-active`, `/organization/invite-member`, `/organization/accept-invitation`, `/organization/update-member-role`, `GET /organization/list`, …) if you call the endpoints directly.

### `session.activeOrganizationId` — the active-org gotcha

There is **no implicit active org**. `session.activeOrganizationId` is written **only** by `setActive()` (it mutates the session row); until then, server-side `auth.api.getSession()` returns it as `null` and org-scoped calls that default to the active org fail. To pick an org automatically on login, set it in a **database hook** rather than calling `setActive` on every boot:

```ts
// in betterAuth({ ... })
databaseHooks: {
  session: {
    create: {
      before: async (session) => {
        const m = await getFirstMembership(session.userId); // your query
        return { data: { ...session, activeOrganizationId: m?.organizationId ?? null } };
      },
    },
  },
}
```

Read it via `auth.api.getSession({ headers })` → `session.session.activeOrganizationId` (and `.activeTeamId` when teams are on). The `headers` argument is mandatory on every `auth.api.*` call — see [core-server-config.md](core-server-config.md).

---

## Admin plugin

App-wide user administration. Distinct from org roles: admin `role` lives on the **user** row and governs the whole app, while org roles live on the **member** row and are scoped to one organization.

### Server `admin(options)`

```ts
admin({
  defaultRole: "user",                  // role assigned to new signups, default "user"
  adminRoles: ["admin"],                // string | string[] treated as admin, default ["admin"]
  adminUserIds: ["user_id_1"],          // hardcoded admin user IDs (bypass the role check entirely)
  impersonationSessionDuration: 60 * 60,// seconds, default 1h
  defaultBanReason: "No reason",
  defaultBanExpiresIn: undefined,       // seconds; undefined = permanent
  bannedUserMessage: "You have been banned from this application",
  ac,                                   // AccessControl instance (its OWN universe)
  roles: { admin, user /* + custom */ },
})
// Adds role, banned, banReason, banExpires to the USER table + impersonatedBy to SESSION — regenerate schema.
```

### Client `adminClient(options)`

```ts
adminClient({ ac, roles: { admin, user /* + custom */ } })
```

### Client methods — `authClient.admin.*`

**User management**

| Method | Notes |
|---|---|
| `admin.createUser({ email, password, name, role?, data? })` | `role: string \| string[]`; `data` = extra user fields |
| `admin.listUsers({ query: { searchValue?, searchField?, searchOperator?, limit?, offset?, sortBy?, sortDirection?, filterField?, filterOperator?, filterValue? } })` | → `{ users, total, limit, offset }` |
| `admin.getUser({ query: { id } })` | server: `auth.api.getUser` |
| `admin.updateUser({ userId, data })` | server endpoint `adminUpdateUser` |
| `admin.removeUser({ userId })` | hard-delete |

**Roles** — the method is **`setRole`**, not `setUserRole`:

| Method | Notes |
|---|---|
| `admin.setRole({ userId, role })` | `role: string \| string[]`; `POST /admin/set-role`, server `auth.api.setRole` |

**Passwords / sessions**

| Method | Notes |
|---|---|
| `admin.setUserPassword({ userId, newPassword })` | |
| `admin.listUserSessions({ userId })` | → `{ sessions }` |
| `admin.revokeUserSession({ sessionToken })` | |
| `admin.revokeUserSessions({ userId })` | all of a user's sessions |

**Ban / impersonation**

| Method | Notes |
|---|---|
| `admin.banUser({ userId, banReason?, banExpiresIn? })` | `banExpiresIn` in **seconds**; omit for permanent |
| `admin.unbanUser({ userId })` | |
| `admin.impersonateUser({ userId })` | issues an impersonation session; sets `session.impersonatedBy` to the admin's id |
| `admin.stopImpersonating()` | no args; returns to the admin's own session |

Detect an active impersonation server-side with `session.session.impersonatedBy != null` — useful for an "impersonating" banner and for blocking destructive actions while impersonating.

---

## Access control / RBAC

Roles aren't strings hardcoded in the library — you **define them** with the access-control engine. Two corrections worth burning in: `createAccessControl` comes from `better-auth/plugins/access` (**not** `better-auth/plugins`), and roles are built with **`ac.newRole(...)`** — there is no `ac.roles()` method. A `statement` maps each resource to its allowed actions (the **`as const` is required** for type inference); `createAccessControl(statement)` returns an `ac`; `ac.newRole(permissions)` returns a `Role`:

```ts
// permissions.ts — imported by BOTH server auth.ts AND client auth-client.ts
import { createAccessControl } from "better-auth/plugins/access";

const statement = { project: ["create", "share", "update", "delete"] } as const; // resource -> actions
export const ac = createAccessControl(statement);

export const user = ac.newRole({ project: ["create"] });
export const myRole = ac.newRole({ project: ["create", "update", "delete"], user: ["ban"] });
```

### Inherit the built-in permissions (don't drop the defaults)

A custom role that only lists *your* resources silently loses the plugin's built-in permissions (admin user/session management, org member/invitation management). Spread `...<helper>.statements` into each role to keep them — each plugin ships a `defaultStatements` object plus per-role helpers.

**Admin** — keep built-in user/session management:

```ts
import { createAccessControl } from "better-auth/plugins/access";
import { defaultStatements, adminAc } from "better-auth/plugins/admin/access";
const statement = { ...defaultStatements, project: ["create", "share", "update", "delete"] } as const;
const ac = createAccessControl(statement);
// admin defaultStatements resources: { user: [...], session: [...] }
export const admin = ac.newRole({ project: ["create", "update"], ...adminAc.statements }); // inherit default admin perms
export const user  = ac.newRole({ project: ["create"] });
```

**Organization** — three role helpers (`ownerAc`, `adminAc`, `memberAc`):

```ts
import { createAccessControl } from "better-auth/plugins/access";
import { defaultStatements, adminAc, ownerAc, memberAc } from "better-auth/plugins/organization/access";

const statement = { ...defaultStatements, project: ["create", "share", "update", "delete"] } as const;
const ac = createAccessControl(statement);
export const member = ac.newRole({ project: ["create"], ...memberAc.statements });
export const admin  = ac.newRole({ project: ["create", "update"], ...adminAc.statements });
export const owner  = ac.newRole({ project: ["create", "update", "delete"], ...ownerAc.statements });
```

Org `defaultStatements`: `organization: ["update","delete"]`, `member: ["create","update","delete"]`, `invitation: ["create","cancel"]`, `team: ["create","update","delete"]`, `ac: ["create","read","update","delete"]`. Built-in roles: **owner** = full; **admin** = full except `organization:delete`; **member** = only `ac: ["read"]`.

> `dynamicAccessControl: { enabled: true }` (v1.3+) lets you create roles at runtime, stored in the `organizationRole` table instead of compiled into code. Gate it behind the flag and regenerate the schema.

---

## Wiring `ac` + `roles` into both halves

The single load-bearing pattern: pass the **same** `ac` instance and the **same** `roles` object into the server plugin **and** its client twin. The role-object **key** is the string stored in the DB (`member.role` / `user.role`); the **value** is the `Role` from `ac.newRole`. Without the roles on the client, `checkRolePermission` can't resolve them and silently fails.

```ts
// SERVER auth.ts
import { betterAuth } from "better-auth";
import { organization, admin } from "better-auth/plugins";
import { ac as orgAc, owner, admin as orgAdmin, member } from "./org-permissions";
import { ac as adminAc2, admin as adminRole, user } from "./admin-permissions";
export const auth = betterAuth({
  plugins: [
    organization({ ac: orgAc, roles: { owner, admin: orgAdmin, member } }),
    admin({ ac: adminAc2, roles: { admin: adminRole, user }, defaultRole: "user", adminRoles: ["admin"] }),
  ],
});
```

```ts
// CLIENT auth-client.ts — SAME ac + roles, or client-side checks won't work
import { createAuthClient } from "better-auth/client";
import { organizationClient, adminClient } from "better-auth/client/plugins";
import { ac as orgAc, owner, admin as orgAdmin, member } from "./org-permissions";
import { ac as adminAc2, admin as adminRole, user } from "./admin-permissions";

export const authClient = createAuthClient({
  plugins: [
    organizationClient({ ac: orgAc, roles: { owner, admin: orgAdmin, member } }),
    adminClient({ ac: adminAc2, roles: { admin: adminRole, user }, }),
  ],
});
```

**Keep two separate `ac` universes** (`org-permissions.ts` and `admin-permissions.ts`) — they have different default statements; sharing one `ac` only makes sense if you deliberately unify the statement object.

---

## Permission checks: which method, where

Two axes: **server vs client**, and **async** (checks the real user against the DB) vs **synchronous** (pure role math, no network). Synchronous client checks are for UI gating only, never authorization.

| Plugin | Method | Where | Sync? | Use for |
|---|---|---|---|---|
| org | `authClient.organization.hasPermission({ permissions: { resource: [actions] } })` | client → server | async | real check: current user in active org |
| org | `authClient.organization.checkRolePermission({ role, permissions: { resource: [actions] } })` | client only | **sync** | UI gating from a known role; needs `ac`+`roles` on client |
| admin | `authClient.admin.hasPermission({ userId?, role?, permission?, permissions? })` | client → server | async | real check; pass **`permission`** (single resource) OR **`permissions`** (multi), not both |
| admin | `authClient.admin.checkRolePermission({ role, permissions })` | client only | **sync** | UI gating; `{ permissions: Record<string,string[]>, role: string }` |
| admin | `auth.api.userHasPermission({ body: { userId?, role?, permission?, permissions? } })` | server | async | authoritative server-side check (note the `body:` wrapper and the `user`-prefixed name) |

```ts
// CLIENT — async, authoritative for the current user in the active org
const { data: canDelete } = await authClient.organization.hasPermission({
  permissions: { project: ["delete"] },
});

// CLIENT — sync, UI gating only (no network); needs ac+roles on the client
const showInvite = authClient.organization.checkRolePermission({
  role: "admin",
  permissions: { invitation: ["create"] },
});

// SERVER — authoritative admin check. Note the body wrapper + userHasPermission name
const allowed = await auth.api.userHasPermission({
  body: { userId, permissions: { user: ["ban"] } },
});
```

For the admin async check, supply **exactly one** of `permission` (single-resource) or `permissions` (multi-resource) — both, or neither, is an error.

---

## Common mistakes

| # | Mistake | Fix |
|---|---|---|
| 1 | `createAccessControl` from `better-auth/plugins` | Import from `better-auth/plugins/access` (or the per-plugin `/access` subpath). |
| 2 | `ac.roles({...})` | No such method — use `ac.newRole({...})`. |
| 3 | `organization.invite(...)` / `admin.setUserRole(...)` | Canonical names are `inviteMember` and `setRole`. |
| 4 | Custom role overwrites built-in perms | Spread `...adminAc.statements` / `...ownerAc.statements` etc. into the role. |
| 5 | Mixing admin's `adminAc` into org roles | Import each plugin's helpers from its own `/access` subpath; keep two `ac` universes. |
| 6 | `ac`/`roles` on the server but not the client | `checkRolePermission` needs them on **both** halves; pass identical objects. |
| 7 | Expecting an implicit active org | `session.activeOrganizationId` is set only by `setActive()` — or auto-set in a `databaseHooks.session.create.before` hook. |
| 8 | Forgetting to regenerate schema | org/admin add tables/columns; re-run `npx @better-auth/cli@latest generate` (alias `npx auth@latest generate`) + migrate. |
| 9 | Trusting `checkRolePermission` for authz | It's synchronous client-side role math — UI gating only. Authorize with `hasPermission` / `auth.api.userHasPermission`. |
| 10 | `admin.hasPermission` with both `permission` and `permissions` | Pass exactly one. |

See also [plugins.md](plugins.md) for the full plugin catalog, [client.md](client.md) for `createAuthClient` per framework, and [security-and-production.md](security-and-production.md) for session/cookie hardening.

Sources: https://better-auth.com/docs
