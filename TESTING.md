# APEX — How to Test the Prototype

A practical, copy-paste guide: reset the database, rebuild the whole pipeline from scratch, bring up the API + both web apps, and then exercise every mode (Guide, Concierge, Analyser, the demo mechanic, the feedback loop) — including the **exact questions to ask** and **what a correct answer looks like**.

> **Mental model.** The backend is a pipeline of CLI steps that each write to Postgres:
> `init_db → generate → train → score → detect → validate → agent loop`.
> The API (`uvicorn`) is a read surface + on-demand pipeline triggers. The two React apps
> (**ops** = bank dashboard, **customer** = Guide/Concierge/Demo) talk to that API.

---

## 0. Prerequisites (one-time)

1. **Postgres running**, and a database named `apex` exists:
   ```bash
   createdb apex          # or: psql -c "CREATE DATABASE apex;"
   ```
2. **Backend env + deps:**
   ```bash
   cd backend
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env          # then edit .env (see below)
   ```
3. **`.env` must have a working `DATABASE_URL`.** For the agent's LLM messages and Concierge/Guide chat to be *real* (not the deterministic fallback), also set `GROQ_API_KEY`. For real email delivery set `RESEND_API_KEY` + `APEX_DEMO_EMAIL`.
   ```
   DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/apex
   GROQ_API_KEY=gsk_...            # optional but recommended — without it, chat/messages degrade to deterministic text
   APEX_DEMO_EMAIL=you@example.com # optional — only needed to test real email
   RESEND_API_KEY=re_...           # optional — only needed to test real email
   ```
4. **Frontend deps (once each):**
   ```bash
   cd ops && npm install
   cd ../customer && npm install
   ```

> **No Groq key?** Everything still runs end-to-end — the agent loop and chat fall back to deterministic text, so you can fully test routing, the ethical gate, signals, and the dashboards. Only the *wording* of messages/answers is templated instead of LLM-generated.

---

## 1. Reset the database and rebuild everything (the core flow)

Run these from `backend/` with the venv active, **in order**. This is the canonical "start clean" sequence.

```bash
cd backend && source .venv/bin/activate

# 1. Create all 12 tables (safe to re-run) + seed the product catalogue into PRODUCTS
python -m apex.database.init_db

# 2. Wipe prior synthetic rows (keeps PRODUCTS) + regenerate the 16 personas + noise population
python -m apex.generator.generate --reset

# 3. Train the ML models (stress synthetic, churn real) → artifacts/
python -m apex.ml.train

# 4. Compute all scores for every customer → SCORES table
python -m apex.ml.score

# 5. Detect signals from scores + raw data → SIGNALS table
python -m apex.signals.detect

# 6. Verify detection against the answer key (generated_manifest.json)
python -m apex.signals.validate

# 7. Run the Analyser agentic loop → DECISIONS + ACTIONS (no email)
python -m apex.agent.loop

# 7b. (optional) Re-engage deliberate WAITs whose acute moment has passed → gentle, product-free insight
python -m apex.agent.reengage --days 0          # --days 0 revisits all waits now (demo pacing)
```

### Agent-loop flags (`python -m apex.agent.loop ...`)

The bare command processes **all customers** with Analyser signals (one decision per customer), wiping prior decisions first, and writes results without sending any email. These flags change that:

- **`--limit N`** — process only the **first N customers** (oldest signal first), instead of all of them.
  *Why:* each *acted* customer makes one LLM call, so a full run is slow and burns API quota. Use `--limit 6` while iterating to get a fast result. Example: `python -m apex.agent.loop --limit 6`.

- **`--send`** — actually **deliver** the acted messages as real email (via Resend). Without it, the loop still writes the `ACTIONS` rows but `sent_at` stays null (nothing leaves the machine).
  *Needs:* `RESEND_API_KEY` + `APEX_DEMO_EMAIL` in `.env`. In non-prod every email routes to the demo sink, never a real customer. Example: `python -m apex.agent.loop --limit 3 --send`.

- **`--incremental`** — **keep** the existing decision/outcome history instead of wiping it, so that when each customer's safe set is built the **dismissal back-off** (a category dismissed ≥2× is dropped), the **held-filter** (adopted products drop out), and the **30-day product cooldown** (a product recommended recently isn't repeated) all take effect.
  *Why:* the default (full reset) is for a clean, repeatable demo. `--incremental` is the *production-style* behavior that proves the feedback/suppression loop — on a re-run a customer's previously-recommended product is held back, so they get a *different* eligible product or resolve to `wait` rather than being re-nudged with the same thing. Example: `python -m apex.agent.loop --incremental`.

Flags combine freely, e.g. `python -m apex.agent.loop --incremental --limit 6 --send`.

**What "reset" means at each level:**
- **Re-seed data only** (most common): re-run steps **2 → 7**. `generate --reset` wipes synthetic customers/accounts/txns/scores/signals/decisions but **keeps PRODUCTS**.
- **Schema changed (new column):** just re-run step **1** — `init_db` applies idempotent column
  migrations (`ADD COLUMN IF NOT EXISTS`, e.g. `decisions.rm_status`) on top of the existing DB, **no
  data loss, no drop needed.** Only drop for a *totally* clean slate:
  ```bash
  psql -c "DROP DATABASE apex;" && psql -c "CREATE DATABASE apex;"
  ```
- **Re-run just the agent** (after tweaking routing/guardrails): `python -m apex.agent.loop` again (it wipes prior decisions/actions by default for a repeatable result).

### What a healthy rebuild looks like

- **Step 3 (train)** prints ROC-AUC per model and writes `apex/ml/artifacts/{stress,churn}.joblib`.
- **Step 6 (validate)** is the report card. Expect: **recall** on every persona's expected signal, **silence** on the ~30 noise customers, and EXTRAS only as warnings.
  - ⚠️ **Expected today (date is 2026-06-22):** `fiscal_year_end_window` (persona *Anita Rao*) is **calendar-gated to Jan–Mar**, so out of that window it is reported as *conditional* (it passes if its precondition holds) — this is correct, not a failure.
- **Step 7 (agent)** prints something like `act=… wait=… escalate=…`. You should see at least one **wait** (the medical/`life_event` persona, *Anjali Desai*) and at least one **escalate** (severe stress with only unsecured debt, *Suresh Kumar*, and/or `churn_risk`).
- **Step 7b (reengage)** prints `re-engaged=… still-waiting(acute)=…`. Expect some waits to be **re-engaged** (the moment has passed → a gentle product-free insight is written) and any in *severe ongoing stress* to be **kept waiting**. Re-running it is idempotent — a wait is followed up at most once (`reengaged=0` on a second pass).

---

## 2. Bring up the API + both web apps

Open **three terminals**.

```bash
# Terminal 1 — backend API  (http://localhost:8000, docs at /docs)
cd backend && source .venv/bin/activate
uvicorn apex.api.app:app --reload --port 8000

# Terminal 2 — bank ops dashboard  (http://localhost:5173)
cd ops && npm run dev

# Terminal 3 — customer site  (http://localhost:5174)
cd customer && npm run dev
```

Quick API smoke test (no browser needed):
```bash
curl localhost:8000/health        # {"status":"ok"}
curl localhost:8000/stats         # customer/signal/decision counts
```

---

## 3. Test the Analyser (the bank ops dashboard) — http://localhost:5173

The Analyser already ran in step 1.7; the dashboard reads its output.

1. **Overview** — confirm signal counts by type and decisions by outcome (act/wait/escalate). The **Run pipeline** button re-runs score → detect → agent (~30–60s with an LLM key).
2. **Customers** — table of everyone with their signals + outcomes.
3. **Customer detail** — the reasoning trace. Open these **hero personas** and check the expected behavior:

| Open this customer | Expected signal | Expected decision | What to verify |
|---|---|---|---|
| **Priya Nair** | `idle_balance` | **act** → MOD/Auto-Sweep or JanNivesh SIP | A calm savings nudge; authority level set; deep link present |
| **Vikram Patel** (Hindi) | `manual_recurring_payment` | **act** → e-PAY AutoPay | Message is in **Hindi**; references paying the bill manually |
| **Anjali Desai** | `life_event` (medical) | **wait** — *no product push* | The money shot: the code gate holds **all** outreach for her; the LLM is never called; **no message generated**, decision logged as wait with the `[gate]` reason |
| **Ramesh Iyer** (Tamil) | `dormancy` | **act** → Insta Plus reactivation | Reactivation framing, not a new-account pitch |
| **Suresh Kumar** | `cash_flow_stress` (severe, ~0.93) | **escalate** — no auto-push | Severely stressed with only *unsecured* debt available → routed to a human, not an auto-offer of debt. Also: his insurance gap is held back (vulnerability restraint) |
| **Lakshmi Banerjee** (Bengali) | `cash_flow_stress` (severe) | **act** → Loan **against FD** | Severely stressed too, but steered to *secured* lending (her own FD) — never unsecured debt. The Suresh-vs-Lakshmi contrast is the nuance to show |

**The key thing to demonstrate:** open **Anjali Desai** and show that APEX *detected* the vulnerability and *chose to wait* — restraint enforced by code, visible in the trace. That's the differentiator no one else shows.

### 3a. The Escalation queue (the RM handoff) — Overview → "Escalations"

`escalate` decisions aren't a dead end — they land in a **human relationship-manager inbox.**

1. Open the **Escalations** tab. Expect the cases the gate refused to auto-act on: **Suresh Kumar** (`cash_flow_stress`, severe + only unsecured debt → escalate) and any **`churn_risk`** customer (the attrition model flagged them → escalate for retention, not a product push).
2. Each card shows the customer, the signal, and **the gate's reason** (why it escalated). Click **Mark handled** → the case disappears from the open queue and the **Escalations open** stat on Overview drops by one.
3. The **Overview** page also shows an **Escalations open** count, and a **Re-engage waits** button (next to *Run pipeline*) — see §3b.

Verify via API if you prefer:
```bash
curl -s localhost:8000/escalations | python -m json.tool        # the open queue
curl -X POST localhost:8000/escalations/<decision_id>/resolve   # mark one handled
```

### 3b. Re-engaging a deliberate wait (the ethical timing, made real) — Overview → "Re-engage waits"

A `wait` is a *pause*, not a refusal. After the acute moment passes, APEX follows up **once** with a gentle, product-free insight (never naming the sensitive event).

1. With at least one `wait` on record (e.g. **Anjali Desai**'s `life_event`), click **Re-engage waits** on Overview. (It calls `/pipeline/reengage?days=0` — revisit all waits now, demo pacing.)
2. Open that customer's **Customer detail**: alongside the original `wait`, you'll now see a new **act** decision badged **re-engagement** — a Level-1, product-free, link-free check-in message.
3. **Restraint still holds:** a customer in *severe ongoing stress* is **not** re-engaged (the moment hasn't passed) — they stay waiting. The pass output reports `re-engaged=N still-waiting(acute)=M`.

Verify via API:
```bash
curl -X POST "localhost:8000/pipeline/reengage?days=0"          # {"reengaged": N, "still_waiting": M, ...}
```

> **One honest caveat to know:** if the *same* customer has two separate waits, they currently get two check-ins (no per-customer cap yet). Mention it if asked — the fix is the multi-signal frequency cap on the roadmap.

---

## 4. Test Concierge mode (customer's own data) — http://localhost:5174 → "My finances"

Concierge answers questions about a **specific** customer's real data using read-only tools (it computes, never guesses). It needs a signed-in customer.

1. Go to the **My finances** tab → use the demo **sign-in picker** to become a customer.
2. Sign in as **Priya Nair** (₹2.8L balance, ₹90k income) and ask:

| Ask this | What a correct answer shows |
|---|---|
| *"How's my spending?"* | A real category breakdown computed from her transactions (calls `get_spending`) |
| *"Can I afford a ₹50,000 phone?"* | Real balance, amount left after, and a verdict — affordable & comfortable for Priya |
| *"What do I already have with SBI?"* | Her actual holdings (Insta Plus account + eShield) via `get_holdings` |
| *"What's my balance?"* | The real total across accounts, not a guess |
| *"What should I get?" / "What do you recommend?"* | Calls `recommend_product` — suggests only **vetted** products (eligible, not already held, ethically cleared via the same routing + guardrail gate the Analyser uses). It never freelances: the LLM phrases, **code picks the product**. Ask the *stressed* Suresh the same thing → it must **not** offer unsecured debt. |

3. Now sign in as a **stressed** customer, **Suresh Kumar** (₹12k balance), and ask:
   - *"Can I afford a ₹50,000 phone?"* → should come back **not comfortable / not affordable** — proving the answer is computed from *his* data, not generic.

4. **Vernacular check:** sign in as **Vikram Patel** (Hindi) or **Lakshmi Banerjee** (Bengali) and ask a question — the reply should come back in that customer's language.

> **Safety to demonstrate:** Concierge is scoped to the signed-in customer. It cannot read another customer's data — the `customer_id` is injected server-side, not chosen by the model.

**"What APEX suggests" panel:** on the same tab you'll see the agent's own act-decisions for that customer (the ones from the Analyser run), each with **Open / I've done this / Not interested** — these feed the feedback loop (Section 7).

**"Why am I seeing this?" (the transparency layer).** Each suggestion has a **Why am I seeing this?** link. Click it:
- For a normal nudge (e.g. Priya's idle balance), it explains using **only a fact she can already see in her own account** ("a significant amount has been sitting idle…") — no jargon, no mention of scores or models.
- **The restraint to demonstrate:** for an outreach that traces back to a vulnerable moment (a re-engagement after a `life_event` wait, or a customer flagged vulnerable), it **declines to elaborate** — a gentle, non-specific reply — so the customer can never reverse-engineer that something sensitive was detected. The decline is enforced in **code** before the LLM is ever called.

Verify headlessly:
```bash
# explanation for one suggestion (action_id from /insights/<customer_id>):
curl -s "localhost:8000/explain/<action_id>" | python -m json.tool   # {"declined": false|true, "explanation": "..."}
```

---

## 4b. Test conversational signals (Concierge → Analyser)

The newest feature: a customer's **stated intent** in a Concierge chat becomes a `stated_intent` signal that the Analyser can act on later — and a disclosed **vulnerability** creates nothing (and withdraws pending intents). It runs as a **background task** after the reply, so the signal appears a moment *after* the chat response.

**A. Explicit intent → a signal is created.**
1. In **My finances**, signed in as e.g. **Priya Nair**, send: *"I'd like to start investing some money for the long term."*
2. Wait ~2–3s (background extraction), then open the **ops dashboard → Priya's Customer detail** (or refresh) — you should see a new **`stated_intent`** signal (source_ref = `investments`).
3. Run the Analyser so it acts on it: ops **Run pipeline**, or `curl -X POST localhost:8000/pipeline/agent`. Priya should now get an **investments** recommendation (it passed the same eligibility + ethical gate as any signal).

**B. Disclosed vulnerability → nothing (restraint).**
1. As the same customer, send: *"I just lost my job and I'm really worried about money."*
2. After the reply, check the dashboard: **no new actionable signal** is created, and any pending `stated_intent` from step A is marked **`expired`** (withdrawn). APEX never turns disclosed distress into a sales trigger.

**Verify without the UI** (quick CLI check):
```bash
# after sending the chat message via the app, inspect the customer's signals:
curl -s localhost:8000/customers/<customer_id> | python -m json.tool | grep -A2 stated_intent
```
Or test the extraction directly (one LLM call each), then clean up:
```bash
python -c "
from apex.database.db import SessionLocal
from apex.database.models import Customer
from apex.agent.intent import extract_and_store
with SessionLocal() as s:
    cid = s.query(Customer).filter_by(name='Priya Nair').first().customer_id
print('explicit intent →', extract_and_store(cid, [{'role':'user','content':'I want to start investing'}]))
print('disclosed distress →', extract_and_store(cid, [{'role':'user','content':'I lost my job, scared about money'}]))
"
```
- Expect: `explicit intent → ['investments']`, then `disclosed distress → []` (and the investments signal is now `expired`).

> **What's happening under the hood:** explicit interest → a `stated_intent` signal whose `source_ref` is the category → routed and gated exactly like a behavioural signal (so vulnerability restraint, dismissal back-off, and "already held" all apply). The ethical split lives in `apex/agent/intent.py`.

---

## 5. Test Guide mode (new customer, no data) — http://localhost:5174 → "Open an account"

Guide is onboarding for someone APEX knows nothing about. It's a **tool-calling agent** (like Concierge): it calls read-only tools for the catalogue, the real document list, and a live application lookup — so its facts are grounded, never recited. It hands off real SBI links and never builds a (non-working) pre-filled deep link.

**Tier-1 — anonymous stranger (no sign-in).** Try these, in order:

| Ask this | What a correct answer shows |
|---|---|
| *"I'm new to SBI and want to open a savings account."* | Asks a clarifying question or two first; recommends an account (e.g. Insta Plus) in plain language; offers a real link |
| *"What documents do I need to open an account?"* | Plain-language list (Aadhaar, PAN, photo, address proof) — pulled by the `get_required_documents` tool, not recited. For a **loan**, also income proof + bank statements |
| *"I want to start saving for my child's education."* | Frames it as a life outcome (not "SIP/PPF"); may surface one or two *adjacent* areas (e.g. protection) — never a product dump |
| *"मुझे बचत खाता खोलना है"* (Hindi: "I want to open a savings account") | Replies **in Hindi** — mirrors the customer's language |
| *"Tell me everything SBI offers."* | Should NOT dump a brochure; gently surfaces a couple of relevant areas and points to the **Explore** tab |

**Tier-2 — drop-off (identified).** A drop-off is *detected by the backend* (`application_dropoff` signal); Guide only confirms it for an **identified** person. To see it: **sign in** as a customer who has an unfinished application (one with an `in_progress`/`abandoned` row in `applications`), then open the **Open an account** tab and just say *"hi"*. Expect Guide to **proactively acknowledge the unfinished application**, name the step they stopped at (e.g. *video KYC*), list what's needed, and link to the real SBI page — without making them start over. (An anonymous visitor never gets this — it's the correct, honest behavior.)

You can also drive it headless:
```bash
# Tier-2: pass the customer_id as identity (it maps to applications.customer_ref)
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"mode":"guide","customer_id":"<id-with-an-application>","messages":[{"role":"user","content":"hi"}]}'
```

**Things to verify about tone (the behavioral philosophy in action):**
- No jargon (no "SIP", "CAGR", "NAV").
- Calm, no urgency, no hype, no scary "click now" language.
- Surfaces one or two adjacent needs, framed as outcomes — not a list.

**Explore tab:** browse the full catalogue grouped by life-need (Save / Grow / Borrow / Protect / Pay) with real links — for the self-directed customer.

---

## 6. Test the Demo mechanic ("Simulate 3 months") — http://localhost:5174 → "See it in action"

This shows the **Guide → Analyser transition**: a brand-new customer suddenly gets data and APEX reacts on the spot. Pick a scenario; APEX seeds one customer's 3 months, runs score → detect → agent for just them, and shows the outreach.

| Scenario | Customer | Expected result |
|---|---|---|
| **Idle balance → savings nudge** | Aarav Khanna | An **act**: calm savings/sweep nudge |
| **Manual recurring bill → autopay** | Neha Joshi (Hindi) | An **act**: autopay nudge, in Hindi |
| **Medical event → restraint (wait)** | Sunita Rao | A **wait**: APEX *notices and holds back* — no product push |

**Lead with the medical scenario** — it proves the ethical guardrail live. After simulating, click through into **My finances** as that customer to continue in Concierge.

> Re-running a scenario is safe: it wipes the prior demo customer for that scenario (identified by a `demo.apex` email) and re-seeds, so clicks don't pile up.

You can also drive this from the API directly:
```bash
curl localhost:8000/demo/scenarios
curl -X POST "localhost:8000/demo/simulate?scenario=life_event"
```

---

## 7. Test the feedback loop (outcome capture + suppression)

This proves APEX "remembers" and backs off.

**A. Capture a response.** From the **My finances → What APEX suggests** panel (or from a real email if you ran the loop with `--send`), click:
- **Open** → logs `clicked`, then redirects to the real SBI page.
- **I've done this** → logs `completed` **and creates a holding** (demo stand-in for SBI confirming adoption).
- **Not interested** → logs `dismissed`.

**B. See suppression work.** Re-run the agent in **incremental mode** — it keeps history, so any product recommended within the last 30 days is held back when its customer's safe set is rebuilt:
```bash
python -m apex.agent.loop --incremental
# or via API:
curl -X POST "localhost:8000/pipeline/agent?reset=false"
```
Expect previously-acted customers to now pick a *different* eligible product (the recent one is on cooldown), or resolve to **wait** if nothing fresh remains — they are not re-nudged with the same thing. Compare the `act / wait / escalate` counts to the full-reset run.

**C. The "ignored" sweep.** Mark un-answered sent actions older than N days as `ignored`:
```bash
curl -X POST "localhost:8000/pipeline/expire-outcomes?days=7"
```

**D. Category-level back-off (distinct from B).** §B paces the *same product* (cooldown). This is different: once a customer has **dismissed a whole product category ≥2×**, `decide_customer` **strips that category from the safe set entirely** ("don't nag") — it's simply never offered again. To force and verify it (the "Ravi" case from the WALKTHROUGH), seed two dismissals in one category for a customer, then re-run the agent incrementally:
```bash
python - <<'PY'
from apex.database.db import SessionLocal
from apex.database.models import Customer, Decision, Action, Outcome
from datetime import datetime
# give a customer two dismissed 'investments' decisions, so the category count hits the back-off threshold
with SessionLocal() as s:
    c = s.query(Customer).filter_by(name='Priya Nair').first()
    for _ in range(2):
        d = Decision(customer_id=c.customer_id, mode='analyser', trigger_ref='idle_balance:seed',
                     outcome='act', product_id='inv_jannivesh_sip'); s.add(d); s.flush()
        a = Action(decision_id=d.decision_id, customer_id=c.customer_id, channel='email',
                   message_text='(seed)'); s.add(a); s.flush()
        s.add(Outcome(action_id=a.action_id, customer_id=c.customer_id,
                      response_type='dismissed', responded_at=datetime.utcnow()))
    s.commit()
print('seeded 2 investments dismissals for Priya')
PY
python -m apex.agent.loop --incremental --limit 20    # investments is now stripped from her safe set
```
Expect her idle-balance outreach to **no longer offer any investments product** — the LLM picks from her remaining safe options (a deposit sweep / FD), or the decision resolves to **wait** if back-off plus cooldown leave nothing fresh. (Re-run the clean rebuild afterward to discard the seeded rows.)

Verify any of this on the **ops → Customer detail** page (the outcome shows on the decision) or via `curl localhost:8000/customers/<id>`.

---

## 8. Test voice (optional)

On either the Guide or Concierge tab:
- Click the 🎤 mic, speak a question → it's sent to the backend, transcribed by Groq Whisper, and used as your message.
- Toggle **"Speak replies"** to have the answer read back via the browser's text-to-speech.

Voice STT reuses `GROQ_API_KEY` — no extra key needed. (If the key is missing, transcription returns empty.)

---

## 9. Fast reference — all the commands

```bash
# ---- full rebuild from scratch (backend/, venv active) ----
python -m apex.database.init_db
python -m apex.generator.generate --reset
python -m apex.ml.train
python -m apex.ml.score
python -m apex.signals.detect
python -m apex.signals.validate
python -m apex.agent.loop                 # flags: --limit N / --send / --incremental (explained in §1)
python -m apex.agent.reengage --days 0    # revisit WAITs whose moment has passed → gentle insight (--send to email)

# ---- serve ----
uvicorn apex.api.app:app --reload --port 8000   # API + /docs
cd ops && npm run dev                            # dashboard  :5173
cd customer && npm run dev                       # customer   :5174

# ---- read endpoints (headless, no browser) ----
curl -s localhost:8000/products | python -m json.tool             # the 28-product catalogue
curl -s localhost:8000/insights/<customer_id> | python -m json.tool # money-at-a-glance + suggestions (each has why_url)
curl -s localhost:8000/explain/<action_id> | python -m json.tool    # "why am I seeing this?" (declines on sensitive triggers)
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"mode":"guide","messages":[{"role":"user","content":"I want to open a savings account"}]}'
curl -s -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"mode":"concierge","customer_id":"<id>","messages":[{"role":"user","content":"what should I get?"}]}'

# ---- on-demand pipeline via API ----
curl -X POST localhost:8000/pipeline/score
curl -X POST localhost:8000/pipeline/detect
curl -X POST "localhost:8000/pipeline/agent?reset=false&limit=6&send=false"
curl -X POST "localhost:8000/pipeline/run-all?send=false"
curl -X POST "localhost:8000/pipeline/reengage?days=0&send=false"   # re-engage deliberate waits
curl -s localhost:8000/escalations                                 # the RM escalation queue
curl -X POST "localhost:8000/demo/simulate?scenario=life_event"
```

---

## 10. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `could not connect` on any `python -m apex...` | `DATABASE_URL` wrong, or Postgres/the `apex` database not running. |
| Chat / messages sound templated, not natural | `GROQ_API_KEY` missing or invalid — the loop and chat fall back to deterministic text. Set the key in `.env`. |
| `concierge mode requires a customer_id` (400) | Sign in via the **My finances** picker first; Concierge is per-customer. |
| `validate` flags `fiscal_year_end_window` | Expected outside Jan–Mar — it's calendar-gated and reported as *conditional*, not a real failure. |
| Emails not arriving with `--send` | Need `RESEND_API_KEY` + `APEX_DEMO_EMAIL`; in Resend test mode the recipient must be your own Resend account email (the sink already is). Without keys, the loop still writes ACTIONS — just doesn't deliver. |
| Frontend can't reach API / CORS | API must be on `:8000`; set `VITE_API_URL` if you changed the port. |
| Want a truly clean slate | `psql -c "DROP DATABASE apex;" && psql -c "CREATE DATABASE apex;"` then run the full rebuild. |
| Agent run is slow | It makes one LLM call per acted customer. Use `python -m apex.agent.loop --limit 6` while iterating. |
```
