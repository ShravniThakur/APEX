# APEX — Bank Ops Console (internal)

The **bank-facing** app — a separate internal view (APEX_README §11) where the bank sees what
the Analyser agent has done across customers. React + Vite + TypeScript + Tailwind. Consumes the
backend API ([../backend/apex/api](../backend/apex/api)). The customer-facing site is a separate
app: [../customer](../customer).

## Setup

```bash
cd ops
npm install
npm run dev          # http://localhost:5173
```

API base from `.env` (`VITE_API_URL`, default `http://localhost:8000`). Make sure the backend runs:

```bash
cd backend && source .venv/bin/activate
uvicorn apex.api.app:app --reload --port 8000
```

## Pages

- **Overview** — pipeline stats (signals by type, decisions by outcome, emails sent) + a
  **Run pipeline** button (score → detect → agent; ~30–60s since the agent calls the LLM per signal).
- **Customers** — table of all customers with their signals and decision outcomes.
- **Customer detail** — the reasoning trace: ML scores, signals, and each agent **decision**
  (hypothesis, self-critique, outcome, confidence, authority level) with the exact vernacular
  message that was sent. Shows restraint explicitly (e.g. a `life_event` → *wait*, no push).

> The "Simulate 3 months" control now lives on the **customer** site ([../customer](../customer)),
> so the whole demo flow stays customer-facing (a deliberate departure from APEX_README §12).

## Build

```bash
npm run build        # tsc --noEmit && vite build  -> dist/
```
