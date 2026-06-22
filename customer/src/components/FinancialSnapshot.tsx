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

  const open = data.suggestions.filter((s) => s.response !== 'dismissed' && s.response !== 'completed')

  return (
    <div className="space-y-4">
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
            <div className="mb-3 text-xs text-slate-400">Where your money went (last 90 days)</div>
            <DonutChart data={data.spend_by_category.map((s) => ({ label: s.category, amount: s.amount }))} />
          </div>
        )}
      </Card>

      {/* What APEX suggests (the agent's ethics-filtered outreach, shown in-app) */}
      <div>
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          What APEX suggests for you
        </div>
        {open.length === 0 ? (
          <Card className="p-4 text-sm text-slate-300">
            Nothing needs your attention right now — APEX will reach out when a real moment comes up.
          </Card>
        ) : (
          <div className="space-y-3">
            {open.map((s) => (
              <Card key={s.action_id} className="p-4">
                <p className="whitespace-pre-line text-sm text-slate-100">{s.message_text}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <a href={s.open_url} target="_blank" rel="noreferrer"
                    className="rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white hover:bg-blue-500">
                    Open in YONO / SBI
                  </a>
                  <button onClick={() => respond(s.adopt_url)}
                    className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-emerald-300 hover:bg-emerald-500/25">
                    I've done this
                  </button>
                  <button onClick={() => respond(s.dismiss_url)}
                    className="rounded-lg px-3 py-1.5 text-slate-400 hover:bg-white/10">
                    Not interested
                  </button>
                  <button onClick={() => explain(s.action_id, s.why_url)}
                    className="ml-auto rounded-lg px-3 py-1.5 text-slate-400 underline-offset-2 hover:underline">
                    Why am I seeing this?
                  </button>
                </div>
                {why[s.action_id] && (
                  <p className="mt-3 border-t border-white/10 pt-3 text-sm italic text-slate-300">
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

// Dependency-free SVG donut. r=15.915 makes the circle's circumference exactly 100, so each
// segment's length is just its percentage; -rotate-90 starts the first slice at the top and each
// later slice is offset by the running total. Blue-family palette to match the SBI theme.
const DONUT_COLORS = ['#3b82f6', '#0ea5e9', '#22d3ee', '#60a5fa', '#1d4ed8', '#38bdf8', '#818cf8']

function DonutChart({ data }: { data: { label: string; amount: number }[] }) {
  const total = data.reduce((s, d) => s + d.amount, 0) || 1
  let cum = 0
  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 42 42" className="h-32 w-32 shrink-0 -rotate-90">
        <circle cx="21" cy="21" r="15.915" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        {data.map((d, i) => {
          const pct = (d.amount / total) * 100
          const seg = (
            <circle
              key={i}
              cx="21"
              cy="21"
              r="15.915"
              fill="none"
              stroke={DONUT_COLORS[i % DONUT_COLORS.length]}
              strokeWidth="5"
              strokeDasharray={`${pct} ${100 - pct}`}
              strokeDashoffset={-cum}
            />
          )
          cum += pct
          return seg
        })}
      </svg>
      <div className="min-w-0 flex-1 space-y-1.5">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }}
            />
            <span className="flex-1 truncate capitalize text-slate-300">{d.label}</span>
            <span className="tabular-nums text-slate-400">{inr(d.amount)}</span>
            <span className="w-9 text-right tabular-nums text-slate-500">
              {Math.round((d.amount / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Stat({ label, value, big }: { label: string; value: string; big?: boolean }) {
  return (
    <div>
      <div className={`font-semibold text-white ${big ? 'text-2xl' : 'text-lg'}`}>{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  )
}
