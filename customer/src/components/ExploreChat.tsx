import { useEffect, useRef, useState } from 'react'
import { api, type ChatMessage, type Product } from '../api'
import { speak, stopSpeaking } from '../lib/voice'
import Avatar from './Avatar'
import { Card } from './ui'

// Persistent side chat for Explore: APEX (Guide mode) explains products and answers follow-ups,
// with the talking avatar. History stays on screen as the customer clicks through products.
const LANGS: Record<string, string> = { en: 'English', hi: 'Hindi', ta: 'Tamil', te: 'Telugu', bn: 'Bengali' }

const URL_RE = /(https?:\/\/[^\s<]+)/g
function withLinks(text: string) {
  return text.split(URL_RE).map((part, i) => {
    if (!/^https?:\/\//.test(part)) return part
    const trail = (part.match(/[.,;:!?)\]}]+$/) || [''])[0]
    const url = trail ? part.slice(0, part.length - trail.length) : part
    return (
      <span key={i}>
        <a href={url} target="_blank" rel="noreferrer" className="break-all text-blue-300 underline hover:text-blue-200">{url}</a>
        {trail}
      </span>
    )
  })
}

// `ask` carries the product to explain plus an incrementing `n`, so even re-clicking the same
// product re-triggers an explanation (appended to the running conversation).
export default function ExploreChat({ ask }: { ask: { product: Product; n: number } | null }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [muted, setMuted] = useState(false)
  const [lang, setLang] = useState('en')
  const listRef = useRef<HTMLDivElement>(null)

  // Scroll the messages container itself (not scrollIntoView, which would scroll the whole page to
  // the bottom on open). Only once there are messages, so opening Explore doesn't jump.
  useEffect(() => {
    const el = listRef.current
    if (el && messages.length) el.scrollTop = el.scrollHeight
  }, [messages, busy])
  useEffect(() => () => stopSpeaking(), [])

  const send = async (content: string) => {
    if (busy || !content.trim()) return
    const next = [...messages, { role: 'user' as const, content }]
    setMessages(next)
    setInput('')
    setBusy(true)
    try {
      const { reply } = await api.chat({ mode: 'guide', messages: next })
      setMessages([...next, { role: 'assistant', content: reply }])
      if (!muted) speak(reply, lang, { onStart: () => setSpeaking(true), onEnd: () => setSpeaking(false) })
    } catch (e) {
      setMessages([...next, { role: 'assistant', content: `(couldn't load that just now: ${e})` }])
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (ask?.product) send(`In simple words, explain the ${ask.product.name} — what it is, who it's for, and how it could genuinely help someone. Plain language, no jargon. Reply in ${LANGS[lang]}.`)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ask?.n])

  return (
    <Card className="flex h-[60vh] flex-col lg:sticky lg:top-20 lg:h-[74vh]">
      <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
        <Avatar speaking={speaking} size={52} />
        <span className="text-base font-semibold text-slate-100">APEX</span>
        <select
          value={lang}
          onChange={(e) => setLang(e.target.value)}
          className="ml-auto rounded-lg border border-white/10 bg-white/[0.08] px-2 py-1 text-xs text-slate-100 outline-none focus:border-blue-400"
        >
          {Object.entries(LANGS).map(([code, name]) => (
            <option key={code} value={code} className="bg-[#0b1220] text-slate-100">{name}</option>
          ))}
        </select>
        <button
          onClick={() => { setMuted((m) => { if (!m) stopSpeaking(); return !m }); setSpeaking(false) }}
          title={muted ? 'Voice off' : 'Voice on'}
          className="rounded-lg px-2 py-1 text-sm text-slate-300 hover:bg-white/10"
        >
          {muted ? '🔇' : '🔊'}
        </button>
      </div>

      <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && !busy && (
          <div className="text-sm text-slate-300">
            Pick a product on the left and I'll explain it in plain language — or just ask me anything.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm ${
              m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white/[0.08] text-slate-100'}`}>
              {m.role === 'assistant' ? withLinks(m.content) : m.content}
            </div>
          </div>
        ))}
        {busy && <div className="text-sm text-slate-300">APEX is thinking…</div>}
      </div>

      <form
        className="flex items-center gap-2 border-t border-white/10 p-3"
        onSubmit={(e) => { e.preventDefault(); send(input) }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a product…"
          disabled={busy}
          className="flex-1 rounded-lg border border-white/10 bg-white/[0.08] px-3 py-2 text-sm text-slate-100 placeholder-slate-400 outline-none focus:border-blue-400"
        />
        <button type="submit" disabled={busy || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50">
          Send
        </button>
      </form>
    </Card>
  )
}
