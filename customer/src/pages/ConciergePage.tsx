import { useEffect, useState } from 'react'
import { api, CUSTOMER_KEY as KEY, type CustomerLite } from '../api'
import ChatPanel from '../components/ChatPanel'
import FinancialSnapshot from '../components/FinancialSnapshot'
import { Card, Spinner } from '../components/ui'

const LANGS: Record<string, string> = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' }

export default function ConciergePage() {
  const [customers, setCustomers] = useState<CustomerLite[] | null>(null)
  const [id, setId] = useState<string | null>(() => localStorage.getItem(KEY))
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.customers().then(setCustomers).catch((e) => setErr(String(e)))
  }, [])

  const signIn = (cid: string) => { localStorage.setItem(KEY, cid); setId(cid) }
  const signOut = () => { localStorage.removeItem(KEY); setId(null) }

  if (err) return <Card className="p-5 text-sm text-rose-600">Couldn't reach APEX: {err}</Card>
  if (!customers) return <Spinner />

  const me = customers.find((c) => c.id === id) ?? null

  // Demo sign-in (production would authenticate the real logged-in customer).
  if (!me) {
    return (
      <div>
        <h1 className="mb-1 text-xl font-semibold text-slate-900">My finances</h1>
        <p className="mb-4 text-sm text-slate-500">Sign in to talk to APEX about your money.</p>
        <Card className="p-5">
          <label className="mb-2 block text-sm font-medium text-slate-600">Sign in as (demo)</label>
          <select
            defaultValue=""
            onChange={(e) => e.target.value && signIn(e.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-400"
          >
            <option value="">Choose your profile…</option>
            {[...customers].sort((a, b) => a.name.localeCompare(b.name)).map((c) => (
              <option key={c.id} value={c.id}>{c.name} · {LANGS[c.language_pref ?? ''] ?? c.language_pref}</option>
            ))}
          </select>
          <p className="mt-3 text-xs text-slate-400">
            In production you'd already be logged in; this picker stands in for authentication.
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Hello, {me.name.split(' ')[0]}</h1>
          <p className="text-sm text-slate-500">Ask APEX anything about your money.</p>
        </div>
        <button onClick={signOut} className="text-sm text-slate-500 hover:underline">Switch profile</button>
      </div>
      <FinancialSnapshot customerId={me.id} />
      <ChatPanel
        mode="concierge"
        customerId={me.id}
        lang={me.language_pref ?? 'en'}
        intro={`Hello ${me.name.split(' ')[0]}, I'm APEX. Ask me anything about your money — "can I afford this?", "how's my spending?", "should I be worried?".`}
      />
    </div>
  )
}
