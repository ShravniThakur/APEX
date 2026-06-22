import { useEffect, useState } from 'react'
import { api, type Product } from '../api'
import { Card, Spinner } from '../components/ui'

// Products grouped by the life-need they serve (not by SBI's internal taxonomy).
const GROUPS: { label: string; blurb: string; cats: string[] }[] = [
  { label: 'Save', blurb: 'Keep your money safe and let it earn a little.', cats: ['accounts', 'deposits'] },
  { label: 'Grow your money', blurb: 'Build wealth over time, in small steps.', cats: ['investments'] },
  { label: 'Borrow', blurb: 'Funds for a goal, a home, a vehicle, or a gap.', cats: ['loans'] },
  { label: 'Protect your family', blurb: 'Low-cost cover for the unexpected.', cats: ['insurance'] },
  { label: 'Pay & spend', blurb: 'Everyday payments, made simpler.', cats: ['payments', 'cards'] },
]

export default function ExplorePage() {
  const [products, setProducts] = useState<Product[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.products().then(setProducts).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <Card className="p-5 text-sm text-rose-600">Couldn't reach APEX: {err}</Card>
  if (!products) return <Spinner />

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold text-slate-900">What SBI can help with</h1>
      <p className="mb-5 text-sm text-slate-500">
        The full picture, grouped by what it's for — so you're not left guessing what to ask.
      </p>

      <div className="space-y-7">
        {GROUPS.map((g) => {
          const items = products.filter((p) => g.cats.includes(p.category))
          if (items.length === 0) return null
          return (
            <section key={g.label}>
              <h2 className="text-base font-semibold text-slate-800">{g.label}</h2>
              <p className="mb-3 text-xs text-slate-500">{g.blurb}</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {items.map((p) => (
                  <Card key={p.product_id} className="p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div className="font-medium text-slate-800">{p.name}</div>
                      {p.tax_saving && (
                        <span className="shrink-0 rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] text-emerald-700">
                          tax-saving
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-sm text-slate-600">{p.primary_use || p.description}</p>
                    {p.landing_url && (
                      <a href={p.landing_url} target="_blank" rel="noreferrer"
                        className="mt-2 inline-block text-xs text-indigo-600 hover:underline">
                        Learn more on SBI
                      </a>
                    )}
                  </Card>
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
