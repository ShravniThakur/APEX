import { NavLink, Route, Routes } from 'react-router-dom'
import Overview from './pages/Overview'
import Customers from './pages/Customers'
import CustomerDetail from './pages/CustomerDetail'
import Escalations from './pages/Escalations'

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 bg-slate-900 p-5 text-slate-100">
        <div className="text-xl font-semibold tracking-tight">APEX</div>
        <div className="mb-8 text-xs text-slate-400">Bank Ops Console</div>
        <nav className="space-y-1 text-sm">
          <NavItem to="/" label="Overview" />
          <NavItem to="/customers" label="Customers" />
          <NavItem to="/escalations" label="Escalations" />
        </nav>
        <p className="mt-10 text-[11px] leading-relaxed text-slate-500">
          Internal view — what the Analyser agent has done across customers: reasoning traces,
          decisions, and restraint.
        </p>
      </aside>
      <main className="flex-1 p-8">
        <div className="mx-auto max-w-6xl">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/customers/:id" element={<CustomerDetail />} />
            <Route path="/escalations" element={<Escalations />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `block rounded-lg px-3 py-2 ${isActive ? 'bg-slate-700 text-white' : 'text-slate-300 hover:bg-slate-800'}`
      }
    >
      {label}
    </NavLink>
  )
}
