// A SCREEN whose name starts with Email -- the settings page for email
// notifications. Named like an email, rendered like a page: it must still be read
// as a screen, or the email exemption would swallow a real defect.
export function EmailDeliveryLog({ rows }: { rows: { id: string }[] }) {
  return (
    <div className="overflow-auto">
      <table className="w-full">
        <thead><tr>
          <th>Sent</th><th>Recipient</th><th>Template</th><th>Status</th>
          <th>Opens</th><th>Clicks</th><th>Bounce</th><th>Action</th>
        </tr></thead>
        <tbody>{rows.map((r) => <tr key={r.id}><td>{r.id}</td></tr>)}</tbody>
      </table>
    </div>
  );
}
