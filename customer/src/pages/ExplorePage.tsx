import { useEffect, useRef, useState } from 'react'
import { api, type Product } from '../api'
import { Card, Spinner } from '../components/ui'
import ExploreChat from '../components/ExploreChat'

// Products grouped by the life-need they serve (not by SBI's internal taxonomy).
const GROUPS: { label: string; blurb: string; cats: string[]; icon: string }[] = [
  { label: 'Save', blurb: 'Keep your money safe and let it earn a little.', cats: ['accounts', 'deposits'], icon: '🏦' },
  { label: 'Grow your money', blurb: 'Build wealth over time, in small steps.', cats: ['investments'], icon: '🌱' },
  { label: 'Borrow', blurb: 'Funds for a goal, a home, a vehicle, or a gap.', cats: ['loans'], icon: '💳' },
  { label: 'Protect your family', blurb: 'Low-cost cover for the unexpected.', cats: ['insurance'], icon: '🛡️' },
  { label: 'Pay & spend', blurb: 'Everyday payments, made simpler.', cats: ['payments', 'cards'], icon: '⚡' },
]

export default function ExplorePage() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [activeCat, setActiveCat] = useState(GROUPS[0].label)
  const [ask, setAsk] = useState<{ product: Product; n: number } | null>(null)
  const askN = useRef(0)

  useEffect(() => {
    api.products().then(setProducts).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <Card className="p-5 text-sm text-rose-300">Couldn't reach APEX: {err}</Card>
  if (!products) return <Spinner />

  const group = GROUPS.find((g) => g.label === activeCat) ?? GROUPS[0]
  const items = products.filter((p) => group.cats.includes(p.category))
  const explain = (p: Product) => { askN.current += 1; setAsk({ product: p, n: askN.current }) }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold text-white sm:text-3xl">What SBI can help with</h1>
      <p className="mb-8 text-base text-slate-300">
        Pick a category, then tap a product — APEX explains it on the right, in plain language.
      </p>

      <div className="grid gap-4 lg:grid-cols-[180px_1fr_1.6fr]">
        {/* category rail (horizontal scroll on mobile, vertical on desktop) */}
        <aside className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
          {GROUPS.map((g) => {
            const active = g.label === activeCat
            return (
              <button
                key={g.label}
                onClick={() => setActiveCat(g.label)}
                className={`flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition lg:w-full ${
                  active
                    ? 'border-blue-400/50 bg-blue-600/20 text-white'
                    : 'border-white/10 text-slate-300 hover:bg-white/[0.08]'
                }`}
              >
                <span className="text-base">{g.icon}</span>
                <span className="font-medium">{g.label}</span>
              </button>
            )
          })}
        </aside>

        {/* products for the selected category */}
        <div>
          <p className="mb-3 text-xs text-slate-300">{group.blurb}</p>
          <div className="grid grid-cols-1 gap-3">
            {items.map((p) => {
              const active = ask?.product.product_id === p.product_id
              return (
                <button
                  key={p.product_id}
                  onClick={() => explain(p)}
                  className={`group flex h-full flex-col rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 hover:border-blue-400/40 hover:bg-white/[0.07] ${
                    active ? 'border-blue-400/50 bg-white/[0.07]' : 'border-white/10 bg-white/[0.07]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-slate-100">{p.name}</div>
                    {p.tax_saving && (
                      <span className="shrink-0 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[11px] text-emerald-300">
                        tax-saving
                      </span>
                    )}
                  </div>
                  <p className="mt-1 flex-1 text-sm text-slate-300">{p.primary_use || p.description}</p>
                  <span className="mt-3 text-xs font-medium text-blue-300 opacity-80 group-hover:opacity-100">
                    Ask APEX about this →
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* persistent Guide chat */}
        <ExploreChat ask={ask} />
      </div>
    </div>
  )
}
