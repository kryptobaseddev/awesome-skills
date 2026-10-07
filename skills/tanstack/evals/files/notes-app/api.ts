export type Note = { id: string; title: string; body: string; updatedAt: string }
export async function saveNote(note: Pick<Note, 'id' | 'title' | 'body'>): Promise<Note> {
  const res = await fetch(`/api/notes/${note.id}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify(note) })
  if (!res.ok) throw new Error(`save failed ${res.status}`)
  return res.json()
}
