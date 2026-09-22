// Three tables that do fit a narrow screen, one per legitimate strategy.
export function Glossary() {
  // A small table with no actions: scrolling it hides nothing anyone must reach.
  // <table><tr><td>the retired layout, kept for reference</td></tr></table>
  return (
    <div className="overflow-x-auto">
      {/* <table><tr><td>an older glossary nobody renders</td></tr></table> */}
      <table>
        <thead><tr><th>Term</th><th>Meaning</th><th>Since</th></tr></thead>
        <tbody><tr><td>Lot</td><td>Samples received together</td><td>2024</td></tr></tbody>
      </table>
    </div>
  );
}

export function PinnedQueue({ rows }: { rows: { id: string }[] }) {
  // A wide data table whose actions column is pinned, so it never scrolls away.
  return (
    <div className="overflow-x-auto">
      <table>
        <thead><tr>
          <th>Sample</th><th>Product</th><th>Target</th><th>Customer</th>
          <th>Testing</th><th>Intake</th><th>Facility</th>
          <th className="sticky right-0 bg-surface">Action</th>
        </tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.id}><td>{r.id}</td>
            <td className="sticky right-0 bg-surface"><a href={`/samples/${r.id}`}>Open sample</a></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

export function CardQueue({ rows }: { rows: { id: string }[] }) {
  // Cards below md, the table from md up: every field and action on both.
  return (
    <>
      <ul className="md:hidden">{rows.map((r) => (
        <li key={r.id}>{r.id} <a href={`/samples/${r.id}`}>Open sample</a></li>
      ))}</ul>
      <table className="hidden md:table">
        <thead><tr>
          <th>Sample</th><th>Product</th><th>Target</th><th>Customer</th>
          <th>Testing</th><th>Intake</th><th>Facility</th><th>Action</th>
        </tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.id}><td>{r.id}</td><td><a href={`/samples/${r.id}`}>Open sample</a></td></tr>
        ))}</tbody>
      </table>
    </>
  );
}
