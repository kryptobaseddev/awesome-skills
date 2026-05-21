---
name: payment-provider-oauth
description: Build OAuth connections for payment providers (Stripe Connect, Square) in SvelteKit applications. Use when creating booking platforms, marketplaces, or applications where businesses need to connect their own payment accounts. Covers complete OAuth flows, database schema with Drizzle, token management, security best practices, webhook handling, and extensible provider abstraction for easily adding new providers. Integrates with Better-Auth authentication and includes token refresh strategies.
---

# Payment Provider OAuth Integration

Build secure OAuth integrations allowing businesses to connect their Stripe or Square payment accounts to your SvelteKit application. Designed for booking platforms, marketplaces, or any application where users need to manage payments through their own merchant accounts.

## When to Use This Skill

Use this skill when building:
- Booking platforms where businesses accept payments
- Marketplace applications with multiple sellers
- SaaS platforms requiring merchant payment processing
- Applications using platform-to-merchant payment flows

This skill provides OAuth integration for users to connect **their own** payment provider accounts (different from your application's billing/subscription needs).

## Core Capabilities

1. **Complete OAuth Flows**: Authorization, callback, token exchange, refresh, and revocation
2. **Multi-Provider Support**: Stripe Connect and Square OAuth implementations
3. **Security**: Encrypted token storage, CSRF protection, webhook verification
4. **Extensibility**: Provider abstraction pattern for adding new payment providers
5. **Token Management**: Automatic refresh for expiring tokens (critical for Square)
6. **Better-Auth Integration**: Works with existing Better-Auth setup

## Quick Start

### Step 1: Review Database Schema

Read [schema.md](./references/schema.md) for the complete Drizzle schema including:
- `payment_providers` table for storing OAuth connections
- Token encryption patterns
- Indexes for performance
- Zod validation schemas

Generate migration:
```bash
npm run drizzle-kit generate
npm run drizzle-kit migrate
```

### Step 2: Choose Implementation Pattern

**Option A: Provider-Specific Routes** (simpler, two providers only)
- Read [stripe-oauth.md](./references/stripe-oauth.md) for Stripe implementation
- Read [square-oauth.md](./references/square-oauth.md) for Square implementation
- Create separate routes for each provider

**Option B: Provider Abstraction** (recommended for 3+ providers or future extensibility)
- Read [provider-abstraction.md](./references/provider-abstraction.md) first
- Implement base provider interface
- Create provider-specific implementations
- Use unified OAuth service
- Dynamic routes handle any provider: `/api/oauth/[provider]/authorize`

### Step 3: Set Up Environment Variables

```bash
# .env
# Stripe
STRIPE_CONNECT_CLIENT_ID=ca_xxx
STRIPE_SECRET_KEY=sk_test_xxx

# Square
SQUARE_APPLICATION_ID=sq0idp-xxx
SQUARE_APPLICATION_SECRET=sq0csp-xxx
SQUARE_ENVIRONMENT=production # or 'sandbox'

# Encryption (32 bytes hex for AES-256)
ENCRYPTION_KEY=<generate-with-crypto.randomBytes(32).toString('hex')>
```

### Step 4: Implement OAuth Routes

Create the following routes based on your chosen pattern:

**Authorization Routes**:
- `src/routes/api/oauth/{stripe|square}/authorize/+server.ts`
- Or: `src/routes/api/oauth/[provider]/authorize/+server.ts`

**Callback Routes**:
- `src/routes/api/oauth/{stripe|square}/callback/+server.ts`
- Or: `src/routes/api/oauth/[provider]/callback/+server.ts`

**Disconnect Routes**:
- `src/routes/api/oauth/{stripe|square}/disconnect/+server.ts`
- Or: `src/routes/api/oauth/[provider]/disconnect/+server.ts`

**Webhook Routes** (optional but recommended):
- `src/routes/api/webhooks/{stripe|square}/+server.ts`

See reference files for complete implementations.

### Step 5: Token Encryption Utilities

Create `src/lib/server/utils/encryption.ts`:

```typescript
import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const KEY = Buffer.from(process.env.ENCRYPTION_KEY!, 'hex');

export function encryptToken(token: string): string {
  const iv = randomBytes(16);
  const cipher = createCipheriv(ALGORITHM, KEY, iv);
  let encrypted = cipher.update(token, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  const authTag = cipher.getAuthTag();
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
}

export function decryptToken(encryptedToken: string): string {
  const [ivHex, authTagHex, encrypted] = encryptedToken.split(':');
  const decipher = createDecipheriv(
    ALGORITHM, 
    KEY, 
    Buffer.from(ivHex, 'hex')
  );
  decipher.setAuthTag(Buffer.from(authTagHex, 'hex'));
  let decrypted = decipher.update(encrypted, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  return decrypted;
}
```

### Step 6: Token Refresh Job (Required for Square)

Square tokens expire after 30 days and **must be refreshed every 7 days** (Square best practice).

Create `src/lib/server/jobs/token-refresh.ts`:

```typescript
import cron from 'node-cron';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq, and, lt } from 'drizzle-orm';

export function startTokenRefreshJob() {
  // Run daily at 2 AM
  cron.schedule('0 2 * * *', async () => {
    const sevenDaysFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    
    const providers = await db.query.paymentProviders.findMany({
      where: and(
        eq(paymentProviders.providerType, 'square'),
        eq(paymentProviders.isActive, true),
        lt(paymentProviders.expiresAt, sevenDaysFromNow)
      ),
    });

    for (const provider of providers) {
      // Implement refresh logic from square-oauth.md
      await refreshSquareToken(provider);
    }
  });
}
```

## UI Integration Example

**Svelte 5 Component** for connecting providers:

```svelte
<script lang="ts">
  let { providers = $bindable([]) } = $props();
  
  async function connectProvider(type: 'stripe' | 'square') {
    window.location.href = `/api/oauth/${type}/authorize`;
  }
  
  async function disconnectProvider(providerId: string) {
    const response = await fetch(`/api/oauth/disconnect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ providerId })
    });
    
    if (response.ok) {
      providers = providers.filter(p => p.id !== providerId);
    }
  }
</script>

<div class="payment-providers">
  <h2>Connected Payment Providers</h2>
  
  {#if providers.length === 0}
    <p>No payment providers connected</p>
  {:else}
    {#each providers as provider}
      <div class="provider-card">
        <span>{provider.providerType}</span>
        <button onclick={() => disconnectProvider(provider.id)}>
          Disconnect
        </button>
      </div>
    {/each}
  {/if}
  
  <div class="connect-buttons">
    <button onclick={() => connectProvider('stripe')}>
      Connect Stripe
    </button>
    <button onclick={() => connectProvider('square')}>
      Connect Square
    </button>
  </div>
</div>
```

## Making Payment API Calls

After OAuth connection, use stored tokens to make API calls:

```typescript
import { decryptToken } from '$lib/server/utils/encryption';

// Stripe example
import Stripe from 'stripe';

export async function createStripePayment(provider, amount, currency) {
  const accessToken = decryptToken(provider.accessToken);
  const stripe = new Stripe(accessToken, {
    apiVersion: '2024-10-28.acacia',
  });
  
  return await stripe.paymentIntents.create({
    amount,
    currency,
  });
}

// Square example
import { Client, Environment } from 'square';

export async function createSquarePayment(provider, amount, currency) {
  // Check if token needs refresh
  if (needsRefresh(provider.expiresAt)) {
    await refreshSquareToken(provider);
  }
  
  const accessToken = decryptToken(provider.accessToken);
  const client = new Client({
    accessToken,
    environment: Environment.Production,
  });
  
  const { result } = await client.paymentsApi.createPayment({
    sourceId: 'payment-nonce',
    amountMoney: { amount: BigInt(amount), currency },
    locationId: provider.metadata.squareLocationId,
    idempotencyKey: crypto.randomUUID(),
  });
  
  return result.payment;
}
```

## Critical Security Practices

1. **Encrypt Tokens at Rest**: Use AES-256-GCM encryption (see schema.md)
2. **Verify OAuth State**: Always validate state parameter to prevent CSRF
3. **HTTPS Only**: Required for production redirect URLs
4. **Webhook Verification**: Always verify webhook signatures
5. **Token Refresh**: Proactively refresh Square tokens every 7 days
6. **Environment Variables**: Never hardcode secrets
7. **Sanitize Logs**: Never log access/refresh tokens

## Testing Strategy

**Development Environment**:
- Use test mode credentials (Stripe test mode, Square sandbox)
- Test complete OAuth flows
- Verify token refresh
- Test disconnection/revocation
- Verify CSRF protection

**Key Test Cases**:
1. Initial connection
2. Reconnection (updating existing provider)
3. User denies authorization
4. Invalid/expired authorization codes
5. Token refresh (especially Square)
6. Webhook handling
7. Concurrent connections (multiple providers)

## Common Errors and Solutions

**Stripe**:
- `invalid_request`: Check client_id and redirect_uri match dashboard config
- `invalid_grant`: Authorization code expired (5 minutes) or already used

**Square**:
- `UNAUTHORIZED`: Token expired, trigger refresh
- Authorization fails in sandbox: Must have Square Dashboard open first
- Token refresh returns same refresh token (code flow) - this is expected

**General**:
- CSRF error: State verification failed, regenerate state
- Database constraint error: Provider already connected, update instead

## References

**Read these files for detailed implementations**:
- [schema.md](./references/schema.md) - Complete database schema with encryption
- [stripe-oauth.md](./references/stripe-oauth.md) - Stripe Connect implementation
- [square-oauth.md](./references/square-oauth.md) - Square OAuth implementation
- [provider-abstraction.md](./references/provider-abstraction.md) - Extensible provider pattern

**External Documentation**:
- [Stripe Connect OAuth](https://docs.stripe.com/connect/oauth-reference)
- [Square OAuth API](https://developer.squareup.com/docs/oauth-api/overview)

## Architecture Decisions

**Why encrypt tokens?**: Access tokens grant full API access to merchant accounts. Encryption protects against database breaches.

**Why CSRF protection?**: OAuth state parameter prevents attackers from tricking users into connecting attacker's accounts.

**Why proactive token refresh?**: Square recommends 7-day refresh cycle to ensure sufficient time to handle failures. Waiting until 30-day expiration risks service disruption.

**Why provider abstraction?**: Standardizes OAuth flows across providers, making it trivial to add new payment providers (PayPal, Adyen, etc.) without duplicating logic.

**Why webhook handlers?**: Provides real-time notification when merchants revoke access, ensuring accurate connection status.
