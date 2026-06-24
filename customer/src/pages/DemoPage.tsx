import { useEffect, useState } from 'react'
import { api, CUSTOMER_KEY, type DemoScenario, type SimulateResult } from '../api'
import { Card, Spinner } from '../components/ui'

export default function DemoPage({ goToConcierge }: { goToConcierge: () => void }) {
  const [scenarios, setScenarios] = useState<DemoScenario[] | null>(null)
  const [running, setRunning] = useState<string | null>(null)
  const [result, setResult] = useState<SimulateResult | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.demoScenarios().then(setScenarios).catch((e) => setErr(String(e)))
  }, [])

  const run = async (key: string) => {
    setRunning(key)
    setErr(null)
    setResult(null)
    try {
      setResult(await api.demoSimulate(key))
    } catch (e) {
      setErr(String(e))
    } finally {
      setRunning(null)
    }
  }

  const continueAsCustomer = () => {
    if (!result) return
    localStorage.setItem(CUSTOMER_KEY, result.customer_id)
    goToConcierge()
  }

  if (err) return <Card className="p-5 text-sm text-rose-300">Couldn't reach APEX: {err}</Card>
  if (!scenarios) return <Spinner />

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold text-white sm:text-3xl">See APEX in action</h1>
      <p className="mb-8 text-base text-slate-300">
        Imagine you just opened an account. Fast-forward three months of real activity — and watch
        whether APEX notices a moment worth reaching out about.
      </p>

      {!result && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {scenarios.map((s) => (
            <Card key={s.key} className="flex flex-col justify-between p-5">
              <div className="mb-4 text-sm font-medium text-slate-100">{s.label}</div>
              <button
                onClick={() => run(s.key)}
                disabled={running !== null}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {running === s.key ? 'Simulating…' : 'Simulate 3 months'}
              </button>
            </Card>
          ))}
        </div>
      )}

      {running && (
        <p className="mt-4 text-sm text-amber-300">
          Three months of activity arrive → APEX reviews it and decides whether to reach out…
        </p>
      )}

      {result && (
        <div>
          <Card className="mb-4 p-5">
            <div className="mb-3 text-sm text-slate-300">
              After three months for <span className="font-medium text-slate-100">{result.name}</span>, APEX:
            </div>
            <div className="space-y-3">
              {result.outreach.map((o, i) => <Outcome key={i} o={o} />)}
            </div>
          </Card>
          <div className="flex gap-2">
            <button
              onClick={continueAsCustomer}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
            >
              Continue to My finances as {result.name.split(' ')[0]}
            </button>
            <button
              onClick={() => setResult(null)}
              className="rounded-lg bg-white/10 px-4 py-2 text-sm text-slate-200 hover:bg-white/20"
            >
              Try another
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Outcome({ o }: { o: { outcome: string; message_text: string | null; deep_link: string | null } }) {
  if (o.outcome === 'act' && o.message_text) {
    return (
      <div>
        <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-300">reached out</div>
        <div className="whitespace-pre-line rounded-2xl bg-white/[0.08] px-4 py-2 text-sm text-slate-100">
          {o.message_text}
        </div>
        {o.deep_link && (
          <a href={o.deep_link} target="_blank" rel="noreferrer"
            className="mt-1 inline-block break-all text-xs text-blue-400 hover:underline">
            {o.deep_link}
          </a>
        )}
      </div>
    )
  }
  if (o.outcome === 'wait') {
    return (
      <div className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
        Noticed something sensitive and <b>chose to wait</b> — no product was pushed at a vulnerable moment.
      </div>
    )
  }
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.08] px-4 py-2 text-sm text-slate-300">
      Flagged for a person to review.
    </div>
  )
}
