import DealCard from '../../components/cards/DealCard'
import { ItemCard } from '../../components/cards/ItemCard'
import { useEffect, useState } from 'react'
export function DealsStrip() {
  const [deals, setDeals] = useState<any[]>([])
  useEffect(() => { fetch('/api/deals').then(r => r.json()).then(setDeals) }, [])
  return (
    <section className="flex gap-4 overflow-x-auto">
      {deals.map(d => <DealCard key={d.id} deal={d} />)}
      {deals.slice(0, 2).map(d => <ItemCard key={'i' + d.id} item={d} />)}
    </section>
  )
}
