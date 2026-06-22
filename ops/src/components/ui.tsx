import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</div>
  )
}

export function Badge({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  )
}

export function Header(
  { title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode },
) {
  return (
    <div className="mb-6 flex items-end justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Card className="p-5">
      <div className="text-3xl font-semibold text-slate-900">{value}</div>
      <div className="mt-1 text-sm text-slate-500">{label}</div>
    </Card>
  )
}

export function Bars({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1])
  const max = Math.max(1, ...entries.map(([, v]) => v))
  if (entries.length === 0) return <p className="text-sm text-slate-400">No data yet.</p>
  return (
    <div className="space-y-2">
      {entries.map(([k, v]) => (
        <div key={k} className="flex items-center gap-3">
          <div className="w-44 shrink-0 truncate text-sm text-slate-600">{k.replace(/_/g, ' ')}</div>
          <div className="h-2 flex-1 rounded-full bg-slate-100">
            <div className="h-2 rounded-full bg-slate-700" style={{ width: `${(v / max) * 100}%` }} />
          </div>
          <div className="w-8 text-right text-sm tabular-nums text-slate-500">{v}</div>
        </div>
      ))}
    </div>
  )
}

export function ErrorBox({ err }: { err: string }) {
  return (
    <Card className="border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
      <div className="font-medium">Couldn't reach the API.</div>
      <div className="mt-1">{err}</div>
      <div className="mt-2 text-rose-500">
        Is the backend running? <code>uvicorn apex.api.app:app --port 8000</code>
      </div>
    </Card>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return <div className="p-8 text-center text-slate-400">{label}</div>
}
