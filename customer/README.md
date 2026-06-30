# APEX — Customer Website (customer-facing)

The **customer-facing** app — APEX's own website where Guide and Concierge
live. React + Vite + TypeScript + Tailwind. Consumes the backend API. The internal bank view is a
separate app: [../ops](../ops).

## Setup

```bash
cd customer
npm install
npm run dev          # http://localhost:5174
```

API base from `.env` (`VITE_API_URL`, default `http://localhost:8000`). The backend must be running
(see [../backend/README.md](../backend/README.md)).

## Tabs

- **Open an account** (Guide) — onboarding chat for a new/prospective customer, no data needed.
  After helping with the immediate need, Guide proactively surfaces one or two *adjacent* relevant
  areas (framed as life outcomes) so the customer isn't left with a partial picture. Language
  selector for the reply/voice language.
- **Explore** — a browsable catalogue of everything SBI offers, grouped by life-need
  (Save / Grow / Borrow / Protect / Pay), plain-language one-liners + real links. For the customer
  who wants the full map without having to ask the right questions.
- **My finances** (Concierge) — a financial-assistant view for the signed-in customer: a "money at
  a glance" snapshot (balance, income, a light spending summary) and **What APEX suggests** — the
  agent's own act-decisions shown in-app (ethics-filtered: a wait/escalate produces nothing), each
  with Open / I've-done-this / Not-interested (which feed the outcome loop) — above a chat over their
  own data ("can I afford this?", "how's my spending?"). A demo sign-in picker stands in for real
  authentication. Deliberately *not* a generic budgeting tracker: it surfaces
  outcome-framed opportunities tied to bank products, not raw expense analytics.
- **See it in action** (Demo) — the "Simulate 3 months" mechanic: pick a scenario, APEX seeds a
  customer's three months of activity then decides whether to reach out (or hold back), shows that
  outreach, and lets you continue into **My finances** as that customer. (This
  was originally a bank-side control; moved here so the demo stays customer-facing.)

Both support voice: 🎤 mic → Groq Whisper (backend) → text; replies can be spoken via the
browser's built-in text-to-speech (toggle "Speak replies"). No extra API keys — voice STT reuses
the backend's Groq key.

## Build

```bash
npm run build        # tsc --noEmit && vite build  -> dist/
```
