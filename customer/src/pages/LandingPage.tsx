import type { Tab } from '../App'

// Intent-routing "home": orients a first-time visitor and routes by who they are — which mirrors
// APEX's data-gated three-mode model (new → Guide, existing → Concierge, curious → Explore/Demo).
// It adds context, never a gate: every card is one click into the existing tabs.
const CARDS: { id: Tab; title: string; blurb: string; cta: string }[] = [
  {
    id: 'guide', title: 'New to SBI',
    blurb: "Open the right account in plain language — APEX asks what you need, then hands you a ready-to-go link. No forms to puzzle over.",
    cta: 'Open an account →',
  },
  {
    id: 'concierge', title: 'Already bank with us',
    blurb: "Ask about your own money — “can I afford this?”, “how’s my spending?” — and get real, computed answers, never guesses.",
    cta: 'Go to my finances →',
  },
  {
    id: 'explore', title: 'Just exploring',
    blurb: 'Browse what SBI offers, grouped by what it does for your life — save, grow, borrow, protect, pay.',
    cta: 'Explore products →',
  },
  {
    id: 'demo', title: 'See it in action',
    blurb: 'Watch APEX notice a real moment in someone’s finances and decide whether — and how — to reach out.',
    cta: 'See the demo →',
  },
]

export default function LandingPage({ go }: { go: (t: Tab) => void }) {
  return (
    <div>
      <section className="mb-8 mt-4 text-center">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Your money, in plain language.</h1>
        <p className="mx-auto mt-3 max-w-xl text-slate-600">
          APEX guides you to the right SBI product, understands your financial life once it has your
          data, and is here any time you have a question — on your side, never pushy.
        </p>
      </section>
      <div className="grid gap-4 sm:grid-cols-2">
        {CARDS.map((c) => (
          <button
            key={c.id}
            onClick={() => go(c.id)}
            className="group rounded-xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:border-indigo-300 hover:shadow"
          >
            <div className="font-semibold text-slate-900">{c.title}</div>
            <p className="mt-1 text-sm text-slate-500">{c.blurb}</p>
            <div className="mt-3 text-sm font-medium text-indigo-600 group-hover:underline">{c.cta}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
