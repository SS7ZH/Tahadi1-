# Tahadi — تحدي

Tahadi (تحدي, "challenge") is an Arabic-first, right-to-left (RTL) web application
for fitness coaches and their clients. Coaches record client body measurements
(wrap, skinfold, weight, etc.) and clients log in to view their own progress
(read-only) and send questions to their coach.

> **Milestone 1** — Requirements and architecture. This repository currently holds
> the project charter, requirements, architecture records, risk register,
> traceability, and templates. Application code arrives in later milestones.

## Project at a glance

| Attribute | Value |
| --- | --- |
| Project type | App (web application) |
| Team size | 2 students |
| Primary language | Arabic (RTL-first) |
| Frontend | React (TypeScript) |
| Backend | FastAPI (Python 3.12) |
| Database | Supabase — managed PostgreSQL only (no Supabase Auth/Storage/Realtime) |
| Hosting | Render (both frontend and backend) |
| Roles | `coach`, `client` (only; no admin — coaches are seeded by a script) |
| Data | Synthetic/generated only. No real personal data, no secrets in the repo |

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
| Deployment targets | 1 |

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
* **Database:** Supabase PostgreSQL (external, managed). Used only as a SQL
  database — no Auth, Storage, Realtime, or Edge Functions from Supabase.
* **Auth:** Handled by the backend (JWT). Supabase is not used for auth.
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
