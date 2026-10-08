import { toolDefinition } from '@tanstack/ai'
import { z } from 'zod'
import { db, jobs } from './db'
import { eq } from 'drizzle-orm'

export const findJob = toolDefinition({
  name: 'find_job',
  description: 'Look up a service job by id',
  inputSchema: z.object({ jobId: z.string() }),
}).server(async ({ jobId }) => {
  const [job] = await db.select().from(jobs).where(eq(jobs.id, jobId))
  return job ?? null
})

export const jobTools = [findJob]
