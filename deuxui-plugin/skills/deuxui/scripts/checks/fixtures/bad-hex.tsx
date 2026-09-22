// Real colours in real colour positions, including an all-digit one: #333 is a
// colour somebody wrote on purpose, and rejecting every all-decimal hex would
// throw it away with the PR numbers.
export function Drift() {
  return (
    <div style={{ color: "#333", borderColor: "#6366f1" }}>
      <span className="text-[#0ea5e9]">Status</span>
      <em style={{ background: "rgb(12, 34, 56)" }}>Due</em>
    </div>
  );
}
