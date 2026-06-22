import { useState } from 'react'
import GuidePage from './pages/GuidePage'
import ConciergePage from './pages/ConciergePage'
import DemoPage from './pages/DemoPage'
import ExplorePage from './pages/ExplorePage'

type Tab = 'guide' | 'explore' | 'concierge' | 'demo'

export default function App() {
  const [tab, setTab] = useState<Tab>('guide')

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-5 py-4">
          <div>
            <div className="text-lg font-semibold text-indigo-700">APEX</div>
            <div className="text-xs text-slate-500">Your money, in plain language</div>
          </div>
          <nav className="flex gap-1 text-sm">
            <TabButton id="guide" tab={tab} setTab={setTab} label="Open an account" />
            <TabButton id="explore" tab={tab} setTab={setTab} label="Explore" />
            <TabButton id="concierge" tab={tab} setTab={setTab} label="My finances" />
            <TabButton id="demo" tab={tab} setTab={setTab} label="See it in action" />
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-5 py-6">
        {tab === 'guide' && <GuidePage />}
        {tab === 'explore' && <ExplorePage />}
        {tab === 'concierge' && <ConciergePage />}
        {tab === 'demo' && <DemoPage goToConcierge={() => setTab('concierge')} />}
      </main>
    </div>
  )
}

function TabButton(
  { id, tab, setTab, label }: { id: Tab; tab: Tab; setTab: (t: Tab) => void; label: string },
) {
  const active = tab === id
  return (
    <button
      onClick={() => setTab(id)}
      className={`rounded-lg px-3 py-2 ${active ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
    >
      {label}
    </button>
  )
}
