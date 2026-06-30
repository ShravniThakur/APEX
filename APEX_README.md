# APEX — Agent for Personalized Engagement and Experience

**SBI Hackathon (GFF 2026) — Agentic AI for Customer Acquisition, Digital Adoption & Digital Engagement**

> An AI agent that guides new customers to the right SBI products and, once it has their data, becomes an analyser that proactively understands their financial life and intervenes at the right moments — reachable anytime as a financial concierge.

---

## Table of contents

1. [Why this exists](#1-why-this-exists)
2. [The behavioral philosophy](#2-the-behavioral-philosophy)
3. [Three operating modes](#3-three-operating-modes)
4. [Customer acquisition](#4-customer-acquisition)
5. [Digital adoption](#5-digital-adoption)
6. [Ethical guardrail for vulnerable moments](#6-ethical-guardrail-for-vulnerable-moments)
7. [Graduated authority model](#7-graduated-authority-model)
8. [Architecture: wrapper, not backend rewrite](#8-architecture-wrapper-not-backend-rewrite)
9. [Data access model](#9-data-access-model)
10. [Delivery channels and cost reality](#10-delivery-channels-and-cost-reality)
11. [Channels and entry points](#11-channels-and-entry-points)
12. [Demo simulation mechanic](#12-demo-simulation-mechanic)
13. [Production integration: webhooks and internal data access](#13-production-integration-webhooks-and-internal-data-access)
14. [Explicitly rejected ideas](#14-explicitly-rejected-ideas)
15. [Open items](#15-open-items)

---

## 1. Why this exists

Banks already know customers need guidance — SBI's own static how-to videos and FAQ pages prove that. What they haven't built is the next step: guidance that's personal, conversational, and timed to a real moment in someone's financial life, rather than generic content waiting to be found.

The core insight behind APEX didn't come from asking "what agentic AI architecture fits this problem statement." It came from asking a more basic question: **why don't people actually use the bank products that already exist for them?** The answer isn't a discovery problem or a UX problem — it's a behavioral one. People are lazy, financially illiterate, distrustful of financial messages, and only receptive to a product in the narrow window when they have a genuine, present need for it. Every design decision in APEX follows from taking these facts seriously rather than assuming a smarter recommendation engine fixes the gap.

This is also, deliberately, a synthesis of all three PS pillars into a single coherent system rather than three separate agents bolted together. Acquisition, adoption, and engagement are not three problems — they're three moments in one continuous relationship, gated by how much APEX actually knows about the person it's talking to.

---

## 2. The behavioral philosophy

This is the actual differentiator. Every other team building on this PS will arrive at a similar agentic architecture, because that's what any AI assistant converges on when asked. Almost none will arrive at this philosophy, because it comes from questioning the obvious answer repeatedly, not from prompting.

1. **People are lazy** → minimize required action. Default to opt-out, not opt-in, wherever it's safe to do so.
2. **People are financially illiterate** → never use jargon (SIP, CAGR, NAV). Speak in concrete life outcomes: *"this becomes ₹X in 5 years,"* not instrument names.
3. **People are distrustful of financial messages that pattern-match to fraud** — regardless of the channel they arrive on. Even from a verified, trusted SBI channel, avoid links, urgency language, and overly benefit-forward phrasing. Real SBI alerts already get phished constantly, which means customers have been trained to distrust certain *shapes* of message independent of source. Calm, institutional tone — never promotional.
4. **Need is momentary, not demographic** → the agent is a life-moment detector, not a segment-based recommender. It acts on present, real signals — never "28-year-olds should invest."
5. **Detecting vulnerability is ethically dangerous** → never act immediately on a fear signal (e.g. a medical bill). Acknowledge and wait. Offer insight, not a product, until the customer's own realization pulls the product forward. The agent is on the customer's side, not the bank's.
6. **People don't read — they might listen** → voice is the primary interface; text is a fallback, never the default.
7. **Notifications are dead** → don't rely on app push notifications. Reach people through channels they already check daily and trust.
8. **Language is a moat** → the agent reasons and speaks natively in Hindi, Tamil, Telugu, Bengali, and other Indian languages — not English-first. This directly serves the semi-urban and rural customer base that fintech competitors (Zerodha, Groww, PhonePe) don't reach, because their products are built English-first for urban users.
9. **SBI's real moat is full product breadth** across someone's entire financial life — savings, loans, insurance, investments, payments — under one institution. No fintech has this. APEX's job is connecting life moments to the right product within that breadth.

---

## 3. Three operating modes

Not three agents. One agent, three trigger-gated modes, sharing the same reasoning core, memory, and data layer.

| Mode | Triggered by | What it does |
|---|---|---|
| **Guide** | Absence of data — new customer, dormant account, mid-onboarding drop-off | Conversational onboarding and navigation. Explains products in plain language. Hands off to SBI's real systems for execution. |
| **Analyser** | Signals in existing customer data — transactions, app usage, payment behavior | Detects life moments and product/adoption gaps. Reaches out proactively. |
| **Concierge** | Customer initiating contact, anytime | Answers direct questions ("can I afford this," "what's my spending trend") using the same data and reasoning. Solves the "no daily means to communicate" gap in long-term engagement. |

Mapped onto the PS pillars:

- **Acquisition** → Guide mode (true strangers, drop-offs, dormant reactivation)
- **Adoption** → Analyser mode (missing or idle products across payments, investments, insurance, mobile banking)
- **Engagement** → Analyser mode (proactive) + Concierge mode (reactive, daily-use)

The division of labor is deliberate: **Analyser mode creates the reason to come back. Guide and Concierge mode are where the customer actually does something, once they're there.**

---

## 4. Customer acquisition

Three honest, explicitly bounded tiers. No illegal data, no ad infrastructure.

### Tier 1 — True stranger, first contact

Arrives via an existing channel — branch referral, search, word of mouth. Guide mode runs conversational onboarding from scratch. Through conversation, APEX determines the right account type, the relevant documents, and the customer's language preference.

APEX never fills or submits a form. It constructs a **deep link to exactly the right official SBI onboarding page** — the right product, at the right step, for this person. The customer completes SBI's own form there; APEX never pre-fills it, and never touches SBI's backend or database. The value is **arriving at the right page already understood**: the conversation has settled the account type, the documents needed, and the language, so there's nothing left to *figure out* — even though the customer still fills SBI's form themselves. (URL-parameter pre-fill — "the page reads `?name=…&type=…` and self-populates" — was considered and dropped: it doesn't work against SBI's real pages, so APEX doesn't rely on it.)

### Tier 2 — Mid-onboarding drop-off

Customer started KYC/account opening and abandoned it. This is internal SBI data with no privacy issue, since the customer gave it directly for this exact purpose. Guide mode reaches out, conversationally identifies why they stopped (confused by a step, missing a document, got busy), and constructs a link back into SBI's actual form at the specific step they left off — not by resubmitting their data, but by routing them to the right point in the real flow instead of forcing a restart from zero.

*Dependency worth naming honestly: this tier assumes SBI's onboarding system can resume an application by ID/step rather than forcing a restart. If it can't, APEX's value here shrinks to a reminder — worth stating as an assumption, not discovering live in front of a judge.*

### Tier 3 — Existing dormant account

SBI already has the account; it's just inactive. Analyser mode detects dormancy, investigates plausibility of reactivation (recent KYC update, a branch visit, a stray transaction), and intervenes using the same graduated authority model as any other Analyser-mode action.

### Explicitly out of scope

APEX does not discover total strangers via ads, social media, or external/purchased data — that would be illegal and is not attempted. APEX never fills out or submits a form on a customer's behalf, and never writes to SBI's account-opening or KYC systems. This keeps the wrapper-not-rewrite boundary intact through every acquisition path, not just the architecture in general.

---

## 5. Digital adoption

Confirmed to span all four PS-named categories — payments, investments, insurance, mobile banking — not just the two that come up most naturally in conversation.

- **Investments** — idle balance detection → SIP/RD nudge, outcome-framed, never jargon.
- **Insurance** — medical/life-event signal → empathetic, delayed, non-exploitative approach (see Section 6).
- **Payments** — manual recurring payment pattern (e.g. the same bill paid manually six times) → autopay/standing-instruction nudge.
- **Mobile banking** — login/app-usage decay → outreach happens *outside* the app (since notifying inside an app nobody opens is pointless), with one concrete reason to open it.

This confirms the synthetic data schema needs more than balance and transaction category: it needs bill payment method history, UPI/payment channel usage, and app login/session logs.

---

## 6. Ethical guardrail for vulnerable moments

Never sequence: **detect vulnerability → push product.**

Always sequence: **detect → acknowledge and wait (typically a few days) → offer insight without a product attached → let the customer pull the product forward themselves, or escalate only if they re-engage.**

Timing matters as much as wording. Immediate contact after a sensitive transaction feels like surveillance, not care — this is the same dynamic behind real-world backlash to predictive marketing (e.g. retailers inferring pregnancy before a family knows). The agent is designed to never be that.

---

## 7. Graduated authority model

How the agent acts safely, without ever holding open-ended authority. Three levels are fully buildable within the wrapper architecture; one is explicitly future-state.

- **Level 1 — Insight only.** No action. Pure information, zero effort required. *"Noticed some larger expenses recently — want me to check your savings cushion?"*
- **Level 2 — One-tap confirm.** The agent prepares a specific action and hands off via a deep link to the right place in SBI's real system. The customer's tap on SBI's own page is what executes it — APEX never touches SBI's backend. *"I can set up autopay for this bill — tap to confirm on YONO."*
- **Level 3 — Standing rule, set up once.** The customer explicitly sets up a rule on SBI's side (e.g. auto-sweep idle balance above ₹50,000), via the same one-tap handoff as Level 2. After that, zero *repeated* effort — the rule executes on SBI's own infrastructure every time its condition is met. APEX's role becomes detection and notification: *"Your auto-sweep rule triggered today — here's why."*
- **Level 4 — Autonomous execution with an undo window** *(future state, not built in the prototype)*. The agent executes a one-shot action directly, with a countdown window for the customer to undo. This genuinely requires SBI to grant scoped, audited write access to its backend — a deeper integration than a read-only wrapper provides. Framed honestly as the natural next phase once trust in the read-only system is established, not claimed in the current build.

**Why this resolves the laziness-vs-architecture tension:** "minimize required action" is satisfied at every level actually built — Level 1 needs zero effort by design, Level 2 needs one tap, Level 3 needs effort only once. The one level that would require true zero-tap, per-instance execution is the one honestly marked as needing capability APEX doesn't have yet, rather than quietly assumed.

The agent never has open-ended authority — only what's explicitly granted at each level, and every action is logged and explainable.

---

## 8. Architecture: wrapper, not backend rewrite

- APEX never touches or modifies SBI's core banking system (CBS).
- APEX reasons, explains, and decides. The actual transaction always executes inside YONO or SBI's existing systems — APEX hands off via a deep link to the right page/step, and the customer completes it there.
- **SBI's CBS remains the sole source of truth** for balances, transactions, and account state. APEX only holds a synced read or cache for reasoning, plus its own audit log of signals, decisions, and outcomes — never a parallel financial ledger.
- This makes APEX a low-risk, pilot-able addition for SBI, not a request to rebuild anything.

This boundary is not a limitation discovered late — it's a deliberate choice. The hard, valuable, defensible part of agentic AI in banking is the reasoning, restraint, and judgment: deciding whether, when, and how to act. The execution step — moving money, opening an account — is comparatively trivial; banks already do that flawlessly. Trying to also own execution would mean solving an already-solved problem while adding risk, instead of staying focused on the genuinely unsolved problem: knowing what to do and saying it right.

---

## 9. Data access model

- **Production** — APEX is deployed by SBI itself, as an internal system, with direct **read-only** access to the core banking system (CBS) — the same kind of access any of SBI's internal analytics tools would have. APEX never writes to the CBS, only reads from it; the wrapper boundary (Section 8) holds regardless of how access is granted.
- **Prototype** — synthetic data simulating what this direct read access would provide. No real customer data, anywhere, at any stage of the build.

---

## 10. Delivery channels and cost reality

There is no fully free way to deliver real SMS, WhatsApp, or voice calls — telecom delivery has real per-message cost, which is true for every team at this hackathon, not a unique weakness.

**Free and fully real options used instead:**
- LLM inference — Groq free tier
- Speech-to-text — Whisper, local, free
- Text-to-speech — Piper/Coqui, local, free
- Email — Resend or Brevo free tiers, genuinely real delivery, not simulated
- In-browser voice — mic/speaker only, no telecom needed

**Decision:** simulate SMS/WhatsApp/voice-call delivery in the demo where needed — standard, expected practice that judges don't penalize — while keeping the reasoning and voice-generation pipeline itself fully real and functional. For Analyser mode's actual outbound trigger in the prototype, use **real email** rather than a simulated WhatsApp/SMS message — see Section 11.

**Production unit-economics note worth mentioning to judges:** WhatsApp Business API service-window messages (customer-initiated) are free; utility/marketing messages are not. A reasonable strategy is to keep first outbound contact minimal and cheap (e.g. SMS), and if the customer responds, the rest of that conversation falls into WhatsApp's free service window.

---

## 11. Channels and entry points

APEX is its own product, with a real website — both for the prototype and the production vision.

- **Guide mode lives on APEX's website.** This is a genuine fit, not a compromise: someone trying to open an account is in active-search mode, already looking for something to do. A website is the normal, expected interface for a task someone came looking for, unlike an unprompted notification.
- **Concierge mode also lives on APEX's website**, on the same surface as Guide mode. This matches how most real products work — support and concierge chatbots almost always live on the company's own platform, not on WhatsApp. Concierge doesn't need to manufacture daily engagement on its own; that job belongs to Analyser mode. Concierge just needs to be available and good whenever a customer arrives with a question, however they got there.
- **Analyser mode is the only mode that reaches out proactively.** It's the answer to "no daily means to communicate" — it creates the reason to engage. In production this would be WhatsApp or SMS, since that's where people already check daily. **For the prototype, this is real email** instead, since WhatsApp/SMS require paid infrastructure with no real free tier. The reasoning, detection, and content are identical either way — only the delivery channel differs, as a deliberate cost decision, not a shortcut.
- **The bank-ops dashboard** is a separate, internal view — where the bank sees what the agent has done across different customers: the reasoning traces, decisions, and outcomes.

**The division of labor, stated plainly:** Analyser mode creates the reason to come back. Guide and Concierge mode are where the customer actually does something, once they're there. WhatsApp/SMS/email are never the interface itself — they're the trigger that brings someone to the interface.

---

## 12. Demo simulation mechanic

The mechanic that demonstrates the Guide-to-Analyser mode transition without requiring real SBI integration or mocking any SBI product page.

1. **Conversation** — a new customer talks to APEX in Guide mode. APEX determines the right account type, language, and documents needed.
2. **Handoff** — the real, specific SBI link is shown — a deep link to exactly the right official page/step. This is the actual onboarding action; nothing here is simulated. (APEX never pre-fills or submits the form — the customer completes it on SBI's page.)
3. **Demo control: "Simulate 3 months of activity"** — a button visible only in the demo dashboard, not part of the customer-facing experience.
4. **On trigger** — a batch insert seeds `CUSTOMERS`, `ACCOUNTS`, `TRANSACTIONS`, and `APP_SESSIONS` with synthetic but schema-correct data: three months of realistic activity for one customer. No consent step here — APEX reads SBI's own data as an internal system, the same way any of SBI's internal tools would, not as a third party requesting access; see Section 9.
5. **Signal detection runs immediately** — for demo pacing, rather than waiting for a nightly sweep.
6. **Dashboard updates** — the same customer record, now in Analyser mode, with a real reasoning trace and decision.

**Why this is the right level of honesty, not a shortcut:** the only thing simulated is the moment data starts existing for a customer — the seam where SBI's internal systems would notify APEX that an account is active. Everything else (the conversation, the link construction, the resulting reasoning) is fully real.

**Technical note — batch insert, not Kafka.** A direct batch write is correct for this one-time, finite seed. Using a streaming pipeline here would be unjustified complexity for what is, at this scale, a simple insert — a technical judge could reasonably question it. Kafka-style event streaming remains the right *production* answer for periodic syncs across millions of real customers, worth naming as the production architecture, just not what powers this specific demo button.

**Line for the pitch:** *"In production, this data would arrive through SBI's own internal systems, since APEX is deployed as part of SBI's infrastructure, not a third party. For today's demo, this button simulates that internal data becoming available directly."*

---

## 13. Production integration: webhooks and internal data access

### Account-level events — webhooks

SBI's system can notify APEX the instant an account is created, the same way Stripe notifies a merchant the instant a payment succeeds. Since APEX is deployed internally by SBI (Section 9), this is an internal event-emission system tied to account creation — meaningfully simpler than any external integration, since both sides are SBI's own infrastructure.

**Honest nuance on timing:** KYC isn't always instant — Aadhaar/PAN validation or video KYC can introduce a real delay between "signed up" and "account exists and is usable." SBI's own systems notify APEX whenever the account is officially open, which APEX doesn't control or accelerate. The Guide-to-Analyser mode transition is bounded by however long SBI's actual activation process takes — before that point, APEX has zero data, full stop.

### Transaction-level data — not a per-transaction webhook

A webhook firing for every one of SBI's hundreds of millions of daily transactions isn't really "a webhook" anymore in the simple sense — at that volume it becomes a production-grade event-streaming pipeline (Kafka-style), not a lightweight HTTP callback. The honest production answer: account-level events (low frequency) are genuine webhooks; transaction-level signals are more realistically delivered as a periodic batch sync via a direct internal feed, since APEX is reading from SBI's own CBS, not pulling from an external source.

---

## 14. Explicitly rejected ideas

Worth remembering for Q&A — these were considered and deliberately discarded, with reasoning.

- **Pure rule-based redirect to SBI pages** — rejected. That's a search engine, not agentic.
- **Simulated deep YONO integration mockups** — rejected as the core build. Would imply a backend rewrite SBI wouldn't realistically adopt, and risks looking fake to a technical judge.
- **A standalone chatbot, separate from the voice agent** — rejected. Contradicts the "people don't want to read" philosophy. Folded into voice-with-text-fallback instead.
- **Budgeting/expense-tracking as a user-facing feature** — rejected. That's a different product entirely (competes with Walnut/CRED) and doesn't connect to bank products. Kept only as an invisible signal layer for life-moment detection, never shown to the customer as a feature.
- **External or purchased customer data for "identifying" new prospects** — rejected outright as illegal and unethical. Replaced with internal-data-only acquisition tiers (Section 4).
- **Multi-agent-per-pillar architecture** (separate Acquisition/Adoption/Engagement agents) — rejected in favor of one agent with three trigger-gated modes, which is more elegant and easier to defend under questioning.
- **Kafka for the demo's data-seeding mechanic** — rejected as unjustified complexity for a one-time batch insert. Kept as the correct production answer for periodic data syncs at real scale.

---

## 15. Open items

Honest gaps still worth resolving before the build is considered complete:

- Whether SBI's real onboarding system supports **resuming an application by ID/step** (Tier 2 acquisition) — an assumption the design currently relies on without confirmation.
- Final decision on which products/flows get full synthetic data coverage versus narrower demonstration scope, given prototype time constraints.
- How agent behavior concretely changes over time based on logged outcomes — this conceptual document establishes *that* a feedback loop exists; the actual mechanism is a technical design question for the implementation README.
- How the agent prioritizes across many customers at scale when a sweep surfaces more signals than can be processed at once — also a technical design question, not yet resolved here.
