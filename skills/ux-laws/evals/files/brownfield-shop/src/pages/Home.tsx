import { Button } from '../components/ui/Button'
import { FeatureCard } from '../components/cards/FeatureCard'
import { ProductGrid } from '../features/products/ProductGrid'
import { DealsStrip } from '../features/products/DealsStrip'
export default function Home() {
  return (
    <main className="font-['Inter']">
      <section className="text-center py-24 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 text-white">
        <h1 className="text-5xl">Build the future of shopping</h1>
        <p>Welcome back! Everything you need, all in one place.</p>
        <Button>Get started</Button>
        <Button variant="secondary">Learn more</Button>
      </section>
      <div className="grid grid-cols-3 gap-6">
        <FeatureCard icon="⚡" title="Fast" body="Lightning fast shipping." />
        <FeatureCard icon="🛡" title="Secure" body="Bank-grade security." />
        <FeatureCard icon="✨" title="Smart" body="AI-powered picks." />
      </div>
      <DealsStrip />
      <ProductGrid />
    </main>
  )
}
