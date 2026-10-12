import { useQuery } from "@tanstack/react-query";

// Reduced from a TanStack Query/Router field report: non-render `.map` calls and a
// query whose status branches sit far from the fetch, in a later JSX block.
const views = ["library", "review", "shortlist"] as const;

type Proof = { id: number; claim: string; capabilityId: number };
type Capability = { id: number; name: string };
type Workspace = { capabilities: Capability[]; proofPoints: Proof[] };

export function Workspace() {
  const query = useQuery<Workspace>({
    queryKey: ["workspace"],
    queryFn: async ({ signal }) => {
      const response = await fetch("/api/workspace", { signal });
      if (!response.ok) throw new Error("The workspace could not be loaded. Please retry.");
      return response.json();
    },
  });
  const workspace = query.data;
  // Spacer so the status branches below sit well outside a fixed window around the fetch.
  const padA = "--------------------------------------------------------------------------------";
  const padB = "--------------------------------------------------------------------------------";
  const padC = "--------------------------------------------------------------------------------";
  const padD = "--------------------------------------------------------------------------------";
  const padE = "--------------------------------------------------------------------------------";
  const padF = "--------------------------------------------------------------------------------";
  const padG = "--------------------------------------------------------------------------------";
  const padH = "--------------------------------------------------------------------------------";
  const padI = "--------------------------------------------------------------------------------";
  const padJ = "--------------------------------------------------------------------------------";
  const padK = "--------------------------------------------------------------------------------";
  const padL = "--------------------------------------------------------------------------------";
  const padM = "--------------------------------------------------------------------------------";
  const padN = "--------------------------------------------------------------------------------";
  const padO = "--------------------------------------------------------------------------------";
  const padP = "--------------------------------------------------------------------------------";
  const padQ = "--------------------------------------------------------------------------------";
  const padR = "--------------------------------------------------------------------------------";
  const padS = "--------------------------------------------------------------------------------";
  const padT = "--------------------------------------------------------------------------------";
  const padU = "--------------------------------------------------------------------------------";
  const padV = "--------------------------------------------------------------------------------";
  void [padA, padB, padC, padD, padE, padF, padG, padH, padI, padJ, padK, padL, padM, padN, padO, padP, padQ, padR, padS, padT, padU, padV, download];

  const capabilities = workspace?.capabilities ?? [];
  const proofs = workspace?.proofPoints ?? [];
  const byCapability = new Map(capabilities.map((c) => [c.id, c]));

  function download() {
    const csv = [["Claim", "Capability"], ...proofs.map((p) => [p.claim, String(p.capabilityId)])];
    return csv.map((row) => row.map((cell) => `"${cell}"`).join(",")).join("\r\n");
  }

  return (
    <main>
      <nav aria-label="Main navigation">
        {views.map((view) => (
          <a key={view} href={`/?view=${view}`}>{view}</a>
        ))}
      </nav>
      {query.isError && (
        <div role="alert">
          <p>{query.error.message}</p>
          <button type="button" onClick={() => void query.refetch()}>Retry loading</button>
        </div>
      )}
      {query.isPending && (
        <section aria-label="Loading workspace" aria-busy="true">
          <output>Loading your workspace</output>
        </section>
      )}
      {query.isSuccess && <ProofList proofs={proofs} byCapability={byCapability} />}
    </main>
  );
}

function ProofList({ proofs, byCapability }: { proofs: Proof[]; byCapability: Map<number, Capability> }) {
  if (!proofs.length) return <p>No evidence yet. Add a proof point to start your shortlist.</p>;
  return (
    <ul>
      {proofs.map((p) => (
        <li key={p.id}>{p.claim} ({byCapability.get(p.capabilityId)?.name})</li>
      ))}
    </ul>
  );
}
