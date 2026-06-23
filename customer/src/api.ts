const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// localStorage key for the demo "signed-in" customer (shared by Concierge + Demo).
export const CUSTOMER_KEY = 'apex_customer_id'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface DemoScenario {
  key: string
  label: string
}

export interface Outreach {
  outcome: string
  product_id: string | null
  message_text: string | null
  deep_link: string | null
}

export interface SimulateResult {
  customer_id: string
  scenario: string
  name: string
  language_pref: string | null
  outreach: Outreach[]
}

export interface CustomerLite {
  id: string
  name: string
  language_pref: string | null
  city_tier: string | null
  customer_type: string | null
}

export interface Dropoff {
  id: string
  name: string
  current_step: string | null
  product: string | null
}

export interface Product {
  product_id: string
  name: string
  category: string
  depth: string
  landing_url: string | null
  tax_saving: boolean
  description: string | null
  primary_use: string | null
}

export interface Suggestion {
  action_id: string
  message_text: string | null
  product_id: string | null
  open_url: string
  adopt_url: string
  dismiss_url: string
  why_url: string
  response: string | null
}

export interface Insights {
  balance: number
  monthly_income: number | null
  credits_90d: number
  spend_by_category: { category: string; amount: number }[]
  suggestions: Suggestion[]
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function postForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST', body: form })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  // Used only for the demo "sign in as" picker — production would authenticate the customer.
  customers: () => get<CustomerLite[]>('/customers'),
  // Customers with an unfinished application (Tier-2 drop-offs) — for the resume path on login.
  dropoffs: () => get<Dropoff[]>('/demo/dropoffs'),
  products: () => get<Product[]>('/products'),
  insights: (id: string) => get<Insights>(`/insights/${id}`),
  explain: (whyUrl: string) => get<{ explanation: string; declined: boolean }>(
    whyUrl.replace(/^https?:\/\/[^/]+/, '')),
  chat: (body: { mode: 'guide' | 'concierge'; customer_id?: string; messages: ChatMessage[] }) =>
    postJson<{ reply: string }>('/chat', body),
  transcribe: (blob: Blob) => {
    const form = new FormData()
    form.append('file', blob, 'audio.webm')
    return postForm<{ text: string }>('/voice/transcribe', form)
  },
  demoScenarios: () => get<DemoScenario[]>('/demo/scenarios'),
  demoSimulate: (scenario: string) => post<SimulateResult>(`/demo/simulate?scenario=${scenario}`),
}
