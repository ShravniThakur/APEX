import { useState } from 'react'
import LandingPage from './pages/LandingPage'
import GuidePage from './pages/GuidePage'
import ConciergePage from './pages/ConciergePage'
import DemoPage from './pages/DemoPage'
import ExplorePage from './pages/ExplorePage'
import LoginPage from './pages/LoginPage'

export type Tab = 'home' | 'guide' | 'explore' | 'concierge' | 'demo' | 'login'

export default function App() {
  const [tab, setTab] = useState<Tab>('home')

  return (
    <div className="app-bg">
      <header className="sticky top-0 z-20 border-b border-white/10 bg-[#070d20]/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <button onClick={() => setTab('home')} className="text-left">
            <div className="text-lg font-semibold text-white">APEX</div>
            <div className="text-xs text-blue-200">Your money, in plain language</div>
          </button>
          <nav className="flex items-center gap-1 text-sm">
            <TabButton id="guide" tab={tab} setTab={setTab} label="Open an account" />
            <TabButton id="explore" tab={tab} setTab={setTab} label="Explore" />
            <TabButton id="concierge" tab={tab} setTab={setTab} label="My finances" />
            <TabButton id="demo" tab={tab} setTab={setTab} label="See it in action" />
            <button
              onClick={() => setTab('login')}
              className={`ml-2 rounded-lg px-3 py-2 ${tab === 'login' ? 'bg-blue-600 text-white' : 'border border-white/15 text-slate-200 hover:bg-white/10'}`}
            >
              Sign in
            </button>
          </nav>
        </div>
      </header>
      <main>
        {tab === 'home' ? (
          <LandingPage go={setTab} />
        ) : (
          // Concierge and Explore are multi-pane workspaces, so they get the wider container.
          <div className={`mx-auto px-5 py-8 sm:py-10 ${tab === 'concierge' || tab === 'explore' ? 'max-w-7xl' : 'max-w-3xl'}`}>
            {tab === 'login' && <LoginPage go={setTab} />}
            {tab === 'guide' && <GuidePage />}
            {tab === 'explore' && <ExplorePage />}
            {tab === 'concierge' && <ConciergePage go={setTab} />}
            {tab === 'demo' && <DemoPage goToConcierge={() => setTab('concierge')} />}
          </div>
        )}
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
      className={`rounded-lg px-3 py-2 ${active ? 'bg-blue-600 text-white' : 'text-slate-300 hover:bg-white/10'}`}
    >
      {label}
    </button>
  )
}
