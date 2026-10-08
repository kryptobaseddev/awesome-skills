import { Button } from '../ui/Button'
export function ProductCard({ product }: any) {
  return (
    <div className="rounded-2xl shadow-lg p-4 bg-white">
      <img src={product.image} />
      <h3 className="text-[17px]">{product.name}</h3>
      <p style={{ color: '#4f46e5' }}>${product.price}</p>
      <Button onClick={() => {}}>Add to cart</Button>
    </div>
  )
}
