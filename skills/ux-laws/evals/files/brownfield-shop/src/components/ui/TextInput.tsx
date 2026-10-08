export const TextInput = ({ label, ...rest }: any) => (
  <label className="block"><span className="text-[13px] text-[#6b7280]">{label}</span><input {...rest} className="border rounded-2xl px-2 py-1 text-[14px]" /></label>
)
