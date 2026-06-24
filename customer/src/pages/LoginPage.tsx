import { useEffect, useState } from 'react'
import type { Tab } from '../App'
import { api, CUSTOMER_KEY, type CustomerLite, type Dropoff } from '../api'
import { Card, Spinner } from '../components/ui'

const LANGS: Record<string, string> = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' }

// APEX's entry surface. Mirrors how SBI actually works: a full-customer login, and a separate
// "resume application" path (phone) for someone mid-onboarding who isn't a customer yet. A brand-new
// visitor needs neither — they just open an account (Guide Tier-1).
export default function LoginPage({ go }: { go: (t: Tab) => void }) {
  const [customers, setCustomers] = useState<CustomerLite[] | null>(null)
  const [dropoffs, setDropoffs] = useState<Dropoff[]>([])
  const [phone, setPhone] = useState('')
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.customers().then(setCustomers).catch((e) => setErr(String(e)))
    api.dropoffs().then(setDropoffs).catch(() => setDropoffs([]))
  }, [])

  const enterAs = (id: string, tab: Tab) => { localStorage.setItem(CUSTOMER_KEY, id); go(tab) }
  const startFresh = () => { localStorage.removeItem(CUSTOMER_KEY); go('guide') }

  // Resume path: in the demo any number signs you in as a customer who has an unfinished
  // application. In production this is SBI's own phone/PAN/OTP resume login (APEX doesn't verify it).
  const resume = () => {
    if (!dropoffs.length) { setErr('No unfinished applications to resume in this demo dataset.'); return }
    enterAs(dropoffs[0].id, 'guide')
  }

  if (err && !customers) return <Card className="p-5 text-sm text-rose-300">Couldn't reach APEX: {err}</Card>
  if (!customers) return <Spinner />

  return (
    <div className="mx-auto max-w-3xl py-8">
      <h1 className="text-2xl font-semibold text-white sm:text-3xl">Welcome to APEX</h1>
      <p className="mt-1 text-base text-slate-300">Sign in, pick up an application you started, or open a new account.</p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {/* Existing customer */}
        <Card className="p-5">
          <h2 className="text-base font-semibold text-white">Already bank with SBI?</h2>
          <p className="mt-1 text-xs text-slate-300">Sign in to talk to APEX about your money.</p>
          <button
            disabled
            title="Wired to SBI SSO in production — use the demo picker below"
            className="mt-4 w-full cursor-not-allowed rounded-lg bg-blue-600/40 px-4 py-2.5 text-sm font-medium text-white/70"
          >
            Login with SBI
          </button>
          <div className="mt-3">
            <label className="mb-1 block text-xs font-medium text-slate-300">Sign in as (demo)</label>
            <select
              defaultValue=""
              onChange={(e) => e.target.value && enterAs(e.target.value, 'concierge')}
              className="w-full rounded-lg border border-white/10 bg-white/[0.08] px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-400"
            >
              <option value="" className="bg-[#0b1220] text-slate-100">Choose your profile…</option>
              {[...customers].sort((a, b) => a.name.localeCompare(b.name)).map((c) => (
                <option key={c.id} value={c.id} className="bg-[#0b1220] text-slate-100">
                  {c.name} · {LANGS[c.language_pref ?? ''] ?? c.language_pref}
                </option>
              ))}
            </select>
            <p className="mt-2 text-[11px] text-slate-400">The picker stands in for SBI's real login.</p>
          </div>
        </Card>

        {/* Resume an application (drop-off) */}
        <Card className="p-5">
          <h2 className="text-base font-semibold text-white">Started an application?</h2>
          <p className="mt-1 text-xs text-slate-300">Enter the mobile number you began with to pick up where you left off.</p>
          <form onSubmit={(e) => { e.preventDefault(); resume() }} className="mt-4">
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              inputMode="tel"
              placeholder="Mobile number"
              className="w-full rounded-lg border border-white/10 bg-white/[0.08] px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-blue-400"
            />
            <button
              type="submit"
              className="mt-3 w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500"
            >
              Resume application
            </button>
          </form>
          <p className="mt-2 text-[11px] text-slate-400">
            Demo: any number resumes a seeded drop-off. In production this is SBI's own phone/PAN/OTP resume.
          </p>
          {err && customers && <p className="mt-2 text-[11px] text-rose-300">{err}</p>}
        </Card>
      </div>

      {/* New customer — no identity needed */}
      <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-300">
        <span>New to SBI?</span>
        <button onClick={startFresh} className="font-medium text-blue-300 hover:underline">
          Open an account →
        </button>
      </div>
    </div>
  )
}
