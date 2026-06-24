import { useEffect, useState } from 'react'

// A focus (coverflow) carousel: the centre card is scaled up and brightly glowing, side cards are
// smaller and dimmed, and it auto-advances — so each card zooms in as it reaches the centre, then
// slides out as the next grows in. Each card's illustration also animates. Pure CSS/SVG, free.
const FEATURES: { kind: Kind; title: string; blurb: string }[] = [
  { kind: 'account', title: 'Open an account', blurb: 'APEX walks you to the right SBI account in plain language, then hands you a ready-to-go link.' },
  { kind: 'ask', title: 'Ask about your money', blurb: '“Can I afford this?” “How’s my spending?” Real, computed answers — never guesses.' },
  { kind: 'shield', title: 'On your side', blurb: 'At a hard moment it waits and offers insight instead of selling. Calm, never pushy.' },
  { kind: 'language', title: 'Speaks your language', blurb: 'Hindi, Tamil, Telugu, Bengali and more — not English-first.' },
  { kind: 'moment', title: 'The right moment', blurb: 'Notices a real moment in your finances and reaches out only when it genuinely matters.' },
  { kind: 'connected', title: 'All of SBI, connected', blurb: 'Save, grow, borrow, protect, pay — your whole financial life in one place.' },
]

export default function FeatureCarousel() {
  const [active, setActive] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % FEATURES.length), 3200)
    return () => clearInterval(t)
  }, [])

  const n = FEATURES.length
  return (
    <div className="relative mx-auto h-[340px] w-full max-w-6xl" style={{ perspective: '1200px' }}>
      <style>{KEYFRAMES}</style>
      {FEATURES.map((f, i) => {
        let off = i - active
        if (off > n / 2) off -= n
        if (off < -n / 2) off += n
        const abs = Math.abs(off)
        const isCenter = off === 0
        return (
          <article
            key={i}
            className="absolute left-1/2 top-2 w-[400px] overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.08] to-white/[0.02] p-1 shadow-2xl shadow-blue-950/50"
            style={{
              transform: `translateX(calc(-50% + ${off * 350}px)) scale(${isCenter ? 1 : 0.82})`,
              opacity: abs === 0 ? 1 : abs === 1 ? 0.5 : 0,
              zIndex: 10 - abs,
              filter: isCenter ? 'none' : 'saturate(0.7) brightness(0.8)',
              transition: 'transform .7s cubic-bezier(.22,.61,.36,1), opacity .7s ease, filter .7s ease',
              pointerEvents: isCenter ? 'auto' : 'none',
            }}
          >
            <div className="relative flex h-44 items-center justify-center overflow-hidden rounded-[1.35rem] bg-gradient-to-br from-blue-500/40 via-blue-700/25 to-indigo-900/30">
              <div className="absolute -inset-10 bg-[radial-gradient(circle_at_50%_45%,rgba(96,165,250,0.55),transparent_60%)]" />
              <Illustration kind={f.kind} active={isCenter} />
            </div>
            <div className="px-5 pb-5 pt-4">
              <h3 className="text-lg font-semibold text-white">{f.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-300">{f.blurb}</p>
            </div>
          </article>
        )
      })}

      {/* dots */}
      <div className="absolute -bottom-2 left-1/2 flex -translate-x-1/2 gap-1.5">
        {FEATURES.map((_, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            className={`h-1.5 rounded-full transition-all ${i === active ? 'w-5 bg-blue-400' : 'w-1.5 bg-white/25'}`}
            aria-label={`Go to slide ${i + 1}`}
          />
        ))}
      </div>
    </div>
  )
}

type Kind = 'account' | 'ask' | 'shield' | 'language' | 'moment' | 'connected'

const KEYFRAMES = `
  @keyframes fc-float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-7px) } }
  @keyframes fc-pulse { 0%,100% { opacity:.45; transform: scale(.9) } 50% { opacity:1; transform: scale(1.08) } }
  @keyframes fc-spin  { to { transform: rotate(360deg) } }
  @keyframes fc-wave  { 0% { opacity:.85; transform: scale(.35) } 100% { opacity:0; transform: scale(1.25) } }
  @keyframes fc-rise  { 0% { opacity:0; transform: translateY(10px) } 30%,70% { opacity:1 } 100% { opacity:0; transform: translateY(-16px) } }
  .fc-fb { transform-box: fill-box; transform-origin: center; }
  .fc-float { animation: fc-float 3s ease-in-out infinite; }
  .fc-pulse { animation: fc-pulse 2s ease-in-out infinite; }
  .fc-spin  { animation: fc-spin 9s linear infinite; }
`

// Each motif is a small animated SVG. `active` (centre card) runs the motion; off-centre stays calm.
function Illustration({ kind, active }: { kind: Kind; active: boolean }) {
  const run = active ? '' : 'paused'
  const sty = { animationPlayState: active ? 'running' : ('paused' as const) }
  return (
    <svg viewBox="0 0 160 120" width="200" height="150" className="relative">
      {kind === 'account' && (
        <g>
          <rect x="40" y="58" width="80" height="48" rx="8" fill="#1e3a8a" stroke="#93c5fd" strokeWidth="2" />
          <rect x="48" y="68" width="30" height="5" rx="2.5" fill="#bfdbfe" />
          <rect x="48" y="80" width="50" height="4" rx="2" fill="#3b82f6" />
          <g className={`fc-fb ${run ? '' : 'fc-float'}`} style={sty}>
            <circle className="fc-float" style={sty} cx="100" cy="42" r="16" fill="#fbbf24" />
            <text x="100" y="48" textAnchor="middle" fontSize="18" fill="#78350f" fontWeight="bold">₹</text>
          </g>
        </g>
      )}
      {kind === 'ask' && (
        <g>
          <rect x="34" y="40" width="62" height="40" rx="12" fill="#3b82f6" />
          <path d="M48 80 l0 12 l14 -12 z" fill="#3b82f6" />
          <rect className="fc-pulse fc-fb" style={sty} x="78" y="62" width="50" height="32" rx="11" fill="#bfdbfe" />
          <circle cx="58" cy="60" r="3" fill="#fff" /><circle cx="68" cy="60" r="3" fill="#fff" /><circle cx="78" cy="60" r="3" fill="#fff" />
        </g>
      )}
      {kind === 'shield' && (
        <g>
          <circle className="fc-pulse fc-fb" style={sty} cx="80" cy="60" r="34" fill="#60a5fa" opacity="0.4" />
          <path d="M80 30 l26 10 v18 c0 18 -12 28 -26 34 c-14 -6 -26 -16 -26 -34 v-18 z" fill="#1d4ed8" stroke="#93c5fd" strokeWidth="2" />
          <path d="M70 60 l7 8 l16 -18" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        </g>
      )}
      {kind === 'language' && (
        <g>
          {[0, 1, 2].map((k) => (
            <circle key={k} className="fc-fb" style={{ ...sty, animation: `fc-wave 2.4s ease-out ${k * 0.8}s infinite` }}
              cx="80" cy="60" r="34" fill="none" stroke="#93c5fd" strokeWidth="2.5" />
          ))}
          <circle cx="80" cy="60" r="14" fill="#3b82f6" />
          <text x="80" y="66" textAnchor="middle" fontSize="15" fill="#fff" fontWeight="bold">अ</text>
        </g>
      )}
      {kind === 'moment' && (
        <g>
          <circle className="fc-pulse fc-fb" style={sty} cx="80" cy="60" r="32" fill="#60a5fa" opacity="0.35" />
          <circle cx="80" cy="60" r="26" fill="#1e3a8a" stroke="#93c5fd" strokeWidth="2" />
          <g className={`fc-fb ${run ? '' : 'fc-spin'}`} style={{ ...sty, transformOrigin: '80px 60px' }}>
            <line x1="80" y1="60" x2="80" y2="42" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
          </g>
          <line x1="80" y1="60" x2="94" y2="60" stroke="#bfdbfe" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="80" cy="60" r="3" fill="#fbbf24" />
        </g>
      )}
      {kind === 'connected' && (
        <g>
          <g className={`fc-fb ${run ? '' : 'fc-spin'}`} style={{ ...sty, transformOrigin: '80px 60px' }}>
            {[0, 72, 144, 216, 288].map((deg) => {
              const r = 34, rad = (deg * Math.PI) / 180
              return <circle key={deg} cx={80 + r * Math.cos(rad)} cy={60 + r * Math.sin(rad)} r="6" fill="#93c5fd" />
            })}
          </g>
          <circle cx="80" cy="60" r="13" fill="#3b82f6" stroke="#bfdbfe" strokeWidth="2" />
        </g>
      )}
    </svg>
  )
}
