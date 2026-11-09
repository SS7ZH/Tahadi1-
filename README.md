# Tahadi — تحدي

Tahadi (تحدي, "challenge") is an Arabic-first team of AI agents that helps fitness
coaches track clients, check exercise form and reply faster. Clients check in through
a Telegram bot, agents turn those messages into measurements, flag stalled or silent
clients and draft replies, and **nothing reaches a client without the coach's approval**.

> **Concept change (2026-11-09):** the original M1 design (in-app Q&A thread) was
> replaced by the agent concept. See `docs/adr/ADR-0007-pivot-to-agent-assisted-coaching.md`
> and `docs/adr/ADR-0008-telegram-instead-of-whatsapp.md`. The M1 requirements below are
> kept for history and are being updated to match.

### The agents

| # | Agent | Reads | Produces | Status |
| --- | --- | --- | --- | --- |
| 1 | Intake | Telegram messages | Saved measurements | Building |
| 2 | Form check | Squat video, in the browser (MediaPipe) | Rep count and form errors | Building (frontend) |
| 3 | Progress photos | Check-in photos | Aligned comparison | Out of scope (photo non-goal) |
| 4 | Progress analyst | Measurement history | Trends, alerts, bilingual summary | Building |
| 5 | Coach assistant | Agent results | Draft replies for coach approval | Building |

Code decides (regex parsing, trend rules, joint-angle rules); the language model only
explains those results in friendly Arabic or English.

## Project at a glance

| Attribute | Value |
| --- | --- |
| Project type | App (web application) |
| Team size | 2 students |
| Primary language | Arabic (RTL-first) |
| Frontend | React (TypeScript) on Vercel; MediaPipe Pose in the browser |
| Backend | FastAPI (Python 3.12) |
| Database | Supabase — managed PostgreSQL (data store) + Supabase Auth (authentication) |
| Hosting | Render (backend), Vercel (frontend) |
| Messaging | Telegram Bot API (ADR-0008) |
| Agents | FastAPI services; LLM behind one swappable wrapper |
| Roles | `coach`, `client` (only; no admin — coaches are seeded by a script) |
| Data | Synthetic/generated only. No real personal data, no secrets in the repo |

## Team

| Member | Role / responsibility |
| --- | --- |
| Saeed Alzahrani | Team member 1 — backend, database, seeding, architecture |
| Muhanad Alhilal | Team member 2 — frontend, RTL UI, accessibility |

## Problem statement

Fitness coaching requires recurring, comparable body-measurement records. Coaches
often track clients in spreadsheets or paper notes, which is error-prone and gives
clients no visibility into their own progress. Tahadi gives coaches a structured,
synthetic-data-safe way to record measurements and gives clients a read-only view
of their progress plus a direct channel to ask their coach a question.

## Scope

* In scope: coach measurement entry, client read-only progress view, coach–client
  messaging (question + reply), seeded coach accounts, synthetic data generator.
* Out of scope (non-goals): payments, workout/nutrition plans, medical advice,
  mobile app, real-time chat, photo upload. See `CHARTER.md` and the limits below.

### Hard scope limits

| Limit | Cap |
| --- | --- |
| Screens | 6 |
| API endpoints | 10 |
| Database tables | 8 |
| Roles | 2 |
| Deployment targets | 2 (raised from 1 by ADR-0009) |

These limits are enforced by the team and reviewed in `docs/risk-register.md` and
`docs/traceability-matrix.md`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `README.md` | Project overview and repository map (this file) |
| `CHARTER.md` | Project charter: stakeholders, scope, non-goals |
| `RULES.md` | Team rules for AI-assisted development |
| `AI_USE_DISCLOSURE.md` | Per-area AI contribution disclosure and provenance |
| `.gitignore` | Ignored files (Python, Node, secrets, OS/editor) |
| `.env.example` | Placeholder environment variables (never real secrets) |
| `backend/` | FastAPI application (placeholder; code in later milestones) |
| `frontend/` | React application (placeholder; code in later milestones) |
| `docs/requirements/` | Personas, stories, use cases, FRs, NFRs, correction log |
| `docs/architecture/` | Trade-off matrix and cost model templates |
| `docs/adr/` | Architecture Decision Records (see `ADR-TEMPLATE.md`) |
| `docs/specs/` | Given–When–Then specification template |
| `docs/risk-register.md` | Risk register with measurable alert thresholds |
| `docs/traceability-matrix.md` | Requirement → ADR → risk → code → test traceability |

## Roles

| Role | Intended use |
| --- | --- |
| `coach` | Authenticate; create/read measurements for their own clients; reply to client questions |
| `client` | Authenticate; view only their own measurements/progress; send a question to their coach |

There is **no admin role**. Coach accounts are created by an idempotent seeding
script (see RULES/requirements for the expected behavior of the seed script).

## Stack & data

* **Frontend:** React + TypeScript, RTL (`dir="rtl"`, `lang="ar"`), Arabic UI copy.
* **Backend:** FastAPI, Pydantic models, OpenAPI docs.
* **Database:** Supabase — managed PostgreSQL as the data store, plus Supabase
  Auth for authentication.
* **Auth:** Supabase Auth signs in users and issues JWTs; the FastAPI backend
  verifies the JWT and enforces role (coach / client) and ownership checks.
* **Synthetic data:** A data generator produces fictional coach/client/measurement
  records. No real personal data is ever committed.

## Development conventions

Before prompting an AI tool, write a `SPEC.md` documenting the expected behavior
and acceptance criteria. Commit raw AI output separately from human fixes. See
`RULES.md` for the full policy.

## Documentation order

1. `docs/requirements/requirements.md` — what we build and why.
2. `docs/architecture/` — how we chose the architecture (trade-offs, cost).
3. `docs/adr/ADR-*.md` — accepted architecture decisions.
4. `docs/specs/SPEC-*.md` — Given–When–Then acceptance criteria per feature.
5. `docs/risk-register.md` — what could go wrong and how we measure it.

## License

See `CHARTER.md` / `AI_USE_DISCLOSURE.md` for data and licensing statements.
Synthetic data only; no real personal data.
