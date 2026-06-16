# Better Auth — social / OAuth login

Configure built-in social providers, link/unlink accounts, sign in with provider ID tokens, read & refresh OAuth tokens, and wire arbitrary OIDC/OAuth2 with the `genericOAuth` plugin. See [the skill overview](../SKILL.md) for the cross-stack mental model.

## Contents

- [Imports](#imports)
- [socialProviders config block](#socialproviders-config-block)
- [Per-provider options](#per-provider-options)
- [Callback URL conventions (the one that bites)](#callback-url-conventions-the-one-that-bites)
- [Client sign-in: authClient.signIn.social](#client-sign-in-authclientsigninsocial)
- [Account linking](#account-linking)
- [link / unlink / list accounts](#link--unlink--list-accounts)
- [ID-token sign-in (native flows)](#id-token-sign-in-native-flows)
- [Access tokens & refresh](#access-tokens--refresh)
- [genericOAuth plugin (arbitrary OIDC/OAuth2)](#genericoauth-plugin-arbitrary-oidcoauth2)
- [requestSignUp / disableImplicitSignUp](#requestsignup--disableimplicitsignup)

## Imports

```ts
import { betterAuth } from "better-auth";                        // server instance
import { genericOAuth } from "better-auth/plugins";              // server plugin (arbitrary OIDC/OAuth2)
import { createAuthClient } from "better-auth/react";            // or /client, /vue, /svelte
import { genericOAuthClient } from "better-auth/client/plugins"; // client twin of genericOAuth
```

`socialProviders` is a built-in config block — no plugin needed. `genericOAuth` IS a plugin, so it needs its client twin registered too (the server/client pairing rule from the hub).

## socialProviders config block

Add providers as keys inside `betterAuth({ socialProviders })`. The **key is the provider id** — it's exactly what you later pass to `provider:`.

```ts
export const auth = betterAuth({
  baseURL: process.env.BETTER_AUTH_URL,          // e.g. http://localhost:3000
  socialProviders: {
    google: {
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    },
    github: {
      clientId: process.env.GITHUB_CLIENT_ID as string,
      clientSecret: process.env.GITHUB_CLIENT_SECRET as string,
    },
  },
});
```

`socialProviders` needs the catch-all `/api/auth/*` route mounted (see [frameworks.md](frameworks.md)) — that handler is what serves `/api/auth/callback/:provider`. For Next.js: `export const { GET, POST } = toNextJsHandler(auth)` at `app/api/auth/[...all]/route.ts`. Full base config in [core-server-config.md](core-server-config.md).

### Built-in provider ids

`google`, `github`, `apple`, `discord`, `microsoft` (Entra ID), `facebook`, `twitter` (X), `gitlab`, `twitch`, `dropbox`, `linkedin`, `reddit`, `spotify`, `kick`, `roblox`, `tiktok`, `vk`, `zoom` — plus more in the codebase (huggingface, salesforce, …). The provider id always equals the config key, so when in doubt the key you wrote is the id you pass.

## Per-provider options

All optional except `clientId`/`clientSecret`.

| Option | Type | Notes |
|---|---|---|
| `clientId` | `string \| string[]` | **required**. Array supported for multi-platform (e.g. Apple web + native). |
| `clientSecret` | `string` | **required** (some providers, e.g. Apple, compute it). |
| `clientKey` | `string` | TikTok uses `clientKey` instead of `clientId`. |
| `scope` | `string[]` | Extra scopes appended to defaults, e.g. `["repo"]`. |
| `disableDefaultScope` | `boolean` | Drop the default `email`/`profile` scopes. |
| `redirectURI` | `string` | Override the callback. Default `${baseURL}/api/auth/callback/${providerId}`. |
| `mapProfileToUser` | `(profile) => object \| Promise<object>` | Map the provider profile onto your user fields. |
| `overrideUserInfoOnSignIn` | `boolean` | Refresh user data from the provider on every sign-in (default `false`). |
| `getUserInfo` | `(tokens) => Promise<{ user, data } \| null>` | Custom userinfo fetch; return `{ user: {…mapped fields}, data: rawProfile }` — NOT a bare user (that bare shape is genericOAuth's, see below). |
| `disableImplicitSignUp` | `boolean` | New users only created when client sends `requestSignUp:true`. |
| `disableSignUp` | `boolean` | Block all new-user creation via this provider. |
| `disableIdTokenSignIn` | `boolean` | Disable the ID-token sign-in path. |
| `verifyIdToken` | `(token, nonce?) => Promise<boolean>` | Custom ID-token verification. |
| `refreshAccessToken` | `(refreshToken) => Promise<...>` | Custom refresh. **Built-in providers only — NOT genericOAuth.** |
| `prompt` | `"select_account" \| "consent" \| "login" \| "none" \| "select_account+consent"` | OAuth `prompt` param. |
| `accessType` | `"offline" \| "online"` | **Google: set `"offline"` to receive a refresh token.** |
| `responseMode` | `"query" \| "form_post"` | Authorize-response transport. |

Default per-provider scopes are not enumerated in the docs — they include `email` and `profile`, removable via `disableDefaultScope`. Don't hardcode an assumed default scope list; request what you need via `scope`.

## Callback URL conventions (the one that bites)

The redirect URL you register at the provider console differs between the two OAuth surfaces. Get this wrong and the provider rejects the redirect (`redirect_uri_mismatch`) — a 20-minute head-scratcher.

| Surface | Callback path | Example |
|---|---|---|
| **`socialProviders`** (built-in) | `/api/auth/callback/:providerId` | `${baseURL}/api/auth/callback/google` |
| **`genericOAuth`** (plugin) | `/api/auth/oauth2/callback/:providerId` | `${baseURL}/api/auth/oauth2/callback/my-provider` |

The genericOAuth path has an extra **`oauth2`** segment. Built-in social = bare `/callback/`; generic = `/oauth2/callback/`. Override either per-provider with `redirectURI`.

## Client sign-in: authClient.signIn.social

```ts
import { authClient } from "@/lib/auth-client";

await authClient.signIn.social({
  provider: "github",             // required: a configured provider id
  callbackURL: "/dashboard",      // redirect on success
  errorCallbackURL: "/error",     // redirect on failure
  newUserCallbackURL: "/welcome", // redirect ONLY for newly-created users
  disableRedirect: false,         // true => return the URL instead of auto-redirecting
  scopes: ["repo"],               // request extra scopes at call time
  requestSignUp: true,            // create the user when provider has disableImplicitSignUp
  loginHint: "user@example.com",
  // idToken: { token, nonce?, accessToken?, refreshToken? }  // native flow — see below
});
```

Server equivalent: `auth.api.signInSocial({ body: { provider, callbackURL, ... }, headers })`. Like every server `auth.api.*` call, it needs `headers` (hub rule). See [client.md](client.md) for the `{ data, error }` shape.

## Account linking

By default Better Auth links a new OAuth account to an existing user **only when the provider returns the same verified email**. Loosen or tighten this in `account.accountLinking`.

```ts
export const auth = betterAuth({
  account: {
    encryptOAuthTokens: true,                                    // encrypt tokens at rest (v1.3+)
    accountLinking: {
      enabled: true,                                             // default true
      trustedProviders: ["google", "github", "email-password"],  // auto-link even without a verified email
                                                                 // may be async: (request) => ["google"]
      allowDifferentEmails: false,    // allow linking when provider email != user email
      allowUnlinkingAll: false,       // allow unlinking the LAST remaining account
      updateUserInfoOnLink: false,    // sync provider profile to the user on link
    },
  },
});
```

**Security caveat:** `trustedProviders` *bypasses* the email-verification check before linking. If you trust a provider that lets users set an arbitrary unverified email, an attacker could link into someone else's account. Only list providers that guarantee verified emails (Google, GitHub, …). Likewise, `allowDifferentEmails: true` widens this surface — enable it only with a deliberate reason.

## link / unlink / list accounts

```ts
// Redirect-based link of a social account to the CURRENT user
await authClient.linkSocial({ provider: "google", callbackURL: "/settings", scopes: ["..."] });

// Link via provider ID token (after a native SDK / custom flow — no redirect)
await authClient.linkSocial({
  provider: "google",
  idToken: {
    token: "id_token_from_provider",
    nonce: "nonce_used_for_token",   // optional
    accessToken: "access_token",     // optional, some providers need it
    refreshToken: "refresh_token",   // optional
  },
});

await authClient.unlinkAccount({ providerId: "google", accountId: "..." }); // accountId optional
const accounts = await authClient.listAccounts();                          // [{ id, providerId, accountId, ... }]
const info = await authClient.accountInfo({ query: { accountId: "..." } });  // fresh provider profile (accountId goes under query)
```

`accountInfo`'s arg shape has drifted across versions (some types want `{ query: { accountId } }`) — pass `accountId` and trust the generated client type for the installed version.

## ID-token sign-in (native flows)

For mobile/native apps you often already hold a provider **ID token** from a native SDK. Pass it straight to `signIn.social` — Better Auth verifies it and returns a session **without any redirect**.

```ts
await authClient.signIn.social({
  provider: "apple",
  idToken: { token: appleIdToken, nonce, accessToken, refreshToken },
  // no redirect — verifies the token and creates/returns the session directly
});
```

Supported out of the box: **Google, Apple, Microsoft Entra, Facebook, Cognito**. Other providers are rejected unless you supply a per-provider `verifyIdToken`. Turn the path off with `disableIdTokenSignIn: true`.

## Access tokens & refresh

Use the stored OAuth access token to call the provider's API. `getAccessToken` **auto-refreshes** if the token is expired — prefer it over manual refresh.

```ts
// Client — auto-refreshes if expired
const { accessToken } = await authClient.getAccessToken({
  providerId: "google",
  accountId: "accountId",   // optional; resolves the current user's account otherwise
});

// Server
const res = await auth.api.getAccessToken({
  body: { providerId: "google", accountId: "...", userId: "..." }, // accountId/userId optional
  headers: await headers(),
});
// If the access token is expired it is refreshed automatically.

// Explicit refresh (rarely needed)
await authClient.refreshToken({ providerId: "google", accountId: "..." });
// Server: auth.api.refreshToken({ body: { providerId, accountId?, userId? }, headers })
```

**Google refresh tokens:** Google only issues a refresh token when you set provider `accessType: "offline"` (and usually `prompt: "consent"`). Without `offline`, `getAccessToken` has nothing to refresh once the access token expires and the user must re-consent. Note the custom `refreshAccessToken` hook works for built-in providers only, not `genericOAuth`.

## genericOAuth plugin (arbitrary OIDC/OAuth2)

For any provider not built in (Keycloak, Auth0, Okta, an internal IdP…), register `genericOAuth` with one entry per provider in `config[]`. Prefer `discoveryUrl` (OIDC autodiscovery); fall back to manual endpoints.

```ts
import { betterAuth } from "better-auth";
import { genericOAuth } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    genericOAuth({
      config: [
        {
          providerId: "my-provider",                  // required — the id you sign in with
          clientId: process.env.MYP_CLIENT_ID!,
          clientSecret: process.env.MYP_CLIENT_SECRET!,
          // OIDC autodiscovery (preferred):
          discoveryUrl: "https://auth.example.com/.well-known/openid-configuration",
          // OR manual endpoints:
          authorizationUrl: "https://auth.example.com/authorize",
          tokenUrl: "https://auth.example.com/token",
          userInfoUrl: "https://auth.example.com/userinfo",
          scopes: ["openid", "email", "profile"],
          redirectURI: "https://app.com/api/auth/oauth2/callback/my-provider", // note /oauth2/
          responseType: "code",
          responseMode: "query",
          prompt: "login",
          pkce: true,                                 // enable PKCE (recommended for public clients)
          accessType: "offline",
          authentication: "post",                     // "basic" | "post" — how client creds are sent
          authorizationUrlParams: { audience: "..." }, // extra authorize-URL query params
          getUserInfo: async (tokens) => ({ /* custom */ }),
          mapProfileToUser: async (profile) => ({ /* field mapping */ }),
        },
      ],
    }),
  ],
});
```

Client — register `genericOAuthClient()`, then sign in with `signIn.oauth2`:

```ts
import { createAuthClient } from "better-auth/react";
import { genericOAuthClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({ plugins: [genericOAuthClient()] });

await authClient.signIn.oauth2({
  providerId: "my-provider",
  callbackURL: "/dashboard",
  errorCallbackURL: "/error",
  newUserCallbackURL: "/welcome",
  disableRedirect: false,
  scopes: ["my-scope"],
  requestSignUp: false,
});

await authClient.oauth2.link({ providerId: "my-provider", callbackURL: "/linked" });
```

Remember: genericOAuth's callback base path is **`/api/auth/oauth2/callback/:providerId`** (the `oauth2` segment), not the bare `/api/auth/callback/` used by `socialProviders`. Register that exact URL at the IdP. More plugin patterns in [plugins.md](plugins.md).

## requestSignUp / disableImplicitSignUp

Controls whether a first-time social/OAuth login auto-creates a user.

| Config | Behavior |
|---|---|
| *(default)* | New social account → user auto-created (implicit sign-up). |
| `disableImplicitSignUp: true` | Existing users can sign in; new users created **only** when the client sends `signIn.social({ ..., requestSignUp: true })`. |
| `disableSignUp: true` | Blocks new-user creation entirely — even with `requestSignUp`. |

Use `disableImplicitSignUp` when you want a "sign up" button distinct from "sign in" but still allow returning users to log in seamlessly.

Sources: https://better-auth.com/docs
