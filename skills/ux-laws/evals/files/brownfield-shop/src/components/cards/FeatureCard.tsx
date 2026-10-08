export const FeatureCard = ({ icon, title, body }: any) => (
  <div className="rounded-2xl shadow-lg p-6 text-center"><div className="text-indigo-500">{icon}</div><h3>{title}</h3><p className="text-gray-500">{body}</p></div>
)
