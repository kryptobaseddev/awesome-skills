// src/server/db.ts (current file in the project) - server only
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import { pgTable, serial, text, timestamp } from 'drizzle-orm/pg-core'
export const posts = pgTable('posts', { id: serial('id').primaryKey(), title: text('title').notNull(), body: text('body').notNull(), updatedAt: timestamp('updated_at').defaultNow() })
export const db = drizzle(postgres(process.env.DATABASE_URL!))
