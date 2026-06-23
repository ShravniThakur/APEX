import { useEffect, useState } from 'react'
import type { Tab } from '../App'
import { api, CUSTOMER_KEY as KEY, type CustomerLite } from '../api'
import ChatPanel from '../components/ChatPanel'
import FinancialSnapshot from '../components/FinancialSnapshot'
import { Card, Spinner } from '../components/ui'

export default function ConciergePage({ go }: { go: (t: Tab) => void }) {
  const [customers, setCustomers] = useState<CustomerLite[] | null>(null)
  const [id] = useState<string | null>(() => localStorage.getItem(KEY))
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.customers().then(setCustomers).catch((e) => setErr(String(e)))
  }, [])

  const logOut = () => { localStorage.removeItem(KEY); go('home') }

  if (err) return <Card className="p-5 text-sm text-rose-300">Couldn't reach APEX: {err}</Card>
  if (!customers) return <Spinner />

  const me = customers.find((c) => c.id === id) ?? null

  // Not signed in → send them to the central login surface (no inline picker here anymore).
  if (!me) {
    return (
      <div>
        <h1 className="mb-1 text-xl font-semibold text-white">My finances</h1>
        <p className="mb-4 text-sm text-slate-400">Sign in to talk to APEX about your money.</p>
        <Card className="p-5">
          <p className="text-sm text-slate-300">You're not signed in.</p>
          <button
            onClick={() => go('login')}
            className="mt-3 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            Sign in
          </button>
        </Card>
      </div>
    )
  }

  return (
    <div>
      {/* Header spans the full width, so the two columns below start at the same level. */}
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Hello, {me.name.split(' ')[0]}</h1>
          <p className="text-sm text-slate-400">Ask APEX anything about your money.</p>
        </div>
        <button onClick={logOut} className="text-sm text-slate-400 hover:underline">Log out</button>
      </div>

      {/* Both columns stretch to the same height (left content sets it; the chat fills via h-full). */}
      <div className="grid gap-4 lg:grid-cols-2">
        <FinancialSnapshot customerId={me.id} />
        <ChatPanel
          mode="concierge"
          customerId={me.id}
          lang={me.language_pref ?? 'en'}
          intro={`Hello ${me.name.split(' ')[0]}, I'm APEX. Ask me anything about your money — "can I afford this?", "how's my spending?", "should I be worried?".`}
        />
      </div>
    </div>
  )
}
