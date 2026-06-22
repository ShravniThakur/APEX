const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// --- types (mirror backend/apex/api/serializers.py) --- #
export interface Stats {
  customers: number
  signals: number
  signals_by_type: Record<string, number>
  decisions: number
  decisions_by_outcome: Record<string, number>
  emails_sent: number
}

export interface Score {
  type: string
  value: any
  computed_at: string | null
}

export interface Signal {
  id: string
  type: string
  source_ref: string | null
  detected_at: string | null
  status: string
}

export interface Outcome {
  response_type: string
  responded_at: string | null
  window_closed: boolean
}

export interface Action {
  id: string
  authority_level: number | null
  channel: string | null
  message_text: string | null
  deep_link: string | null
  sent_at: string | null
  response: Outcome | null
}

export interface Decision {
  id: string
  mode: string
  trigger_ref: string | null
  hypothesis: string | null
  critique_result: string | null
  confidence: number | null
  outcome: string
  product_id: string | null
  created_at: string | null
  action: Action | null
}

export interface Account {
  id: string
  account_type: string
  balance: number | null
  status: string
  opened_date: string | null
}

export interface Holding {
  id: string
  product_id: string
  current_value: number | null
}

export interface Transaction {
  id: string
  amount: number | null
  direction: string
  merchant_category: string | null
  channel: string | null
  payee_id: string | null
  txn_time: string | null
  is_manual_recurring: boolean
}

export interface CustomerBase {
  id: string
  name: string
  age: number
  gender: string | null
  city_tier: string | null
  language_pref: string | null
  occupation: string | null
  customer_type: string | null
  kyc_status: string | null
  monthly_income: number | null
  owns_property: boolean
  dependents: number
  owns_gold: boolean
  has_papl_offer: boolean
  has_card_offer: boolean
}

export interface CustomerSummary extends CustomerBase {
  signal_count: number
  signal_types: string[]
  decision_outcomes: Record<string, number>
}

export interface CustomerDetail extends CustomerBase {
  accounts: Account[]
  holdings: Holding[]
  scores: Score[]
  signals: Signal[]
  decisions: Decision[]
  recent_transactions: Transaction[]
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  stats: () => get<Stats>('/stats'),
  customers: () => get<CustomerSummary[]>('/customers'),
  customer: (id: string) => get<CustomerDetail>(`/customers/${id}`),
  runPipeline: () => post<{ ok: boolean }>('/pipeline/run-all'),
}
