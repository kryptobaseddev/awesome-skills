export function Modal({ open, title, children, onClose }: any) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg p-6 w-[480px]">
        <h2 className="text-[19px] font-semibold">{title}</h2>
        {children}
        <button onClick={onClose} className="text-[11px]">x</button>
      </div>
    </div>
  )
}
