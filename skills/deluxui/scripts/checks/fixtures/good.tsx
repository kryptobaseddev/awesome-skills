import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";

export function GoodPanel({ items, isLoading, error, onDelete }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const handleDelete = async () => {
    if (!window.confirm("Delete this?")) return;
    setBusy(true);
    try { await onDelete(); } catch { setBusy(false); }
  };
  if (isLoading) return <p role="status">Loading your rows…</p>;
  if (error) return <p role="alert">We could not load your rows. Retry?</p>;
  return (
    <div className="min-h-dvh bg-surface p-4 motion-reduce:transition-none">
      <h1 className="text-2xl">Dashboard</h1>
      <h2 className="text-xl">Your rows</h2>
      <button type="button" onClick={() => setQ("")} className="h-11 px-4 focus-visible:ring-2">
        Reset
      </button>
      <label htmlFor="email">Email address</label>
      <input id="email" type="email" autoComplete="email" placeholder="you@example.com" />
      <button aria-label="Edit row" className="h-11 w-11 focus-visible:ring-2">
        <svg viewBox="0 0 1 1" aria-hidden="true" />
      </button>
      <p className="text-brand-500 bg-surface">Readable</p>
      <img src="/a.png" alt="Sales trend for the last quarter" width={320} height={200} />
      <Dialog.Root><Dialog.Content aria-label="Confirm">Confirm</Dialog.Content></Dialog.Root>
      <button type="button" disabled={busy} onClick={handleDelete}>Delete</button>
      {items.length === 0
        ? <p>No rows yet. Add your first one to get started.</p>
        : <ul>{items.map((i) => <li key={i.id}>{i.name}</li>)}</ul>}
    </div>
  );
}
