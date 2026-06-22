import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type CustomerSummary } from '../api'
import { Badge, Card, ErrorBox, Header, Spinner } from '../components/ui'
import { inr, LANG, outcomeStyle } from '../lib/format'

export default function Customers() {
  const [rows, setRows] = useState<CustomerSummary[] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.customers().then(setRows).catch((e) => setErr(String(e)))
  }, [])

  if (err) return <ErrorBox err={err} />
  if (!rows) return <Spinner />

  // Customers with signals first, then by name.
  const sorted = [...rows].sort((a, b) => b.signal_count - a.signal_count || a.name.localeCompare(b.name))

  return (
    <div>
      <Header title="Customers" subtitle={`${rows.length} customers · ${rows.filter((r) => r.signal_count).length} with active signals`} />
      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Income</th>
              <th className="px-4 py-3">Signals</th>
              <th className="px-4 py-3">Decisions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sorted.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <Link to={`/customers/${c.id}`} className="font-medium text-slate-900 hover:underline">
                    {c.name}
                  </Link>
                  <div className="text-xs text-slate-400">
                    {c.age} · {c.city_tier} · {LANG[c.language_pref ?? ''] ?? c.language_pref}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-600">{c.customer_type}</td>
                <td className="px-4 py-3 tabular-nums text-slate-600">{inr(c.monthly_income)}</td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {c.signal_types.length === 0 && <span className="text-slate-300">—</span>}
                    {c.signal_types.map((s) => (
                      <Badge key={s} className="bg-slate-100 text-slate-600">{s.replace(/_/g, ' ')}</Badge>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(c.decision_outcomes).map(([o, n]) => (
                      <Badge key={o} className={outcomeStyle[o] ?? 'bg-slate-100 text-slate-600'}>
                        {o} {n}
                      </Badge>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
