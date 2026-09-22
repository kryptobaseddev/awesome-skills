// Field report, deuxui 5.24.4: the owner filed this table twice -- "you have to
// scroll all the way to the right to get all details", then "it is cutoff on the
// right side". 1563px of table in a 1118px box, the Action column in the hidden
// 445px. S-RESP-TABLE scored it PASS because the wrapper says overflow-auto.
export function WideQueue({ rows }: { rows: { id: string }[] }) {
  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead><tr>
          <th>Rush service</th><th>Sample / AX ID</th><th>Product</th><th>Target</th>
          <th>Customer</th><th>Testing</th><th>Vial plan</th><th>Intake</th>
          <th>Facility</th><th>Waiting</th><th>Certificate</th><th>Action</th>
        </tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.id}</td></tr>)}</tbody>
      </table>
    </div>
  );
}
