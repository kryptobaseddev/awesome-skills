import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

// 5.27.0 field report reduction. Each block below was flagged in a real
// TanStack Query/Router app and is correct as written.

type Proof = { id: number; title: string };

export function Evidence({ selected }: { selected: string }) {
  const query = useQuery<Proof[]>({
    queryKey: ["proofs"],
    queryFn: async ({ signal }) => {
      const response = await fetch("/api/proofs", { signal });
      return response.json();
    },
  });
  const data = query.data ?? [];
  // A transform of a URL param, not a rendered list.
  const selectedIds = new Set(
    selected
      .split(",")
      .map(Number)
      .filter((n) => Number.isSafeInteger(n) && n > 0),
  );
  const visible = data.filter((p) => !selectedIds.has(p.id));
  const [limit, setLimit] = useState(20);
  if (query.isPending) return <p role="status">Loading evidence</p>;
  if (query.isError) {
    return (
      <p role="alert">
        We could not load the evidence. <button type="button" onClick={() => query.refetch()}>Retry</button>
      </p>
    );
  }
  return (
    <section>
      <ul>
        {visible.slice(0, limit).map((p) => (
          <li key={p.id}>{p.title}</li>
        ))}
      </ul>
      {visible.length > limit && (
        <button type="button" onClick={() => setLimit((n) => n + 20)}>
          Show more evidence
        </button>
      )}
    </section>
  );
}

export function Review({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (note: string) => Promise<void>;
}) {
  const [note, setNote] = useState("");
  const ref = useRef<HTMLDialogElement>(null);
  // Registers a listener; there is no request in this effect to race.
  useEffect(() => {
    if (!note.trim()) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [note]);
  async function save() {
    await onSave(note);
  }
  // The native dialog cancel event is Escape. It closes; it promises nothing
  // about a request.
  return (
    <dialog
      ref={ref}
      aria-label="Review note"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      <label>
        Note
        <textarea value={note} onChange={(e) => setNote(e.target.value)} />
      </label>
      <button type="button" onClick={save}>Save note</button>
    </dialog>
  );
}

