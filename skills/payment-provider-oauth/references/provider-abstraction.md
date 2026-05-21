# Provider Abstraction Pattern

Design pattern for easily adding new payment provider OAuth integrations.

## Architecture Overview

Create a provider abstraction layer that standardizes OAuth flows across different payment providers. This makes adding new providers straightforward and maintains consistency.

## Directory Structure

```
src/lib/server/
├── providers/
│   ├── base.ts                 # Base provider interface
│   ├── stripe-provider.ts      # Stripe implementation
│   ├── square-provider.ts      # Square implementation
│   └── registry.ts             # Provider registry
├── services/
│   └── oauth-service.ts        # OAuth service using providers
└── db/
    └── schema.ts               # Database schema
```

## Base Provider Interface

**File**: `src/lib/server/providers/base.ts`

```typescript
export interface OAuthConfig {
  authorizationUrl: string;
  tokenUrl: string;
  revokeUrl?: string;
  scopes: string[];
}

export interface OAuthTokens {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
  tokenType?: string;
  scope?: string;
}

export interface ProviderMetadata {
  accountId: string;
  [key: string]: any;
}

export interface AuthorizationParams {
  clientId: string;
  redirectUri: string;
  state: string;
  scopes?: string[];
  [key: string]: any;
}

export interface TokenExchangeParams {
  code: string;
  clientId: string;
  clientSecret?: string;
  redirectUri?: string;
  [key: string]: any;
}

export interface TokenRefreshParams {
  refreshToken: string;
  clientId: string;
  clientSecret?: string;
  [key: string]: any;
}

export interface RevokeParams {
  accessToken?: string;
  accountId?: string;
  clientId: string;
  clientSecret?: string;
}

export abstract class BaseOAuthProvider {
  abstract readonly name: 'stripe' | 'square';
  abstract readonly displayName: string;
  
  // OAuth configuration
  abstract getConfig(): OAuthConfig;
  
  // Build authorization URL
  abstract buildAuthorizationUrl(params: AuthorizationParams): string;
  
  // Exchange authorization code for tokens
  abstract exchangeCodeForTokens(params: TokenExchangeParams): Promise<{
    tokens: OAuthTokens;
    metadata: ProviderMetadata;
  }>;
  
  // Refresh access token
  abstract refreshAccessToken(params: TokenRefreshParams): Promise<OAuthTokens>;
  
  // Revoke access
  abstract revokeAccess(params: RevokeParams): Promise<void>;
  
  // Check if token needs refresh
  abstract needsRefresh(expiresAt?: Date): boolean;
  
  // Additional provider-specific API calls
  abstract fetchAccountInfo?(accessToken: string): Promise<any>;
}
```

## Stripe Provider Implementation

**File**: `src/lib/server/providers/stripe-provider.ts`

```typescript
import { BaseOAuthProvider, type OAuthConfig, type AuthorizationParams, type TokenExchangeParams, type TokenRefreshParams, type RevokeParams, type OAuthTokens, type ProviderMetadata } from './base';

export class StripeOAuthProvider extends BaseOAuthProvider {
  readonly name = 'stripe' as const;
  readonly displayName = 'Stripe';

  constructor(
    private clientId: string,
    private secretKey: string
  ) {
    super();
  }

  getConfig(): OAuthConfig {
    return {
      authorizationUrl: 'https://connect.stripe.com/oauth/authorize',
      tokenUrl: 'https://connect.stripe.com/oauth/token',
      revokeUrl: 'https://connect.stripe.com/oauth/deauthorize',
      scopes: ['read_write'], // Default scope
    };
  }

  buildAuthorizationUrl(params: AuthorizationParams): string {
    const config = this.getConfig();
    const url = new URL(config.authorizationUrl);
    
    url.searchParams.set('response_type', 'code');
    url.searchParams.set('client_id', params.clientId);
    url.searchParams.set('scope', params.scopes?.join(' ') || config.scopes.join(' '));
    url.searchParams.set('state', params.state);
    url.searchParams.set('redirect_uri', params.redirectUri);

    // Add any Stripe-specific prefill parameters
    if (params.stripe_user_email) {
      url.searchParams.set('stripe_user[email]', params.stripe_user_email);
    }
    if (params.stripe_user_url) {
      url.searchParams.set('stripe_user[url]', params.stripe_user_url);
    }

    return url.toString();
  }

  async exchangeCodeForTokens(params: TokenExchangeParams): Promise<{
    tokens: OAuthTokens;
    metadata: ProviderMetadata;
  }> {
    const config = this.getConfig();
    
    const response = await fetch(config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: params.code,
        client_secret: this.secretKey,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Stripe token exchange failed: ${JSON.stringify(error)}`);
    }

    const data = await response.json();

    return {
      tokens: {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        scope: data.scope,
        // Stripe tokens don't expire
      },
      metadata: {
        accountId: data.stripe_user_id,
        stripeUserId: data.stripe_user_id,
        stripePublishableKey: data.stripe_publishable_key,
        stripeLivemode: data.livemode,
      },
    };
  }

  async refreshAccessToken(params: TokenRefreshParams): Promise<OAuthTokens> {
    // Stripe tokens don't expire, but can use refresh token if needed
    const config = this.getConfig();
    
    const response = await fetch(config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: params.refreshToken,
        client_secret: this.secretKey,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Stripe token refresh failed: ${JSON.stringify(error)}`);
    }

    const data = await response.json();

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      tokenType: data.token_type,
      scope: data.scope,
    };
  }

  async revokeAccess(params: RevokeParams): Promise<void> {
    const config = this.getConfig();
    
    if (!config.revokeUrl) {
      throw new Error('Revoke URL not configured');
    }

    const response = await fetch(config.revokeUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': `Bearer ${this.secretKey}`,
      },
      body: new URLSearchParams({
        client_id: params.clientId,
        stripe_user_id: params.accountId!,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Stripe revoke failed: ${JSON.stringify(error)}`);
    }
  }

  needsRefresh(expiresAt?: Date): boolean {
    // Stripe tokens don't expire
    return false;
  }
}
```

## Square Provider Implementation

**File**: `src/lib/server/providers/square-provider.ts`

```typescript
import { BaseOAuthProvider, type OAuthConfig, type AuthorizationParams, type TokenExchangeParams, type TokenRefreshParams, type RevokeParams, type OAuthTokens, type ProviderMetadata } from './base';

export class SquareOAuthProvider extends BaseOAuthProvider {
  readonly name = 'square' as const;
  readonly displayName = 'Square';

  constructor(
    private applicationId: string,
    private applicationSecret: string,
    private environment: 'production' | 'sandbox' = 'production'
  ) {
    super();
  }

  private getBaseUrl(): string {
    return this.environment === 'production'
      ? 'https://connect.squareup.com'
      : 'https://connect.squareupsandbox.com';
  }

  getConfig(): OAuthConfig {
    const baseUrl = this.getBaseUrl();
    
    return {
      authorizationUrl: `${baseUrl}/oauth2/authorize`,
      tokenUrl: `${baseUrl}/oauth2/token`,
      revokeUrl: `${baseUrl}/oauth2/revoke`,
      scopes: ['MERCHANT_PROFILE_READ', 'PAYMENTS_READ', 'PAYMENTS_WRITE'],
    };
  }

  buildAuthorizationUrl(params: AuthorizationParams): string {
    const config = this.getConfig();
    const url = new URL(config.authorizationUrl);
    
    url.searchParams.set('client_id', params.clientId);
    url.searchParams.set('scope', params.scopes?.join(' ') || config.scopes.join(' '));
    url.searchParams.set('state', params.state);
    
    if (this.environment === 'production') {
      url.searchParams.set('session', 'false');
    }

    return url.toString();
  }

  async exchangeCodeForTokens(params: TokenExchangeParams): Promise<{
    tokens: OAuthTokens;
    metadata: ProviderMetadata;
  }> {
    const config = this.getConfig();
    
    const response = await fetch(config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17',
      },
      body: JSON.stringify({
        client_id: params.clientId,
        client_secret: params.clientSecret,
        code: params.code,
        grant_type: 'authorization_code',
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Square token exchange failed: ${JSON.stringify(error)}`);
    }

    const data = await response.json();
    const expiresAt = new Date(data.expires_at);

    // Fetch merchant info
    const merchantInfo = await this.fetchAccountInfo(data.access_token);

    return {
      tokens: {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        tokenType: data.token_type,
        expiresAt,
      },
      metadata: {
        accountId: data.merchant_id,
        squareMerchantId: data.merchant_id,
        squareLocationId: merchantInfo?.main_location_id,
        squareCountry: merchantInfo?.country,
        squareCurrency: merchantInfo?.currency,
      },
    };
  }

  async refreshAccessToken(params: TokenRefreshParams): Promise<OAuthTokens> {
    const config = this.getConfig();
    
    const response = await fetch(config.tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17',
      },
      body: JSON.stringify({
        client_id: params.clientId,
        client_secret: params.clientSecret,
        grant_type: 'refresh_token',
        refresh_token: params.refreshToken,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Square token refresh failed: ${JSON.stringify(error)}`);
    }

    const data = await response.json();

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token, // Square returns same refresh token
      tokenType: data.token_type,
      expiresAt: new Date(data.expires_at),
    };
  }

  async revokeAccess(params: RevokeParams): Promise<void> {
    const config = this.getConfig();
    
    if (!config.revokeUrl) {
      throw new Error('Revoke URL not configured');
    }

    const response = await fetch(config.revokeUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Square-Version': '2024-10-17',
      },
      body: JSON.stringify({
        client_id: params.clientId,
        access_token: params.accessToken,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(`Square revoke failed: ${JSON.stringify(error)}`);
    }
  }

  needsRefresh(expiresAt?: Date): boolean {
    if (!expiresAt) return false;
    
    // Refresh if expiring within 7 days (Square best practice)
    const sevenDaysFromNow = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    return new Date(expiresAt) < sevenDaysFromNow;
  }

  async fetchAccountInfo(accessToken: string): Promise<any> {
    const baseUrl = this.getBaseUrl();
    
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
}
```

## Provider Registry

**File**: `src/lib/server/providers/registry.ts`

```typescript
import { BaseOAuthProvider } from './base';
import { StripeOAuthProvider } from './stripe-provider';
import { SquareOAuthProvider } from './square-provider';
import {
  STRIPE_CONNECT_CLIENT_ID,
  STRIPE_SECRET_KEY,
  SQUARE_APPLICATION_ID,
  SQUARE_APPLICATION_SECRET,
  SQUARE_SANDBOX_APPLICATION_ID,
  SQUARE_SANDBOX_APPLICATION_SECRET,
  SQUARE_ENVIRONMENT,
} from '$env/static/private';

export type ProviderType = 'stripe' | 'square';

class ProviderRegistry {
  private providers = new Map<ProviderType, BaseOAuthProvider>();

  constructor() {
    // Register Stripe
    this.register(
      'stripe',
      new StripeOAuthProvider(STRIPE_CONNECT_CLIENT_ID, STRIPE_SECRET_KEY)
    );

    // Register Square
    const squareAppId = SQUARE_ENVIRONMENT === 'production'
      ? SQUARE_APPLICATION_ID
      : SQUARE_SANDBOX_APPLICATION_ID;
    const squareAppSecret = SQUARE_ENVIRONMENT === 'production'
      ? SQUARE_APPLICATION_SECRET
      : SQUARE_SANDBOX_APPLICATION_SECRET;
    
    this.register(
      'square',
      new SquareOAuthProvider(
        squareAppId,
        squareAppSecret,
        SQUARE_ENVIRONMENT as 'production' | 'sandbox'
      )
    );
  }

  register(type: ProviderType, provider: BaseOAuthProvider): void {
    this.providers.set(type, provider);
  }

  get(type: ProviderType): BaseOAuthProvider {
    const provider = this.providers.get(type);
    
    if (!provider) {
      throw new Error(`Provider ${type} not registered`);
    }
    
    return provider;
  }

  getAll(): BaseOAuthProvider[] {
    return Array.from(this.providers.values());
  }

  getAllTypes(): ProviderType[] {
    return Array.from(this.providers.keys());
  }
}

// Singleton instance
export const providerRegistry = new ProviderRegistry();
```

## OAuth Service

**File**: `src/lib/server/services/oauth-service.ts`

```typescript
import { providerRegistry, type ProviderType } from '../providers/registry';
import { db } from '../db';
import { paymentProviders, oauthStates } from '../db/schema';
import { eq, and } from 'drizzle-orm';
import { encryptToken, decryptToken } from '../utils/encryption';

export class OAuthService {
  async initiateAuthorization(
    userId: string,
    providerType: ProviderType,
    redirectUri: string,
    options?: { scopes?: string[]; [key: string]: any }
  ): Promise<string> {
    const provider = providerRegistry.get(providerType);
    const state = crypto.randomUUID();

    // Store state for CSRF protection
    await db.insert(oauthStates).values({
      userId,
      state,
      provider: providerType,
      expiresAt: new Date(Date.now() + 5 * 60 * 1000),
    });

    // Build authorization URL
    const authUrl = provider.buildAuthorizationUrl({
      clientId: this.getClientId(providerType),
      redirectUri,
      state,
      scopes: options?.scopes,
      ...options,
    });

    return authUrl;
  }

  async handleCallback(
    userId: string,
    providerType: ProviderType,
    code: string,
    state: string
  ): Promise<void> {
    // Verify state
    const isValid = await this.verifyState(userId, providerType, state);
    if (!isValid) {
      throw new Error('Invalid OAuth state');
    }

    const provider = providerRegistry.get(providerType);

    // Exchange code for tokens
    const { tokens, metadata } = await provider.exchangeCodeForTokens({
      code,
      clientId: this.getClientId(providerType),
      clientSecret: this.getClientSecret(providerType),
    });

    // Check if connection already exists
    const existing = await db.query.paymentProviders.findFirst({
      where: and(
        eq(paymentProviders.userId, userId),
        eq(paymentProviders.providerType, providerType),
        eq(paymentProviders.providerAccountId, metadata.accountId)
      ),
    });

    if (existing) {
      // Update existing
      await db.update(paymentProviders)
        .set({
          accessToken: encryptToken(tokens.accessToken),
          refreshToken: tokens.refreshToken ? encryptToken(tokens.refreshToken) : null,
          expiresAt: tokens.expiresAt,
          scope: tokens.scope,
          metadata,
          isActive: true,
          lastSyncedAt: new Date(),
          updatedAt: new Date(),
        })
        .where(eq(paymentProviders.id, existing.id));
    } else {
      // Create new
      await db.insert(paymentProviders).values({
        userId,
        providerType,
        providerAccountId: metadata.accountId,
        accessToken: encryptToken(tokens.accessToken),
        refreshToken: tokens.refreshToken ? encryptToken(tokens.refreshToken) : null,
        tokenType: tokens.tokenType,
        expiresAt: tokens.expiresAt,
        scope: tokens.scope,
        metadata,
        isActive: true,
        lastSyncedAt: new Date(),
      });
    }

    // Clean up state
    await this.deleteState(userId, state);
  }

  async refreshToken(providerId: string): Promise<void> {
    const providerRecord = await db.query.paymentProviders.findFirst({
      where: eq(paymentProviders.id, providerId),
    });

    if (!providerRecord || !providerRecord.refreshToken) {
      throw new Error('Provider or refresh token not found');
    }

    const provider = providerRegistry.get(providerRecord.providerType);
    const refreshToken = decryptToken(providerRecord.refreshToken);

    const tokens = await provider.refreshAccessToken({
      refreshToken,
      clientId: this.getClientId(providerRecord.providerType),
      clientSecret: this.getClientSecret(providerRecord.providerType),
    });

    await db.update(paymentProviders)
      .set({
        accessToken: encryptToken(tokens.accessToken),
        refreshToken: tokens.refreshToken ? encryptToken(tokens.refreshToken) : providerRecord.refreshToken,
        expiresAt: tokens.expiresAt,
        lastSyncedAt: new Date(),
        updatedAt: new Date(),
      })
      .where(eq(paymentProviders.id, providerId));
  }

  async revokeAccess(providerId: string): Promise<void> {
    const providerRecord = await db.query.paymentProviders.findFirst({
      where: eq(paymentProviders.id, providerId),
    });

    if (!providerRecord) {
      throw new Error('Provider not found');
    }

    const provider = providerRegistry.get(providerRecord.providerType);
    const accessToken = decryptToken(providerRecord.accessToken);

    await provider.revokeAccess({
      accessToken,
      accountId: providerRecord.providerAccountId,
      clientId: this.getClientId(providerRecord.providerType),
      clientSecret: this.getClientSecret(providerRecord.providerType),
    });

    await db.update(paymentProviders)
      .set({
        isActive: false,
        updatedAt: new Date(),
      })
      .where(eq(paymentProviders.id, providerId));
  }

  private async verifyState(userId: string, providerType: ProviderType, state: string): Promise<boolean> {
    const stored = await db.query.oauthStates.findFirst({
      where: (states, { and, eq, gt }) => and(
        eq(states.userId, userId),
        eq(states.state, state),
        eq(states.provider, providerType),
        gt(states.expiresAt, new Date())
      ),
    });
    
    return !!stored;
  }

  private async deleteState(userId: string, state: string): Promise<void> {
    await db.delete(oauthStates)
      .where(and(
        eq(oauthStates.userId, userId),
        eq(oauthStates.state, state)
      ));
  }

  private getClientId(providerType: ProviderType): string {
    // Implementation depends on your env setup
    return providerType === 'stripe'
      ? STRIPE_CONNECT_CLIENT_ID
      : SQUARE_APPLICATION_ID;
  }

  private getClientSecret(providerType: ProviderType): string {
    return providerType === 'stripe'
      ? STRIPE_SECRET_KEY
      : SQUARE_APPLICATION_SECRET;
  }
}

export const oauthService = new OAuthService();
```

## Using the Abstraction in Routes

**Example**: `src/routes/api/oauth/[provider]/authorize/+server.ts`

```typescript
import { redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { oauthService } from '$lib/server/services/oauth-service';
import type { ProviderType } from '$lib/server/providers/registry';

export const GET: RequestHandler = async ({ params, locals, url }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw redirect(302, '/login');
  }

  const providerType = params.provider as ProviderType;
  const redirectUri = `${url.origin}/api/oauth/${providerType}/callback`;

  const authUrl = await oauthService.initiateAuthorization(
    session.user.id,
    providerType,
    redirectUri
  );

  throw redirect(302, authUrl);
};
```

**Example**: `src/routes/api/oauth/[provider]/callback/+server.ts`

```typescript
import { error, redirect } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { oauthService } from '$lib/server/services/oauth-service';
import type { ProviderType } from '$lib/server/providers/registry';

export const GET: RequestHandler = async ({ params, url, locals }) => {
  const session = await locals.auth();
  
  if (!session?.user) {
    throw redirect(302, '/login');
  }

  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const errorParam = url.searchParams.get('error');

  if (errorParam) {
    throw redirect(302, `/dashboard/settings?error=${errorParam}`);
  }

  if (!code || !state) {
    throw error(400, 'Missing OAuth parameters');
  }

  try {
    const providerType = params.provider as ProviderType;
    
    await oauthService.handleCallback(
      session.user.id,
      providerType,
      code,
      state
    );

    throw redirect(302, `/dashboard/settings?success=${providerType}_connected`);
  } catch (err) {
    console.error('OAuth callback error:', err);
    throw redirect(302, '/dashboard/settings?error=connection_failed');
  }
};
```

## Adding a New Provider

To add a new provider (e.g., PayPal):

1. Create `src/lib/server/providers/paypal-provider.ts` extending `BaseOAuthProvider`
2. Implement all required methods
3. Register in `src/lib/server/providers/registry.ts`
4. Add provider type to database enum
5. Routes automatically work with `[provider]` parameter

## Benefits of This Pattern

- **Consistency**: All providers follow same interface
- **Extensibility**: Easy to add new providers
- **Maintainability**: Provider logic isolated
- **Type Safety**: Full TypeScript support
- **DRY**: No duplicate OAuth flow logic
- **Testability**: Easy to mock providers
