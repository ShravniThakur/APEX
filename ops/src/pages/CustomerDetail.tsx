import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, type CustomerDetail as Detail, type Decision, type Score } from '../api'
import { Badge, Card, ErrorBox, Header, Spinner } from '../components/ui'
import { dateShort, dateTime, human, inr, LANG, outcomeStyle, responseStyle } from '../lib/format'

export default function CustomerDetail() {
  const { id } = useParams()
  const [c, setC] = useState<Detail | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (id) api.customer(id).then(setC).catch((e) => setErr(String(e)))
  }, [id])

  if (err) return <ErrorBox err={err} />
  if (!c) return <Spinner />

  return (
    <div>
      <Link to="/customers" className="text-sm text-slate-500 hover:underline">← Customers</Link>
      <Header
        title={c.name}
        subtitle={`${c.age} · ${c.occupation} · ${c.city_tier} · speaks ${LANG[c.language_pref ?? ''] ?? c.language_pref}`}
      />

      <div className="mb-6 flex flex-wrap gap-2">
        <Badge className="bg-slate-100 text-slate-600">{c.customer_type}</Badge>
        <Badge className="bg-slate-100 text-slate-600">income {inr(c.monthly_income)}</Badge>
        <Badge className="bg-slate-100 text-slate-600">{c.dependents} dependents</Badge>
        {c.owns_property && <Badge className="bg-slate-100 text-slate-600">owns property</Badge>}
        {c.owns_gold && <Badge className="bg-slate-100 text-slate-600">owns gold</Badge>}
        {c.has_papl_offer && <Badge className="bg-indigo-100 text-indigo-700">PAPL offer</Badge>}
        {c.has_card_offer && <Badge className="bg-indigo-100 text-indigo-700">card offer</Badge>}
      </div>

      {/* Scores */}
      <Section title="ML scores">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          {c.scores.map((s) => <ScoreCard key={s.type} s={s} />)}
        </div>
      </Section>

      {/* Signals */}
      <Section title="Signals detected">
        <div className="flex flex-wrap gap-2">
          {c.signals.length === 0 && <span className="text-sm text-slate-400">None this cycle.</span>}
          {c.signals.map((s) => (
            <Badge key={s.id} className="bg-amber-100 text-amber-800">
              {human(s.type)} <span className="font-normal text-amber-600">· {s.source_ref}</span>
            </Badge>
          ))}
        </div>
      </Section>

      {/* Decisions — the reasoning trace */}
      <Section title="Agent decisions">
        <div className="space-y-4">
          {c.decisions.length === 0 && (
            <p className="text-sm text-slate-400">
              No decisions yet. Run the pipeline from the Overview page.
            </p>
          )}
          {c.decisions.map((d) => <DecisionCard key={d.id} d={d} />)}
        </div>
      </Section>

      {/* Recent transactions */}
      <Section title="Recent transactions">
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Date</th>
                <th className="px-4 py-2">Category</th>
                <th className="px-4 py-2">Channel</th>
                <th className="px-4 py-2 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {c.recent_transactions.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-2 text-slate-500">{dateShort(t.txn_time)}</td>
                  <td className="px-4 py-2 text-slate-700">{t.merchant_category}</td>
                  <td className="px-4 py-2 text-slate-500">{t.channel}</td>
                  <td className={`px-4 py-2 text-right tabular-nums ${t.direction === 'credit' ? 'text-emerald-600' : 'text-slate-700'}`}>
                    {t.direction === 'credit' ? '+' : '−'}{inr(t.amount)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </Section>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
      {children}
    </section>
  )
}

function ScoreCard({ s }: { s: Score }) {
  const v = s.value ?? {}
  if (typeof v.score === 'number') {
    return (
      <Card className="p-4">
        <div className="mb-2 text-sm font-medium text-slate-600">{human(s.type)}</div>
        <Meter value={v.score} />
      </Card>
    )
  }
  if (s.type === 'propensity') {
    return (
      <Card className="p-4">
        <div className="mb-2 text-sm font-medium text-slate-600">Propensity</div>
        <div className="space-y-1.5">
          {Object.entries(v as Record<string, number>).map(([k, val]) => (
            <div key={k} className="flex items-center gap-2">
              <div className="w-20 text-xs text-slate-500">{k}</div>
              <Meter value={val} compact />
            </div>
          ))}
        </div>
      </Card>
    )
  }
  if (s.type === 'anomaly') {
    const flagged = (v.flagged ?? []) as Array<{ category: string; magnitude: number }>
    return (
      <Card className="p-4">
        <div className="mb-2 text-sm font-medium text-slate-600">Anomaly</div>
        <div className="text-2xl font-semibold text-slate-900">{v.max_magnitude ?? 0}</div>
        <div className="text-xs text-slate-500">max magnitude · {flagged.length} flagged</div>
        {flagged.map((f, i) => (
          <div key={i} className="mt-1 text-xs text-rose-600">{f.category} ({f.magnitude})</div>
        ))}
      </Card>
    )
  }
  return (
    <Card className="p-4">
      <div className="mb-1 text-sm font-medium text-slate-600">{human(s.type)}</div>
      <pre className="text-xs text-slate-500">{JSON.stringify(v)}</pre>
    </Card>
  )
}

function Meter({ value, compact }: { value: number; compact?: boolean }) {
  const pct = Math.round(value * 100)
  const color = value >= 0.66 ? 'bg-rose-500' : value >= 0.33 ? 'bg-amber-500' : 'bg-emerald-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 rounded-full bg-slate-100">
        <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {!compact && <span className="w-10 text-right text-sm tabular-nums text-slate-600">{pct}%</span>}
      {compact && <span className="w-8 text-right text-xs tabular-nums text-slate-400">{pct}</span>}
    </div>
  )
}

function DecisionCard({ d }: { d: Decision }) {
  const isReengage = (d.trigger_ref ?? '').startsWith('reengage:')
  return (
    <Card className="p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Badge className={outcomeStyle[d.outcome] ?? 'bg-slate-100 text-slate-600'}>{d.outcome.toUpperCase()}</Badge>
        {isReengage && <Badge className="bg-violet-100 text-violet-700">re-engagement</Badge>}
        {d.product_id && <Badge className="bg-slate-100 text-slate-600">{d.product_id}</Badge>}
        {d.outcome === 'escalate' && (
          <Badge className={d.rm_status === 'resolved' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}>
            RM {d.rm_status ?? 'open'}
          </Badge>
        )}
        {d.confidence != null && (
          <span className="text-xs text-slate-400">confidence {(d.confidence * 100).toFixed(0)}%</span>
        )}
        {d.action?.authority_level && (
          <span className="text-xs text-slate-400">· authority L{d.action.authority_level}</span>
        )}
      </div>

      <Field label="Hypothesis" value={d.hypothesis} />
      <Field label="Self-critique" value={d.critique_result} />

      {d.action ? (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Message sent · {d.action.channel}
            </span>
            <span className="text-xs text-slate-400">
              {d.action.sent_at ? `delivered ${dateTime(d.action.sent_at)}` : 'not sent'}
            </span>
          </div>
          <p className="whitespace-pre-line text-sm text-slate-800">{d.action.message_text}</p>
          {d.action.deep_link && (
            <a href={d.action.deep_link} target="_blank" rel="noreferrer"
              className="mt-2 inline-block text-xs text-indigo-600 hover:underline">
              {d.action.deep_link}
            </a>
          )}
          {d.action.response && (
            <div className="mt-3 border-t border-slate-200 pt-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Customer response: </span>
              <Badge className={responseStyle[d.action.response.response_type] ?? 'bg-slate-100 text-slate-600'}>
                {d.action.response.response_type}
              </Badge>
            </div>
          )}
        </div>
      ) : (
        <p className="mt-2 text-xs italic text-slate-400">
          No message sent — {d.outcome === 'wait' ? 'deliberate restraint.' : 'routed to bank-ops review.'}
        </p>
      )}
    </Card>
  )
}

function Field({ label, value }: { label: string; value: string | null }) {
  if (!value) return null
  return (
    <div className="mb-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <p className="text-sm text-slate-700">{value}</p>
    </div>
  )
}
