# APEX — Backend

Python + SQLAlchemy + Postgres. Implements the data substrate ([../specs/schema.md](../specs/schema.md)) and the synthetic data generator ([../specs/data-generator.md](../specs/data-generator.md)).

> **New here?** [WALKTHROUGH.md](WALKTHROUGH.md) is a plain-English, file-by-file explanation of
> the entire backend (the pipeline, every module, the agentic workflow, the feedback loop, and
> prototype-vs-production). Start there to understand *how it all fits*; this README is for
> *setup and commands*.

## Setup

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env and set your Postgres password
```

`.env` (gitignored) must contain a working `DATABASE_URL`:

```
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>
```

The target database must already exist (e.g. `CREATE DATABASE apex;`).

## Commands

```bash
# 1. Create all 12 tables + seed the 28-product catalogue into PRODUCTS
python -m apex.database.init_db   # idempotent: re-running also applies additive column migrations (no data loss)

# 2. Generate synthetic data (16 signal-personas + noise population)
python -m apex.generator.generate --reset      # --reset wipes prior synthetic rows (keeps products)

# 3. Train the ML models (stress synthetic, churn real, propensity synthetic) + write SCORES
python -m apex.ml.train                         # persists artifacts to apex/ml/artifacts/
python -m apex.ml.score                         # writes the SCORES table

# 4. Detect signals from scores + raw data, then validate against the manifest
python -m apex.signals.detect                   # writes the SIGNALS table
python -m apex.signals.validate                 # checks detected vs generated_manifest.json

# 5. Run the Analyser-mode agentic loop (needs GROQ_API_KEY in .env)
python -m apex.agent.loop                        # writes DECISIONS + ACTIONS (no email)
python -m apex.agent.loop --limit 6              # process only the first 6 (saves LLM calls)
python -m apex.agent.loop --limit 3 --send       # also deliver acted messages via Resend

# 5b. Re-engage deliberate WAITs whose acute moment has passed (gentle, product-free insight)
python -m apex.agent.reengage                    # revisit waits >= 3 days old
python -m apex.agent.reengage --days 0 --send    # demo: revisit all waits now + deliver email

# 6. Serve the HTTP API (read surface for the dashboard + pipeline triggers)
uvicorn apex.api.app:app --reload --port 8000    # interactive docs at http://localhost:8000/docs
```

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/stats` | dashboard counts (signals by type, decisions by outcome, emails sent) |
| GET | `/customers` | list with per-customer signal/decision summary |
| GET | `/customers/{id}` | full reasoning trace: profile, accounts, holdings, scores, signals, decisions+actions, recent txns |
| GET | `/products` | catalogue |
| GET | `/insights/{id}` | customer money-at-a-glance + APEX's suggestions (each carries a `why_url`) |
| GET | `/explain/{action_id}` | customer-facing "why am I seeing this?" — explains from a visible fact; declines on a vulnerability-linked outreach |
| POST | `/pipeline/score` · `/pipeline/detect` · `/pipeline/agent` · `/pipeline/run-all` | re-run pipeline stages on demand (`?send=true` to email; `?limit=N` and `?reset=false` for the agent — `reset=false` = incremental/suppression mode) |
| POST | `/pipeline/reengage` | revisit WAIT decisions whose acute moment has passed → gentle product-free insight (`?days=0` revisits all now; `?send=true` to email) |
| GET | `/escalations` | RM queue — escalate decisions awaiting a human (`?include_resolved=true` to include handled ones) |
| POST | `/escalations/{decision_id}/resolve` | mark an escalation handled by the relationship manager |
| POST | `/chat` | conversational reply — `{mode: guide\|concierge, customer_id?, messages[]}` (Groq, context-injected) |
| POST | `/voice/transcribe` | speech-to-text (multipart audio → text) via Groq Whisper |
| GET | `/demo/scenarios` | list "simulate 3 months" scenarios |
| POST | `/demo/simulate?scenario=` | seed one customer's 3 months + score/detect/reason → Guide→Analyser transition |
| GET | `/track/{action_id}` | log `clicked` in `OUTCOMES`, then redirect to the real SBI page |
| GET | `/track/{action_id}/adopt` | log `completed` + create the holding (demo stand-in for the CBS read) |
| GET | `/track/{action_id}/dismiss` | log `dismissed` |
| POST | `/pipeline/expire-outcomes?days=` | mark un-answered sent actions older than N days as `ignored` |

After step 2, `generated_manifest.json` maps each `customer_id` → its expected signals;
`apex.signals.validate` (step 4) is the harness that asserts detection against it
(recall on every persona + noise silence; EXTRAS reported as warnings).

## Layout

```
apex/
  config.py              env + paths (DATABASE_URL, catalogue path, Groq/Resend keys, seed)
  database/
    db.py                engine, session, declarative Base
    models.py            the 12 tables
    seed_products.py     load product_catalogue.json into PRODUCTS
    init_db.py           create_all + seed  (python -m apex.database.init_db)
  shaping.py             shared financial-history shaper (used by generator + ML)
  demo.py                "simulate 3 months" mechanic (drives the whole pipeline for one customer)
  generator/
    personas.py          the 16 signal-personas
    generate.py          generation engine  (python -m apex.generator.generate)
  ml/
    loaders.py features.py anomaly.py trainset.py    feature + training plumbing
    train.py             fit + persist models  (python -m apex.ml.train)
    score.py             write SCORES          (python -m apex.ml.score)
  signals/
    thresholds.py        spec anchor numbers (tunable)
    detectors.py         the 17 signal detectors (pure functions)
    detect.py            write SIGNALS         (python -m apex.signals.detect)
    validate.py          manifest harness      (python -m apex.signals.validate)
  agent/
    routing.py           deterministic signal -> product routing + eligibility
    guardrails.py        the code gate: confidence, ethical restraint, Decide + authority
    graph.py             LangGraph flow: route -> hypothesise -> critique -> decide -> compose
    prompts.py llm.py    Groq calls for the hypothesise / critique / compose nodes
    mailer.py            real outbound email via Resend (routes to the demo sink)
    loop.py              Analyser loop -> DECISIONS + ACTIONS  (python -m apex.agent.loop)
    reengage.py          revisit WAITs after the acute moment passes -> gentle insight  (python -m apex.agent.reengage)
    guide.py             Guide mode — onboarding chat (context injection)
    concierge.py         Concierge mode — LangGraph tool-calling agent (read-only per-customer tools)
    voice.py             Groq Whisper speech-to-text (used by both modes)
    mailer.py            real outbound email via Resend (routes to the demo sink)
    feedback.py          OUTCOMES capture (clicks / adopt / dismiss / ignored)
    _shared.py           shared Groq client + language names
  api/
    serializers.py       ORM -> JSON shapes
    app.py               FastAPI app (uvicorn apex.api.app:app)
```

## Conversational modes (Guide / Concierge) + voice

- **Concierge** (`mode=concierge`, needs `customer_id`): a **LangGraph tool-calling agent**
  (`concierge.py`) — the LLM decides which read-only, per-customer tools to call (`get_balance`,
  `get_spending`, `check_affordability`, `get_holdings`, `list_products`) and answers with the
  *computed* figures, never guesses. "Can I afford this?", "how's my spending?".
- **Guide** (`mode=guide`): onboarding for a new customer with no data — the full-depth
  product catalogue (with links) is injected so it can recommend and hand off.
- **Voice:** `/voice/transcribe` runs Groq Whisper (reuses `GROQ_API_KEY` — no extra key).
  Text-to-speech is done browser-side in the frontend. Both modes reply in the customer's
  language, jargon-free, per the behavioral philosophy.

## Notes on the agentic loop

- **LangGraph flow, with a deterministic code gate.** The Analyser runs as a LangGraph
  graph: `route → hypothesise (LLM) → critique (LLM) → decide (code) → compose (LLM, only
  if act)`. The LLM *reasons and writes*, but the **`decide` node is `guardrails.evaluate`**
  — the act/wait/escalate decision and the ethical restraint (e.g. `life_event` → *wait*)
  are guaranteed in code, never left to the prompt. "LLM proposes, code disposes."
- Product routing + eligibility (`routing.py`) and the gate (`guardrails.py`) stay fully
  deterministic; only hypothesise/critique/compose are LLM calls.
- **Vernacular by design.** Messages are generated in the customer's `language_pref`
  (en/hi/ta/te/bn), jargon-free and outcome-framed, per the behavioral philosophy.
- Set `GROQ_API_KEY` (and optionally `GROQ_MODEL`) in `.env`. If the key is missing or a
  call fails, the loop degrades gracefully to deterministic text and still completes.
- **Real email (`--send`).** Acted messages are delivered via Resend. In non-prod every
  message routes to `APEX_DEMO_EMAIL` (the sink) — never to a real customer. Without
  `--send` the loop only writes `ACTIONS` (and `sent_at` stays null until actually sent).
  Set `RESEND_API_KEY` in `.env`; in Resend test mode the recipient must be your own
  Resend account email (which the sink already is).

## Notes

- No secrets in code — everything reads from `.env`.
- Generation is deterministic (`APEX_RANDOM_SEED`, default 42).
- The generator is **offline-testable** (build logic runs without a DB); only `init_db`
  and the final write step in `generate` touch Postgres.
