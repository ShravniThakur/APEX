import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, type Insights } from '../api'
import { Card, Spinner } from './ui'

const inr = (n: number | null | undefined) =>
  n == null ? '—' : '₹' + Math.round(n).toLocaleString('en-IN')

// Compact rupee for tight chips: ₹2.8L, ₹90k, ₹1.2Cr.
const inrShort = (n: number | null | undefined) => {
  if (n == null) return '—'
  const a = Math.abs(n)
  if (a >= 1e7) return '₹' + (n / 1e7).toFixed(a >= 1e8 ? 0 : 1).replace(/\.0$/, '') + 'Cr'
  if (a >= 1e5) return '₹' + (n / 1e5).toFixed(a >= 1e6 ? 0 : 1).replace(/\.0$/, '') + 'L'
  if (a >= 1e3) return '₹' + Math.round(n / 1e3) + 'k'
  return '₹' + Math.round(n)
}

// Count up to a target once, easing out. Respects reduced-motion (jumps straight to the value).
function useCountUp(target: number, ms = 900) {
  const [val, setVal] = useState(0)
  const raf = useRef<number>()
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { setVal(target); return }
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ms)
      setVal(target * (1 - Math.pow(1 - t, 3))) // easeOutCubic
      if (t < 1) raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
    return () => { if (raf.current) cancelAnimationFrame(raf.current) }
  }, [target, ms])
  return val
}

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

  // Safety cushion = how many months the balance would cover at the current income level.
  // Honest, accurate metric derived from real figures (unlike a "total spent", which the API
  // only exposes as the top-5 categories — so we never present that as a complete number).
  const cushion =
    data.monthly_income && data.monthly_income > 0 ? data.balance / data.monthly_income : null

  return (
    <div className="space-y-4">
      {/* ---- Hero: total balance ---- */}
      <HeroBalance balance={data.balance} received90d={data.credits_90d} />

      {/* ---- Metric chips ---- */}
      <div className="grid grid-cols-3 gap-3">
        <Metric
          icon={<CoinsIcon />}
          label="Monthly income"
          value={inrShort(data.monthly_income)}
          delay={60}
        />
        <Metric
          icon={<ArrowInIcon />}
          label="Received · 90d"
          value={inrShort(data.credits_90d)}
          delay={120}
        />
        <Metric
          icon={<ShieldIcon />}
          label="Safety cushion"
          value={cushion == null ? '—' : `${cushion.toFixed(1)} mo`}
          hint={cushion == null ? undefined : 'balance ÷ income'}
          delay={180}
        />
      </div>

      {/* ---- Spending breakdown ---- */}
      {data.spend_by_category.length > 0 && (
        <Card className="apex-rise p-5" style={{ animationDelay: '220ms' }}>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-blue-300"><PieIcon /></span>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-300">
              Where your money went
            </span>
            <span className="ml-auto text-[11px] text-slate-400">last 90 days</span>
          </div>
          <DonutChart data={data.spend_by_category.map((s) => ({ label: s.category, amount: s.amount }))} />
        </Card>
      )}

      {/* ---- What APEX suggests (the agent's ethics-filtered outreach, shown in-app) ---- */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <span className="text-blue-300"><SparkIcon /></span>
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-300">
            What APEX suggests for you
          </span>
        </div>
        {open.length === 0 ? (
          <Card className="p-4 text-sm text-slate-300">
            Nothing needs your attention right now — APEX will reach out when a real moment comes up.
          </Card>
        ) : (
          <div className="space-y-3">
            {open.map((s) => (
              <Card key={s.action_id} className="border-l-2 border-l-blue-500/60 p-4">
                <p className="whitespace-pre-line text-sm text-slate-100">{s.message_text}</p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <a href={s.open_url} target="_blank" rel="noreferrer"
                    className="rounded-lg bg-blue-600 px-3 py-1.5 font-medium text-white transition hover:bg-blue-500">
                    Open in YONO / SBI
                  </a>
                  <button onClick={() => respond(s.adopt_url)}
                    className="rounded-lg bg-emerald-500/15 px-3 py-1.5 text-emerald-300 transition hover:bg-emerald-500/25">
                    I've done this
                  </button>
                  <button onClick={() => respond(s.dismiss_url)}
                    className="rounded-lg px-3 py-1.5 text-slate-300 transition hover:bg-white/10">
                    Not interested
                  </button>
                  <button onClick={() => explain(s.action_id, s.why_url)}
                    className="ml-auto rounded-lg px-3 py-1.5 text-slate-300 underline-offset-2 transition hover:underline">
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

// --------------------------------------------------------------------------- //
// Hero — the balance as the centerpiece, on a blue gradient with an ornamental
// glow + wave. The wave is purely decorative (NOT a data chart): the API gives
// no balance time-series, so nothing here implies a real trend line.
// --------------------------------------------------------------------------- //
function HeroBalance({ balance, received90d }: { balance: number; received90d: number }) {
  const shown = useCountUp(balance)
  return (
    <div className="apex-rise relative overflow-hidden rounded-2xl border border-blue-400/20 bg-gradient-to-br from-blue-600/30 via-blue-500/10 to-transparent p-5 shadow-lg shadow-blue-950/30">
      {/* soft corner glow */}
      <div className="pointer-events-none absolute -right-12 -top-16 h-44 w-44 rounded-full bg-blue-500/25 blur-3xl" />
      {/* ornamental wave along the bottom (decorative, not data) */}
      <svg
        className="pointer-events-none absolute inset-x-0 bottom-0 h-16 w-full text-blue-400/20"
        viewBox="0 0 400 60" preserveAspectRatio="none" aria-hidden="true"
      >
        <path d="M0 38 C 60 12, 120 12, 180 32 S 320 56, 400 26 L400 60 L0 60 Z"
          fill="currentColor" />
        <path d="M0 44 C 70 24, 140 26, 210 40 S 330 58, 400 38"
          fill="none" stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.5" />
      </svg>

      <div className="relative">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-blue-100/90">
          <WalletIcon /> Total balance
        </div>
        <div className="mt-1.5 text-4xl font-bold tabular-nums tracking-tight text-white">
          {inr(shown)}
        </div>
        {received90d > 0 && (
          <div className="mt-2.5 inline-flex items-center gap-1.5 rounded-full bg-emerald-500/15 px-2.5 py-1 text-xs font-medium text-emerald-300 ring-1 ring-inset ring-emerald-400/20">
            <TrendUpIcon />
            {inr(received90d)} received · last 90 days
          </div>
        )}
      </div>
    </div>
  )
}

function Metric(
  { icon, label, value, hint, delay = 0 }:
  { icon: ReactNode; label: string; value: string; hint?: string; delay?: number },
) {
  return (
    <Card className="apex-rise p-3.5 transition hover:bg-white/[0.08]" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex items-center gap-1.5 text-blue-300">{icon}</div>
      <div className="mt-2 text-lg font-semibold tabular-nums text-white">{value}</div>
      <div className="text-[11px] leading-tight text-slate-300">{label}</div>
      {hint && <div className="mt-0.5 text-[10px] text-slate-400">{hint}</div>}
    </Card>
  )
}

// --------------------------------------------------------------------------- //
// Dependency-free SVG donut. r=15.915 makes the circle's circumference exactly
// 100, so each segment's length is just its percentage; -rotate-90 starts the
// first slice at the top and each later slice is offset by the running total.
// The hole now holds the total, so the donut reads as a real summary.
// --------------------------------------------------------------------------- //
const DONUT_COLORS = ['#3b82f6', '#0ea5e9', '#22d3ee', '#60a5fa', '#1d4ed8', '#38bdf8', '#818cf8']

function DonutChart({ data }: { data: { label: string; amount: number }[] }) {
  const total = data.reduce((s, d) => s + d.amount, 0) || 1
  let cum = 0
  return (
    <div className="flex items-center gap-5">
      <div className="relative h-32 w-32 shrink-0">
        <svg viewBox="0 0 42 42" className="h-32 w-32 -rotate-90">
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
                strokeLinecap="round"
              />
            )
            cum += pct
            return seg
          })}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-semibold tabular-nums text-white">{inrShort(total)}</span>
          <span className="text-[10px] text-slate-400">spent</span>
        </div>
      </div>
      <div className="min-w-0 flex-1 space-y-1.5">
        {data.map((d, i) => (
          <div key={i} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ background: DONUT_COLORS[i % DONUT_COLORS.length] }}
            />
            <span className="flex-1 truncate capitalize text-slate-300">{d.label}</span>
            <span className="tabular-nums text-slate-300">{inr(d.amount)}</span>
            <span className="w-9 text-right tabular-nums text-slate-400">
              {Math.round((d.amount / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// Inline stroke icons (no icon dependency). 14px, currentColor.
// --------------------------------------------------------------------------- //
const ico = 'h-3.5 w-3.5'
const sp = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const }

function WalletIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1" /><path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7H7a2 2 0 0 1-2-2" /><circle cx="16" cy="13" r="1.2" fill="currentColor" stroke="none" /></svg>)
}
function CoinsIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><ellipse cx="9" cy="7" rx="6" ry="3" /><path d="M3 7v5c0 1.7 2.7 3 6 3" /><path d="M15 9.5c2.6.4 4.5 1.6 4.5 3v5c0 1.7-2.7 3-6 3s-6-1.3-6-3v-1" /></svg>)
}
function ArrowInIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M12 5v10" /><path d="M7 12l5 5 5-5" /><path d="M5 19h14" /></svg>)
}
function ShieldIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" /><path d="M9 12l2 2 4-4" /></svg>)
}
function TrendUpIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M4 16l5-5 3 3 7-7" /><path d="M14 7h6v6" /></svg>)
}
function PieIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M12 3v9l7 4" /><circle cx="12" cy="12" r="9" /></svg>)
}
function SparkIcon() {
  return (<svg className={ico} viewBox="0 0 24 24" {...sp}><path d="M12 3l1.8 4.7L18 9.5l-4.2 1.8L12 16l-1.8-4.7L6 9.5l4.2-1.8z" /></svg>)
}
