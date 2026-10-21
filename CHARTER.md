# Project Charter — Tahadi (تحدي)

## Document control

| Field | Value |
| --- | --- |
| Project name | Tahadi (تحدي / "challenge") |
| Version | 0.1.0 |
| Status | Draft — Milestone 1 (requirements & architecture) |
| Date | 2026-10-21 |
| Owner | Team members (see below) |

## Team

| Role | Name (placeholder) | Responsibility |
| --- | --- | --- |
| Team member 1 | **[Your Name Here]** | e.g. backend + DB + seeding, architecture |
| Team member 2 | **[Your Name Here]** | e.g. frontend + RTL UI + accessibility |

> Replace the bracketed placeholders with the real names of the two team members
> (and their student IDs / section as required by your course) before submission.
> Each member must also sign the ownership statement in `AI_USE_DISCLOSURE.md`.

## Stakeholders

| Stakeholder | Need |
| --- | --- |
| Fitness coach (primary) | Record client body measurements quickly and reliably; reply to client questions. |
| Client (primary) | View their own progress read-only; ask their coach a question. |
| Student team (2) | Deliver an approved-scope App for the software engineering course. |
| Course instructor / assessor | Verify scope compliance, traceability, traceable AI use, and quality. |

## Problem statement

Fitness coaches need a reliable way to record and compare client body measurements
over time. Common practice — spreadsheets or handwritten notes — is error-prone
and offers clients no visibility into their own trend. Tahadi replaces that with a
structured web app where coaches record measurements and clients see their progress
and can ask their coach a question.

## Product scope

### In scope (this project)

* Coach authenticates and manages measurements for **their own** clients.
* Client authenticates and views **only their own** measurements and progress.
* Client sends a question to their coach; coach replies (one Q&A thread per client).
* Coach accounts are seeded by an idempotent script (no admin role).
* Synthetic data generator for coaches, clients, and measurements.
* Arabic-first, RTL UI.
* Deployed to a single target (Render) with Supabase PostgreSQL as the store.

### Out of scope (non-goals)

The following are **explicitly not** part of this project:

* Payments, billing, subscriptions, or monetization.
* Workout or nutrition plans / program builder.
* Medical advice, diagnoses, or anything clinical.
* Native mobile application.
* Real-time chat / push notifications (messaging is a question–reply thread).
* Photo upload or file attachments.
* Admin role or multi-tenant back-office.
* Integration with third-party wearables, APIs, or social logins.

Any of the above that appears later must first be justified and run through the
scope-change process (see `RULES.md` and `docs/adr/ADR-TEMPLATE.md`).

## Hard scope limits

| Dimension | Cap | How we stay within it |
| --- | --- | --- |
| Screens | 6 | Screen inventory in `docs/requirements/requirements.md` |
| API endpoints | 10 | Endpoint inventory in `docs/requirements/requirements.md` |
| Database tables | 8 | Schema is constrained; see ADRs |
| Roles | 2 | `coach` and `client` only |
| Deployment targets | 1 | Render (frontend + backend) |

## Success criteria (Milestone 1)

* Requirements documented as personas, scenarios, user stories, use cases (with
  failure paths), FR-n, and NFRs as quality-attribute scenarios.
* Two architecture options compared in a trade-off matrix; one recorded as an ADR.
* A cost model with published rates, arithmetic, and sensitivity scenarios.
* Risk register and traceability matrix populated.
* AI usage disclosed per area with provenance.

## Related documents

* `RULES.md` — team rules for AI-assisted development.
* `docs/specs/SPEC-TEMPLATE.md` — Given–When–Then acceptance criteria.
* `docs/adr/ADR-TEMPLATE.md` — how decisions are recorded.
