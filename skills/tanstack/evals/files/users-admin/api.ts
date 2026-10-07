export type User = { id: number; name: string; email: string; role: 'admin' | 'member'; createdAt: string }
export type SortDir = 'asc' | 'desc'
// GET /api/users?page=0&pageSize=25&sort=name&dir=asc&q=ann  ->  { rows: User[]; total: number }
export async function fetchUsers(params: { page: number; pageSize: number; sort?: keyof User; dir?: SortDir; q?: string }) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== '').map(([k, v]) => [k, String(v)]))
  const res = await fetch(`/api/users?${qs}`)
  if (!res.ok) throw new Error(`users ${res.status}`)
  return (await res.json()) as { rows: User[]; total: number }
}
