import type { ReactNode } from 'react'

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>{children}</div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return <div className="p-8 text-center text-slate-400">{label}</div>
}
