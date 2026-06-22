import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type Escalation } from '../api'
import { Badge, Card, ErrorBox, Header, Spinner } from '../components/ui'
import { dateTime, human, inr, LANG } from '../lib/format'

// The RM inbox: cases the deterministic gate refused to auto-act on and handed to a human —
// churn risk, severe stress with only unsecured debt available, or no eligible product. This is
// what makes `escalate` a real path (a relationship manager picks it up) rather than a dead end.
export default function Escalations() {
  const [rows, setRows] = useState<Escalation[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = () => api.escalations().then(setRows).catch((e) => setErr(String(e)))
  useEffect(() => { load() }, [])

  const resolve = async (id: string) => {
    setBusy(id)
    try {
      await api.resolveEscalation(id)
      await load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(null)
    }
  }

  if (err) return <ErrorBox err={err} />
  if (!rows) return <Spinner />

  return (
    <div>
      <Header
        title="Escalation queue"
        subtitle={`${rows.length} case${rows.length === 1 ? '' : 's'} awaiting a relationship manager`}
      />

      {rows.length === 0 ? (
        <Card className="p-8 text-center text-sm text-slate-400">
          Nothing in the queue. When the gate declines to auto-act — churn risk, severe stress with
          only unsecured debt, or no eligible product — the case lands here for a human RM.
        </Card>
      ) : (
        <div className="space-y-4">
          {rows.map((e) => (
            <Card key={e.decision_id} className="p-5">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Badge className="bg-rose-100 text-rose-800">ESCALATE</Badge>
                <Badge className="bg-slate-100 text-slate-600">{human(e.signal)}</Badge>
                {e.confidence != null && (
                  <span className="text-xs text-slate-400">confidence {(e.confidence * 100).toFixed(0)}%</span>
                )}
                <span className="ml-auto text-xs text-slate-400">{dateTime(e.created_at)}</span>
              </div>

              <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                {e.customer_name && (
                  <Link to={`/customers/${e.customer_id}`} className="font-medium text-slate-900 hover:underline">
                    {e.customer_name}
                  </Link>
                )}
                <span className="text-slate-400">
                  {e.city_tier} · {LANG[e.language_pref ?? ''] ?? e.language_pref} · income {inr(e.monthly_income)}
                </span>
              </div>

              {e.reason && (
                <div className="mb-3 rounded-lg border border-rose-100 bg-rose-50/60 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-rose-400">Why escalated</div>
                  <p className="whitespace-pre-line text-sm text-rose-900">{e.reason}</p>
                </div>
              )}

              <div className="flex items-center justify-end">
                <button
                  onClick={() => resolve(e.decision_id)}
                  disabled={busy === e.decision_id}
                  className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {busy === e.decision_id ? 'Marking…' : 'Mark handled'}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
