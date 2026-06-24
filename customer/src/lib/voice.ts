import { useRef, useState } from 'react'

const LANG_BCP: Record<string, string> = {
  en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', bn: 'bn-IN',
}

export interface SpeakHandlers {
  onStart?: () => void
  onEnd?: () => void
}

/** Speak text with the browser's built-in TTS, in the customer's language. Optional handlers
 *  report start/end so a talking avatar can animate while speech is playing. */
export function speak(text: string, lang?: string, handlers?: SpeakHandlers) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = LANG_BCP[lang ?? 'en'] ?? 'en-IN'
  if (handlers) {
    u.onstart = () => handlers.onStart?.()
    u.onend = () => handlers.onEnd?.()
    u.onerror = () => handlers.onEnd?.()
  }
  window.speechSynthesis.speak(u)
}

export function stopSpeaking() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/** Mic capture via MediaRecorder. stop() resolves to the recorded audio Blob. */
export function useRecorder() {
  const [recording, setRecording] = useState(false)
  const mr = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])

  const start = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const m = new MediaRecorder(stream)
    chunks.current = []
    m.ondataavailable = (e) => chunks.current.push(e.data)
    m.start()
    mr.current = m
    setRecording(true)
  }

  const stop = () =>
    new Promise<Blob>((resolve) => {
      const m = mr.current
      if (!m) return resolve(new Blob())
      m.onstop = () => {
        m.stream.getTracks().forEach((t) => t.stop())
        resolve(new Blob(chunks.current, { type: 'audio/webm' }))
      }
      m.stop()
      setRecording(false)
    })

  return { recording, start, stop }
}
