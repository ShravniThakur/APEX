import { useEffect, useRef, useState } from 'react'
import { api, type ChatMessage } from '../api'
import { speak, stopSpeaking, useRecorder } from '../lib/voice'
import { Card } from './ui'

interface Props {
  mode: 'guide' | 'concierge'
  customerId?: string
  lang?: string
  intro: string
}

// Where this conversation is cached so it survives a page refresh. Scoped per mode +
// customer, so switching profiles (or Guide vs Concierge) loads the right history.
const chatKey = (mode: string, customerId?: string) => `apex_chat_${mode}_${customerId ?? 'guest'}`

export default function ChatPanel({ mode, customerId, lang, intro }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [tts, setTts] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const recorder = useRecorder()
  const endRef = useRef<HTMLDivElement>(null)
  // Skip the very first persist after a (re)load, so loading saved history doesn't immediately
  // overwrite it with the transient empty state during the load render.
  const skipPersist = useRef(true)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  // Load this conversation's saved history when the customer/mode changes (and on first mount) —
  // this is what makes the chat survive a page refresh.
  useEffect(() => {
    setErr(null)
    stopSpeaking()
    skipPersist.current = true
    try {
      const saved = localStorage.getItem(chatKey(mode, customerId))
      setMessages(saved ? JSON.parse(saved) : [])
    } catch {
      setMessages([])
    }
  }, [customerId, mode])

  // Persist on every change after the initial load.
  useEffect(() => {
    if (skipPersist.current) { skipPersist.current = false; return }
    try { localStorage.setItem(chatKey(mode, customerId), JSON.stringify(messages)) } catch { /* quota */ }
  }, [messages, customerId, mode])

  const send = async (text: string) => {
    const content = text.trim()
    if (!content || busy) return
    const next = [...messages, { role: 'user' as const, content }]
    setMessages(next)
    setInput('')
    setBusy(true)
    setErr(null)
    try {
      const { reply } = await api.chat({ mode, customer_id: customerId, messages: next })
      setMessages([...next, { role: 'assistant', content: reply }])
      if (tts) speak(reply, lang)
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  const onMic = async () => {
    if (recorder.recording) {
      const blob = await recorder.stop()
      setBusy(true)
      try {
        const { text } = await api.transcribe(blob)
        if (text) await send(text)
      } catch (e) {
        setErr(String(e))
      } finally {
        setBusy(false)
      }
    } else {
      stopSpeaking()
      await recorder.start()
    }
  }

  return (
    <Card className="flex h-[68vh] flex-col lg:h-full">
      <div className="flex items-center justify-end border-b border-white/10 px-4 py-2">
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={tts} onChange={(e) => setTts(e.target.checked)} />
          Speak replies
        </label>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        <Bubble role="assistant" content={intro} />
        {messages.map((m, i) => <Bubble key={i} role={m.role} content={m.content} />)}
        {busy && <div className="text-sm text-slate-400">APEX is thinking…</div>}
        {err && <div className="text-sm text-rose-300">{err}</div>}
        <div ref={endRef} />
      </div>

      <form
        className="flex items-center gap-2 border-t border-white/10 p-3"
        onSubmit={(e) => { e.preventDefault(); send(input) }}
      >
        <button
          type="button"
          onClick={onMic}
          disabled={busy}
          title="Speak instead of typing"
          className={`rounded-lg px-3 py-2 text-sm ${
            recorder.recording ? 'bg-rose-600 text-white' : 'bg-white/10 text-slate-200 hover:bg-white/20'
          } disabled:opacity-50`}
        >
          {recorder.recording ? '● stop' : '🎤'}
        </button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={busy}
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-blue-400"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </Card>
  )
}

// Turn any http(s) URL in a message into a clickable link. Concierge is reactive — the customer
// asked — so surfacing a tappable link is helpful here (unlike the proactive Analyser emails, which
// deliberately carry no links). Trailing punctuation (e.g. a sentence-ending ".") is kept out of the href.
const URL_RE = /(https?:\/\/[^\s<]+)/g

function renderWithLinks(text: string, isUser: boolean) {
  return text.split(URL_RE).map((part, i) => {
    if (!/^https?:\/\//.test(part)) return part
    const trail = (part.match(/[.,;:!?)\]}]+$/) || [''])[0]
    const url = trail ? part.slice(0, part.length - trail.length) : part
    return (
      <span key={i}>
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className={`break-all underline ${isUser ? 'text-white' : 'text-blue-300 hover:text-blue-200'}`}
        >
          {url}
        </a>
        {trail}
      </span>
    )
  })
}

function Bubble({ role, content }: { role: 'user' | 'assistant'; content: string }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] whitespace-pre-line rounded-2xl px-4 py-2 text-sm ${
          isUser ? 'bg-blue-600 text-white' : 'bg-white/5 text-slate-100'
        }`}
      >
        {renderWithLinks(content, isUser)}
      </div>
    </div>
  )
}
