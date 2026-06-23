# APEX — Presentation Content

**SBI Hackathon (GFF 2026) · Agentic AI for Customer Acquisition, Digital Adoption & Digital Engagement**

> This document is the complete content for the ideathon deck. It is organised as slides. Each slide has a **headline**, the **on-slide content** (what the audience reads), and **speaker notes** (what you say / Q&A ammunition). It is intentionally exhaustive — cut to fit your time budget; the priority order is marked.
>
> **Structure:** Part A — The Idea & Why It Wins · Part B — Production Architecture & Scalability (full layer-by-layer) · Part C — The Prototype (tech stack + demo decisions).
>
> **The single sentence to anchor everything:** *APEX is one AI agent that guides new customers to the right SBI product, then — once it has their data — becomes an analyser that understands their financial life and intervenes at the right moments, and is reachable any time as a financial concierge.*

---

# PART A — THE IDEA & WHY IT WINS

---

## Slide 1 — Title

**APEX — Agent for Personalized Engagement and eXperience**

- One agent. Three modes. The whole customer relationship.
- *Acquisition → Adoption → Engagement, solved as one continuous system — not three bolted-together bots.*
- Team name · GFF 2026 · SBI Hackathon

**Speaker notes:** Open with the anchor sentence above. Don't lead with architecture — lead with the relationship. The architecture is *how*; the relationship is *what*.

---

## Slide 2 — The Problem (the real one, not the obvious one) · PRIORITY

**Banks already have the products. People still don't use them. Why?**

The gap isn't discovery or UX. It's **behavioral**:
- People are **lazy** — they won't take action unless it's nearly effortless.
- People are **financially illiterate** — jargon (SIP, CAGR, NAV) repels them.
- People are **distrustful** — real SBI alerts get phished constantly, so customers have been trained to distrust the *shape* of financial messages, regardless of source.
- **Need is momentary, not demographic** — "28-year-olds should invest" is noise; "you just paid a hospital bill" is a moment.

**Speaker notes:** This is the slide that separates you from every other team. State plainly: "Every team here will arrive at a similar agentic architecture, because that's what any AI assistant converges on. Almost none will arrive at this *philosophy*, because it comes from questioning the obvious answer, not from prompting." SBI's own static how-to videos and FAQ pages prove they know customers need guidance — what hasn't been built is guidance that is *personal, conversational, and timed to a real moment.*

---

## Slide 3 — The Behavioral Philosophy (the actual differentiator) · PRIORITY

**Nine principles. Every design decision in APEX follows from these.**

1. **People are lazy** → minimise required action; default to opt-out where safe.
2. **People are financially illiterate** → never use jargon; speak in life outcomes ("this becomes ₹X in 5 years," not "SIP").
3. **People distrust financial messages** → calm, institutional tone; no links, no urgency, no hype — never pattern-match to a scam.
4. **Need is momentary** → a life-moment *detector*, not a segment-based recommender.
5. **Detecting vulnerability is ethically dangerous** → never act immediately on a fear signal (a medical bill). Acknowledge, wait, offer insight — let the customer pull the product forward.
6. **People don't read — they might listen** → voice-first, text as fallback.
7. **Notifications are dead** → reach people on channels they already check daily (WhatsApp/SMS), not app push.
8. **Language is a moat** → reason and speak natively in Hindi, Tamil, Telugu, Bengali — not English-first. This is the semi-urban/rural base fintechs (Zerodha, Groww, PhonePe) don't reach.
9. **SBI's real moat is product breadth** — savings, loans, insurance, investments, payments under one roof. No fintech has this. APEX connects life moments to the right product across that whole breadth.

**Speaker notes:** Read 2–3 of these aloud, not all nine. The ones that land hardest with judges: #5 (ethics), #8 (language moat), #9 (breadth as moat). Emphasise that the agent is **on the customer's side, not the bank's** — and that this restraint is what *earns* the trust that ultimately drives conversion.

---

## Slide 4 — The Solution: One Agent, Three Modes · PRIORITY

**Not three agents. One reasoning core, three trigger-gated modes, sharing the same memory and data layer.**

| Mode | Triggered by | What it does | PS pillar |
|---|---|---|---|
| **Guide** | Absence of data — new customer, drop-off, dormant | Conversational onboarding & navigation in plain language; hands off to SBI's real systems | **Acquisition** |
| **Analyser** | Signals in existing data — transactions, app usage | Detects life moments & product gaps; reaches out proactively | **Adoption + Engagement** |
| **Concierge** | The customer, any time | Answers direct questions ("can I afford this?", "how's my spending?") | **Engagement** |

**The division of labor:** *Analyser creates the reason to come back. Guide and Concierge are where the customer actually does something, once they're there.*

**Speaker notes:** The elegance is the point: three PS pillars are not three problems — they're three moments in one relationship, gated by how much APEX knows about the person. This is why one agent beats three. (See Slide 25 for the "why one agent" defense.)

---

## Slide 5 — Differentiator: The Ethical Guardrail for Vulnerable Moments · PRIORITY

**Never sequence: detect vulnerability → push product.**

**Always sequence:** detect → acknowledge & wait (typically a few days) → offer insight with no product attached → let the customer pull the product forward, or escalate only if they re-engage.

- Immediate contact after a sensitive transaction (a hospital bill) feels like surveillance, not care.
- This is the same dynamic behind real-world backlash to predictive marketing (retailers inferring pregnancy before the family knew). APEX is designed to *never be that.*
- **In the build, this is enforced in code, not a prompt:** a `life_event` (medical) signal is hard-wired to **WAIT** — the agent literally cannot push a product on it.
- **And it's *holistic*, not per-signal:** if a customer is in a vulnerable moment, APEX also suppresses insurance pushes that a *different* signal (e.g. a "no insurance yet" gap) would otherwise surface — so it never exploits the moment through a side door. The restraint follows the customer, not the trigger.
- **The wait is a pause, not a refusal — and it's *built*, not just described:** a scheduled **re-engagement** pass revisits a `wait` once the acute moment has passed and — *only* if the customer isn't still in severe stress — sends a single **product-free, link-free Level-1 insight** that never names the sensitive event. The full "acknowledge → wait → offer insight, let them pull the product forward" sequence runs end to end, in code.

**Speaker notes:** This is the most defensible slide under questioning. It demonstrates judgment and restraint — the genuinely hard, valuable part of agentic AI in banking. Pair it with the demo's "medical event → restraint" scenario, then show the re-engagement follow-up appearing days later (the "Re-engage waits" action on the ops dashboard) — proof the wait actually *resolves*, it doesn't just stall.

---

## Slide 6 — Differentiator: The Graduated Authority Model

**The agent never holds open-ended authority — only what's explicitly granted at each level. Every action is logged and explainable.**

- **Level 1 — Insight only.** Pure information, zero effort. *"Noticed some larger expenses — want me to check your savings cushion?"*
- **Level 2 — One-tap confirm.** Agent prepares a specific action, hands off via a deep link into SBI's real system; the customer's tap on SBI's own page executes it.
- **Level 3 — Standing rule, set once.** Customer sets up a rule (e.g. auto-sweep idle balance above ₹50,000) on SBI's infrastructure. After that, zero repeated effort — the rule runs on SBI's side; APEX just detects and explains.
- **Level 4 — Autonomous execution with undo window** *(future state, honestly not built).* Requires SBI to grant scoped, audited write access.

**Speaker notes:** This resolves the laziness-vs-safety tension: "minimize required action" is satisfied at every built level (L1 zero effort, L2 one tap, L3 effort once). The one level that needs true zero-tap is the one honestly marked future-state — *not quietly assumed.* Honesty here builds credibility.

---

## Slide 7 — Differentiator: Wrapper, Not Backend Rewrite · PRIORITY

**APEX never touches or modifies SBI's Core Banking System (CBS). It reasons, explains, and decides. SBI executes.**

- SBI's CBS remains the **sole source of truth** for balances, transactions, account state.
- APEX holds only a synced **read** for reasoning, plus its own **audit log** of signals, decisions, and outcomes — never a parallel financial ledger.
- Execution (moving money, opening an account) always happens inside YONO / SBI's existing systems, via a **deep link**, pre-filled where the page supports it.

**Why this is a deliberate strength, not a limitation:**
> The hard, defensible part of agentic AI in banking is the *reasoning, restraint, and judgment* — deciding whether, when, and how to act. Execution is comparatively trivial; banks already do it flawlessly. Owning execution would mean re-solving a solved problem while adding risk.

**Speaker notes:** This is what makes APEX a **low-risk, pilot-able** addition for SBI — not a request to rebuild anything. Comes back as a major scalability/blast-radius point in Part B.

---

## Slide 8 — Customer Acquisition: Three Honest Tiers

**No illegal data. No ad infrastructure. No purchased prospect lists.**

- **Tier 1 — True stranger.** Arrives via an existing channel (branch referral, search, word of mouth). Guide mode runs onboarding from scratch, determines the right account type, documents, and language, then constructs a **specific deep link** into SBI's real onboarding flow (e.g. `sbi.com/open-account?type=savings&name=Rohan&lang=hi`) — SBI's page reads the parameters and self-fills. APEX never fills or submits a form.
- **Tier 2 — Mid-onboarding drop-off.** Customer abandoned KYC. Internal SBI data, no privacy issue (they gave it for this exact purpose). Guide conversationally identifies why they stopped and routes them back to the exact step — not a restart from zero.
- **Tier 3 — Existing dormant account.** Analyser detects dormancy and intervenes via the same graduated-authority model.

**Explicitly out of scope:** discovering strangers via ads/social/purchased data (illegal, not attempted); filling or submitting forms; writing to SBI's KYC/account-opening systems.

**Speaker notes:** Tier 2 honestly depends on SBI's onboarding system being able to resume by ID/step — name this as an assumption, not a claim. Drop-off is more detectable the further along they got (a video-KYC step has a backend record; the first screen may not).

---

## Slide 9 — Digital Adoption: All Four Categories

**Spans payments, investments, insurance, and mobile banking — not just the obvious two.**

- **Investments** — idle-balance detection → SIP/RD/sweep nudge, outcome-framed, never jargon.
- **Insurance** — medical/life-event signal → empathetic, delayed, non-exploitative (the ethical guardrail).
- **Payments** — manual recurring payment pattern (same bill paid manually 6×) → autopay/standing-instruction nudge.
- **Mobile banking** — login/app-usage decay → outreach happens *outside* the app (notifying inside an app nobody opens is pointless), with one concrete reason to open it.

**Speaker notes:** This is why the data schema needs more than balance + category: it needs bill-payment method history, payment-channel usage, and app login/session logs. (Foreshadows the prototype's schema design.)

---

## Slide 10 — Why an Agent, Not a Rule Engine or a Single LLM Call · PRIORITY

**Rejected: signal → one LLM call → output. (That's inference with a trigger, not an agent.)**

**Adopted: a deterministic decision gate + a constrained LLM step.** Code decides *whether, when, and what*; the LLM only picks the best fit from a pre-vetted set and writes the message.

- The mechanical step (match candidates against eligibility) *is* a rule — and we keep it a rule.
- What a rule alone **structurally cannot do**, and where the system earns its keep:
  1. **Timing judgment** — code holds *all* outreach during a vulnerable moment (`life_event`), then a scheduled pass re-engages gently once it has passed.
  2. **Output is language, not a row** — outcome-framed, jargon-free, in the customer's language.
  3. **Relevance judgment** — among several *eligible* products, the LLM picks the one that fits this specific person (a conservative deposit for a risk-averse saver over a higher-ranked investment).
- **The technically-correct-but-wrong case is caught in *code*, not hoped for in a prompt:** a high insurance propensity that exists *because* of a recent medical expense is blocked by the deterministic vulnerability lock — guaranteed, every time.

**The hybrid principle: "code disposes, the LLM proposes."** Code makes the act/wait/escalate decision and fixes the set of allowed products; the LLM proposes the relevance pick and the wording — it can never reach an unsafe option, raise the authority level, or act when code said hold.

**Speaker notes:** If a judge says "this could just be rules" — agree about the *decision*: it **is** deterministic, on purpose, because proactive financial outreach must be guaranteed, not probabilistic. Then pivot: "What rules can't do is read this specific person, choose the most fitting of several eligible options, and say it well in their language — that's the LLM, bounded by a code gate that guarantees the ethics."

---

# PART B — PRODUCTION ARCHITECTURE & SCALABILITY

*This part walks the system layer by layer (Slides 11–18), then the scalability and production-operations story (Slides 19–25).*

---

## Slide 11 — Architecture Overview (the map) · PRIORITY

**One coherent system, seven layers — each layer cheaper than the next, which is what makes it scale.**

```
 ┌─ Layer 1  DATA SUBSTRATE ........ SBI's CBS (read-only) + product catalogue        [what exists]
 ├─ Layer 2  ML SCORING ............ stress · propensity · churn · anomaly (+sim,conf) [interpretation]
 ├─ Layer 3  SIGNAL DETECTION ...... cheap rule/threshold gate — who's worth waking    [the gate]
 ├─ Layer 4  THE DECISION GATE ..... per-customer code gate (act/wait/escalate + safe set) → LLM pick+compose [judgment]
 ├─ Layer 5  THREE MODES ........... Guide / Analyser / Concierge (shared data + ethics)  [context]
 ├─ Layer 6  EXECUTION BOUNDARY .... deep link · standing rule · pure info — never CBS  [the wrapper]
 └─ Layer 7  POST-DECISION FLOW .... generate → validate → deliver → log → outcome      [closing the loop]
```

**Speaker notes:** Walk top to bottom once, slowly, then say: "The next seven slides take each layer in turn." The recurring idea to plant now: **scoring runs for everyone (cheap); reasoning is gated to the few who have a signal (expensive)** — the foundation of the scalability story on Slide 19.

---

## Slide 12 — Layer 1: The Data Substrate (what exists) · PRIORITY

**The system of record APEX reasons over — read-only. SBI's CBS is the sole source of truth.**

- **Core entities:** customers, accounts, transactions, app sessions, applications, holdings — plus the product catalogue. In production this is SBI's CBS, accessed via direct internal **read-only** access. APEX keeps a synced read/cache for reasoning, **never a parallel ledger.**
- **The schema is engineered for life-moment detection, not just banking basics.** Three fields do the heavy lifting:
  - **Payment *method* history** (`channel`: upi / neft / autopay / card) — lets APEX tell a manual payment from an automated one.
  - **A stable `payee_id`** — so "the *same* electricity bill paid manually six times" is distinguishable from "six different utility payments." Category alone can't do this.
  - **App login / session logs** (`login_time`, `duration_seconds`, `features_used`) — the basis for engagement-decay and dormancy.
- **Alongside the substrate sits APEX's own operational/audit log** (scores, signals, decisions, actions, outcomes) — its brain and explainability trace.

**Speaker notes:** The key insight: **almost all of this raw data already exists inside any bank** as a byproduct of running a CBS and a mobile app. What doesn't exist is the *interpretation*. APEX adds interpretation, not new data collection — which is exactly why it's a low-friction internal deployment, not a data-grab.

---

## Slide 13 — Layer 2: The ML Scoring Layer (interpretation) · PRIORITY

**Turn raw data into a few calibrated scores per customer, so the agent reasons on "stress = 0.81," never on raw transactions.**

| Score | Answers | Type |
|---|---|---|
| **Stress** | Under financial strain right now? | Supervised (gradient-boosted trees) |
| **Propensity** | How likely to want each product category? | Supervised, multi-label |
| **Churn / dormancy** | Disengaging — and how far along? | Supervised (decay-trend features) |
| **Anomaly** | Is this event unusual *for this customer*? | Unsupervised (per-customer baseline) |
| *+ Similarity* | "Customers like this responded better to a 4-day wait" | Embedding / cosine |
| *+ Confidence* | How sure are we? | **Derived** (distance from decision boundary — not a 5th model) |

**Why ML and not just rules:** stress, propensity, and decay are **multi-signal patterns relative to a customer's own baseline** — no single threshold captures "spending velocity rising *while* balance drops, *for this person*." Where a clean rule suffices (e.g. "no transaction for 90 days = dormant"), APEX uses a rule. The mix is deliberate, not maximalist.

**Two computation patterns:** scheduled **batch** (nightly — powers Analyser) and **on-demand** (live, one customer — powers Concierge). All scores land in a `SCORES` table.

**Speaker notes:** Two points to land. (1) Discipline: we only reach for ML where the pattern genuinely needs it — anything reducible to a clean, explainable rule stays a rule (cheaper, auditable). (2) Anomaly is **per-customer** — compare each person only to themselves — so a fixed ₹-threshold neither floods high-spenders nor misses low-spenders.

---

## Slide 14 — Layer 3: The Signal Detection Layer (the gate) · PRIORITY

**A cheap, mostly rule-based check that decides *whether the expensive agent runs at all* for a customer this cycle.**

- It sits between scoring (cheap, computed for *everyone*) and the agent (expensive, run only when warranted). **Only a signal being created wakes the agent.**
- **Three kinds of signal:**
  - **Pure-rule** (read raw data directly): `idle_balance`, `manual_recurring_payment`, `dormancy`, `application_dropoff`, `sustained_rent_payment`, `tuition_payment` …
  - **Score-threshold** (fire when an ML score crosses a line): `cash_flow_stress` (stress), `login_decay` (engagement decay), `life_event` (anomaly flags a *medical* transaction), `churn_risk` (attrition model → escalate to a human for retention).
  - **Conversational** (`stated_intent`): a product interest the customer *voiced* in a Concierge chat, extracted and written as a signal (see Slide 16). The strongest signal of all — a present, stated need — and it flows through the very same ethical gate.
- **Coverage spans every PS category:** investments (`idle_balance`), payments (`manual_recurring_payment`), mobile banking / reactivation (`login_decay`, `dormancy`), insurance + vulnerability (`life_event`), acquisition Tier 2 (`application_dropoff`), and the loan family (`sustained_rent_payment`→home, `tuition_payment`→education, `cash_flow_stress`→personal/secured).
- **Lifecycle:** a signal has a status — **new → processed → expired.** One not acted on within its window expires rather than staying open forever. *This is the hook the scale-prioritisation lever uses (Slide 20).*

**Speaker notes:** This is the single most important layer for cost. "Scoring is universal per cycle; reasoning is gated." Cheap comparisons decide who's worth waking the agent for — that's what makes the funnel on Slide 19 real rather than aspirational.

---

## Slide 15 — Layer 4: The Decision Gate (judgment) · PRIORITY

**Per customer, code decides — then the LLM picks the best fit and writes it.**

- **Gather** — for one customer, *all at once*: profile, transactions, scores, eligibility, their **dismissal-count "memory"** (per-category, from the outcome log), their **recently-recommended products** (cooldown), and their **full set of active signals**.
- **Decide (deterministic code — `decide_customer`)** — resolves to **act / wait / escalate** and builds the **safe set**: eligible, unheld products, minus vulnerability-locked categories (insurance / unsecured debt in a vulnerable moment), minus dismissed categories, minus anything on cooldown. Bright-line ethics live here — e.g. an active `life_event` holds *all* outreach for that customer.
- **Pick + compose (LLM, only on `act`)** — from the vetted safe set the LLM chooses the single best fit for *this* person and writes the outcome-framed, jargon-free, in-language message. Code validates the pick is in the set; it can't reach anything else.
- **None of the three outcomes is a dead end:** `act` delivers, `wait` is revisited later by the re-engagement pass (Slide 5), and `escalate` lands in a **human-RM queue** (a real inbox on the ops dashboard) — for `churn_risk`, severe-stress-with-only-unsecured-debt, and "nothing eligible."

**"Code disposes, the LLM proposes."** The decision and every ethic are deterministic code, not the LLM — that's what makes the guarantees trustworthy. The LLM exercises only *relevance* (which eligible product fits this person) and *language*. Even if it were prompt-injected, the worst it could do is pick a different *already-vetted* product or write weaker copy. **Every step is logged**, so the reasoning trace *is* the audit log.

**Speaker notes:** We deliberately removed an earlier hypothesise→self-critique LLM loop — the critique was fed the same two numbers (stress, dismissal count) the code gate already decided on, so it added cost and an illusion of "agentic-ness," nothing more. The honest, leaner design (code makes every decision; the LLM picks relevance and phrases) is cheaper — *zero* LLM calls on wait/escalate — and more defensible. If asked "where's the AI judgment, then?": choosing the most fitting of several eligible products for a real person, in their language, bounded by a gate that guarantees the ethics.

---

## Slide 16 — Layer 5: Three Modes, One Core (context)

**It's not three agents. The three modes share one **data substrate + product/eligibility logic + ethical guardrail** — what changes is the *trigger*, the *starting context*, and the *technique* best suited to each.**

| Mode | Trigger | What it pulls | Technique | Channel |
|---|---|---|---|---|
| **Guide** | Absence of data | Catalogue, real document lists, and live application-lookup — via tools | Tool-calling agent (grounded onboarding; spots drop-offs) | APEX website |
| **Analyser** | A batch-computed signal | The whole customer — real data + history, all signals at once | Per-customer code gate + LLM relevance pick | Email (proto) / WhatsApp-SMS (prod) |
| **Concierge** | The customer asks | Scoped to the question ("can I afford this?" → balance + stress only) | Tool-calling agent (computes real answers) | APEX website |

**Concierge "code disposes" too.** When a customer asks "what should I get?", Concierge doesn't freelance — it calls a `recommend_product` tool that runs the **same routing + eligibility + guardrail gate as the Analyser** and returns only vetted products (eligible, not already held, ethically cleared). The LLM phrases; code decides the product — the same principle, applied to all modes.

**Concierge also *feeds* the Analyser.** After each chat, a background pass extracts the customer's **stated intents** and writes them as `stated_intent` signals — so a conversation today becomes a proactive, well-timed follow-up later, through the same gate. The ethical split holds: an explicit "I want to invest" is actionable; if the chat reveals distress, APEX creates nothing and *withdraws* any pending intents. This is what makes APEX **one continuous relationship** rather than three silos — the modes feed each other.

**Three meanings of "memory," not conflated:**
1. **Conversational** (within one session) — standard LLM context.
2. **Interaction** (across sessions — "have we talked before, what happened") — a read of the decisions/actions/outcomes log.
3. **Model** (does it retrain) — handled for now by the explainable **dismissal-count** mechanism, not silent retraining.

**Speaker notes:** Reinforce the "why one agent" point (Slide 25): the ethical guardrail lives in the *shared* core, so it can't be accidentally forgotten in one mode. Different inputs, same conscience.

---

## Slide 17 — Layer 6: The Execution Boundary (the wrapper)

**Every action APEX takes resolves to exactly one of three safe things. It never writes to CBS.**

- **Deep link (Mechanism B)** — SBI's own page reads URL parameters and self-fills; the customer's tap *on SBI's page* executes the action. APEX never touches the backend.
- **Standing rule** — the customer sets up a rule **once** on SBI's own infrastructure (e.g. MOD/Auto-Sweep: real ₹50,000 trigger, ₹35,000 floor); SBI then runs it every time the condition is met. APEX's role shrinks to detect-and-explain.
- **Pure information** — no action at all (Level 1 insight).

The **graduated authority model** (Levels 1–3 buildable, Level 4 future-state) governs which of the three applies. "Minimize required action" is satisfied at every level actually built.

**Speaker notes:** Framed as a layer, the point is: **execution lives *outside* APEX, by design.** This is the same wrapper idea as Slide 7, but here it's the architectural seam where APEX stops and SBI's systems take over — which is precisely what makes it safe and pilot-able.

---

## Slide 18 — Layer 7: The Post-Decision Flow (closing the loop)

**After the gate says "act," five steps — not one.**

1. **Generation** — the decision becomes customer-facing text, in the customer's language, behavioral-philosophy-compliant.
2. **Validation** — a rule-based guardrail pass on the *generated text*: no jargon leak, no recommending a product eligibility didn't confirm, no ethical-timing violation. A safety net on generation, not a new ML model — **defense in depth** after the decide-gate.
3. **Delivery** — by mode: Analyser → email/WhatsApp; Guide/Concierge → rendered directly in the website thread.
4. **Deep-link construction** — build the Mechanism B link from the product's URL template, pre-filled where supported, and attach it.
5. **Logging + outcome capture** — full trace → `DECISIONS`/`ACTIONS`; whatever the customer does later (clicked / dismissed / ignored / completed) → `OUTCOMES`, feeding the dismissal-count memory.

**Plus a "Why am I seeing this?" layer:** a second, constrained generation that explains a decision using only facts the customer already knows — and **declines to elaborate if the trigger was a vulnerability signal**, so they can't reverse-engineer that something sensitive was detected.

**Speaker notes:** Two guardrail passes (the decide-gate *and* output validation) = defense in depth. The explanation layer makes "on the customer's side" concrete and clickable — transparency that still respects the same restraint as everything else.

---

## Slide 19 — Scalability: The Architecture IS a Cost Funnel · TOP PRIORITY

**"How does this work for SBI's 50 crore customers?" — The expensive part never runs on the whole base.**

```
Layer 2: score everyone   →  Layer 3: detect signals  →  Layer 4: decide (code)     →  Layer 4: LLM reasoning
 (cheap, batchable)            (cheap rule checks)         (cheap deterministic gate)     (expensive — tiny subset)
 ~500M customers               only a few % fire           runs on all signals            only on "act" + prioritised
```

- **LLM volume scales with real life-events, not population size.**
- An LLM call only happens for a customer who (a) tripped a signal, (b) resolved to "act" at the deterministic gate, (c) survived prioritisation, and (d) isn't inside a cooldown window.

**Speaker notes:** THE slide for the technical judge, and the reason the layer-by-layer walk mattered: each layer filters the next. Every other team says "we'll add servers." You say: "Our architecture spends compute *proportional to need, by design* — we never run the expensive model on people for whom nothing happened."

---

## Slide 20 — Scalability: The Six Concrete Levers

1. **Batch scoring is embarrassingly parallel** — Layer 2 is tabular model inference on a feature store; the same nightly workload banks already run for fraud/risk. Distribute (Spark/batch), partition the base. No novel risk.
2. **The LLM is off the critical path of the *decision*** — Layer 3 detection and the Layer 4 gate are deterministic and run cheaply on *every* customer. The LLM only does the relevance pick + message wording — one call, and *only* on the small "act" subset (wait/escalate make zero LLM calls). Decisions scale with customers; *generation* scales with the much smaller acted set.
3. **Prioritisation when signals exceed capacity** — rank by `confidence × propensity × business value`; process top-N; let the rest **expire** via the signal `status` lifecycle (Layer 3). A 30-day cooldown prevents nagging.
4. **Concierge scales with active users, not the base** — it's user-initiated; standard stateless-API + LLM chatbot scaling (horizontal workers, on-demand scoring for that one customer). Never touches the 500M.
5. **MLOps closes the loop** — the `OUTCOMES` log becomes training data: propensity graduates from a cold-start prior to a model retrained on real responses, with drift monitoring + a model registry.
6. **Blast radius ≈ zero** — as a read-only wrapper (Layer 6), if APEX fails, core banking is untouched, and the LLM degrades gracefully to deterministic text. This is what makes it *pilot-able* at a 1% slice, then scaled up.

**Speaker notes:** Lever 2 is the subtle, impressive one — call it out. "Even at scale, the *decision* for millions of signals is cheap deterministic code. We only spend a language-model call once we've already decided to actually say something."

---

## Slide 21 — Production: Data Access & Ingestion · PRIORITY

**APEX is deployed *by SBI itself*, as an internal system — not a third party, no Account Aggregator.**

- **Data access** — direct **read-only** access to CBS (Layer 1), the same kind any internal SBI analytics tool has. APEX never writes to CBS.
- **Account-level events → webhooks.** SBI's system notifies APEX the instant an account is created/activated — low-frequency, genuinely real-time. This fires the Guide→Analyser transition (bounded by SBI's actual KYC timing, which APEX doesn't control or accelerate).
- **Transaction-level data → streaming/batch sync, not per-transaction webhooks.** At hundreds of millions of daily transactions, this is a production-grade event-streaming pipeline (Kafka-style) / periodic internal feed — never a lightweight HTTP callback per transaction.

**Speaker notes:** Be precise about the distinction — it signals you understand scale. Account events are true webhooks; transaction volume is a streaming/CDC problem. Latency is acceptable because Analyser is *intentionally* not real-time (it waits, by design); Concierge gets freshness via on-demand scoring for the single customer asking.

---

## Slide 22 — Production: The Feedback Loop & "Getting Smarter"

**The system improves by reading its own audit log — not (yet) by retraining on thin data.**

- Every outreach and its outcome (clicked / dismissed / ignored / completed) is logged (Layer 7).
- A **per-category dismissal count** (read from that log) is **causal**: the deterministic gate strips any category a customer has dismissed ≥2× from their safe set, so it's simply never offered again — *"this customer has dismissed two investment nudges; stop offering investments."* Alongside it, a **30-day product cooldown** (also read from the log) holds back any product recommended recently. Both are visible and explainable, not silent score adjustments. (Today the count is flat; recency-weighting is a planned refinement.)
- **At production scale**, accumulated real outcomes become the training set: the propensity model graduates from cold-start prior to a genuinely trained predictor — with MLOps (retraining cadence, drift detection, A/B, model registry).

**Speaker notes:** The honest nuance, worth stating: full retraining needs *enough* real outcomes to be meaningful. The dismissal-count mechanism is the answer that works from day one (and it's already causal — it changes decisions); retraining is the answer once volume accumulates. Don't over-claim retraining on launch.

---

## Slide 23 — Production: Identity, Security & Compliance

**The wrapper principle applies to identity too.**

- **Identity** — SBI-delegated login (SSO-style handoff): the customer logs into YONO/SBI as normal; SBI redirects to APEX with a signed token ("this is customer X, authenticated by us"). **APEX never sees a password.** Same pattern as "Login with Google."
- **Audit & explainability as a compliance asset** — the decisions/actions/outcomes log (Layer 7) isn't just memory; it directly satisfies the regulatory requirement that every automated action be logged and explainable (RBI / DPDP Act).
- **PII & access control** — strict, role-based, audited; APEX reads only what it needs, holds no parallel ledger.

**Speaker notes:** "One agent" is also a *security* argument: APEX structurally separates "decides" from "executes" — not via a second agent, but via the wrapper architecture (it has no write access regardless of mode). That separation is usually the reason to go multi-agent; here it's enforced architecturally.

---

## Slide 24 — Production: Channels & Unit Economics

**WhatsApp/SMS/email are never the interface — they're the trigger that brings someone to the interface.**

- **Analyser** (the only proactive mode) reaches out via WhatsApp/SMS in production — the channels people actually check daily.
- **Guide & Concierge** live on APEX's own website (active-search and support-chat are normal there).
- **Unit-economics lever:** WhatsApp Business API service-window messages (customer-initiated) are **free**; utility/marketing messages are not. Strategy: keep first outbound contact minimal and cheap (e.g. SMS); if the customer replies, the rest of the conversation falls into WhatsApp's free service window.

**Speaker notes:** Naming the cost model shows operational maturity. The funnel (Slide 19) already keeps outbound volume low; this keeps per-message cost low too.

---

## Slide 25 — Why One Agent, Not Multiple (defense slide)

**"One agent" = one reasoning core, three trigger-gated modes — not mode-blindness.**

- What differs between modes is the **trigger, starting context, and technique** (Layer 5); what's shared is the **data substrate, the product/eligibility logic, and the ethical guardrail**. Guide works from onboarding context; Analyser works from transaction history — but a vulnerable customer is shielded the same way in both, because the restraint lives in shared code, not per-mode prompts.
- Three separate agents would duplicate the loop (and the guardrail logic) three times, for no gain in capability — just more code to keep consistent.
- Where multi-agent genuinely helps (a privileged "acts" agent separated from a "decides" agent) **APEX already has that separation** — structurally, via the read-only wrapper (Layer 6), not via a second agent.

**Speaker notes:** Pre-empt the "why not microservice-per-pillar?" question. The answer: elegance + a single consistent ethical core + the wrapper already provides the safety separation people use multi-agent for.

---

# PART C — THE PROTOTYPE

---

## Slide 26 — What We Actually Built · PRIORITY

**A working end-to-end prototype of all three modes — not slideware.**

- The full pipeline runs: synthetic data → ML scores → signal detection → the agentic loop → a real email (or principled restraint) → outcome capture → a feedback/suppression loop.
- **All three decision outcomes resolve — none dead-ends:** `act` delivers; `wait` is revisited by a **scheduled re-engagement** pass (sends a gentle, product-free insight once the moment has passed, holds if the customer is still in acute stress); `escalate` lands in a **human-RM escalation queue** on the dashboard (open → mark handled).
- **Two real web apps:** a customer-facing site (Guide + Concierge + voice + explore) and an internal **bank-ops dashboard** (the reasoning traces, decisions, outcomes across customers, plus the escalation queue and a "Re-engage waits" trigger).
- **A live demo mechanic** — the "Simulate 3 months of activity" button that shows the Guide→Analyser transition happen on the spot.

**The honest claim:** *Everything hard is real — the reasoning, the judgment, the restraint, the vernacular generation, the voice pipeline. Only the seams where real bank integration isn't possible at hackathon scale are simulated.*

**Speaker notes:** Set expectations honestly here so the simulated parts (Slide 30) read as *deliberate engineering judgment*, not gaps.

---

## Slide 27 — Tech Stack

**Backend (Python)**
- **API:** FastAPI + Uvicorn (read surface for the dashboard + pipeline triggers).
- **Data:** PostgreSQL via SQLAlchemy 2.0 (12 tables); `psycopg2`.
- **Agent orchestration:** **LangGraph** (the Analyser flow and the Concierge tool-calling loop).
- **LLM:** **Groq** free tier — `llama-3.3-70b-versatile` for reasoning + message generation.
- **Speech-to-text:** Groq **Whisper** (`whisper-large-v3`); text-to-speech is browser-side (Web Speech API).
- **ML:** **LightGBM** (falls back to scikit-learn `HistGradientBoosting`), pandas, joblib for artifacts.
- **Email:** **Resend** (real delivery, routed to a demo sink in non-prod).
- **Synthetic data:** Faker + a custom deterministic generator (seeded).

**Frontend (×2)**
- **React 18 + TypeScript + Vite 6 + Tailwind 4**; `react-router` on the ops dashboard.

**Free/real-by-design:** LLM (Groq free tier), STT (Whisper), TTS (browser), email (Resend free tier), in-browser voice (mic/speaker). No paid telecom needed for the prototype.

**Speaker notes:** Emphasise these are *real, functional* services on free tiers — the reasoning and voice pipeline are genuinely live, not mocked. Map the stack onto Part B: SQLAlchemy/Postgres = Layer 1, LightGBM = Layer 2, the detectors = Layer 3, LangGraph + Groq = Layer 4–5, Resend + tracking links = Layer 7.

---

## Slide 28 — The Data Substrate, As Built (Layer 1 concretely)

**12 tables, two groups — mirroring the architecture (Slide 12).**

- **Substrate (7 tables)** — "SBI's world," which APEX only reads: `PRODUCTS`, `CUSTOMERS`, `ACCOUNTS`, `TRANSACTIONS`, `APP_SESSIONS`, `APPLICATIONS`, `HOLDINGS`.
- **Operational (5 tables)** — APEX's own brain & audit log: `SCORES`, `SIGNALS`, `DECISIONS`, `ACTIONS`, `OUTCOMES`. These chain together — a score fires a signal, which triggers a decision, which produces an action, which gets an outcome. *That chain is the reasoning trace.*

**Product catalogue:** 28 SBI products across 6 categories, tiered `full` (demo-exercised, machine-checkable eligibility) vs `reference` (real facts so Concierge answers accurately without hallucinating).

**Signals:** 17 detectors (e.g. `idle_balance`, `manual_recurring_payment`, `life_event`, `dormancy`, `cash_flow_stress`, `churn_risk`) — pure rules or thin wrappers over an ML score — **plus** a conversational `stated_intent` signal created from Concierge chats (Slide 16).

**Speaker notes:** This is Slide 12's architecture made concrete. The substrate/operational split *is* the wrapper philosophy made literal: read SBI's data, keep your own explainable log, never a parallel ledger.

---

## Slide 29 — The ML Scoring Layer, As Built (Layer 2 concretely)

**5 scores per customer: 3 trained models + 2 heuristics.**

| Score | Answers | How (in the prototype) |
|---|---|---|
| **Stress** | Under financial pressure? | Trained model (LightGBM) on synthetic latent-driver data |
| **Attrition/churn** | About to leave? | Trained model on **real Kaggle** churn data → drives the `churn_risk` signal (escalate to a human RM for retention) |
| **Propensity** | Likely to want each product category? | Trained model, synthetic — an honest **cold-start prior** |
| **Engagement decay** | Opening the app less? | Heuristic (formula) |
| **Anomaly** | Any transaction weird *for them*? | Heuristic (median + MAD, per-customer baseline) |

**The one core idea — train/serve parity:** the *same feature functions* run in training and in serving (one shared shaping function builds both the model's training history and the demo's synthetic customers). No train/serve skew.

**Speaker notes:** Be honest that propensity is a cold-start prior, not a validated predictor — there's no real customer-response ground truth in synthetic data. That honesty is a strength. Note we used *real* data where it exists (Kaggle churn) and synthetic only where it must be.

---

## Slide 30 — Demo Decisions: What's Simulated, and Why (the honesty slide) · PRIORITY

**One principle: simulate the *handoff*, never the *intelligence.* Every simulated piece is a seam where SBI's own infrastructure would hand APEX something.**

| Decision | What we did | Why it's the right call |
|---|---|---|
| **Synthetic dataset** | Generated schema-correct customers/accounts/transactions/sessions, engineered backwards from the signals | No real customer data, ever, at any stage — the only legal/ethical option, and it lets us exercise every signal deterministically |
| **"Simulate 3 months" button** | Batch-inserts one customer's 3 months of activity on click | Stands in for SBI's internal system notifying APEX an account went live (a webhook in production). The *only* thing faked is "data starts existing" |
| **Batch insert, not Kafka** | Direct DB write for the one-time seed | Correct for a finite one-time seed; Kafka would be unjustified complexity. Streaming is the *production* answer for continuous syncs (Slide 21) — named, not pretended |
| **Email instead of WhatsApp/SMS** | Real email via Resend, routed to a sink | WhatsApp/SMS need paid telecom with no free tier. The reasoning/detection/content is identical; only the channel differs — a deliberate cost decision |
| **Phone + OTP instead of SSO** | Lightweight identity tied to a synthetic customer | Demonstrates *delegated identity* without claiming a real SBI SSO integration exists (Slide 23) |
| **On-demand pipeline runs** | Score/detect/reason fire instantly on the demo trigger | Demo pacing — in production this is a nightly sweep + on-demand Concierge |

**Speaker notes:** This is the slide that disarms the "what's fake here?" question before it's asked. The pattern is consistent: it's never a random patchwork of shortcuts — it's *one principle applied everywhere.* Recite the one-liner: "Everything hard is fully real; the only things simulated are the handful of seams where real bank integration genuinely isn't possible at hackathon scale: data arriving, time passing, and login."

---

## Slide 31 — The Live Demo Flow

**Three scenarios, each proving a different agent behavior:**

1. **Idle balance → savings nudge** (an **act**) — Aarav has ₹3L sitting idle; APEX proposes a sweep/savings option at the right authority level.
2. **Manual recurring bill → autopay** (an **act**) — Neha pays the same bill manually 6×; APEX proposes autopay.
3. **Medical event → restraint** (a **wait**) — Sunita has a ₹95k medical shock; APEX *notices and holds back* — no product push. **This is the money shot.**

Then: open the **ops dashboard** to show the reasoning trace; click the **email link** to show outcome capture; ask **Concierge** "can I afford this?" to show the tool-calling, computed-answer path; switch language to show the vernacular generation.

**Speaker notes:** Lead the live demo with scenario 3 if you have to cut — restraint is what no one else will show. End on Concierge in a regional language to land the "language moat" point viscerally.

---

## Slide 32 — Prototype vs Production (one consolidated view)

**Guiding rule: simulate the plumbing, keep the brain real.**

| Concern | Prototype (built) | Production |
|---|---|---|
| Data source | Synthetic generator | Read-only feed from SBI's CBS |
| Data arrival | One-shot batch insert | Account webhooks + transaction streaming (Kafka) |
| Cadence | On-demand "recompute fresh" | Nightly sweep + on-demand Concierge |
| Dedup / suppression | Wipe & recompute (repeatable demo) | Incremental: signal lifecycle + cooldown + outcome back-off |
| Models | Stress + propensity synthetic; churn real | Retrained on real outcomes (full MLOps) |
| Channels | Real email to a sink; SMS/voice simulated | Real SMS/WhatsApp/voice telecom |
| Scale | One process, in memory | Millions → distributed, queues, prioritisation |
| Identity | Phone+OTP "sign in as" | SSO handoff from SBI's login |
| PII/security | Synthetic, no real PII | RBAC, audit, RBI/DPDP compliance |

**Never faked, even now:** the reasoning (real LLM + code gate), the ethics, the voice pipeline (Whisper), and one real channel (email).

**Speaker notes:** This table is your single best Q&A reference — keep it printed. Every "but in production…?" question is answered in a row here.

---

## Slide 33 — Roadmap & Honest Open Items

**What's next, and what we're deliberately not claiming yet:**

- **Level 4 autonomous execution** (with undo window) — needs SBI to grant scoped, audited write access. The natural next phase once trust in the read-only system is established.
- **Propensity retraining** on accumulated real outcomes (replacing the cold-start prior).
- **Tier 2 acquisition** depends on SBI's onboarding system resuming an application by ID/step — stated as an assumption, to be confirmed.
- **`yono_path` → real deep-link URL templates** (real navigation structure already confirmed against `sbi.bank.in`).
- **Prioritisation policy** for when a sweep surfaces more signals than capacity allows.
- **Per-customer frequency cap (multi-signal synthesis)** — today a customer with several signals (or several waits) can receive more than one outreach in a cycle. The next step is to collapse them to the single most relevant contact per customer, per window — a natural extension of the re-engagement + cooldown machinery already built.

**Speaker notes:** Ending on honest open items is a strength, not a weakness — it signals you know the difference between what's built, what's assumed, and what's future. Judges trust teams that draw that line clearly.

---

## Slide 34 — Closing

**APEX: the reasoning, restraint, and judgment of a great relationship manager — at the scale of SBI's entire customer base, in their own language, on their side.**

- One agent, three modes, one continuous relationship.
- A behavioral philosophy no recommendation engine arrives at.
- A wrapper that's safe to pilot tomorrow and scales by design.

**Speaker notes:** Return to the anchor sentence from Slide 1. Last line to leave them with: *"We didn't build a smarter recommendation engine. We built the judgment about whether, when, and how to speak — which is the part banking AI actually gets wrong."*

---

## Appendix — Q&A Rapid-Fire (keep in back pocket)

- **"Isn't this just a chatbot?"** → No — Analyser is *proactive* and *signal-gated*; the chatbot (Concierge) is one of three modes, and even it computes real answers via tools, never guesses.
- **"Could this be all rules?"** → The decision *is* all rules — deliberately, because proactive financial outreach must be guaranteed, not probabilistic. What rules can't do is read this specific person, pick the most fitting of several *eligible* options, and say it well in their language — that's the LLM, bounded by the code gate (Slide 15).
- **"How do you handle 50 crore customers?"** → The cost funnel (Slide 19): the expensive LLM only runs on the tiny acted subset; scoring/detection/decision are cheap and batchable.
- **"What about privacy / a creepy-AI backlash?"** → The ethical guardrail (Slide 5): never push on a vulnerability signal; wait, offer insight, let the customer pull the product forward. Enforced in code.
- **"So a `wait` just stalls forever?"** → No — a scheduled re-engagement pass revisits it once the acute moment has passed and sends a *single, product-free* check-in (never naming what it detected); if the customer is still in severe stress it keeps waiting. The wait resolves, on the customer's timeline, not the bank's. (Slide 5.)
- **"What happens to an `escalate`?"** → It goes to a human-RM **escalation queue** on the ops dashboard — churn risk, severe stress with only unsecured debt, or nothing eligible. A relationship manager sees the gate's reason and marks it handled. The agent knows the limits of its own authority. (Slide 15.)
- **"What's actually fake in the demo?"** → Only the seams where SBI's own infrastructure would hand us something: data arriving, time passing, login. Never the reasoning. (Slide 30.)
- **"Why not three agents for three pillars?"** → One reasoning core is more elegant and easier to keep ethically consistent; the wrapper already provides the decide/execute separation people use multi-agent for. (Slide 25.)
- **"Why email and not WhatsApp?"** → Cost only — WhatsApp/SMS need paid telecom with no free tier. The reasoning and content are identical; only the delivery channel differs.
- **"Where does ML stop and rules begin?"** → ML for multi-signal, baseline-relative patterns (stress, propensity, decay, anomaly); rules for clean thresholds (dormancy, idle balance, manual-recurring). We don't use ML where a rule is honest and cheaper. (Slides 13–14.)
- **"Where exactly is the LLM, and where is the code?"** → Code decides act/wait/escalate and builds the safe set (eligibility + every ethical rule). The LLM runs only on an `act`, and only to (a) pick the best-fit product from that already-vetted set and (b) write the message. We *had* a hypothesise→self-critique LLM loop and removed it — it was fed the same numbers the code gate already decided on, so it added cost and an illusion of reasoning, nothing causal. The leaner design is cheaper and more honest. (Slide 15.)
- **"Can Concierge recommend something silly?"** → No longer — it calls `recommend_product`, which runs the same routing + eligibility + guardrail gate the Analyser uses, so it can't suggest something ineligible, already held, or inappropriate. The LLM phrases; code decides the product. (Slide 16.)
- **"Isn't mining conversations for intent creepy?"** → It's the opposite of creepy *when done right*: an explicit, customer-voiced "I want to invest" is the customer pulling the product forward — the ideal. The guardrail is that a *disclosed vulnerability* (job loss, medical crisis) creates nothing and withdraws pending intents — we never turn distress into a sales trigger. Same ethical line, applied to conversation. (Slides 14, 16.)
