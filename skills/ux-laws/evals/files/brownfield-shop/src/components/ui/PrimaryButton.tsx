export const PrimaryButton = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} style={{ background: '#6366f1', color: '#fff', borderRadius: 16, padding: '6px 10px', fontSize: 13 }}>{label}</button>
)
