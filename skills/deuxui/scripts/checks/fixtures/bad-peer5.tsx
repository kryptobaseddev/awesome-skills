import { useQuery } from "@tanstack/react-query";

type Proof = { id: number; claim: string };

export function Shortlist() {
  const query = useQuery<Proof[]>({
    queryKey: ["proofs"],
    queryFn: async () => {
      const response = await fetch("/api/proofs");
      if (!response.ok) throw new Error("The shortlist could not be fetched.");
      return response.json();
    },
  });
  const proofs = query.data ?? [];
  const byId = new Map(proofs.map((p) => [p.id, p]));
  if (query.isError) return <p role="alert">{query.error.message}</p>;
  return (
    <ul data-count={byId.size}>
      {proofs.map((p) => {
        const label = p.claim.trim();
        return <li key={p.id}>{label}</li>;
      })}
    </ul>
  );
}
