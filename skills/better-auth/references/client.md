# Better Auth — Client SDK reference

`createAuthClient` builds a fully-typed client that mirrors your `betterAuth()` server: the same action methods, the same `{ data, error }` shape, the same plugin surface — only the **reactivity wrapper** of `useSession` changes per framework.

## Contents

- [Pick the import subpath](#pick-the-import-subpath)
- [Instance options](#instance-options)
- [Action methods & signatures](#action-methods--signatures)
- [useSession per framework](#usesession-per-framework)
- [The `{ data, error }` shape & `$ERROR_CODES`](#the--data-error--shape--error_codes)
- [fetchOptions callbacks & `throw`](#fetchoptions-callbacks--throw)
- [`$fetch` escape hatch](#fetch-escape-hatch)
- [Typing custom fields](#typing-custom-fields)
- [Client plugins import path](#client-plugins-import-path)

## Pick the import subpath

One package, per-framework subpaths. The subpath you choose is the **only** thing that determines how `useSession` (and other reactive atoms) behave — every action method (`signIn`, `signUp`, `signOut`, …) is byte-for-byte identical across all of them.

```ts
import { createAuthClient } from "better-auth/react"    // React  → useSession is a hook
import { createAuthClient } from "better-auth/vue"      // Vue    → useSession returns a reactive object
import { createAuthClient } from "better-auth/svelte"   // Svelte → useSession returns a store ($session)
import { createAuthClient } from "better-auth/solid"    // Solid  → useSession returns an accessor: session()
import { createAuthClient } from "better-auth/client"   // Vanilla / framework-agnostic (nanostore atom)
```

(`better-auth/lynx` also exists for Lynx.) The reactivity engine underneath is **nanostores**; the subpath picks the right binding (`@nanostores/react`, `@nanostores/vue`, the Svelte store contract, `@nanostores/solid`). You never import nanostores yourself for normal usage. Per-framework mount + session-read details live in [frameworks.md](frameworks.md).

## Instance options

```ts
// lib/auth-client.ts
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: "http://localhost:3000", // base URL of the auth SERVER — OMIT if client & server share an origin
  basePath: "/api/auth",            // default "/api/auth"; change ONLY if the server changed its basePath
  plugins: [ /* CLIENT plugins, see below */ ],
  fetchOptions: { /* global better-fetch options, applied to every request */ },
});
```

- **`baseURL`** — the auth server's origin. Leave it off when the client runs on the same domain. If you set it because the client is on a different origin, you must also add that origin to the server's `trustedOrigins` (see [core-server-config.md](core-server-config.md)) or every call dies on CORS/CSRF. This is the most common "works in dev, 403s in prod" cause.
- **`basePath`** — must match the server's `basePath`. The default `/api/auth` is paired with the catch-all route; only override it if you deliberately moved the server mount.
- **`plugins`** — **client** plugins from `better-auth/client/plugins` (not the server's `better-auth/plugins`). Each adds methods/types to the client surface and pairs with a server plugin.
- **`fetchOptions`** — any [better-fetch](https://better-fetch.dev) option, applied globally to every request (global `onError`, `headers`, `credentials`, `throw`). Per-call `fetchOptions` extend/override these.

Recommended barrel export so call sites stay terse and tree-shakeable:

```ts
export const { signIn, signUp, signOut, useSession, getSession } = authClient;
```

## Action methods & signatures

Every action returns a `Promise<{ data, error }>` (see below) unless `throw: true` is set. The second argument to any method is a `fetchOptions` object — that's where `onRequest`/`onSuccess`/`onError` live.

### `signUp.email`

```ts
await authClient.signUp.email({
  email,                       // string
  password,                    // string — min 8 chars by default
  name,                        // string (display name)
  image,                       // string URL (optional)
  callbackURL: "/dashboard",   // optional — redirect after email verification
}, {
  onRequest: (ctx) => {},
  onSuccess: (ctx) => {},
  onError:   (ctx) => {},
});
```

### `signIn.email`

```ts
const { data, error } = await authClient.signIn.email({
  email,                       // string
  password,                    // string
  rememberMe: false,           // optional — persist the session past browser close
  callbackURL: "/dashboard",   // optional
}, { /* fetchOptions callbacks */ });
```

### `signIn.social`

```ts
await authClient.signIn.social({
  provider: "github",             // a configured socialProviders key: "github" | "google" | "apple" | "discord" | …
  callbackURL: "/dashboard",      // optional — redirect on success
  errorCallbackURL: "/error",     // optional
  newUserCallbackURL: "/welcome", // optional — redirect only for first-time users
  disableRedirect: true,          // optional — return the URL instead of auto-redirecting
});
```

Provider config and account linking live in [social-oauth.md](social-oauth.md). The exact option set here drifts slightly between minor versions; check the docs if a flag is rejected.

### `signIn.username`

Requires the `usernameClient()` plugin on the client **and** the `username()` plugin on the server — without the server twin the route doesn't exist.

```ts
import { usernameClient } from "better-auth/client/plugins";
export const authClient = createAuthClient({ plugins: [usernameClient()] });

await authClient.signIn.username({
  username,                    // string
  password,                    // string
  rememberMe,                  // optional
});
```

### `signOut`

```ts
await authClient.signOut();

// redirect on success:
await authClient.signOut({
  fetchOptions: { onSuccess: () => { router.push("/login"); } },
});
```

### `getSession` (imperative, non-reactive)

Use this when you need the session once (an event handler, a non-component module) rather than a live subscription.

```ts
const { data: session, error } = await authClient.getSession();

// bypass the cookie cache and hit the DB:
await authClient.getSession({
  query: { disableCookieCache: true },
});
```

## useSession per framework

`useSession` is the **reactive** counterpart to `getSession` — it re-renders when the session changes. The returned object always exposes the same fields; only how you *reach* `.data` differs by framework:

```ts
{ data, isPending, error, refetch }
//  data: { user, session } | null
//  isPending: boolean       — loading state
//  error: object | null
//  refetch: () => void      — force a re-fetch
```

| Framework | Import subpath        | How you read the session                                        |
|-----------|-----------------------|-----------------------------------------------------------------|
| React     | `better-auth/react`   | `const { data } = authClient.useSession()` — a real hook, destructure directly |
| Vue       | `better-auth/vue`     | `session.data` — reactive object, auto-unwrapped in templates    |
| Svelte    | `better-auth/svelte`  | `$session.data` — it's a store, read with the `$` prefix         |
| Solid     | `better-auth/solid`   | `session()` then `.data` — it's an accessor, **call it**         |
| Vanilla   | `better-auth/client`  | a nanostore atom — `useSession.get()` / `useSession.subscribe(cb)` |

The trap is treating one framework's pattern as universal: `$session` is Svelte-only, `session()` is Solid-only, and in vanilla there's no hook at all — you subscribe to the atom.

```tsx
// React — call inside a component
import { authClient } from "@/lib/auth-client";
export function User() {
  const { data: session, isPending } = authClient.useSession();
  if (isPending) return null;
  return <span>{session?.user.email}</span>;
}
```

```svelte
<!-- Svelte — a store, so prefix with $ to read -->
<script lang="ts">
  import { authClient } from "$lib/auth-client";
  const session = authClient.useSession();
</script>
{#if $session.data}
  <p>{$session.data.user.name}</p>
{/if}
```

```vue
<!-- Vue — reactive object, access .data directly -->
<script lang="ts" setup>
  import { authClient } from '@/lib/auth-client'
  const session = authClient.useSession()
</script>
<template>
  <button v-if="session.data" @click="authClient.signOut()">Sign out</button>
</template>
```

```tsx
// Solid — an accessor, so call session()
import { authClient } from "~/lib/auth-client";
import { Show } from "solid-js";
export default function Home() {
  const session = authClient.useSession();
  return <Show when={session()} fallback={<button>Log in</button>}>…</Show>;
}
```

`useSession` is a client convenience — for **authoritative** server-side protection (loaders, route handlers, middleware), always use the server `auth.api.getSession({ headers })`, covered in [frameworks.md](frameworks.md) and [core-server-config.md](core-server-config.md).

## The `{ data, error }` shape & `$ERROR_CODES`

Every action and `getSession` resolves to `{ data, error }`. `error` is `null` on success; on failure it's an object:

```ts
{ message?: string, status: number, statusText: string, code?: string }
```

`error.code` is a **stable** string key — branch on it for i18n or per-error UI instead of matching `message` text. Better Auth exposes every server-returned code (extended by plugins) on `authClient.$ERROR_CODES`, so you don't hardcode strings:

```ts
const { data, error } = await authClient.signUp.email({ email, password, name });
if (error) {
  if (error.code === authClient.$ERROR_CODES.USER_ALREADY_EXISTS) {
    setMsg("That email is already registered.");
  } else {
    setMsg(error.message);
  }
}
```

## fetchOptions callbacks & `throw`

`fetchOptions` are better-fetch options. The lifecycle callbacks are `onRequest(ctx)`, `onResponse(ctx)`, `onSuccess(ctx)`, `onError(ctx)` — `ctx.error.message` holds the message, `ctx.response` the raw Response. (Better Auth docs lean on `onRequest`/`onSuccess`/`onError`; `onResponse` comes from better-fetch and is supported but rarely shown.) You can pass them two ways:

```ts
// Form A — second argument
await authClient.signIn.email(
  { email, password },
  {
    onRequest: (ctx) => setLoading(true),
    onSuccess: (ctx) => router.push("/dashboard"),
    onError:   (ctx) => toast.error(ctx.error.message),
  }
);

// Form B — nested fetchOptions key inside the body
await authClient.signIn.email({
  email, password,
  fetchOptions: { onSuccess(ctx) {}, onError(ctx) {} },
});
```

### `throw: true` — opt out of `{ data, error }`

With `throw: true`, the method returns the data **directly** (no wrapper) and throws on failure — handy in `try/catch` flows.

```ts
// per call
const data = await authClient.signIn.email({ email, password }, { throw: true });

// globally, on the instance
const authClient = createAuthClient({ fetchOptions: { throw: true } });
```

### Global hooks on every request

Put cross-cutting handling on the instance — e.g. a single place to catch rate limiting:

```ts
const authClient = createAuthClient({
  fetchOptions: {
    onError: (ctx) => {
      if (ctx.response.status === 429) toast.error("Too many requests — slow down.");
    },
  },
});
```

## `$fetch` escape hatch

`authClient.$fetch` is the underlying better-fetch instance. Use it to call endpoints that have **no generated client method** — typically routes added by a custom server plugin.

```ts
const { data, error } = await authClient.$fetch("/my-custom-endpoint", {
  method: "POST",
  body: { foo: "bar" },
  // plus any fetchOptions: onSuccess, onError, headers, query, …
});
```

Inside a client plugin definition, the same `$fetch` is handed to `getActions($fetch)` and `getAtoms($fetch)` so plugin methods and reactive atoms hit your custom routes. The exact arg shape follows better-fetch conventions — confirm against the better-fetch docs if you lean on it heavily.

## Typing custom fields

Custom columns you added via the server's `user.additionalFields` (or a `customSession`) don't appear on the client's types automatically — these plugins bridge that gap. They add **types only**, no runtime endpoints.

### `inferAdditionalFields` — typing `additionalFields`

```ts
import { createAuthClient } from "better-auth/client";
import { inferAdditionalFields } from "better-auth/client/plugins";
import type { auth } from "@/lib/auth";   // import as TYPE only — keeps server code out of the bundle

// Form A — monorepo: infer straight from the server instance (preferred)
export const authClient = createAuthClient({
  plugins: [inferAdditionalFields<typeof auth>()],
});

// Form B — separate client/server projects: declare the schema inline
export const authClient2 = createAuthClient({
  plugins: [
    inferAdditionalFields({
      user: { role: { type: "string" } },
    }),
  ],
});
```

Now `session.data.user.<customField>` is type-safe and matches the server.

### `customSessionClient` — typing a `customSession` response

If the server wraps the session with `customSession(...)` to add derived data (roles, computed fields), mirror its return type on the client:

```ts
import { createAuthClient } from "better-auth/client";
import { customSessionClient } from "better-auth/client/plugins";
import type { auth } from "@/lib/auth"; // type only

const authClient = createAuthClient({
  plugins: [customSessionClient<typeof auth>()],
});

const { data } = authClient.useSession();        // data.roles, data.user.newField now typed
const { data: s } = await authClient.getSession();
```

## Client plugins import path

This is the single most common import mistake. **Client** plugins come from `better-auth/client/plugins`; the **server** counterparts come from `better-auth/plugins`. Mixing them up gives you "is not a function" or missing-type errors.

```ts
// CLIENT — better-auth/client/plugins
import {
  usernameClient,
  magicLinkClient,
  inferAdditionalFields,
  customSessionClient,
  adminClient,
  organizationClient,
  twoFactorClient,
} from "better-auth/client/plugins";
import { passkeyClient } from "@better-auth/passkey/client"; // scoped package — passkey is NOT in the barrel
```

```ts
// SERVER — better-auth/plugins (contrast)
import { username, organization, admin, customSession } from "better-auth/plugins";
```

A server plugin and its client twin are a **pair** — register both or the client methods/types won't exist, and keep any shared `ac`/`roles` config identical on both sides. Plugin client methods extend the client surface, e.g. `authClient.signIn.magicLink({ email })`, `authClient.twoFactor.verifyTotp({ code })`, `authClient.organization.create({ … })`. The full catalog of plugins and which ones add database schema is in [plugins.md](plugins.md), and orgs/admin/RBAC specifically in [organization-admin-rbac.md](organization-admin-rbac.md).

> Version note: on current Better Auth, `passkey` (since v1.4) and `sso`/`apiKey` (since v1.5) live in scoped packages — import their client plugins from `@better-auth/passkey/client`, `@better-auth/sso/client`, `@better-auth/api-key/client` (on ≤v1.4 they're still in `better-auth/client/plugins`). Check the installed version.

Back to [the skill overview](../SKILL.md).

Sources: https://better-auth.com/docs
