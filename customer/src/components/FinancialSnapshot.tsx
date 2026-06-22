import { useEffect, useState } from 'react'
import { api, type Insights } from '../api'
import { Card, Spinner } from './ui'

const inr = (n: number | null | undefined) =>
  n == null ? '—' : '₹' + Math.round(n).toLocaleString('en-IN')

export default function FinancialSnapshot({ customerId }: { customerId: string }) {
  const [data, setData] = useState<Insights | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [why, setWhy] = useState<Record<string, string>>({})

  const load = () => api.insights(customerId).then(setData).catch((e) => setErr(String(e)))
  useEffect(() => { load() }, [customerId])
  // reset any open explanations when switching customer
  useEffect(() => { setWhy({}) }, [customerId])

  const respond = async (url: string) => {
    try { await fetch(url) } catch { /* ignore */ }
    load()
  }

  const explain = async (actionId: string, whyUrl: string) => {
    if (why[actionId]) { setWhy((w) => { const n = { ...w }; delete n[actionId]; return n }); return }
    try {
      const r = await api.explain(whyUrl)
      setWhy((w) => ({ ...w, [actionId]: r.explanation }))
    } catch { /* ignore */ }
  }

  if (err) return null
  if (!data) return <Spinner />

  const maxSpend = Math.max(1, ...data.spend_by_category.map((s) => s.amount))
  const open = data.suggestions.filter((s) => s.response !== 'dismissed' && s.response !== 'completed')

  return (
    <div className="mb-5 space-y-4">
      {/* Money at a glance */}
      <Card className="p-5">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Your money at a glance</div>
        <div className="mt-2 grid grid-cols-3 gap-4">
          <Stat label="Total balance" value={inr(data.balance)} big />
          <Stat label="Monthly income" value={inr(data.monthly_income)} />
          <Stat label="Received (90 days)" value={inr(data.credits_90d)} />
        </div>
        {data.spend_by_category.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 text-xs text-slate-500">Where your money went (last 90 days)</div>
            <div className="space-y-1.5">
              {data.spend_by_category.map((s) => (
                <div key={s.category} className="flex items-center gap-3">
                  <div className="w-24 shrink-0 text-sm capitalize text-slate-600">{s.category}</div>
                  <div className="h-2 flex-1 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-indigo-400" style={{ width: `${(s.amount / maxSpend) * 100}%` }} />
                  </div>
                  <div className="w-20 text-right text-sm tabular-nums text-slate-500">{inr(s.amount)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* What APEX suggests (the agent's ethics-filtered outreach, shown in-app) */}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          What APEX suggests for you
        </div>
        {open.length === 0 ? (
          <Card className="p-4 text-sm text-slate-500">
            Nothing needs your attention right now — APEX will reach out when a real moment comes up.
          </Card>
        ) : (
          <div className="space-y-3">
            {open.map((s) => (
              <Card key={s.action_id} className="p-4">
                <p className="whitespace-pre-line text-sm text-slate-800">{s.message_text}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <a href={s.open_url} target="_blank" rel="noreferrer"
                    className="rounded-lg bg-indigo-600 px-3 py-1.5 font-medium text-white hover:bg-indigo-700">
                    Open in YONO / SBI
                  </a>
                  <button onClick={() => respond(s.adopt_url)}
                    className="rounded-lg bg-emerald-50 px-3 py-1.5 text-emerald-700 hover:bg-emerald-100">
                    I've done this
                  </button>
                  <button onClick={() => respond(s.dismiss_url)}
                    className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-slate-100">
                    Not interested
                  </button>
                  <button onClick={() => explain(s.action_id, s.why_url)}
                    className="ml-auto rounded-lg px-3 py-1.5 text-slate-500 underline-offset-2 hover:underline">
                    Why am I seeing this?
                  </button>
                </div>
                {why[s.action_id] && (
                  <p className="mt-3 border-t border-slate-100 pt-3 text-sm italic text-slate-600">
                    {why[s.action_id]}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value, big }: { label: string; value: string; big?: boolean }) {
  return (
    <div>
      <div className={`font-semibold text-slate-900 ${big ? 'text-2xl' : 'text-lg'}`}>{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  )
}
