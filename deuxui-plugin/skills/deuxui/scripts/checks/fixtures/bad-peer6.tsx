import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

// The real defects the good-peer6 reductions must not hide.

export function Search({ q }: { q: string }) {
  const [hits, setHits] = useState<string[]>([]);
  useEffect(() => {
    fetch(`/api/search?q=${q}`)
      .then((r) => r.json())
      .then(setHits);
  }, [q]);
  return <p>{hits.length} results</p>;
}

export function Ledger() {
  const query = useQuery({ queryKey: ["rows"], queryFn: () => fetch("/api/rows").then((r) => r.json()) });
  const rows = query.data ?? [];
  return (
    <table>
      <tbody>
        {rows.map((row) => (
          <tr key={row.id}><td>{row.name}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

export function Upload({ file }: { file: File }) {
  const [open, setOpen] = useState(true);
  const start = () => fetch("/api/upload", { method: "POST", body: file });
  return open ? (
    <Modal onCancel={() => setOpen(false)}>
      <button type="button" onClick={start}>Upload</button>
    </Modal>
  ) : null;
}
