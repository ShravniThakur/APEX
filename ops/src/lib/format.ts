export const inr = (n: number | null | undefined) =>
  n == null ? '—' : '₹' + Math.round(n).toLocaleString('en-IN')

export const human = (s: string) =>
  s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export const dateShort = (s: string | null) =>
  s ? new Date(s).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '—'

export const dateTime = (s: string | null) =>
  s ? new Date(s).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'

export const LANG: Record<string, string> = {
  en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali',
}

export const outcomeStyle: Record<string, string> = {
  act: 'bg-emerald-100 text-emerald-800',
  wait: 'bg-amber-100 text-amber-800',
  escalate: 'bg-rose-100 text-rose-800',
}

export const responseStyle: Record<string, string> = {
  clicked: 'bg-blue-100 text-blue-800',
  completed: 'bg-emerald-100 text-emerald-800',
  dismissed: 'bg-slate-200 text-slate-700',
  ignored: 'bg-amber-100 text-amber-800',
}
