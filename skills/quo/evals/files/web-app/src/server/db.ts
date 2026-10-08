import { drizzle } from 'drizzle-orm/postgres-js'
import { pgTable, text, timestamp } from 'drizzle-orm/pg-core'
import postgres from 'postgres'

export const customers = pgTable('customers', {
  id: text('id').primaryKey(),
  name: text('name').notNull(),
  phone: text('phone'),
  email: text('email'),
})
export const jobs = pgTable('jobs', {
  id: text('id').primaryKey(),
  customerId: text('customer_id').references(() => customers.id),
  status: text('status').notNull(),
  scheduledAt: timestamp('scheduled_at', { withTimezone: true }),
})
export const db = drizzle(postgres(process.env.DATABASE_URL!))
