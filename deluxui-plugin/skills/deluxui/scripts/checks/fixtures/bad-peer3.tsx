// S-TRUST-DESTRUCT: a real destructive handler with no confirmation and no undo.
export function DangerousRow({ id }) {
  const handleDelete = () => fetch(`/api/sites/${id}`, { method: "DELETE" });
  return <button type="button" onClick={handleDelete}>Delete site</button>;
}
