import { useMutation, useQuery } from "@tanstack/react-query";

type Row = { id: string; name: string; poc: string; ready: number };

// A read owns its policy and its error copy, however close the mutation below
// sits. The mutation itself is never re-sent automatically.
export function useWorkspace() {
  const query = useQuery<Row[]>({
    queryKey: ["workspace"],
    retry: (count) => count < 2,
    queryFn: async ({ signal }) => {
      const response = await fetch("/api/workspace", { signal });
      if (!response.ok) throw new Error("The workspace could not be loaded.");
      return response.json();
    },
  });
  const mutation = useMutation({
    mutationFn: async (id: string) => {
      const response = await fetch("/api/workspace", {
        method: "POST",
        body: JSON.stringify({ id }),
      });
      if (!response.ok) throw new Error("The update could not be saved. Please retry.");
      return response.json();
    },
  });
  // isPending drives the spinner and disables the save button.
  return { query, mutation, busy: query.isPending || mutation.isPending };
}

// Stacked below 768px by peer-components.css: every cell carries its label.
export function Matrix({ rows, onOpen }: { rows: Row[]; onOpen: (id: string) => void }) {
  if (rows.length === 0) return <p>No capabilities yet. Add the first one.</p>;
  return (
    <section className="table-stack" aria-label="Capability matrix">
      <table>
        <caption>Evidence coverage by capability.</caption>
        <thead>
          <tr>
            <th scope="col">Capability</th>
            <th scope="col">Point of contact</th>
            <th scope="col">Ready</th>
            <th scope="col">Evidence</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 50).map((r) => (
            <tr key={r.id}>
              <th scope="row">{r.name}</th>
              <td data-label="Point of contact">{r.poc}</td>
              <td data-label="Ready">{r.ready}</td>
              <td data-label="Evidence">
                <button type="button" onClick={() => onOpen(r.id)}>
                  View evidence for {r.name}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

// Shortlist membership is a toggle, not a disclosure: nothing expands.
export function ShortlistButton({ id, selected, toggle }: {
  id: string; selected: boolean; toggle: (id: string) => void;
}) {
  return (
    <button type="button" aria-pressed={selected} onClick={() => toggle(id)}>
      {selected ? "In shortlist" : "Shortlist"}
    </button>
  );
}

export function DetailActions({ selected, toggle }: { selected: boolean; toggle: () => void }) {
  return (
    <div className="dialog-actions">
      <button type="button" onClick={toggle}>
        {selected ? "Remove from shortlist" : "Add to shortlist"}
      </button>
    </div>
  );
}
