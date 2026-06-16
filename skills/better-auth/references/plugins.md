# Better Auth — plugin catalog

The complete official plugin set with exact server/client imports, key methods, and which ones touch the database — so you wire the right halves and regenerate the schema when you must.

## Contents

- [Two rules before you add any plugin](#two-rules-before-you-add-any-plugin)
- [Scoped-package split (v1.5+)](#scoped-package-split-v15)
- [Master table](#master-table)
- [Common snippets](#common-snippets)
- [Plugins with no client twin](#plugins-with-no-client-twin)
- [Other official + community plugins](#other-official--community-plugins)
- [Gotchas](#gotchas)

## Two rules before you add any plugin

**Rule 1 — regenerate the schema after adding any plugin that adds tables/columns.** Plugins marked **[SCHEMA]** below extend the DB. Adding the plugin to `betterAuth({ plugins })` does NOT create the tables — forgetting this gives you a `column/table does not exist` crash at runtime, the single most common plugin error.

```bash
npx @better-auth/cli@latest generate     # writes schema for Drizzle/Prisma/Kysely, then run your ORM's migrate
npx @better-auth/cli@latest migrate      # built-in Kysely / raw driver only — applies directly
# (npx auth@latest generate|migrate is the short alias; @better-auth/cli is the canonical form)
```

See [database-adapters.md](database-adapters.md) for the generate-vs-migrate distinction per adapter.

**Rule 2 — server and client plugins come in pairs.** Almost every server plugin from `better-auth/plugins` has a client twin in `better-auth/client/plugins`. Register BOTH (and keep them in the same order for clean type inference), or the client methods and types simply won't exist:

```ts
// auth.ts          plugins: [twoFactor()]
// auth-client.ts   plugins: [twoFactorClient()]   // <- without this, authClient.twoFactor is undefined
```

A handful of plugins are server-only — see [Plugins with no client twin](#plugins-with-no-client-twin).

## Scoped-package split (v1.5+)

Three plugins **moved out of the `better-auth/plugins` barrel** into their own npm packages: `passkey` in **v1.4**, `sso` and `apiKey` in **v1.5**. If you import them from `better-auth/plugins` on a current version, the import resolves to nothing and the plugin silently does not load. On v1.4 and earlier they still live in the core barrel — check the installed version before copying an import path.

| Plugin | Install | Server import | Client import |
|---|---|---|---|
| passkey | `npm i @better-auth/passkey` | `@better-auth/passkey` | `@better-auth/passkey/client` |
| sso | `npm i @better-auth/sso` | `@better-auth/sso` | `@better-auth/sso/client` |
| apiKey | `npm i @better-auth/api-key` | `@better-auth/api-key` | `@better-auth/api-key/client` |

The v1.5 migration diff is literally `- import { apiKey } from "better-auth/plugins"` → `+ import { apiKey } from "@better-auth/api-key"`.

## Master table

Server imports come from `better-auth/plugins` and client imports from `better-auth/client/plugins` **unless the import column says otherwise** (the scoped `@better-auth/*` packages). `—` = server-only, no client twin.

| Plugin | Server import | Client import | Purpose | Schema? |
|---|---|---|---|---|
| `twoFactor` | `better-auth/plugins` | `twoFactorClient` | TOTP + email/SMS OTP + backup-code 2FA | **[SCHEMA]** |
| `username` | `better-auth/plugins` | `usernameClient` | Username login alongside email | **[SCHEMA]** |
| `anonymous` | `better-auth/plugins` | `anonymousClient` | Guest sessions; auto-link on later sign-up | **[SCHEMA]** |
| `phoneNumber` | `better-auth/plugins` | `phoneNumberClient` | Phone sign-in/verification via OTP | **[SCHEMA]** |
| `magicLink` | `better-auth/plugins` | `magicLinkClient` | Passwordless email login link | no-schema |
| `emailOTP` | `better-auth/plugins` | `emailOTPClient` | Email one-time-password sign-in/verify/reset | no-schema |
| `genericOAuth` | `better-auth/plugins` | `genericOAuthClient` | Sign in with ANY OAuth2/OIDC provider — see [social-oauth.md](social-oauth.md) | no-schema |
| `oneTap` | `better-auth/plugins` | `oneTapClient` | Google One Tap (client needs `clientId`) | no-schema |
| `admin` | `better-auth/plugins` | `adminClient` | User admin, ban, impersonation, RBAC — see [organization-admin-rbac.md](organization-admin-rbac.md) | **[SCHEMA]** |
| `organization` | `better-auth/plugins` | `organizationClient` | Multi-tenant orgs, members, teams — see [organization-admin-rbac.md](organization-admin-rbac.md) | **[SCHEMA]** |
| `oidcProvider` | `better-auth/plugins` | `oidcClient` | Make YOUR app an OIDC provider | **[SCHEMA]** |
| `bearer` | `better-auth/plugins` | — | Accept session token via `Authorization: Bearer` | no-schema |
| `jwt` | `better-auth/plugins` | `jwtClient` | Issue JWTs + JWKS for stateless verification | **[SCHEMA]** |
| `multiSession` | `better-auth/plugins` | `multiSessionClient` | Multiple concurrent accounts in one browser | no-schema |
| `oAuthProxy` | `better-auth/plugins` | — | Proxy OAuth redirects for preview/dev URLs | no-schema |
| `customSession` | `better-auth/plugins` | `customSessionClient` | Add custom fields to the session object | no-schema |
| `openAPI` | `better-auth/plugins` | — | Auto-generate OpenAPI spec + Scalar UI | no-schema |
| `haveIBeenPwned` | `better-auth/plugins` | — | Reject breached passwords (HIBP) on signup/reset | no-schema |
| `captcha` | `better-auth/plugins` | — | Bot protection (Turnstile/reCAPTCHA/hCaptcha) | no-schema |
| `lastLoginMethod` | `better-auth/plugins` | `lastLoginMethodClient` | Track/display last login method | cookie default; **[SCHEMA]** if `storeInDatabase:true` |
| `siwe` | `better-auth/plugins` | `siweClient` | Sign In With Ethereum (EIP-4361 wallet auth) | **[SCHEMA]** |
| `deviceAuthorization` | `better-auth/plugins` | `deviceAuthorizationClient` | OAuth Device Grant (RFC 8628) for TV/CLI | **[SCHEMA]** |
| `oneTimeToken` | `better-auth/plugins` | `oneTimeTokenClient` | Single-use tokens (server→client handoff) | no-schema |
| `passkey` | `@better-auth/passkey` | `@better-auth/passkey/client` → `passkeyClient` | WebAuthn / FIDO2 passkeys | **[SCHEMA]** |
| `sso` | `@better-auth/sso` | `@better-auth/sso/client` → `ssoClient` | Enterprise SSO (OIDC + SAML 2.0) | **[SCHEMA]** |
| `apiKey` | `@better-auth/api-key` | `@better-auth/api-key/client` → `apiKeyClient` | Programmatic API-key auth w/ rate limits | **[SCHEMA]** |

### Key methods at a glance

- **twoFactor** → `authClient.twoFactor.enable({password})`, `.disable({password})`, `.verifyTotp({code})`, `.getTotpUri()`, `.sendOtp()`, `.verifyOtp({code})`, `.generateBackupCodes()`, `.verifyBackupCode({code})`. Sign-in returns `{ twoFactorRedirect: true, twoFactorMethods }` when 2FA is required. Adds the `twoFactor` table + `twoFactorEnabled` on user.
- **username** → `authClient.signIn.username({username, password})`, `username` passed to `signUp.email`, `authClient.isUsernameAvailable({username})`. Adds `username` + `displayUsername` on user.
- **anonymous** → `authClient.signIn.anonymous()`; link via `onLinkAccount`. Adds `isAnonymous` on user.
- **phoneNumber** → `authClient.phoneNumber.sendOtp({phoneNumber})`, `.verify({phoneNumber, code})`, `authClient.signIn.phoneNumber({phoneNumber, password})`, `.requestPasswordReset`, `.resetPassword`. Adds `phoneNumber` + `phoneNumberVerified` on user.
- **emailOTP** → `authClient.emailOtp.sendVerificationOtp({email, type})`, `authClient.signIn.emailOtp({email, otp})`, `authClient.emailOtp.verifyEmail({email, otp})`, `.resetPassword`, `.checkVerificationOtp`.
- **oneTap** → `authClient.oneTap({callbackURL, onPromptNotification})`.
- **multiSession** → `authClient.multiSession.listDeviceSessions()`, `.setActive({sessionToken})`, `.revoke({sessionToken})`.
- **siwe** → `authClient.siwe.nonce({walletAddress, chainId})`, `authClient.siwe.verify({message, signature, walletAddress, chainId})`; provide `getNonce` + `verifyMessage` server-side. (Exact schema field list — `walletAddress`/`chainId`/`isPrimary` linked to user — is indicative; verify against the generated migration.)
- **deviceAuthorization** → endpoints `/device/code`, `/device/token`; client `authClient.device.code(...)`, `.token(...)`, `.approve(...)`, `.deny(...)`.
- **oneTimeToken** → `auth.api.generateOneTimeToken()` (server), `authClient.oneTimeToken.verify({token})`.
- **sso** → `authClient.sso.register({...})` (OIDC or SAML by config), `authClient.signIn.sso({...})`, `.verifyDomain()`, `.requestDomainVerification()`; server `auth.api.registerSSOProvider()`, `auth.api.signInSSO()`. Adds the `ssoProvider` table.
- **apiKey** → `authClient.apiKey.create|list|get|update|delete|verify` + `deleteAllExpiredApiKeys`; server `auth.api.createApiKey|verifyApiKey|getApiKey|updateApiKey|deleteApiKey|listApiKeys|deleteAllExpiredApiKeys`. Adds the `apikey` table.

(`admin` and `organization` method lists live in [organization-admin-rbac.md](organization-admin-rbac.md); `genericOAuth` in [social-oauth.md](social-oauth.md).)

## Common snippets

End-to-end (server + client) for the four you reach for most. Each assumes you've also re-run `generate`/`migrate` if the plugin is **[SCHEMA]**.

### twoFactor — TOTP + OTP + backup codes

```ts
// auth.ts
import { betterAuth } from "better-auth";
import { twoFactor } from "better-auth/plugins";

export const auth = betterAuth({
  appName: "My App",            // TOTP issuer label — set this or the QR code is unlabeled
  emailAndPassword: { enabled: true },
  plugins: [twoFactor()],       // [SCHEMA] -> regenerate
});
```

```ts
// auth-client.ts
import { createAuthClient } from "better-auth/react";
import { twoFactorClient } from "better-auth/client/plugins";
export const authClient = createAuthClient({ plugins: [twoFactorClient()] });

// enable -> show QR from getTotpUri() -> verify the first code
await authClient.twoFactor.enable({ password });
const { data } = await authClient.twoFactor.getTotpUri();   // data.totpURI -> QR
await authClient.twoFactor.verifyTotp({ code });

// on sign-in, branch when 2FA is required:
const { data: res } = await authClient.signIn.email({ email, password });
if (res?.twoFactorRedirect) {
  await authClient.twoFactor.verifyTotp({ code }); // or .sendOtp() then .verifyOtp({ code })
}
```

### magicLink — passwordless email link

```ts
// auth.ts — you OWN the delivery; sendMagicLink is where you email the url
import { magicLink } from "better-auth/plugins";
plugins: [
  magicLink({
    sendMagicLink: async ({ email, url, token }) => {
      await sendEmail(email, `Sign in: ${url}`);
    },
  }),
];
```

```ts
// auth-client.ts
import { magicLinkClient } from "better-auth/client/plugins";
export const authClient = createAuthClient({ plugins: [magicLinkClient()] });

await authClient.signIn.magicLink({ email, callbackURL: "/dashboard" });
// the link hits GET /magic-link/verify automatically; verify manually if needed:
await authClient.magicLink.verify({ query: { token } });
```

`magicLink` is no-schema — it reuses the verification table, so no regenerate.

### passkey — WebAuthn (scoped package)

```ts
// auth.ts — import from @better-auth/passkey, NOT better-auth/plugins
import { passkey } from "@better-auth/passkey";
plugins: [
  passkey({
    rpID: "example.com",        // your registrable domain
    rpName: "My App",
    origin: "https://example.com",
  }),                            // [SCHEMA] -> adds the passkey table -> regenerate
];
```

```ts
// auth-client.ts — client twin is @better-auth/passkey/client
import { passkeyClient } from "@better-auth/passkey/client";
export const authClient = createAuthClient({ plugins: [passkeyClient()] });

await authClient.passkey.addPasskey();          // register (while signed in)
await authClient.signIn.passkey();              // authenticate
await authClient.passkey.listUserPasskeys();
await authClient.passkey.deletePasskey();
await authClient.passkey.updatePasskey();
```

### bearer + jwt — token-based / stateless verification

`bearer` lets clients send the session token in `Authorization: Bearer <token>` instead of a cookie (mobile, CLI, cross-origin) — it is **server-only**, no client plugin. `jwt` issues real JWTs plus a JWKS endpoint so other services can verify statelessly without hitting your DB.

```ts
// auth.ts
import { bearer, jwt } from "better-auth/plugins";
plugins: [bearer(), jwt()];     // jwt is [SCHEMA] (adds jwks table); bearer is no-schema
```

```ts
// auth-client.ts — bearer has no twin; only jwtClient exists
import { jwtClient } from "better-auth/client/plugins";
export const authClient = createAuthClient({ plugins: [jwtClient()] });

// bearer: store the token from the set-auth-token response header, then send it back:
authClient.$fetch("/some/endpoint", { auth: { type: "Bearer", token } });

// jwt: fetch a JWT and the JWKS
const { data } = await authClient.token();      // GET /api/auth/token
const jwks = await authClient.jwks();           // GET /api/auth/jwks
// authClient.getSession() also returns the JWT in the set-auth-jwt response header
```

## Plugins with no client twin

These are server-only — there is no `xClient()` to register. Configure them on `betterAuth` and the behavior applies to your existing endpoints:

| Plugin | How the client participates |
|---|---|
| `bearer` | Client reads the `set-auth-token` response header and sends `Authorization: Bearer …` (or `fetchOptions.auth`). |
| `oAuthProxy` | Transparent — proxies OAuth redirects for dynamic preview URLs (config `productionURL`, `currentURL`). |
| `openAPI` | Serves `/api/auth/reference` (Scalar UI); spec via `auth.api.generateOpenAPISchema()`. |
| `haveIBeenPwned` | Transparent — rejects breached passwords on signup/reset (`customPasswordCompromisedMessage`). |
| `captcha` | Client sends the captcha token via `fetchOptions.headers["x-captcha-response"]`. |

`customSession` is a special case: it HAS a client twin, but the client plugin needs the server plugin's type for inference — `customSessionClient<typeof auth>()`.

## Other official + community plugins

Exist in the catalog, less central to a typical auth build:

- **scim** (`@better-auth/scim` → `scim` — own package, NOT `better-auth/plugins`) — SCIM 2.0 user provisioning **[SCHEMA]**.
- **mcp** (`{ mcp }` from `better-auth/plugins`) — make your app an OAuth provider for Model Context Protocol clients; helpers `withMcpAuth`, `auth.api.getMcpSession`. **[SCHEMA]** (shares OIDC tables).
- **i18n** — translate auth error messages (no-schema).
- **agentAuth** — AI-agent identity/registration/capability authz **[SCHEMA]**.
- **testUtils** — integration/E2E testing utilities.

**Payment/billing** plugins are community-maintained and live in their OWN packages (NOT `better-auth/plugins`), each adding its own tables (**[SCHEMA]**): `stripe` (`@better-auth/stripe` → `stripe`/`stripeClient`), `polar` (`@polar-sh/better-auth`), `dub` (`@dub/better-auth`), `commet` (`@commet/better-auth`), plus `autumn`, `chargebee`, `creem`, `dodopayments`.

## Gotchas

- **Register both halves, in matching order.** A server plugin without its client twin means `authClient.<plugin>` is `undefined` at runtime — not a type error you'll always notice. Keep server and client plugin arrays parallel.
- **The scoped-package trap.** On v1.5+, importing `passkey`/`sso`/`apiKey` from `better-auth/plugins` resolves to nothing and the plugin quietly doesn't load. Use `@better-auth/passkey`, `@better-auth/sso`, `@better-auth/api-key` (client subpath `…/client`). On ≤v1.4 it's the opposite — check the installed version.
- **Forgetting to regenerate is the #1 plugin error.** After adding `twoFactor`, `username`, `admin`, `organization`, `passkey`, `jwt`, `apiKey`, `sso`, `oidcProvider`, `siwe`, or `deviceAuthorization`, re-run `npx @better-auth/cli@latest generate` (then your ORM migrate) or you'll hit `column/table does not exist`.
- **`lastLoginMethod` is cookie-based by default** — only `storeInDatabase: true` makes it **[SCHEMA]** (adds `lastLoginMethod` on user).
- **`customSession` client needs the server type.** Use `customSessionClient<typeof auth>()` or your custom fields won't be typed on the client.
- **`admin`/`organization` share access-control infra.** Build roles with `createAccessControl` from `better-auth/plugins/access` and pass the SAME `ac`/`roles` to both server and client plugins — details in [organization-admin-rbac.md](organization-admin-rbac.md).
- **`appName` matters for `twoFactor`.** It's the TOTP issuer shown in authenticator apps; unset means an unlabeled QR entry.

See also [the skill overview](../SKILL.md), [core-server-config.md](core-server-config.md), and [client.md](client.md).

Sources: https://better-auth.com/docs
