export default function DealCard({ deal }: any) {
  return (
    <div style={{ borderRadius: 20, boxShadow: '0 10px 30px rgba(99,102,241,.3)', padding: 18 }}>
      <img src={deal.img} />
      <span style={{ fontSize: 12, color: '#a855f7' }}>{deal.badge}</span>
      <h4>{deal.name}</h4>
      <button style={{ fontSize: 12 }}>Grab deal</button>
    </div>
  )
}
