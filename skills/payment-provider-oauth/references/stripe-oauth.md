# Stripe Connect OAuth Implementation

Complete implementation guide for Stripe Connect OAuth in SvelteKit.

## Overview

Stripe Connect OAuth allows your platform to connect to merchant Stripe accounts. Use Standard Connect for this use case where merchants manage their own accounts.

**Key Details**:
- Authorization endpoint: `https://connect.stripe.com/oauth/authorize`
- Token endpoint: `https://connect.stripe.com/oauth/token`
- Deauthorize endpoint: `https://connect.stripe.com/oauth/deauthorize`
- Access tokens: Do not expire (but can be revoked)
- Refresh tokens: Available but not required (access tokens don't expire)
- Test mode: Use `client_id` from test mode for development

## Environment Variables

```bash
# .env
STRIPE_CONNECT_CLIENT_ID=ca_xxx # From Stripe Dashboard -> Settings -> Connect
STRIPE_SECRET_KEY=sk_test_xxx # or sk_live_xxx for production
STRIPE_WEBHOOK_SECRET=whsec_xxx # For webhook signature verification

# Encryption
ENCRYPTION_KEY=<64-char-hex-string> # 32 bytes for AES-256
```

## SvelteKit Route Structure

```
src/routes/
├── api/
│   ├── oauth/
│   │   ├── stripe/
│   │   │   ├── authorize/+server.ts    # Initiate OAuth flow
│   │   │   ├── callback/+server.ts     # Handle OAuth callback
│   │   │   └── disconnect/+server.ts   # Revoke connection
│   │   └── webhooks/
│   │       └── stripe/+server.ts       # Handle Stripe webhooks
```

## Step 1: Authorization Initiation

**Route**: `src/routes/api/oauth/stripe/authorize/+server.ts`

```typescript
import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { STRIPE_CONNECT_CLIENT_ID } from '$env/static/private';

export const GET: RequestHandler = async ({ locals, url }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw redirect(302, '/login');
  }

  // Generate CSRF state token
  const state = crypto.randomUUID();
  
  // Store state in session or database with expiration (5 minutes)
  // This prevents CSRF attacks
  await storeOAuthState(session.user.id, state);

  // Build authorization URL
  const authUrl = new URL('https://connect.stripe.com/oauth/authorize');
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('client_id', STRIPE_CONNECT_CLIENT_ID);
  authUrl.searchParams.set('scope', 'read_write'); // or 'read_only'
  authUrl.searchParams.set('state', state);
  
  // Redirect URI must match exactly what's configured in Stripe Dashboard
  const redirectUri = `${url.origin}/api/oauth/stripe/callback`;
  authUrl.searchParams.set('redirect_uri', redirectUri);

  // Optional: Prefill merchant information
  const email = session.user.email;
  if (email) {
    authUrl.searchParams.set('stripe_user[email]', email);
  }

  throw redirect(302, authUrl.toString());
};

// Helper function to store state (implement based on your needs)
async function storeOAuthState(userId: string, state: string) {
  // Option 1: Store in database with expiration
  // Option 2: Store in signed, encrypted cookie
  // Option 3: Store in Redis with TTL
  
  // Example with database:
  await db.insert(oauthStates).values({
    userId,
    state,
    provider: 'stripe',
    expiresAt: new Date(Date.now() + 5 * 60 * 1000), // 5 minutes
  });
}
```

## Step 2: OAuth Callback Handler

**Route**: `src/routes/api/oauth/stripe/callback/+server.ts`

```typescript
import { error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { STRIPE_CONNECT_CLIENT_ID, STRIPE_SECRET_KEY } from '$env/static/private';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { encryptToken } from '$lib/server/utils/encryption';

export const GET: RequestHandler = async ({ url, locals }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw redirect(302, '/login');
  }

  // Extract OAuth response parameters
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const errorParam = url.searchParams.get('error');
  const errorDescription = url.searchParams.get('error_description');

  // Handle errors
  if (errorParam) {
    console.error('Stripe OAuth error:', errorParam, errorDescription);
    throw redirect(302, '/dashboard/settings?error=stripe_oauth_failed');
  }

  if (!code || !state) {
    throw error(400, 'Missing required OAuth parameters');
  }

  // Verify state to prevent CSRF
  const isValidState = await verifyOAuthState(session.user.id, state);
  if (!isValidState) {
    throw error(400, 'Invalid OAuth state');
  }

  try {
    // Exchange authorization code for access token
    const tokenResponse = await fetch('https://connect.stripe.com/oauth/token', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        client_secret: STRIPE_SECRET_KEY,
      }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Stripe token exchange failed:', errorData);
      throw error(500, 'Failed to connect Stripe account');
    }

    const tokenData = await tokenResponse.json();

    // Token response structure:
    // {
    //   access_token: string,
    //   livemode: boolean,
    //   refresh_token: string,
    //   token_type: 'bearer',
    //   stripe_publishable_key: string,
    //   stripe_user_id: string,
    //   scope: string
    // }

    // Check if user already has this provider connected
    const existingProvider = await db.query.paymentProviders.findFirst({
      where: (providers, { and, eq }) => and(
        eq(providers.userId, session.user.id),
        eq(providers.providerType, 'stripe'),
        eq(providers.providerAccountId, tokenData.stripe_user_id)
      ),
    });

    if (existingProvider) {
      // Update existing connection
      await db.update(paymentProviders)
        .set({
          accessToken: encryptToken(tokenData.access_token),
          refreshToken: tokenData.refresh_token ? encryptToken(tokenData.refresh_token) : null,
          scope: tokenData.scope,
          metadata: {
            stripeUserId: tokenData.stripe_user_id,
            stripePublishableKey: tokenData.stripe_publishable_key,
            stripeLivemode: tokenData.livemode,
          },
          isActive: true,
          lastSyncedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.id, existingProvider.id));
    } else {
      // Create new provider connection
      await db.insert(paymentProviders).values({
        userId: session.user.id,
        providerType: 'stripe',
        providerAccountId: tokenData.stripe_user_id,
        accessToken: encryptToken(tokenData.access_token),
        refreshToken: tokenData.refresh_token ? encryptToken(tokenData.refresh_token) : null,
        tokenType: tokenData.token_type,
        scope: tokenData.scope,
        metadata: {
          stripeUserId: tokenData.stripe_user_id,
          stripePublishableKey: tokenData.stripe_publishable_key,
          stripeLivemode: tokenData.livemode,
        },
        isActive: true,
        lastSyncedAt: new Date(),
      });
    }

    // Clean up OAuth state
    await deleteOAuthState(session.user.id, state);

    // Redirect to success page
    throw redirect(302, '/dashboard/settings?success=stripe_connected');
  } catch (err) {
    console.error('Error processing Stripe OAuth callback:', err);
    throw redirect(302, '/dashboard/settings?error=stripe_connection_failed');
  }
};

async function verifyOAuthState(userId: string, state: string): Promise<boolean> {
  // Verify state matches and hasn't expired
  const stored = await db.query.oauthStates.findFirst({
    where: (states, { and, eq, gt }) => and(
      eq(states.userId, userId),
      eq(states.state, state),
      eq(states.provider, 'stripe'),
      gt(states.expiresAt, new Date())
    ),
  });
  
  return !!stored;
}

async function deleteOAuthState(userId: string, state: string) {
  await db.delete(oauthStates)
    .where(and(
      eq(oauthStates.userId, userId),
      eq(oauthStates.state, state)
    ));
}
```

## Step 3: Disconnect/Revoke Handler

**Route**: `src/routes/api/oauth/stripe/disconnect/+server.ts`

```typescript
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { STRIPE_SECRET_KEY } from '$env/static/private';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';

export const POST: RequestHandler = async ({ request, locals }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw error(401, 'Unauthorized');
  }

  const { providerId } = await request.json();

  if (!providerId) {
    throw error(400, 'Provider ID required');
  }

  // Get provider details
  const provider = await db.query.paymentProviders.findFirst({
    where: and(
      eq(paymentProviders.id, providerId),
      eq(paymentProviders.userId, session.user.id),
      eq(paymentProviders.providerType, 'stripe')
    ),
  });

  if (!provider) {
    throw error(404, 'Provider not found');
  }

  try {
    // Revoke access on Stripe
    const revokeResponse = await fetch('https://connect.stripe.com/oauth/deauthorize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        client_id: STRIPE_CONNECT_CLIENT_ID,
        stripe_user_id: provider.providerAccountId,
      }),
      // Must use Authorization header with secret key
      headers: {
        'Authorization': `Bearer ${STRIPE_SECRET_KEY}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    if (!revokeResponse.ok) {
      const errorData = await revokeResponse.json();
      console.error('Stripe revoke failed:', errorData);
      // Continue to deactivate locally even if Stripe revoke fails
    }

    // Deactivate provider in database
    await db.update(paymentProviders)
      .set({
        isActive: false,
        updatedAt: new Date(),
      })
      .where(eq(paymentProviders.id, providerId));

    return json({ success: true });
  } catch (err) {
    console.error('Error disconnecting Stripe:', err);
    throw error(500, 'Failed to disconnect Stripe account');
  }
};
```

## Step 4: Making Authenticated API Calls

Use the stored access token to make calls on behalf of connected accounts:

```typescript
import { decryptToken } from '$lib/server/utils/encryption';
import Stripe from 'stripe';

export async function createStripeCharge(
  provider: PaymentProvider,
  amount: number,
  currency: string
) {
  // Decrypt the access token
  const accessToken = decryptToken(provider.accessToken);

  // Initialize Stripe with the connected account's token
  const stripe = new Stripe(accessToken, {
    apiVersion: '2024-10-28.acacia',
  });

  // Create a payment intent on the connected account
  const paymentIntent = await stripe.paymentIntents.create({
    amount,
    currency,
    // Additional parameters...
  });

  return paymentIntent;
}

// Alternative: Use platform account with Stripe-Account header
export async function createChargeWithHeader(
  stripeAccountId: string,
  amount: number,
  currency: string
) {
  const stripe = new Stripe(STRIPE_SECRET_KEY, {
    apiVersion: '2024-10-28.acacia',
  });

  // Make request on behalf of connected account
  const paymentIntent = await stripe.paymentIntents.create(
    {
      amount,
      currency,
    },
    {
      stripeAccount: stripeAccountId, // Connected account ID
    }
  );

  return paymentIntent;
}
```

## Step 5: Webhook Handler (Optional but Recommended)

**Route**: `src/routes/api/webhooks/stripe/+server.ts`

```typescript
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET } from '$env/static/private';
import Stripe from 'stripe';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';

const stripe = new Stripe(STRIPE_SECRET_KEY, {
  apiVersion: '2024-10-28.acacia',
});

export const POST: RequestHandler = async ({ request }) => {
  const body = await request.text();
  const signature = request.headers.get('stripe-signature');

  if (!signature) {
    throw error(400, 'Missing stripe-signature header');
  }

  let event: Stripe.Event;

  try {
    // Verify webhook signature
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      STRIPE_WEBHOOK_SECRET
    );
  } catch (err) {
    console.error('Webhook signature verification failed:', err);
    throw error(400, 'Invalid signature');
  }

  // Handle relevant events
  switch (event.type) {
    case 'account.application.deauthorized': {
      // Account disconnected from your platform
      const account = event.data.object as Stripe.Account;
      
      // Deactivate provider in database
      await db.update(paymentProviders)
        .set({
          isActive: false,
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.providerAccountId, account.id));
      
      break;
    }
    
    case 'account.updated': {
      // Account information changed
      const account = event.data.object as Stripe.Account;
      
      // Update metadata if needed
      await db.update(paymentProviders)
        .set({
          lastSyncedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.providerAccountId, account.id));
      
      break;
    }
  }

  return json({ received: true });
};
```

## Testing

**Test Mode Setup**:
1. Use test mode `client_id` from Stripe Dashboard
2. Use test mode API keys (`sk_test_...`)
3. Connect test Stripe accounts
4. Test disconnection flow

**Key Test Cases**:
- Initial connection
- Reconnection (updating existing provider)
- Revocation
- CSRF protection (invalid state)
- Expired authorization codes
- User denies authorization

## Error Handling

Common error scenarios:

```typescript
// Handle Stripe API errors
try {
  const result = await stripe.paymentIntents.create(params, {
    stripeAccount: accountId,
  });
} catch (err) {
  if (err instanceof Stripe.errors.StripeAuthenticationError) {
    // Invalid or expired access token - deactivate provider
    await deactivateProvider(providerId);
    throw error(401, 'Stripe authentication failed');
  } else if (err instanceof Stripe.errors.StripePermissionError) {
    // Insufficient permissions
    throw error(403, 'Insufficient Stripe permissions');
  }
  
  throw err;
}
```

## Security Best Practices

1. **Always verify OAuth state parameter** - Prevents CSRF attacks
2. **Use HTTPS for redirect URLs** - Required in production
3. **Encrypt tokens at rest** - Use AES-256-GCM
4. **Never log tokens** - Sanitize logs
5. **Implement webhook verification** - Verify signatures
6. **Handle revocation gracefully** - Listen for deauthorization events
7. **Use environment variables** - Never hardcode secrets
