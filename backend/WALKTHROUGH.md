# APEX Backend — Plain-English Walkthrough

A file-by-file explanation of the whole backend, in simple words. This is the *learning* doc
(the "why" and "how it fits"). For setup/commands see [README.md](README.md); for the terse
implementation specs see [../specs](../specs).

## Contents

1. [The big picture](#1-the-big-picture)
2. [Foundations — config.py + db.py](#2-foundations)
3. [The data model — models.py](#3-the-data-model)
4. [Setup — init_db.py + seed_products.py](#4-setup)
5. [Synthetic data generator — shaping.py + generator/](#5-synthetic-data-generator)
6. [ML scoring layer — ml/](#6-ml-scoring-layer)
7. [Signal detection — signals/](#7-signal-detection)
8. [The agentic loop — agent/](#8-the-agentic-loop)
8b. [Conversational modes — Guide & Concierge](#8b-conversational-modes)
9. [The complete agentic workflow](#9-the-complete-agentic-workflow)
9b. [The demo mechanic — demo.py](#9b-the-demo-mechanic)
10. [The feedback loop — outcome capture](#10-the-feedback-loop)
10b. [The API layer — api/](#10b-the-api-layer)
11. [Signals → products mapping](#11-signals--products-mapping)
12. [Prototype vs production](#12-prototype-vs-production)
13. [Concepts glossary](#13-concepts-glossary)

---

## 1. The big picture

APEX watches a customer's banking data and steps in only at a real moment. The backend is a
**pipeline**, where each stage is cheaper than the next — so expensive AI reasoning only happens
for the few customers who need it:

```
raw data → ML scores → signals → the agent → a message (or restraint) → outcome
 (synthetic)  (cheap,     (cheap     (LLM + code gate,    (real email)     (feedback)
              everyone)    gate)      only if a signal fires)
```

Two halves of the data model mirror this: the **substrate** (SBI's world — customers, accounts,
transactions) which APEX only *reads*, and the **operational** tables (APEX's own scores,
signals, decisions, actions, outcomes) which are its brain and audit log.

---

## 2. Foundations

### `config.py` — the single source of settings
Nothing secret or environment-specific is hardcoded. This file reads everything from a gitignored
`.env` (database URL, catalogue path, random seed, Groq/Resend keys, the demo email sink, the
public URL). It also computes the repo paths so the code runs from anywhere. Other files just do
`from .config import DATABASE_URL`.

> Layout note: `db.py`, `models.py`, `init_db.py`, and `seed_products.py` live together in
> **`apex/database/`**. `config.py` stays at the `apex/` root, because it holds *all* settings
> (Groq, Resend, email, paths), not just database ones.

### `db.py` — the connection to Postgres
Sets up three things via SQLAlchemy:
- **`engine`** — the live connection to Postgres,
- **`SessionLocal`** — a factory for a "session" (one unit of DB conversation: open → read/write → commit → close),
- **`Base`** — the parent class every table model inherits from (SQLAlchemy's registry of all tables).

Dependency flow: **config → db → everything else.**

---

## 3. The data model

`models.py` defines the **12 tables**, in two groups.

### Substrate (7 tables) — "SBI's world" (APEX reads, never invents)

| Table | Holds | Key columns & their use |
|---|---|---|
| `products` | the 28-product catalogue | `category`, `depth` (full vs reference), `eligibility_rules` (JSON the agent checks), `key_facts` (real numbers so the LLM doesn't hallucinate), `landing_url` (becomes the deep link), `tax_saving` (fiscal signal) |
| `customers` | the person | `age`, `city_tier`, `language_pref` (which language APEX speaks), `occupation`, `monthly_income`, `dependents`, `owns_property`/`owns_gold` (gate signals), `has_papl_offer`/`has_card_offer` (route/gate), `account_opened_date` (tenure) |
| `accounts` | accounts held | `account_type` (FK→products), `balance` (idle signal), `status` (active/dormant) |
| `transactions` | money movements | `amount`, `direction` (debit/credit), `merchant_category` (drives most signals), `payee_id` (groups recurring), `channel`, `txn_time` (recency), `is_manual_recurring` |
| `app_sessions` | app logins | `login_time` (engagement/dormancy), `duration_seconds`, `features_used` |
| `applications` | in-progress onboarding | `customer_ref` (may exist before a customer does), `current_step`, `last_updated_at`, `status` |
| `holdings` | products owned | `product_id` (FK), `current_value` — gates protection_gap, routes cash-flow-stress |

### Operational (5 tables) — "APEX's brain & memory"

These form a chain: a **score** → fires a **signal** → triggers a **decision** → produces an
**action** → gets an **outcome**. That chain *is* the reasoning trace.

| Table | Holds | Written by |
|---|---|---|
| `scores` | ML scores per customer | the ML layer |
| `signals` | a detected trigger | signal detection (`status`: new→processed→expired) |
| `decisions` | the agent's reasoning: `mode`, `hypothesis` (the LLM's one-line *why-this-product* pick reason), `critique_result` (the deterministic `[gate]` reason — why act/wait/escalate), `confidence`, `outcome` (act/wait/escalate), `product_id`, `rm_status` (open/resolved — the human-RM queue, used by `escalate` rows) | the agent |
| `actions` | what was sent: `authority_level` (1-3), `channel`, `message_text`, `deep_link`, `sent_at` | the agent |
| `outcomes` | customer response: `response_type` (clicked/dismissed/ignored/completed) | the feedback layer |

Design notes: UUID primary keys; foreign keys link the chain; `JSONB` for flexible fields (a
score's value, a product's rules). The substrate/operational split mirrors the architecture
philosophy: APEX is a **read-only wrapper** over SBI's data that keeps its own reasoning log.

---

## 4. Setup

Run once with `python -m apex.database.init_db`.

- **`init_db.py`** — creates all 12 tables (`Base.metadata.create_all`, safe to re-run), then applies
  **idempotent column migrations** (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`, e.g. `decisions.rm_status`),
  then seeds products. The migration step matters because `create_all` only ever creates *missing
  tables* — it never alters an existing one — so re-running `init_db` on a populated DB brings the
  schema up to date **without a drop/regenerate** (no data loss). The `from . import models` line looks
  unused but is essential: importing it is what registers the tables onto `Base`.
- **`seed_products.py`** — loads `product_catalogue.json` into `products` with an **idempotent
  upsert** (insert new, update existing) — so re-running never duplicates or errors. Products are
  fixed reference data (seeded once); everything else is synthetic and regenerated.

---

## 5. Synthetic data generator

Fills the substrate with believable fake people, engineered *backwards from the signals*.

### `shaping.py`
Given an income + a **stress dial** (0=calm, 1=stressed), it builds a believable 90-day history.
One dial pulls four levers together: spending vs income, spending acceleration, medical
transactions, leftover balance. **The same function is used to train the stress model AND to make
the demo's stressed customers** → no train/serve skew.

### `generator/personas.py`
16 hand-authored personas, each a recipe written backwards from a signal (Priya = idle balance,
Vikram = manual bill, etc.). Each has profile fields, a list of **traits**, and its
**expected_signals** (the answer key).

### `generator/generate.py`
Turns recipes into database rows. Each **trait** maps to an **emitter** that produces transactions
or sessions:

| Trait | Emits | For signal |
|---|---|---|
| `salary` | 3 monthly salary credits | income presence |
| `baseline` | 15–25 everyday debits | realistic noise |
| `idle` | nothing (keeps balance high) | idle_balance, fiscal_year_end |
| `manual_bill` | repeated same-payee utility payments | manual_recurring_payment |
| `rent` | monthly rent to a landlord payee | sustained_rent_payment |
| `tuition` | 2 seasonal education lumps | tuition_payment |
| `medical_anomaly` | one large medical debit | life_event |
| `vehicle_anomaly` | one large vehicle debit | large_asset_purchase |
| `stress` | a full high-stress history (via shaping.py) | cash_flow_stress |
| `gold_dips` | ~12 small recent withdrawals | gold_loan_liquidity_gap |
| `dormant_history` | one old txn, nothing recent | dormancy |
| `sessions` | app logins (healthy/decay/none) | login_decay, dormancy |

It also builds a **noise population** (~30 customers engineered to trip nothing), writes everything
in FK order, and emits `generated_manifest.json` (the answer key for validation). Deterministic via
a seed; `--reset` wipes synthetic rows but keeps products.

---

## 6. ML scoring layer

Turns raw substrate into a few calibrated **scores** per customer, so the agent reasons on
"stress = 0.81" instead of raw transactions. **4 scores: 2 trained models + 2 heuristics.**

| Score | Answers | How |
|---|---|---|
| stress | under financial pressure? | trained model (synthetic data) |
| attrition | about to leave the bank? | trained model (real Kaggle data) |
| engagement_decay | opening the app less? | heuristic (formula) |
| anomaly | any transaction weird *for them*? | heuristic (statistics) |

> **No propensity ("likely to want X") model.** A demographic affinity score — "people like
> you tend to want investments" — is exactly the *segment-based recommender* the behavioral
> philosophy rejects (APEX is a life-moment detector, not "28-year-olds should invest"). Product
> relevance comes from the **signal that fired** (a real present need), and explicit preference
> comes from **`stated_intent`** — what the customer actually told Concierge they want — never
> from inferring desire off a profile.

**The one idea behind the whole layer — train/serve skew:** a model must see identically-shaped
data in training and in production. The defense: the *same feature functions run at both times.*

### Which signals each score actually fires

A score is only useful if a detector *reads* it. Most of the 17 signals are **pure raw-data rules**
that touch no score at all; only a few are score-driven. Mapping the four scores to the signals
they trigger (in `signals/detectors.py`):

| Score | Signal(s) it fires | How |
|---|---|---|
| **stress** | `cash_flow_stress` | fires when `stress ≥ 0.80` |
| **anomaly** | `life_event`, `large_asset_purchase` | fires when the anomaly scorer **flags** a transaction — a *medical*-category flag → `life_event`; a retail/vehicle/property flag → `large_asset_purchase` |
| **engagement_decay** | `login_decay` | fires when `engagement_decay ≥ 0.30` |
| **attrition / churn** | `churn_risk` | fires when `attrition ≥ 0.80` *and* the customer isn't already dormant |

Two honest notes a reviewer will appreciate:
- **`churn_risk` is the attrition model's payoff.** The churn model (trained on real Kaggle data)
  scores every customer; `churn_risk` fires when that score is high **and** they're not *already*
  dormant — an early warning *before* the hard `dormancy` line (no txn/login ≥ 90d). Its outcome is
  **escalate to a human relationship manager for retention** — you don't auto-push products at someone
  heading for the door — so it shows on the dashboard as an escalation, not a customer message. (Day
  disengagement is still also caught by the hard `dormancy` rule and by `login_decay`.)
- **`gold_loan_liquidity_gap` is *not* stress-driven**, despite being a "liquidity" signal: it's a
  pure raw rule (`owns_gold` + ≥8 small dips in 45d). The stress score only influences its *confidence*
  later in `guardrails`, never whether it fires.

Everything else (`dormancy`, `application_dropoff`, `idle_balance`, `fiscal_year_end_window`,
`sip_graduation`, `manual_recurring_payment`, `sustained_rent_payment`, `tuition_payment`,
`salary_credit_upgrade`, `protection_gap`, `preapproved_card_offer`) is a **pure rule** over raw
`ACCOUNTS`/`TRANSACTIONS`/`APP_SESSIONS`/`APPLICATIONS` — no ML score involved in firing.

### `trainset.py` — the synthetic training data
- `generate_stress_trainset`: ~3000 fake customers, each with a random stress dial → a `shaping.py`
  history; label = stressed if dial > 0.6, then **~12% labels flipped** (so the model learns a real
  boundary, not the generator's recipe).

### `features.py` — the shared translator (the skew defense)
Three jobs: (1) the 5 **stress features** (spending velocity, balance slope, spend-to-income,
withdrawal irregularity, medical recency — with one-off giant debits stripped out first); (2) the
**engagement-decay** heuristic; (3) the **churn mapper** (translate a customer into Kaggle's exact
column names). Both training and serving call these same functions.

### `loaders.py` — the one real dataset
Reads Kaggle's churn CSV for attrition, keeping only columns it can also compute for real customers
(feature-intersection rule).

### `anomaly.py` — per-customer anomaly (heuristic, no model)
"Is this debit unusually large *for this person*?" Uses median + MAD of their own debits; flags any
debit > ~3.5 spreads above their normal. Compares each person only to themselves. Feeds life_event
(medical) and large_asset_purchase (vehicle/retail).

### `train.py` — the one-time factory
Fits the 2 models (same recipe: data → features → 80/20 split → fit → ROC-AUC → save). Uses
LightGBM, falling back to scikit-learn. Each `.joblib` bundle also stores the feature list (skew
defense at the artifact edge).

### `score.py` — the conductor
Loads the frozen models, gathers all customers' data once, and for each computes the 4 scores **via
the same `features.py` functions training used**, writing the `scores` table (wiped and recomputed
fresh each run).

---

## 7. Signal detection

The **cheap gate** between scores and the expensive agent. Only a `signals` row wakes the agent.

- **`thresholds.py`** — just named numbers (the cutoffs): `IDLE_BALANCE_MIN=50000`,
  `DORMANCY_DAYS=90`, `STRESS_THRESHOLD=0.80`, etc. Centralised so tuning is one place.
- **`detectors.py`** — 17 rules as pure functions. Each is handed a packet of one customer's info
  (the `Context`) and returns a **reason string** (fired) or **None**. 12 read raw data; 5 read an
  ML score (`cash_flow_stress`←stress, `life_event`/`large_asset_purchase`←anomaly,
  `login_decay`←engagement_decay, `churn_risk`←attrition). A registry at the bottom pairs each
  signal name with its function.
- **`detect.py`** — the runner: clears old signals, gathers all data once, runs the 17 rules per
  customer, saves a `signals` row (status `new`) for each that fires.
- **`validate.py`** — the report card: compares detected signals against the manifest. Checks
  **recall** (each persona's expected signal fired), **noise silence** (the ~30 noise customers fire
  nothing), and **extras** (a persona firing more than expected → warnings). `fiscal_year_end_window`
  is calendar-gated, so out of Jan–Mar it's reported as *conditional* (passes if its precondition is
  present). This is how thresholds get tuned and how changes stay safe.

### The 17 rules, in plain English
1. **dormancy** — has an account, but no transaction *and* no login for ≥90 days.
2. **application_dropoff** — an in-progress application untouched ≥48h, stuck at a KYC/upload step.
3. **idle_balance** — biggest balance > ₹50k *and* no single large (≥₹50k) withdrawal in 90 days.
4. **fiscal_year_end_window** — it's Jan–Mar *and* idle_balance is true *and* holds no tax product.
5. **sip_graduation** — a micro-SIP account opened > ~4 months ago with a positive balance.
6. **life_event** — anomaly flagged a *medical* transaction (→ restraint path).
7. **large_asset_purchase** — anomaly flagged a large retail/vehicle/property debit.
8. **manual_recurring_payment** — same payee paid manually ≥3 times in 6 months (rent/education/salary excluded).
9. **login_decay** — engagement-decay score ≥ 0.30.
10. **sustained_rent_payment** — doesn't own property *and* same payee got rent ≥6 months.
11. **tuition_payment** — has dependents *and* same payee got education payments ≥2 times.
12. **cash_flow_stress** — stress score ≥ 0.80.
13. **gold_loan_liquidity_gap** — owns gold *and* ≥8 small (≤₹2.5k) withdrawals in 45 days.
14. **salary_credit_upgrade** — gets salary credits *and* they land in a plain regular savings account.
15. **protection_gap** — age 18–70 *and* has income *and* holds no insurance.
16. **preapproved_card_offer** — has a card offer flag *and* shows real spending.
17. **churn_risk** — the trained attrition model scores ≥ 0.80 *and* the customer isn't already dormant (an early warning before the hard dormancy line) → **escalate to a human RM** for retention.

---

## 8. The agentic loop

This is the `agent/` folder — APEX's **brain**. It holds three "modes" of talking to a customer,
plus shared plumbing and two side-effect helpers. This section covers **Analyser mode** (the
proactive one) and the shared pieces; Guide and Concierge are in §8b, the feedback writer in §10.

The Analyser reasons **per customer, not per signal** — it looks at *all* of one person's active
signals at once, so restraint follows the person and the customer gets **one coherent outreach**
instead of a separate nudge per signal. It's built on one principle — **"code disposes, the LLM
proposes":**

```
gather a customer's signals → DECIDE (CODE GATE) → if ACT: pick best fit + compose (LLM) → record
```

The act/wait/escalate decision, the eligibility checks, the ethical restraint, and the very *set* of
products that are even allowed are **all deterministic code**. The LLM's only job — once code has
decided to act — is to **pick the single best-fit product from a pre-vetted safe set and write the
message**. It can never reach a product code didn't allow, raise the authority level, or act when
code said hold.

### Shared plumbing (used by everything)

- **`_shared.py`** — the phone line to the LLM. Creates *one* Groq client and hands the same one to
  every module (no new connection per call). Also keeps the language-code → name map (`hi → Hindi`).
- **`prompts.py`** — the actual *words* APEX thinks in: a system prompt (personality — on the
  customer's side, no jargon, calm, no scammy links) plus the **select-and-compose** template
  (pick the best fit + write the message), and the reengage/explain templates.
- **`llm.py`** — the hand that dials. Sends a built prompt to Groq. Key logic: **on any failure (no
  key, rate limit, bad JSON) it returns `{}`/`""` instead of crashing** — a dead LLM never breaks the
  pipeline; the code gate has already made every decision, so the loop just falls back to the
  top-ranked product + a deterministic message.

### Analyser mode — split so the LLM never makes the real decision

- **`routing.py` — proposes the candidate products, by fixed rules.** Given *one* signal it returns
  an ordered (best-first) candidate list, then `is_eligible` filters it (age, income, already-owns-it,
  has-an-offer). The result is the *relevance-ranked, eligible* set for that signal — code decides
  what's **appropriate** and **allowed**. Some signals branch by what the customer holds (e.g.
  cash_flow_stress → PAPL / loan-vs-FD / …). The LLM later picks *within* this set; it can never reach
  anything outside it.
- **`guardrails.py` — the code gate, now per customer (`decide_customer`).** It reasons over *all* of
  one customer's active signals together and returns act/wait/escalate plus the **safe set** — the
  union of every signal's eligible candidates, minus held products, minus the vulnerability-locked
  categories, minus dismissed categories, minus anything on cooldown (detailed just below). Bright-line
  ethics live here. (The older per-signal `evaluate` is kept too, because Concierge's
  `recommend_product` still uses it — §8b.)
- **`loop.py` — the runner.** Loads the catalogue **from the `PRODUCTS` table** (single source of
  truth — not the JSON file), groups Analyser signals **by customer** (dropping Guide's
  `application_dropoff`), gathers each customer's data + **dismissal history** (per-category counts from
  `DECISIONS→ACTIONS→OUTCOMES`) + **recently-recommended products** (the cooldown set), runs
  `decide_customer`, and — *only* when it says ACT — asks the LLM to pick the best fit + compose the
  message. Writes the `decision` (+ `action` if act), optionally emails (`--send`), marks the
  customer's signals processed. `--limit N` = the first N customers.

### How `decide_customer` works — the safe set

For one customer, in order (first match wins):

1. **Ethical pre-empt (no LLM):** an active `life_event` (recent medical event) → **whole-customer
   wait** — APEX holds *all* outreach, not just the medical-related signal; `reengage.py` revisits
   gently later. An active `churn_risk` → **escalate** to a human RM (never auto-push at someone
   heading out the door).
2. **Build the safe set:** union the eligible, unheld candidates across every remaining signal, then
   strip — (a) **insurance + unsecured debt** if the customer is in severe stress (the vulnerability
   lock); (b) any **category dismissed ≥2×** (back-off); (c) any **product recommended within the last
   30 days** (the sliding cooldown — re-spam prevention, §10).
3. **Decide:** nothing eligible at all → **escalate** (or, severe stress with *only* unsecured debt
   left → escalate for human judgement — the **Suresh** case); everything eligible was ethically held
   back → **wait**; everything was on cooldown / dismissed → **wait**; otherwise → **act** with the
   safe set. Confidence is *derived* from how far the driving score sits past its threshold.

### The LLM step — pick + compose (one call)

When the gate says ACT, `llm.select_and_compose` is handed the customer line, the vetted safe set
(each product tagged with the moment that surfaced it), and the stress context, and returns strict
JSON: the chosen `product_id`, a one-line internal reason, and the customer message. Code then
**validates the pick is actually in the safe set** (else falls back to the top-ranked option) and
computes the authority level from (signal + product). So the genuine LLM judgement is **relevance** —
e.g. choosing a conservative FD over a higher-ranked investment for a risk-averse person — plus the
vernacular wording. Everything binding is already settled before the LLM is asked anything.

### What changed, and why it's more honest

The Analyser used to run a `route → hypothesise → critique → decide → compose` LangGraph with two
extra LLM "reasoning" nodes and a self-critique loop-back. In practice the critique was fed the *same
two numbers* (stress, dismissal count) the code gate already decided on — so it couldn't add anything
the gate didn't already guarantee. It was narration: a thought that changed nothing. Those nodes (and
`graph.py`) were removed. The result is leaner, **cheaper** (wait/escalate cases now make *zero* LLM
calls), and the description is finally exactly true: **code makes every decision and enforces every
ethic; the LLM picks the most fitting option and says it well.** Even if the LLM hallucinates or is
prompt-injected, the worst it can do is pick a different *already-vetted* product or write worse copy
— it cannot act when code said hold, reach an unsafe option, or skip an ethical rule.

**The dismissal-memory worked example — Ravi**, idle cash, has brushed off two investment nudges:
the loop reads `investments: 2` from the outcome log, so `decide_customer` strips investment products
from his safe set (back-off). If that leaves other eligible options (a deposit sweep, say) the LLM
picks one of *those*; if it empties the set, the outcome is **wait**. Either way Ravi is not nagged
about investing a third time — enforced in code, not hoped for in a prompt.

### The ethical gate, in plain words (`guardrails.decide_customer`)

Because the gate now reasons over a customer's **whole signal set at once**, the ethics are enforced
*structurally* rather than patched per-signal. The rules, checked top-to-bottom (first match wins):

- **Medical / `life_event` → whole-customer wait.** A recent medical shock silences *all* outreach,
  not just the medical-related one — APEX acknowledges and holds back entirely, then `reengage.py`
  follows up gently once the acute moment has passed. This is stronger than the old per-signal gate,
  which would still have sent, say, a cheery savings nudge the day after surgery.
- **Holistic vulnerability restraint, by construction.** Reasoning per customer closes a hole the old
  per-signal loop had: **Anjali** has *both* a `life_event` and a `protection_gap` — the old loop
  processed them separately, so the protection-gap pass would offer insurance mid-crisis. Now the
  vulnerability lock is applied while *building the one safe set*, so insurance simply never enters it.
  The restraint follows the **customer**, not the trigger.
- **Severe stress counts as vulnerable too**, and the lock also covers **unsecured debt** (personal
  loans, credit cards) — but **not secured lending** (loan-against-FD, home, gold), which is
  collateralised and often genuinely helpful.
  - *Standout — Suresh vs Lakshmi, both severely stressed:* Suresh's only eligible option is an
    unsecured personal loan → it's stripped, the safe set empties → **escalate to a human** (don't
    auto-push debt); Lakshmi's idle-balance / FD routes to safe savings → **act**. Same stress,
    opposite outcome — decided by whether the available help is safe or risky.
- **Already holds it → never enters the safe set. Category dismissed ≥2× → stripped (back-off).
  Recommended within 30 days → stripped (cooldown).** If those filters empty the set → **wait**; if
  the customer qualifies for nothing at all → **escalate**.

### Side-effect helper

- **`mailer.py`** — sends an `act` message as real email via Resend. In non-prod it routes *every*
  message to the demo sink (never a real third party), and the links it embeds are click-tracked
  (they point back at the API, which logs the response then redirects to SBI). Any failure is
  returned, never raised, so one bad send never breaks the batch.

**Where ethics are enforced:** in the `decide` node (code), which runs *before* `compose`. If the
gate says anything other than "act," no message is ever written — restraint is structural, not a
prompt request.

### Re-engaging a `wait` (`reengage.py`) — a pause, not a dead end

A `wait` isn't the end of the story; it's a deliberate pause (APEX_README §6: *detect → acknowledge
and wait → offer insight without a product → let the customer pull it forward*). `reengage.py` is the
scheduled second look that makes that real instead of conceptual.

It finds **vulnerability** `wait` decisions older than `--days` (default **3**; the demo uses
`--days 0` so you don't have to wait, the same "run it now for pacing" choice the demo mechanic
makes). It deliberately revisits *only* `life_event` waits (`trigger_ref` begins `life_event:`) —
never the gate's other holds (a cooldown/over-contact wait, or an insurance-only restraint), which
must **not** receive a "we noticed a sensitive moment" check-in. It skips any wait already followed up
(each follow-up is tagged `trigger_ref="reengage:<original_decision_id>"`, so a wait is re-engaged
**at most once**), and for each remaining wait makes **one** call:

- **Still acutely vulnerable?** If the customer is in *severe ongoing financial stress* (stress ≥ the
  same `SEVERE_STRESS` the gate uses), it **keeps waiting** — APEX never follows up *during* the hard
  window. (A medical `life_event`, by contrast, eases with time, which is exactly what "days since the
  wait" represents — so those do become eligible.)
- **Moment has passed?** It writes a follow-up decision (`outcome="act"`, **authority Level 1**,
  `product_id=None`) and a product-free, link-free **insight** message composed by `llm.reengage` — a
  warm check-in that *names nothing sensitive* ("we're here if you'd like to talk anything through"),
  never a push. If the LLM is unavailable it degrades to a calm deterministic fallback, same as the
  loop. `--send` delivers it through the same Resend sink.

So the worked example finally closes: **Anjali**'s medical-event wait, days later and only if she's
not still in acute stress, becomes a single gentle, product-free check-in — not a sales nudge.

### The escalation queue — the `escalate` handoff (`rm_status`)

The other non-act outcome, `escalate`, used to dead-end as a logged decision. It's now a real
**human-RM inbox.** `escalate` covers the cases the gate refuses to auto-act on — `churn_risk`
(don't auto-push at someone heading for the door), severe stress with only *unsecured* debt available
(Suresh), and "nothing eligible." Each such decision carries an `rm_status` (**open → resolved**); the
API exposes the queue (`GET /escalations`) and a resolve action (`POST /escalations/{id}/resolve`), and
the ops dashboard renders it as an **Escalations** page where a relationship manager reads the gate's
reason and clicks **Mark handled**. The escalate path now leads somewhere — to a person.

---

## 8b. Conversational modes

The Analyser is **proactive**. The other two modes are **reactive** — the *customer* starts the
chat. The cleanest way to see all three at once is to ask: **how does the LLM get its data?**

| Mode | Data source | Control flow |
|---|---|---|
| **Guide** | fetched on demand via tools (catalogue, docs, application lookup) | a loop |
| **Concierge** | fetched on demand via tools | a loop |
| **Analyser** | gathered by `loop.py`, gated by code | fixed line |

### Guide — a tool-calling agent (`guide.py`)

For brand-new / prospective customers — APEX has **zero** banking data on them. Earlier this was a
single context-injection call (the catalogue stuffed into the prompt), but two things a one-shot
prompt can't do *safely* pushed it to the same **tool-calling** shape as Concierge:

- **`get_required_documents`** — the real KYC/doc list per product, grounded in code (a small
  `category → standard documents` map), never recited from the model's memory.
- **`lookup_application`** — the **agentic core**: whether this person has an *unfinished* application
  (and which step they stopped at) is *live* state in the `applications` table — the one thing
  injection structurally cannot know. This is the Tier-2 **drop-off** path.

Plus `list_products` (the catalogue grouped by life-need: Save / Grow / Borrow / Protect / Pay) and
`get_product_details`. The LLM decides which to call, in the same `agent ⇄ tools` loop Concierge uses.

**How it knows you're a drop-off:** it doesn't *guess* — detection is the backend's job (the
`application_dropoff` signal over the `applications` table). Guide only **confirms context** for an
*identified* person: the signed-in `customer_id` (the demo's "sign in as" identity, passed through
`/chat`) or a reference the customer volunteers in chat. An anonymous visitor is always a **Tier-1
stranger** — Guide can't, and shouldn't, recognise them.

**The floor (what code guarantees):** Guide **never invents a URL** — it only ever surfaces a
product's real `landing_url` from the catalogue; documents come from data; and it **never writes to
SBI** (no form submission). Deep links / pre-filled onboarding URLs are deliberately *not* built —
that pre-fill mechanism doesn't work against SBI's real pages, so Tier-2 is an honest **reminder +
document help + a plain link to the official page**, not a magic resume-to-the-step.

Behavioral rules baked into the prompt: ask what they need *first*; mirror their language; never
dump a product list (surface one or two *adjacent* areas as life-outcomes — "a low-cost way to
protect your family," never "PMJJBY"); calm, on the customer's side. (For self-directed browsing the
customer site also has a separate **Explore** page — the full catalogue by life-need with links.)

### Concierge — a tool-calling agent (`concierge.py`)

For existing customers asking about their own money ("can I afford this?"). The opposite technique:
instead of stuffing data in, hand the LLM a **menu of read-only tools** and let it decide which to
call — `get_balance`, `get_spending`, `check_affordability`, `get_holdings`, `list_products`, and
`recommend_product`. Each runs a real DB query (all sharing **one session** for the turn, reading the
`PRODUCTS` table — not the JSON file) and returns real numbers. The instruction is blunt: *never
guess a number — if a tool gives it to you, use it.* So "can I afford a ₹80k laptop?" calls
`check_affordability` and answers from the real math, never an estimate.

**`recommend_product` — "code disposes" applied to Concierge too.** Early on, Concierge *freelanced*
product suggestions (it once recommended a product the customer already held). Now, when the customer
asks "what should I get?", the LLM calls `recommend_product`, which runs the **same
`routing` + `eligibility` + ethical `guardrails` the Analyser is built on** (via the per-signal
`guardrails.evaluate`) over the customer's live signals and
returns only vetted products — eligible, not already held, and ethically cleared (a customer in a
vulnerable moment gets no insurance push). The LLM phrases the answer; **code decides the product** —
so Concierge can no longer suggest something ineligible, held, or inappropriate.

**Safety:** every tool takes a `customer_id` injected from the session, **not** from the LLM. The
model can only ask for "balance," not "balance for customer X" — so Concierge structurally **cannot
read another customer's money.** (The customer site also shows a "money at a glance" snapshot above
the chat — balance, income, a light spending summary, and **What APEX suggests** (the agent's own
act-decisions, already ethics-filtered). Each suggestion has a **"Why am I seeing this?"** link backed
by `/explain` — a plain-language reason drawn only from a fact the customer can already see, which
*declines* to elaborate on anything sensitive. Deliberately *not* a budgeting tracker — APEX_README
§14 rejects that.)

**The looping graph (where LangGraph earns its keep).** Two nodes that cycle:

```
agent (LLM thinks) ⇄ tools (run DB lookups)
```

One turn: the **agent** node either answers or emits tool calls; a fork checks *did it ask for
tools?* — **yes** → the **tools** node runs them, appends the results, loops back to agent; **no** →
it's the final answer → end. The number of loops isn't fixed: the LLM can fetch balance, realise it
also needs spending, fetch again, then answer. *That* unpredictable, LLM-decided path is exactly what
a graph is for — unlike the Analyser, whose path is fully knowable, so it needs no graph at all. To stop a runaway loop, after
`MAX_TOOL_ROUNDS` (4) the agent is forced to answer (tools switched off), and a `GraphRecursionError`
is caught and turned into a graceful "couldn't work that out" reply rather than a crash.

### Voice
Voice doesn't change the brain. Speech in → Groq Whisper transcribes (`voice.py`) → the same mode
runs → the browser speaks the answer back. Same logic, different input/output. Returns "" on failure.

### How they differ from the Analyser
- **Analyser** is proactive → a strict deterministic code-gate decides act/wait/escalate and the safe
  set; the LLM only picks within it + composes (never push on a vulnerable moment).
- **Guide / Concierge** are reactive → free-form chat, no act/wait/escalate gate on the *reply* (the
  customer is steering). The behavioral rules still apply via the system prompt.

### Conversational signals — Concierge feeds the Analyser (`intent.py`)

A customer's **stated** intent is the strongest life-moment signal there is — "I want to start
investing" is a *present, voluntary* need, where behavioural signals are only ever inferred after
the fact. So Concierge isn't just a Q&A surface; it's also a **signal source.**

How it works: after each Concierge reply, a background task (`extract_and_store`) runs **one
LLM pass** over the conversation and returns strict JSON — the explicit product interests (mapped to
a catalogue category) plus a `vulnerable` flag. Then:
- **Explicit intent** → a new `stated_intent` signal (its `source_ref` = the category) is written to
  `SIGNALS`, de-duped per category. It flows through the **same routing + eligibility + ethical gate**
  as any other signal (a new `route()` branch serves full-depth products in that category), so the
  vulnerability restraint and dismissal back-off apply for free.
- **Disclosed vulnerability** (medical crisis, job loss, money fear) → APEX creates **nothing**, and
  *withdraws* any pending `stated_intent` signals (marks them `expired`). Never turn distress someone
  confided into a sales trigger — the ethical guardrail, applied to conversation.

**Worked example — happy path.** Priya says *"I'd like to start investing for the long term."* →
extraction returns `{intents: [{category: investments}], vulnerable: false}` → APEX writes a
`stated_intent → investments` signal for her → the next Analyser run routes it to an investment
product, finds her eligible and not already holding it, and reaches out later with a calm, well-timed
nudge for exactly the thing she asked about. *Something she said in a chat became a vetted follow-up.*

**Worked example — distress path.** Priya says *"I just lost my job and I'm scared about money."* →
extraction returns `{intents: [], vulnerable: true}` → APEX creates nothing **and** expires any
pending intent (e.g. that investments signal). Even a previously-stated wish is withdrawn the moment
she discloses fear.

**Double protection.** Even if an intent signal slips through, the gate *still* suppresses it for a
vulnerable customer (the holistic restraint runs on every signal). The extraction's `vulnerable`
check and the gate's restraint back each other up.

It runs as a **background task** (FastAPI `BackgroundTasks`), so it never delays the chat reply, and
it's best-effort — if the LLM call fails, no signal, no error. This is the cleanest expression of the
whole architecture: *Concierge gathers the intent, code decides whether/what to act on, the Analyser
follows up later — one continuous relationship across the three modes.*

---

## 9. The complete agentic workflow

Walk it with **Priya** (idle balance) and **Anjali** (medical event):

1. **Scores** (cheap, everyone): Priya looks healthy; Anjali's ₹90k medical txn is flagged by the
   anomaly scorer.
2. **Signals** (cheap gate): Priya → `idle_balance`; Anjali → `life_event`. Only these two wake the
   agent; everyone else with nothing going on is never reasoned about.
3. **The agent** (per customer): **`decide_customer` (code)** builds the safe set and rules
   act/wait/escalate → if act, the LLM picks the best fit from that set + composes (one call).
   - Priya → **act** → a calm savings nudge (the LLM picks from her vetted savings/growth options).
   - Anjali → **wait** → the gate holds *all* outreach (active `life_event`); the LLM is never called;
     **no message written**.
4. **Record & deliver**: a `decision` is saved either way (the audit trail). Priya gets an `action`
   + a real email; Anjali gets a decision on record showing APEX *noticed and held back*.
5. **Re-engage / escalate (the non-act tails close too)**: days later, `reengage.py` revisits Anjali's
   `wait` — and *only* if she's no longer in an acute moment, sends one gentle, product-free check-in
   (§8). And anyone the gate `escalate`d (e.g. Suresh) sits in the **RM queue** (`rm_status=open`)
   until a human resolves it. Neither outcome is a dead end.

One sentence: *score everyone cheaply → let cheap rules pick who's worth waking the agent for →
reason with an LLM but let code make the act/wait/escalate call → reach the right person, at the
right moment, with the right restraint, in their language.*

---

## 9b. The demo mechanic

`demo.py` is the **"Simulate 3 months of activity" button** made real: take a customer with *no*
data, suddenly give them three months of activity, and run the whole pipeline on just them — so you
watch the **Guide → Analyser transition live**.

**Why it exists.** APEX's story is "no data (Guide) → data starts flowing → APEX detects a moment and
reaches out (Analyser)." In production that "data appears" moment comes from SBI's systems. A demo
can't wait three months, so this file fakes *that one seam* — and nothing else.

**Three canned scenarios, each chosen to show a different agent behaviour:**
- **`idle_balance`** (Aarav, ₹3L idle) → savings/sweep nudge — an **act**.
- **`manual_bill`** (Neha, same bill paid 6×) → autopay nudge — an **act**.
- **`life_event`** (Sunita, ₹95k medical shock) → APEX shows **restraint and waits**, doesn't push
  insurance.

That third one is the money shot: it proves the ethical guardrail actually fires, not just the
happy-path sale.

**The flow when you click (`simulate`):**
1. **Wipe the old demo customer** for this scenario (found by its `demo.apex` marker email), in
   FK-safe order — so repeated clicks don't pile up duplicates.
2. **Build + insert the data** using the *same* `build_persona` the real generator uses (not a
   separate fake path): customer, accounts, holdings, 3 months of transactions, sessions.
3. **Run the real pipeline, scoped to this one customer:** `score_all()` → `detect_all()` →
   `run_agent(customer_id=…)`. The data is seeded, but the scoring/detection/reasoning is the genuine
   pipeline — just on demand instead of nightly.
4. **Return the outreach** — only the *result* (`outcome`, `product_id`, `message_text`,
   `deep_link`), not the internal reasoning trace (the pick reason + the `[gate]` reason). The
   **customer site** shows what APEX would say; the **ops dashboard** holds the raw reasoning.

**Honest shortcut:** the *only* thing faked is the moment data starts existing — the seam where, in
production, SBI's systems would notify APEX that an account went live. Everything after is the real
pipeline. Batch insert, not Kafka — correct for a one-time finite seed; streaming is the production
answer for continuous data.

---

## 10. The feedback loop

When a customer engages, APEX captures it in `outcomes` (the writer is `agent/feedback.py`).

- **clicked** — emails link through `/track/{action_id}`, which logs `clicked` then redirects to the
  real SBI page. (Production captures clicks the same way.)
- **dismissed** — a "Not interested" link → `/track/{action_id}/dismiss`.
- **ignored** — `/pipeline/expire-outcomes` marks sent actions with no response after N days.
- **completed/adopted** — genuinely needs SBI's CBS in production. In the demo,
  `/track/{action_id}/adopt` logs `completed` **and creates the holding** — so the substrate reflects
  the adoption and the next sweep naturally skips them.

Captured responses show on the ops customer-detail view.

**Using the outcomes — two ways the "memory" is now causal:**

1. **Product-level cooldown (re-spam suppression).** When the loop builds a customer's safe set, it
   **strips any product recommended within the last 30 days** — a per-(customer, product) *sliding*
   window read straight from the `DECISIONS→ACTIONS` log (no separate "history" table). A sliding
   window beats a "clear the list every 30 days" scheme: it has no boundary, so a product recommended
   on day 29 can't be re-sent on day 31. Because a full reset wipes that history, the cooldown is
   simply empty in demo (`reset=true`) mode and active in incremental (`/pipeline/agent?reset=false`)
   mode — same code, no special-casing. Adopted products drop out permanently (the held-filter); the
   decision's `trigger_ref` stays self-describing (`"signal_type:id"`).
2. **Category-level back-off (every run).** `loop.py` computes a per-category **dismissal count**
   from `DECISIONS→ACTIONS→OUTCOMES` and puts it in the agent context. The **gate** then strips any
   category the customer has dismissed ≥2× while building the safe set (`guardrails.decide_customer`),
   so a category they keep rejecting simply never gets offered again. This *is* the "dismissal-count
   memory" the design doc describes (what `get_interaction_history` was meant to provide) — built as
   deterministic context, not a named LLM tool.

Both layers are the *same idea* — don't repeat yourself at someone — applied at two grains: cooldown
paces the *same product*, back-off retires a *dismissed category*. Together they also sequence a
customer's multiple needs over time: one outreach now, the rest deferred to later runs, never all at
once.

Still remaining: making the dismissal count **recency-weighted** (today it's a flat count).

---

## 10b. The API layer

Everything above runs as CLI scripts + DB writes. The API (`api/`) is the **HTTP surface** that
makes it interactive — it's what the two frontends (`ops/`, `customer/`) talk to.

- **`api/app.py`** — a FastAPI app (run with `uvicorn apex.api.app:app`). It exposes:
  - **read endpoints** the bank dashboard needs — `/stats`, `/customers`, `/customers/{id}` (the full
    reasoning trace), `/products`, `/insights/{id}` (the customer money-at-a-glance + suggestions), and
    `/explain/{action_id}` (the customer-facing "why am I seeing this?" — explains from a fact the
    customer can already see, but **declines** if the outreach traces back to a vulnerable moment, so
    nothing sensitive can be reverse-engineered; the decline is in code, before the LLM is called);
  - **pipeline triggers** — `/pipeline/score|detect|agent|run-all` (re-run a stage on demand;
    `?reset=false` for incremental/suppression mode), and `/pipeline/reengage` (revisit `wait`
    decisions whose moment has passed → gentle insight; `?days=0` revisits all now);
  - **RM escalation queue** — `/escalations` (the inbox of `escalate` decisions awaiting a human) and
    `/escalations/{decision_id}/resolve` (mark one handled);
  - **conversational** — `/chat` (routes to Guide or Concierge) and `/voice/transcribe` (Whisper STT);
  - **demo + feedback** — `/demo/simulate`, and `/track/{action_id}[/adopt|/dismiss]` + `/pipeline/expire-outcomes`.
  - CORS is open so the Vite dev servers can call it directly.
- **`api/serializers.py`** — small functions that turn ORM rows into predictable JSON (UUID→string,
  Decimal→float, datetimes→ISO). Keeps the response shape stable and decoupled from the DB models.

The API holds no business logic — it's a thin layer that calls the pipeline/agent/conversation
modules and serializes the result. The thinking lives in the modules above; this just exposes it.

---

## 11. Signals → products mapping

Defined in `agent/routing.py` (code) and `specs/signals.md` (design).

| Signal | Routes to |
|---|---|
| dormancy | Insta Plus (reactivation) |
| idle_balance | MOD auto-sweep → SIP → FD → RD (first eligible) |
| fiscal_year_end_window | NPS if 80C covered, else Tax Saver FD → PPF |
| sip_graduation | SBI Mutual Fund |
| life_event | eShield (but gate → wait) |
| large_asset_purchase | Auto Loan → asset insurance |
| manual_recurring_payment | e-PAY AutoPay |
| login_decay | YONO Cash |
| sustained_rent_payment | Home Loan |
| tuition_payment | Education Loan |
| cash_flow_stress | PAPL → Loan-vs-FD → Loan-vs-MF → Personal Loan (by holdings) |
| gold_loan_liquidity_gap | Gold Loan |
| salary_credit_upgrade | Salary Package Account |
| protection_gap | PMJJBY → PMSBY |
| preapproved_card_offer | SBI Credit Card |
| churn_risk | (no product — gate escalates to a human RM for retention) |
| stated_intent | full-depth products in the category the customer asked about (Concierge-sourced) |
| application_dropoff | (Guide mode — not Analyser) |

---

## 12. Prototype vs production

The guiding rule: **simulate the plumbing, keep the brain real.**

| Concern | Prototype (built) | Production |
|---|---|---|
| Data source | synthetic generator | read-only feed from SBI's CBS |
| Data arrival | one-shot batch insert | account webhooks + transaction streaming (Kafka) |
| Cadence | on-demand, "recompute fresh" | nightly sweep + on-demand Concierge |
| Dedup | wipe & recompute | incremental: signal lifecycle + cooldown + outcome back-off |
| Models | stress synthetic; churn real | periodic retraining + drift monitoring (MLOps) |
| Channels | real email to a sink; SMS/voice simulated | real SMS/WhatsApp/voice telecom |
| Scale | one process, ~46 customers, all in memory | millions → distributed, queues, prioritisation |
| Identity | "sign in as" picker | real authentication |
| PII/security | synthetic, no real PII | strict access control, audit, RBI compliance |

What APEX **never fakes**, even now: the reasoning (real LLM + code gate), the ethics, the voice
pipeline (Groq Whisper), and one real channel (email).


A single consolidated comparison, pulling together every demo/production distinction made throughout this document, since they were established piecemeal across many sections.

| Layer | **Demo (prototype)** | **Production** |
|---|---|---|
| **Data source** | Synthetic — generated `CUSTOMERS`/`ACCOUNTS`/`TRANSACTIONS`/`APP_SESSIONS`/`APPLICATIONS`, schema-correct but invented | SBI's real CBS, accessed via direct internal read-only access (APEX deployed by SBI itself — no AA, no third party) |
| **New customer onboarding (Tier 1)** | Real — actual conversation, real product-page link construction, real Mechanism B link logic | Identical mechanism — nothing changes |
| **Account creation confirmation** | Simulated — "Simulate 3 months of activity" button stands in for SBI's internal system notifying APEX an account is live | Real — an internal event (webhook-style) fires the moment SBI's own KYC process completes |
| **Mid-onboarding drop-off (Tier 2)** | Simulated — "Simulate drop-off here" button seeds an `APPLICATIONS` row after a backend-touching step (Aadhaar/PAN verification), since that's the realistic point SBI's backend would actually know | Real — SBI's own onboarding system already has this record as a side effect of running verification steps |
| **Transaction/session data arrival** | Batch insert, instant, for demo pacing | Periodic internal sync (nightly/hourly) — never a per-transaction push; only account-level events are true real-time webhooks |
| **ML scoring (stress, attrition, anomaly)** | Real computation, run on synthetic data — the actual model logic, not faked | Identical models, run on real data |
| **Signal detection** | Real rule logic, running against synthetic data | Identical — same rules, real data |
| **Analyser decision loop (per-customer code gate → LLM pick + compose)** | Fully real — deterministic act/wait/escalate + safe-set ethics, then a genuine LLM relevance pick + vernacular message | Identical — this never changes between demo and production |
| **Authority levels 1–3** | Fully real — insight, one-tap deep link, standing-rule detection all genuinely work | Identical |
| **Authority level 4 (autonomous + undo window)** | Not built — explicitly future-state | Requires SBI to grant scoped write access; doesn't exist yet in either |
| **Execution (deep links)** | Real link construction; clicking through to SBI's actual site is possible but not the focus of the demo | Identical mechanism, real SBI pages |
| **Guide/Concierge channel** | Real — APEX's own website, live chat | Identical |
| **Analyser outreach channel** | Real email (Resend/Brevo free tier) | WhatsApp/SMS — swapped because those require paid infrastructure, not because the logic differs |
| **Customer authentication** | Simulated — phone + OTP tied to a synthetic customer record | Real SSO handoff from SBI's own login (APEX never sees a password) |
| **Customer-facing explanation ("why am I seeing this")** | Fully real — same constrained generation, same guardrails | Identical |
| **Dismissal-count "memory"** | Fully real — reads the same `DECISIONS`/`ACTIONS`/`OUTCOMES` tables | Identical |
| **Audit logging** | Fully real — every decision logged exactly as designed | Identical |
| **Model retraining / feedback loop** | Explicitly out of scope — not enough synthetic outcomes to mean anything | Also not really solved — same dismissal-count approach is the actual answer, not retraining |

**The one-sentence version, if a judge asks directly:** *"Everything that's hard — the reasoning, the judgment, the restraint — is fully real in this demo. The only things simulated are the handful of seams where real bank integration genuinely isn't possible at hackathon scale: data arriving, time passing, and login. Nothing about the agent's intelligence is faked."*

**The honest pattern across every simulated piece:** every single thing marked "simulated" above shares the same shape — it's a seam where SBI's own infrastructure would need to hand APEX something (a data event, a login token) — never a seam where APEX's own reasoning or judgment is faked. That consistency is worth stating directly if asked "what's real here": it's not a random patchwork of shortcuts, it's one principle applied everywhere — simulate the handoff, never the intelligence.

---

## 13. Concepts glossary

- **Train/serve skew** — when a model's training data is described differently from production data,
  silently breaking it. Defended by sharing the feature functions across both.
- **Latent driver** — a hidden trait not in any column (e.g. the stress trainset's hidden
  `stress_level`) that shapes visible behaviour. Used so a model must *infer* the hidden cause from
  noisy observables, not echo a flat rule.
- **Graduated authority** — Level 1 insight (no action), Level 2 one-tap (confirm link), Level 3
  standing rule (set up once, runs itself). APEX never holds open-ended authority.
- **Code gate** — the deterministic `decide` step where act/wait/escalate is settled in plain code,
  so bright-line ethics are guaranteed, not requested in a prompt.
- **Re-engagement** — the scheduled second look at a `wait` (`reengage.py`): once the acute moment has
  passed (and only if the customer isn't still in severe stress), APEX sends one gentle, product-free
  Level-1 insight. The "acknowledge and wait, then offer insight" ethic, made operational.
- **RM queue** — the inbox of `escalate` decisions awaiting a human relationship manager, tracked by
  the `decisions.rm_status` field (open → resolved) and surfaced on the ops **Escalations** page.
