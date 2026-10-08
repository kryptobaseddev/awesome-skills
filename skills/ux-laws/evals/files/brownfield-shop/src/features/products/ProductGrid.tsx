import { useQuery } from '@tanstack/react-query'
import { ProductCard } from '../../components/cards/ProductCard'
export function ProductGrid() {
  const { data } = useQuery({ queryKey: ['products'], queryFn: () => fetch('/api/products').then(r => r.json()) })
  return <div className="grid grid-cols-4 gap-6">{data?.map((p: any) => <ProductCard key={p.id} product={p} />)}</div>
}
