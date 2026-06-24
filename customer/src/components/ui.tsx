import type { CSSProperties, ReactNode } from 'react'

export function Card(
  { children, className = '', style }:
  { children: ReactNode; className?: string; style?: CSSProperties },
) {
  return (
    <div style={style} className={`rounded-xl border border-white/25 bg-gradient-to-br from-blue-300/[0.10] to-blue-700/[0.04] shadow-[0_0_0_1px_rgba(96,165,250,0.12),0_0_16px_-3px_rgba(59,130,246,0.30),0_8px_20px_-10px_rgba(0,0,0,0.55)] ${className}`}>{children}</div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return <div className="p-8 text-center text-slate-300">{label}</div>
}
