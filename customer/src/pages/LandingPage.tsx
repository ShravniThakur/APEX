import type { Tab } from '../App'
import FeatureCarousel from '../components/FeatureCarousel'

export default function LandingPage({ go }: { go: (t: Tab) => void }) {
  return (
    <div className="relative overflow-hidden">
      {/* hero */}
      <section className="relative z-10 px-5 pb-8 pt-12 text-center sm:pt-16">
        <div className="mx-auto mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.08] px-3 py-1 text-xs text-blue-200">
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
            className="rounded-xl border border-white/15 bg-white/[0.08] px-5 py-2.5 text-sm font-medium text-slate-100 transition hover:bg-white/10"
          >
            I already bank with SBI
          </button>
        </div>
      </section>

      {/* focus carousel — centre card zooms in and glows, then slides out as the next grows in;
          each card's illustration animates (coverflow, like the reference) */}
      <div className="relative z-10 py-8">
        <FeatureCarousel />
      </div>

      {/* glowing horizon arc (the planet curve in the reference) */}
      <div className="pointer-events-none relative z-0 -mt-2 h-44 overflow-hidden">
        <div className="absolute left-1/2 top-10 h-[640px] w-[1300px] -translate-x-1/2 rounded-[50%] bg-[#060b1a] shadow-[0_-32px_120px_-8px_rgba(59,130,246,0.55)] ring-1 ring-blue-400/30" />
      </div>
    </div>
  )
}
