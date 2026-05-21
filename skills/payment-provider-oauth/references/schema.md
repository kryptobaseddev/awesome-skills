# Payment Provider OAuth Schema

Complete Drizzle ORM schema for storing payment provider OAuth connections.

## Core Tables

### payment_providers Table

Stores OAuth connections for external payment providers (Stripe, Square, etc).

```typescript
import { pgTable, text, timestamp, jsonb, boolean, pgEnum } from 'drizzle-orm/pg-core';
import { createInsertSchema, createSelectSchema } from 'drizzle-zod';
import { z } from 'zod';

// Provider type enum
export const providerTypeEnum = pgEnum('provider_type', ['stripe', 'square']);

// Main payment providers table
export const paymentProviders = pgTable('payment_providers', {
  id: text('id').primaryKey().$defaultFn(() => crypto.randomUUID()),
  userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),
  
  // Provider information
  providerType: providerTypeEnum('provider_type').notNull(),
  providerAccountId: text('provider_account_id').notNull(), // Stripe account ID or Square merchant ID
  
  // OAuth tokens
  accessToken: text('access_token').notNull(),
  refreshToken: text('refresh_token'),
  tokenType: text('token_type').default('bearer'),
  scope: text('scope'), // Space-separated scopes
  
  // Token expiration (for providers that expire tokens)
  expiresAt: timestamp('expires_at', { withTimezone: true }),
  
  // Provider-specific metadata
  metadata: jsonb('metadata').$type<{
    stripeUserId?: string;
    stripePublishableKey?: string;
    stripeLivemode?: boolean;
    squareMerchantId?: string;
    squareLocationId?: string;
    squareCountry?: string;
    squareCurrency?: string;
  }>(),
  
  // Connection status
  isActive: boolean('is_active').default(true).notNull(),
  lastSyncedAt: timestamp('last_synced_at', { withTimezone: true }),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow().notNull(),
});

// Zod schemas for validation
export const insertPaymentProviderSchema = createInsertSchema(paymentProviders, {
  userId: z.string().uuid(),
  providerType: z.enum(['stripe', 'square']),
  providerAccountId: z.string().min(1),
  accessToken: z.string().min(1),
  refreshToken: z.string().optional(),
  scope: z.string().optional(),
  metadata: z.object({
    stripeUserId: z.string().optional(),
    stripePublishableKey: z.string().optional(),
    stripeLivemode: z.boolean().optional(),
    squareMerchantId: z.string().optional(),
    squareLocationId: z.string().optional(),
    squareCountry: z.string().optional(),
    squareCurrency: z.string().optional(),
  }).optional(),
}).omit({ id: true, createdAt: true, updatedAt: true });

export const selectPaymentProviderSchema = createSelectSchema(paymentProviders);

// Type exports
export type PaymentProvider = typeof paymentProviders.$inferSelect;
export type NewPaymentProvider = z.infer<typeof insertPaymentProviderSchema>;
```

### payment_provider_webhooks Table (Optional)

Track webhook events from payment providers for debugging and auditing.

```typescript
export const paymentProviderWebhooks = pgTable('payment_provider_webhooks', {
  id: text('id').primaryKey().$defaultFn(() => crypto.randomUUID()),
  paymentProviderId: text('payment_provider_id')
    .references(() => paymentProviders.id, { onDelete: 'cascade' }),
  
  // Webhook details
  eventType: text('event_type').notNull(),
  eventData: jsonb('event_data').notNull(),
  
  // Processing status
  processed: boolean('processed').default(false).notNull(),
  processedAt: timestamp('processed_at', { withTimezone: true }),
  
  // Timestamps
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
});

export const insertPaymentProviderWebhookSchema = createInsertSchema(paymentProviderWebhooks)
  .omit({ id: true, createdAt: true });

export type PaymentProviderWebhook = typeof paymentProviderWebhooks.$inferSelect;
export type NewPaymentProviderWebhook = z.infer<typeof insertPaymentProviderWebhookSchema>;
```

## Indexes

Add indexes for efficient querying:

```typescript
import { index } from 'drizzle-orm/pg-core';

// In your schema definition
export const paymentProviderUserIdx = index('payment_provider_user_idx')
  .on(paymentProviders.userId);

export const paymentProviderTypeIdx = index('payment_provider_type_idx')
  .on(paymentProviders.providerType);

export const paymentProviderAccountIdx = index('payment_provider_account_idx')
  .on(paymentProviders.providerAccountId);
```

## Migration Example

```typescript
// drizzle.config.ts should include this schema
export default {
  schema: "./src/lib/server/db/schema.ts",
  out: "./drizzle",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
};
```

Generate migration:
```bash
npm run drizzle-kit generate
npm run drizzle-kit migrate
```

## Security Considerations

**CRITICAL**: 
- Store `accessToken` and `refreshToken` encrypted at rest
- Use database-level encryption or application-level encryption (AES-256-GCM)
- Never log tokens
- Rotate encryption keys periodically
- Use environment variables for encryption keys, never hardcode

**Encryption Implementation Example**:

```typescript
import { createCipheriv, createDecipheriv, randomBytes } from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const KEY = Buffer.from(process.env.ENCRYPTION_KEY!, 'hex'); // 32 bytes

export function encryptToken(token: string): string {
  const iv = randomBytes(16);
  const cipher = createCipheriv(ALGORITHM, KEY, iv);
  
  let encrypted = cipher.update(token, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  const authTag = cipher.getAuthTag();
  
  // Format: iv:authTag:encrypted
  return `${iv.toString('hex')}:${authTag.toString('hex')}:${encrypted}`;
}

export function decryptToken(encryptedToken: string): string {
  const [ivHex, authTagHex, encrypted] = encryptedToken.split(':');
  
  const iv = Buffer.from(ivHex, 'hex');
  const authTag = Buffer.from(authTagHex, 'hex');
  const decipher = createDecipheriv(ALGORITHM, KEY, iv);
  
  decipher.setAuthTag(authTag);
  
  let decrypted = decipher.update(encrypted, 'hex', 'utf8');
  decrypted += decipher.final('utf8');
  
  return decrypted;
}
```

## Query Patterns

Common queries for payment providers:

```typescript
import { db } from '$lib/server/db';
import { paymentProviders } from '$lib/server/db/schema';
import { eq, and } from 'drizzle-orm';

// Get active provider for user
export async function getUserProvider(userId: string, providerType: 'stripe' | 'square') {
  return db.query.paymentProviders.findFirst({
    where: and(
      eq(paymentProviders.userId, userId),
      eq(paymentProviders.providerType, providerType),
      eq(paymentProviders.isActive, true)
    ),
  });
}

// Get all active providers for user
export async function getUserProviders(userId: string) {
  return db.query.paymentProviders.findMany({
    where: and(
      eq(paymentProviders.userId, userId),
      eq(paymentProviders.isActive, true)
    ),
  });
}

// Update provider tokens after refresh
export async function updateProviderTokens(
  providerId: string,
  accessToken: string,
  refreshToken?: string,
  expiresAt?: Date
) {
  return db.update(paymentProviders)
    .set({
      accessToken: encryptToken(accessToken),
      ...(refreshToken && { refreshToken: encryptToken(refreshToken) }),
      ...(expiresAt && { expiresAt }),
      updatedAt: new Date(),
      lastSyncedAt: new Date(),
    })
    .where(eq(paymentProviders.id, providerId))
    .returning();
}

// Deactivate provider
export async function deactivateProvider(providerId: string) {
  return db.update(paymentProviders)
    .set({
      isActive: false,
      updatedAt: new Date(),
    })
    .where(eq(paymentProviders.id, providerId))
    .returning();
}
```
