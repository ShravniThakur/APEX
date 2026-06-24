import { useState } from 'react'
import ChatPanel from '../components/ChatPanel'
import { CUSTOMER_KEY } from '../api'

const LANGS: Record<string, string> = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' }

export default function GuidePage() {
  const [lang, setLang] = useState('en')
  // If someone is signed in (demo identity), pass it so Guide can spot an unfinished application
  // (the Tier-2 drop-off path). Anonymous visitors get plain Tier-1 onboarding.
  const customerId = localStorage.getItem(CUSTOMER_KEY) ?? undefined

  return (
    <div>
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white sm:text-3xl">Open an account</h1>
          <p className="mt-1 text-base text-slate-300">Tell APEX what you need — it'll guide you to the right account.</p>
        </div>
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="rounded-lg border border-white/10 bg-white/[0.08] px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-400"
        >
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code} className="bg-[#0b1220] text-slate-100">{name}</option>
          ))}
        </select>
      </div>
      <ChatPanel
        mode="guide"
        customerId={customerId}
        lang={lang}
        intro="Hi, I'm APEX. I can help you open the right SBI account and tell you what documents you'll need. What are you looking to do?"
      />
    </div>
  )
}
