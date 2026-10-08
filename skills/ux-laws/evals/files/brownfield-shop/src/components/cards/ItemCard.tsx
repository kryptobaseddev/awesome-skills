import { PrimaryButton } from '../ui/PrimaryButton'
export const ItemCard = ({ item }: any) => (
  <div className="rounded-xl shadow-md p-3 bg-white">
    <img src={item.thumb} className="w-full" />
    <div className="text-[15px] font-bold">{item.title}</div>
    <div className="text-center text-[#6366f1]">{item.cost}</div>
    <PrimaryButton label="Buy" onClick={() => {}} />
  </div>
)
