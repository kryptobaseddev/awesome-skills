# Square OAuth Implementation

Complete implementation guide for Square OAuth in SvelteKit.

## Overview

Square OAuth allows your platform to connect to Square seller accounts using OAuth 2.0. This guide uses the **code flow** for server-side applications.

**Key Details**:
- Authorization endpoint: `https://connect.squareup.com/oauth2/authorize` (production) or `https://connect.squareupsandbox.com/oauth2/authorize` (sandbox)
- Token endpoint: `https://connect.squareup.com/oauth2/token` (production) or `https://connect.squareupsandbox.com/oauth2/token` (sandbox)
- Revoke endpoint: `https://connect.squareup.com/oauth2/revoke` (production) or `https://connect.squareupsandbox.com/oauth2/revoke` (sandbox)
- Access tokens: Expire after 30 days
- Refresh tokens: Never expire (code flow)
- **Must refresh tokens every 7 days** - Square best practice

## Environment Variables

```bash
# .env
# Production
SQUARE_APPLICATION_ID=sq0idp-xxx # From Square Developer Dashboard
SQUARE_APPLICATION_SECRET=sq0csp-xxx # From Square Developer Dashboard
SQUARE_ENVIRONMENT=production # or 'sandbox'

# Sandbox (for testing)
SQUARE_SANDBOX_APPLICATION_ID=sandbox-sq0idb-xxx
SQUARE_SANDBOX_APPLICATION_SECRET=sandbox-sq0csb-xxx

# Encryption
ENCRYPTION_KEY=<64-char-hex-string> # 32 bytes for AES-256
```

## SvelteKit Route Structure

```
src/routes/
├── api/
│   ├── oauth/
│   │   ├── square/
│   │   │   ├── authorize/+server.ts    # Initiate OAuth flow
│   │   │   ├── callback/+server.ts     # Handle OAuth callback
│   │   │   └── disconnect/+server.ts   # Revoke connection
│   │   └── webhooks/
│   │       └── square/+server.ts       # Handle Square webhooks
```

## Step 1: Authorization Initiation

**Route**: `src/routes/api/oauth/square/authorize/+server.ts`

```typescript
import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import {
  SQUARE_APPLICATION_ID,
  SQUARE_SANDBOX_APPLICATION_ID,
  SQUARE_ENVIRONMENT
} from '$env/static/private';

export const GET: RequestHandler = async ({ locals, url }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw redirect(302, '/login');
  }

  // Generate CSRF state token
  const state = crypto.randomUUID();
  
  // Store state in session or database with expiration (5 minutes)
  await storeOAuthState(session.user.id, state);

  // Determine environment
  const isProduction = SQUARE_ENVIRONMENT === 'production';
  const applicationId = isProduction 
    ? SQUARE_APPLICATION_ID 
    : SQUARE_SANDBOX_APPLICATION_ID;
  const baseUrl = isProduction
    ? 'https://connect.squareup.com'
    : 'https://connect.squareupsandbox.com';

  // Build authorization URL
  const authUrl = new URL(`${baseUrl}/oauth2/authorize`);
  authUrl.searchParams.set('client_id', applicationId);
  authUrl.searchParams.set('state', state);
  
  // Scopes - request only what you need
  // Available scopes: MERCHANT_PROFILE_READ, MERCHANT_PROFILE_WRITE, 
  // PAYMENTS_READ, PAYMENTS_WRITE, CUSTOMERS_READ, CUSTOMERS_WRITE, etc.
  // See: https://developer.squareup.com/docs/oauth-api/square-permissions
  const scopes = [
    'MERCHANT_PROFILE_READ',
    'PAYMENTS_READ',
    'PAYMENTS_WRITE',
  ];
  authUrl.searchParams.set('scope', scopes.join(' '));

  // session=false recommended for production apps
  if (isProduction) {
    authUrl.searchParams.set('session', 'false');
  }

  throw redirect(302, authUrl.toString());
};

async function storeOAuthState(userId: string, state: string) {
  await db.insert(oauthStates).values({
    userId,
    state,
    provider: 'square',
    expiresAt: new Date(Date.now() + 5 * 60 * 1000), // 5 minutes
  });
}
```

## Step 2: OAuth Callback Handler

**Route**: `src/routes/api/oauth/square/callback/+server.ts`

```typescript
import { error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import {
  SQUARE_APPLICATION_ID,
  SQUARE_APPLICATION_SECRET,
  SQUARE_SANDBOX_APPLICATION_ID,
  SQUARE_SANDBOX_APPLICATION_SECRET,
  SQUARE_ENVIRONMENT
} from '$env/static/private';
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
    console.error('Square OAuth error:', errorParam, errorDescription);
    throw redirect(302, '/dashboard/settings?error=square_oauth_failed');
  }

  if (!code || !state) {
    throw error(400, 'Missing required OAuth parameters');
  }

  // Verify state to prevent CSRF
  const isValidState = await verifyOAuthState(session.user.id, state);
  if (!isValidState) {
    throw error(400, 'Invalid OAuth state');
  }

  // Determine environment
  const isProduction = SQUARE_ENVIRONMENT === 'production';
  const applicationId = isProduction ? SQUARE_APPLICATION_ID : SQUARE_SANDBOX_APPLICATION_ID;
  const applicationSecret = isProduction ? SQUARE_APPLICATION_SECRET : SQUARE_SANDBOX_APPLICATION_SECRET;
  const baseUrl = isProduction 
    ? 'https://connect.squareup.com'
    : 'https://connect.squareupsandbox.com';

  try {
    // Exchange authorization code for access token
    const tokenResponse = await fetch(`${baseUrl}/oauth2/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17', // Use current Square API version
      },
      body: JSON.stringify({
        client_id: applicationId,
        client_secret: applicationSecret,
        code,
        grant_type: 'authorization_code',
      }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Square token exchange failed:', errorData);
      throw error(500, 'Failed to connect Square account');
    }

    const tokenData = await tokenResponse.json();

    // Token response structure:
    // {
    //   access_token: string,
    //   token_type: 'bearer',
    //   expires_at: string (ISO 8601),
    //   merchant_id: string,
    //   refresh_token: string,
    //   short_lived: boolean
    // }

    // Calculate expiration date
    const expiresAt = new Date(tokenData.expires_at);

    // Check if user already has this provider connected
    const existingProvider = await db.query.paymentProviders.findFirst({
      where: (providers, { and, eq }) => and(
        eq(providers.userId, session.user.id),
        eq(providers.providerType, 'square'),
        eq(providers.providerAccountId, tokenData.merchant_id)
      ),
    });

    // Fetch additional merchant information
    const merchantInfo = await fetchSquareMerchantInfo(
      tokenData.access_token,
      isProduction
    );

    if (existingProvider) {
      // Update existing connection
      await db.update(paymentProviders)
        .set({
          accessToken: encryptToken(tokenData.access_token),
          refreshToken: encryptToken(tokenData.refresh_token),
          expiresAt,
          metadata: {
            squareMerchantId: tokenData.merchant_id,
            squareLocationId: merchantInfo?.main_location_id,
            squareCountry: merchantInfo?.country,
            squareCurrency: merchantInfo?.currency,
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
        providerType: 'square',
        providerAccountId: tokenData.merchant_id,
        accessToken: encryptToken(tokenData.access_token),
        refreshToken: encryptToken(tokenData.refresh_token),
        tokenType: tokenData.token_type,
        expiresAt,
        metadata: {
          squareMerchantId: tokenData.merchant_id,
          squareLocationId: merchantInfo?.main_location_id,
          squareCountry: merchantInfo?.country,
          squareCurrency: merchantInfo?.currency,
        },
        isActive: true,
        lastSyncedAt: new Date(),
      });
    }

    // Clean up OAuth state
    await deleteOAuthState(session.user.id, state);

    // Redirect to success page
    throw redirect(302, '/dashboard/settings?success=square_connected');
  } catch (err) {
    console.error('Error processing Square OAuth callback:', err);
    throw redirect(302, '/dashboard/settings?error=square_connection_failed');
  }
};

async function fetchSquareMerchantInfo(accessToken: string, isProduction: boolean) {
  const baseUrl = isProduction
    ? 'https://connect.squareup.com'
    : 'https://connect.squareupsandbox.com';

  try {
    const response = await fetch(`${baseUrl}/v2/merchants/me`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Square-Version': '2024-10-17',
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      return data.merchant;
    }
  } catch (err) {
    console.error('Failed to fetch Square merchant info:', err);
  }
  
  return null;
}

async function verifyOAuthState(userId: string, state: string): Promise<boolean> {
  const stored = await db.query.oauthStates.findFirst({
    where: (states, { and, eq, gt }) => and(
      eq(states.userId, userId),
      eq(states.state, state),
      eq(states.provider, 'square'),
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

## Step 3: Token Refresh (Critical for Square)

**Route**: `src/lib/server/services/square-token-refresh.ts`

Square access tokens expire after 30 days. **Square requires refreshing tokens every 7 days as a best practice.**

```typescript
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq, and, lt } from 'drizzle-orm';
import { decryptToken, encryptToken } from '$lib/server/utils/encryption';
import {
  SQUARE_APPLICATION_ID,
  SQUARE_APPLICATION_SECRET,
  SQUARE_SANDBOX_APPLICATION_ID,
  SQUARE_SANDBOX_APPLICATION_SECRET,
  SQUARE_ENVIRONMENT
} from '$env/static/private';

export async function refreshSquareToken(provider: PaymentProvider) {
  const isProduction = SQUARE_ENVIRONMENT === 'production';
  const applicationId = isProduction ? SQUARE_APPLICATION_ID : SQUARE_SANDBOX_APPLICATION_ID;
  const applicationSecret = isProduction ? SQUARE_APPLICATION_SECRET : SQUARE_SANDBOX_APPLICATION_SECRET;
  const baseUrl = isProduction
    ? 'https://connect.squareup.com'
    : 'https://connect.squareupsandbox.com';

  // Decrypt refresh token
  const refreshToken = decryptToken(provider.refreshToken!);

  try {
    const tokenResponse = await fetch(`${baseUrl}/oauth2/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17',
      },
      body: JSON.stringify({
        client_id: applicationId,
        client_secret: applicationSecret,
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
      }),
    });

    if (!tokenResponse.ok) {
      const errorData = await tokenResponse.json();
      console.error('Square token refresh failed:', errorData);
      
      // If refresh fails, deactivate the provider
      await db.update(paymentProviders)
        .set({
          isActive: false,
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.id, provider.id));
      
      throw new Error('Failed to refresh Square token');
    }

    const tokenData = await tokenResponse.json();
    const expiresAt = new Date(tokenData.expires_at);

    // Update tokens in database
    await db.update(paymentProviders)
      .set({
        accessToken: encryptToken(tokenData.access_token),
        // Note: Square code flow returns the SAME refresh token
        refreshToken: encryptToken(tokenData.refresh_token),
        expiresAt,
        lastSyncedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(paymentProviders.id, provider.id));

    return {
      accessToken: tokenData.access_token,
      expiresAt,
    };
  } catch (err) {
    console.error('Error refreshing Square token:', err);
    throw err;
  }
}

// Cron job or scheduled task to refresh tokens
export async function refreshExpiringSqu areTokens() {
  // Find Square tokens expiring within 7 days
  const sevenDaysFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
  
  const providers = await db.query.paymentProviders.findMany({
    where: and(
      eq(paymentProviders.providerType, 'square'),
      eq(paymentProviders.isActive, true),
      lt(paymentProviders.expiresAt, sevenDaysFromNow)
    ),
  });

  console.log(`Refreshing ${providers.length} Square tokens`);

  for (const provider of providers) {
    try {
      await refreshSquareToken(provider);
      console.log(`Refreshed token for provider ${provider.id}`);
    } catch (err) {
      console.error(`Failed to refresh token for provider ${provider.id}:`, err);
    }
  }
}
```

**Setup Cron Job** (using node-cron or your preferred scheduler):

```typescript
// src/lib/server/jobs/token-refresh.ts
import cron from 'node-cron';
import { refreshExpiringSquareTokens } from '$lib/server/services/square-token-refresh';

// Run daily at 2 AM
export function startTokenRefreshJob() {
  cron.schedule('0 2 * * *', async () => {
    console.log('Running Square token refresh job');
    await refreshExpiringSquareTokens();
  });
}
```

## Step 4: Disconnect/Revoke Handler

**Route**: `src/routes/api/oauth/square/disconnect/+server.ts`

```typescript
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import {
  SQUARE_APPLICATION_ID,
  SQUARE_APPLICATION_SECRET,
  SQUARE_SANDBOX_APPLICATION_ID,
  SQUARE_SANDBOX_APPLICATION_SECRET,
  SQUARE_ENVIRONMENT
} from '$env/static/private';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';
import { decryptToken } from '$lib/server/utils/encryption';

export const POST: RequestHandler = async ({ request, locals }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw error(401, 'Unauthorized');
  }

  const { providerId } = await request.json();

  if (!providerId) {
    throw error(400, 'Provider ID required');
  }

  const provider = await db.query.paymentProviders.findFirst({
    where: and(
      eq(paymentProviders.id, providerId),
      eq(paymentProviders.userId, session.user.id),
      eq(paymentProviders.providerType, 'square')
    ),
  });

  if (!provider) {
    throw error(404, 'Provider not found');
  }

  const isProduction = SQUARE_ENVIRONMENT === 'production';
  const applicationId = isProduction ? SQUARE_APPLICATION_ID : SQUARE_SANDBOX_APPLICATION_ID;
  const applicationSecret = isProduction ? SQUARE_APPLICATION_SECRET : SQUARE_SANDBOX_APPLICATION_SECRET;
  const baseUrl = isProduction
    ? 'https://connect.squareup.com'
    : 'https://connect.squareupsandbox.com';

  try {
    // Decrypt access token
    const accessToken = decryptToken(provider.accessToken);

    // Revoke access on Square
    const revokeResponse = await fetch(`${baseUrl}/oauth2/revoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17',
      },
      body: JSON.stringify({
        client_id: applicationId,
        access_token: accessToken,
      }),
    });

    if (!revokeResponse.ok) {
      const errorData = await revokeResponse.json();
      console.error('Square revoke failed:', errorData);
      // Continue to deactivate locally even if Square revoke fails
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
    console.error('Error disconnecting Square:', err);
    throw error(500, 'Failed to disconnect Square account');
  }
};
```

## Step 5: Making Authenticated API Calls

Use the Square SDK with the stored access token:

```typescript
import { Client, Environment } from 'square';
import { decryptToken } from '$lib/server/utils/encryption';
import { SQUARE_ENVIRONMENT } from '$env/static/private';

export async function createSquarePayment(
  provider: PaymentProvider,
  amount: number,
  currency: string,
  locationId: string
) {
  // Check if token needs refresh
  if (provider.expiresAt && new Date(provider.expiresAt) < new Date()) {
    await refreshSquareToken(provider);
    // Refetch provider with new token
    provider = await db.query.paymentProviders.findFirst({
      where: eq(paymentProviders.id, provider.id),
    });
  }

  // Decrypt access token
  const accessToken = decryptToken(provider.accessToken);

  // Initialize Square client
  const client = new Client({
    accessToken,
    environment: SQUARE_ENVIRONMENT === 'production' 
      ? Environment.Production 
      : Environment.Sandbox,
  });

  // Create payment
  const { result } = await client.paymentsApi.createPayment({
    sourceId: 'cnon:card-nonce-ok', // From Square Web Payments SDK
    amountMoney: {
      amount: BigInt(amount),
      currency,
    },
    locationId,
    idempotencyKey: crypto.randomUUID(),
  });

  return result.payment;
}
```

## Step 6: Webhook Handler (Optional but Recommended)

**Route**: `src/routes/api/webhooks/square/+server.ts`

```typescript
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import crypto from 'crypto';

// Square webhook signature verification
function verifySquareWebhookSignature(
  body: string,
  signature: string,
  webhookSignatureKey: string
): boolean {
  const hmac = crypto.createHmac('sha256', webhookSignatureKey);
  hmac.update(body);
  const hash = hmac.digest('base64');
  return hash === signature;
}

export const POST: RequestHandler = async ({ request }) => {
  const body = await request.text();
  const signature = request.headers.get('x-square-hmacsha256-signature');

  if (!signature) {
    throw error(400, 'Missing signature header');
  }

  // Verify signature
  const webhookSignatureKey = SQUARE_WEBHOOK_SIGNATURE_KEY; // From Square Dashboard
  const isValid = verifySquareWebhookSignature(body, signature, webhookSignatureKey);

  if (!isValid) {
    throw error(400, 'Invalid signature');
  }

  const event = JSON.parse(body);

  // Handle relevant events
  switch (event.type) {
    case 'oauth.authorization.revoked': {
      // Merchant revoked access
      const merchantId = event.merchant_id;
      
      await db.update(paymentProviders)
        .set({
          isActive: false,
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.providerAccountId, merchantId));
      
      break;
    }
  }

  return json({ success: true });
};
```

## Testing in Sandbox

1. Use sandbox credentials
2. Open Square Sandbox Dashboard separately
3. Navigate to authorization URL in the same browser
4. Approve authorization in Sandbox Dashboard
5. Test token refresh
6. Test disconnection

## Error Handling

```typescript
import { ApiError } from 'square';

try {
  const result = await client.paymentsApi.createPayment(params);
} catch (err) {
  if (err instanceof ApiError) {
    const errors = err.result?.errors || [];
    
    // Check for authentication errors
    if (errors.some(e => e.code === 'UNAUTHORIZED')) {
      // Token expired or invalid - refresh or deactivate
      await refreshSquareToken(provider);
    }
    
    console.error('Square API error:', errors);
  }
  
  throw err;
}
```

## Security Best Practices

1. **Always verify OAuth state** - Prevents CSRF
2. **Refresh tokens proactively** - Every 7 days minimum
3. **Encrypt tokens at rest** - Use AES-256-GCM
4. **Never log tokens** - Sanitize logs
5. **Verify webhook signatures** - Prevent spoofing
6. **Handle revocation** - Listen for oauth.authorization.revoked events
7. **Use HTTPS** - Required for redirect URLs in production
8. **Store secrets securely** - Use environment variables
