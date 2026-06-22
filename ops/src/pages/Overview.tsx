import { useEffect, useState } from 'react'
import { api, type Stats } from '../api'
import { Bars, Card, ErrorBox, Header, Spinner, Stat } from '../components/ui'

export default function Overview() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [reengaging, setReengaging] = useState(false)

  const load = () => api.stats().then(setStats).catch((e) => setErr(String(e)))
  useEffect(() => { load() }, [])

  const run = async () => {
    setRunning(true)
    setErr(null)
    try {
      await api.runPipeline()
      await load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setRunning(false)
    }
  }

  const reengage = async () => {
    setReengaging(true)
    setErr(null)
    try {
      await api.runReengage()
      await load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setReengaging(false)
    }
  }

  if (err) return <ErrorBox err={err} />
  if (!stats) return <Spinner />

  return (
    <div>
      <Header
        title="Overview"
        subtitle="Live state of the Analyser pipeline"
        action={
          <div className="flex gap-2">
            <button
              onClick={reengage}
              disabled={running || reengaging}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
            >
              {reengaging ? 'Re-engaging…' : 'Re-engage waits'}
            </button>
            <button
              onClick={run}
              disabled={running || reengaging}
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {running ? 'Running pipeline…' : 'Run pipeline'}
            </button>
          </div>
        }
      />
      {running && (
        <p className="mb-4 text-sm text-amber-600">
          Scoring → detecting → reasoning (the agent calls the LLM for each signal — this can take ~30–60s).
        </p>
      )}
      {reengaging && (
        <p className="mb-4 text-sm text-amber-600">
          Revisiting deliberate waits whose moment has passed — sending gentle, product-free check-ins.
        </p>
      )}
      <div className="mb-8 grid grid-cols-5 gap-4">
        <Stat label="Customers" value={stats.customers} />
        <Stat label="Signals detected" value={stats.signals} />
        <Stat label="Decisions made" value={stats.decisions} />
        <Stat label="Emails sent" value={stats.emails_sent} />
        <Stat label="Escalations open" value={stats.escalations_open} />
      </div>
      <div className="grid grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="mb-3 font-semibold text-slate-700">Signals by type</h3>
          <Bars data={stats.signals_by_type} />
        </Card>
        <Card className="p-5">
          <h3 className="mb-3 font-semibold text-slate-700">Decisions by outcome</h3>
          <Bars data={stats.decisions_by_outcome} />
        </Card>
      </div>
    </div>
  )
}
