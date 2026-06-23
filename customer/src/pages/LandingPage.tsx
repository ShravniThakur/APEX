import type { Tab } from '../App'

// Showcase cards for the auto-scrolling carousel (purely visual, like the reference). Real
// navigation is the header tabs + the two hero CTAs below — so the carousel can just glide.
const FEATURES = [
  { icon: '🏦', title: 'Open an account', blurb: 'APEX walks you to the right SBI account in plain language, then hands you a ready-to-go link.' },
  { icon: '💬', title: 'Ask about your money', blurb: '“Can I afford this?” “How’s my spending?” Real, computed answers — never guesses.' },
  { icon: '🛡️', title: 'On your side', blurb: 'At a hard moment it waits and offers insight instead of selling. Calm, never pushy.' },
  { icon: '🗣️', title: 'Speaks your language', blurb: 'Hindi, Tamil, Telugu, Bengali and more — not English-first.' },
  { icon: '⏱️', title: 'The right moment', blurb: 'Notices a real moment in your finances and reaches out only when it genuinely matters.' },
  { icon: '🧭', title: 'All of SBI, connected', blurb: 'Save, grow, borrow, protect, pay — your whole financial life in one place.' },
]

export default function LandingPage({ go }: { go: (t: Tab) => void }) {
  const cards = [...FEATURES, ...FEATURES] // two copies → seamless marquee loop

  return (
    <div className="relative overflow-hidden">
      {/* hero */}
      <section className="relative z-10 px-5 pb-8 pt-12 text-center sm:pt-16">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-blue-200">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
          AI financial concierge · on your side
        </div>
        <h1 className="mx-auto max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          Your money, in plain language.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-300">
          APEX guides you to the right SBI product, understands your financial life once it has your
          data, and is here any time you have a question — on your side, never pushy.
        </p>
        <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={() => go('guide')}
            className="rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-900/40 transition hover:bg-blue-500"
          >
            Open an account
          </button>
          <button
            onClick={() => go('login')}
            className="rounded-xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-medium text-slate-100 transition hover:bg-white/10"
          >
            I already bank with SBI
          </button>
        </div>
      </section>

      {/* auto-scrolling showcase */}
      <div className="marquee marquee-mask relative z-10 py-6">
        <div className="marquee-track gap-5 px-5">
          {cards.map((f, i) => (
            <article
              key={i}
              className="w-72 shrink-0 overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.07] to-white/[0.02] p-1 shadow-xl shadow-blue-950/40"
            >
              <div className="relative flex h-40 items-center justify-center overflow-hidden rounded-[1.25rem] bg-gradient-to-br from-blue-500/40 via-blue-700/30 to-indigo-900/30">
                <div className="absolute -inset-10 bg-[radial-gradient(circle_at_50%_40%,rgba(96,165,250,0.55),transparent_60%)]" />
                <span className="relative text-5xl drop-shadow-[0_0_18px_rgba(96,165,250,0.7)]">{f.icon}</span>
              </div>
              <div className="px-4 pb-4 pt-4">
                <h3 className="text-lg font-semibold text-white">{f.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-slate-300">{f.blurb}</p>
              </div>
            </article>
          ))}
        </div>
      </div>

      {/* glowing horizon arc (the planet curve in the reference) */}
      <div className="pointer-events-none relative z-0 -mt-2 h-44 overflow-hidden">
        <div className="absolute left-1/2 top-10 h-[640px] w-[1300px] -translate-x-1/2 rounded-[50%] bg-[#060b1a] shadow-[0_-32px_120px_-8px_rgba(59,130,246,0.55)] ring-1 ring-blue-400/30" />
      </div>
    </div>
  )
}
