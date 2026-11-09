# SPEC-agents-backend — Agent backend (intake, analyst, coach assistant)

> Intent defined by the team (Saeed Alzahrani) before implementation, per `RULES.md` §1.
> Decisions behind it: `ADR-0007`, `ADR-0008`.

### Goal

Give the coach a backend where client check-ins arrive from Telegram as structured
measurements, each client's progress is summarized with alerts, and replies are drafted
for the coach to approve before anything is sent.

### Scope / non-goals

* **In scope:** intake agent, progress analyst, coach assistant (drafts + approve/reject),
  saving squat form-check results produced by the browser, seed data, tests, Render deploy.
* **Out of scope:** progress photos (charter non-goal), video upload/processing on the
  server, payments, workout/nutrition plans, medical advice, WhatsApp, login/auth for the demo.

### Constraints

* **Stack:** Python 3.12, FastAPI, supabase-py, Render (one web service).
* **Scope caps:** 4 tables (≤8), 9 endpoints (≤10), roles unchanged.
* **Security:** secrets only in `.env`; service key used by the backend only; synthetic data only.
* **Agents:** built in DevAI Desktop and run by id via `app/llm.py` (`docs/devai-agents.md`). Numbers, trends and alerts
  are computed in code; the LLM never invents figures.

### Acceptance criteria (Given–When–Then)

#### Happy path

* **Given** a client linked to Telegram chat 111
  **When** `handle_message(111, "وزني ٨٢٫٥")` is called
  **Then** a measurement with `weight_kg = 82.5`, `source = 'telegram'`, today's date is saved
  and an Arabic confirmation is returned.
* **Given** a client whose weight changed by less than 0.3 kg over the last 3 weeks
  **When** `GET /summary/{id}` is called
  **Then** `alerts` contains `"stalled"` and `summary_ar` / `summary_en` are non-empty.
* **Given** a pending draft
  **When** `POST /drafts/{id}/approve`
  **Then** its status is `approved`, `sent_at` is set, and the response includes the
  client's `telegram_chat_id`.

#### Failure path

* **Given** an unknown chat id **When** a message arrives
  **Then** reply "Your account isn't linked yet. Ask your coach for a code." and save nothing.
* **Given** an unknown client or draft id **When** any endpoint is called **Then** 404.
* **Given** a draft that is already approved or rejected **When** approve/reject is called
  **Then** 409 and the draft is unchanged.

#### Boundary case

* Weight outside 30–300 kg or waist outside 40–200 cm is not saved (treated as not a measurement).
* "stalled" needs at least 3 weeks of history; with less data it is never raised.
* "no_checkin" is raised when the last entry is **exactly** 10 days old or older.
* A client with no measurements gets `facts` with nulls, no alerts, and a summary saying there is no data yet.

### Input / output / error contracts

| Endpoint | Input | Success |
| --- | --- | --- |
| `GET /health` | — | `200 {"status":"ok"}` |
| `GET /clients` | — | `200 [{id, name, telegram_chat_id}]` |
| `POST /telegram/message` | `{chat_id:int, text:str}` | `200 {reply:str}` |
| `GET /summary/{client_id}` | — | `200 {client_id, facts, alerts[], summary_ar, summary_en}` |
| `POST /draft/{client_id}` | — | `201 draft` |
| `GET /drafts?status=pending` | status filter | `200 [draft + client_name]` |
| `POST /drafts/{id}/approve` | — | `200 {draft, telegram_chat_id}` |
| `POST /drafts/{id}/reject` | — | `200 draft` |
| `POST /form-checks` | `{client_id, exercise, reps, errors, confidence}` | `201 form_check` |

Errors: `404` unknown id, `409` draft not pending, `422` invalid body. If an agent fails, template text is returned instead.

### Tests and oracle

* Parser and analyst rules are pure functions tested with hand-written expected values
  (the oracle is the rule text above, not the code's own output).
* The LLM is mocked in tests; no network or database is needed to run `pytest`.
