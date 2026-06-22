import { useState } from 'react'
import ChatPanel from '../components/ChatPanel'

const LANGS: Record<string, string> = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' }

export default function GuidePage() {
  const [lang, setLang] = useState('en')

  return (
    <div>
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Open an account</h1>
          <p className="text-sm text-slate-400">Tell APEX what you need — it'll guide you to the right account.</p>
        </div>
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 outline-none focus:border-blue-400"
        >
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code} className="bg-[#0b1220] text-slate-100">{name}</option>
          ))}
        </select>
      </div>
      <ChatPanel
        mode="guide"
        lang={lang}
        intro="Hi, I'm APEX. I can help you open the right SBI account and tell you what documents you'll need. What are you looking to do?"
      />
    </div>
  )
}
