# Trade-off Matrix — Architecture Options

> This compares the two viable options and records the decision in `docs/adr/`.
> The decision is recorded in **ADR-0001**.

## Decision context

* **Topic / decision:** Three-tier (React → FastAPI → Supabase) vs two-tier
  (React → Supabase directly) for Tahadi.
* **Related requirements:** FR-2, FR-12, NFR-3 (auth/authorization), NFR-6
  (maintainability), NFR-7 (scope compliance); also FR-1..FR-15 and NFR-1..NFR-9.
* **Date:** 2026-10-21
* **Deciders:** Team (Muhaned + Saeed)

## Options

* **Option A:** Three-tier — React + TypeScript SPA → FastAPI backend → Supabase
  PostgreSQL. Centralizes auth, authorization, and business logic in the backend.
* **Option B:** Two-tier — React + TypeScript SPA → Supabase directly, using
  Supabase Auth + PostgREST + Row Level Security for auth and authorization.

## Criteria (weighted)

Assign a weight from 0–5 per criterion (5 = most important). Score each option 1–5.
Weighted score = weight × score.

| Criterion | Weight | Why it matters | Option A score | Option B score |
| --- | --- | --- | --- | --- |
| Build effort (team of 2) | 5 | Small team; must ship in scope | 3 | 4 |
| Deployment simplicity (1 target) | 5 | One deploy target on Render | 3 | 5 |
| Cost | 4 | Free/low-cost tiers preferred | 3 | 4 |
| Performance / latency | 3 | History loads < 500 ms | 4 | 4 |
| RTL / UX fit | 4 | Arabic-first experience | 5 | 4 |
| Maintainability | 4 | Course project; extensible | 4 | 2 |
| Risk (data/auth) | 5 | Owner-scoping must be safe (NFR-3, pass condition) | 4 | 2 |
| **Total** | | | **110** | **107** |

## Weighted totals

* **Option A total:** 110
* **Option B total:** 107
* **Recommended:** **Option A**

## Justification

Option A loses on build effort and deployment simplicity (it needs a backend and
two Render services), but wins decisively on the criteria that matter most for this
course: maintainability and, above all, **risk (data/auth)**. Owner-scoping and the
client-read-only rule are enforced and unit-tested in one place (FastAPI) rather
than split across client logic and Row Level Security policies that are harder to
test and to explain. Option A also keeps the React frontend decoupled from the SQL
schema, so adding a metric touches only the API + schema (NFR-6).

## Trade-offs accepted

Accepted downside of the chosen option (explicitly acknowledge what we lose):

* **We run two services on Render** (a static frontend and a FastAPI web service)
  instead of one, and we must keep both reachable. We accept the extra deployment
  surface and the free-tier sleep / cold-start on the backend, because the backend
  gives us testable authorization and a stable API contract for the frontend.

## Rejected option — why not

* **Option B** was rejected because: it moves authorization into Supabase RLS + client
  logic, which is harder to test, harder to explain to an assessor, and risks
  cross-owner data exposure if a policy or client check is wrong (NFR-3, FR-12). It
  also couples the client directly to the schema, hurting maintainability.

## Related ADR

* `docs/adr/ADR-0001-choose-three-tier-option-a.md` — "Status: Accepted"
