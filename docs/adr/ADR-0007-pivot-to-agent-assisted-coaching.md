# ADR-0007 — Pivot to agent-assisted coaching (coach-approved AI agents)

### Status

* **Proposed** (becomes Accepted once both team members approve the PR)
* **Supersedes:** `ADR-0004-one-thread-per-client.md` (messaging model)
* **Amends:** `ADR-0003-owner-scoped-read-only.md` (adds the coach-approval rule; owner scoping still applies)

### Date

2026-11-09

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Related requirement IDs

* FR-4, FR-5 (measurements), FR-6, FR-10 (coach–client messages — replaced by drafts)
* FR-13 (synthetic data), FR-14 (≤10 endpoints), FR-15 (≤6 screens, 2 roles)
* NFR-7 (scope compliance), NFR-9 (secret hygiene)

### Context

The team changed the product concept (see the deck *"Tahadi — An AI agent team that
helps fitness coaches track clients, check exercise form and reply faster"*, October
2026). Coaching today runs on chat threads: clients send numbers and videos by message,
the coach copies them by hand, form videos pile up, and stalled or silent clients are
missed.

The new concept keeps Tahadi's core (coach, client, measurements, Arabic-first) but
replaces the in-app Q&A thread with a small team of agents. The agents do the busywork,
and **the coach makes every decision**: nothing reaches a client without coach approval.

The deck describes five agents:

| # | Agent | Reads | Produces |
| --- | --- | --- | --- |
| 1 | Intake and router | Client chat messages | Saved measurements, routed media |
| 2 | Form check | Exercise video (in the browser) | Rep count and form errors |
| 3 | Progress photos | Check-in photos | Quality check, aligned comparison |
| 4 | Progress analyst | Measurement history | Trends, alerts, weekly summary |
| 5 | Coach assistant | All agent results | Draft replies in Arabic and English |

### Decision

1. **Build agents 1, 2, 4 and 5 now.** Agent 3 (progress photos) stays out of scope:
   photo upload is still a charter non-goal, and this ADR does not lift it.
2. **Code decides, the language model explains.** Measurements are parsed by regex
   first; trends, plateaus and missed check-ins are computed in Python; squat errors
   come from joint-angle rules (MediaPipe, in the browser). The LLM only turns those
   computed facts into short text and is the fallback parser for unusual messages.
3. **Coach approval is mandatory.** The coach assistant writes a *draft* with status
   `pending`. Only an explicit approve sets it to `approved` and hands it to the
   messaging channel. Rejected drafts are never sent.
4. **Messaging channel:** Telegram (see `ADR-0008`), not an in-app thread and not WhatsApp.
5. **Data model (4 tables, cap 8):** `clients`, `measurements`, `form_checks`, `drafts`.
6. **API (9 endpoints, cap 10):**
   `GET /health`, `GET /clients`, `POST /telegram/message`, `GET /summary/{client_id}`,
   `POST /draft/{client_id}`, `GET /drafts`, `POST /drafts/{id}/approve`,
   `POST /drafts/{id}/reject`, `POST /form-checks`.
7. **Agents are built in DevAI Desktop.** The backend runs them by id through DevAI's local
   host (`backend/app/llm.py`, `docs/devai-agents.md`) and falls back to fixed templates
   when DevAI is not reachable, so the demo never depends on it.

### Rejected alternative

* **Option:** Keep the M1 design (in-app Q&A thread) and add AI later.
* **Why rejected:** It does not address the real problem in the new concept (data
  arriving in chat, form videos, missed check-ins), and the thread endpoints would use
  up endpoint budget the agents need.

### Accepted downside

* **Downside:** For the first demo the agent endpoints are not behind the ADR-0002 JWT
  checks; they run on synthetic data only.
* **Mitigation / acceptance:** Demo data is synthetic (ADR-0006). Auth is re-applied
  before any non-demo use; tracked as `R-013` in the risk register.
* **Downside:** LLM output can be wrong or invent numbers.
* **Mitigation / acceptance:** The LLM only receives computed facts, every reply is a
  coach-approved draft, and the tests cover the computed rules without the LLM.

### Consequences

* `ADR-0004` threads are replaced by `drafts`; its endpoints are removed.
* Scope caps still hold: 4 tables, 9 endpoints, 2 roles.
* New risks: LLM cost and errors, Telegram bot token leak (see `docs/risk-register.md`).
* Requirements FR-6 and FR-10 must be rewritten for the draft/approve flow
  (to be done in `docs/requirements/correction-log.md`).

### Related ADRs

* `ADR-0003-owner-scoped-read-only.md`
* `ADR-0004-one-thread-per-client.md` (superseded)
* `ADR-0006-synthetic-data-secrets-hygiene.md`
* `ADR-0008-telegram-instead-of-whatsapp.md`

### How this gets verified

* Unit tests: measurement parser (English, Arabic, Arabic-Indic digits) and analyst
  rules (stalled, no check-in) — no network, LLM mocked.
* Smoke test: a draft is never returned with a `telegram_chat_id` until it is approved.
