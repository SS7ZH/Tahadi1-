# ADR-0001 — Choose three-tier (Option A) over two-tier (Option B)

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* FR-2 (authenticate and issue JWT), FR-12 (owner-scoped access)
* NFR-3 (authorization, 403/404), NFR-6 (maintainability), NFR-7 (scope compliance)

### Context

Tahadi needs to record coach-entered body measurements, give clients a read-only
view of their own progress, and support a coached Q&A thread — all within 6
screens, 10 endpoints, 8 tables, 2 roles, and one deployment target. We considered
two genuinely distinct architectures: a three-tier option where a FastAPI backend
sits between the React frontend and Supabase (Option A), and a two-tier option where
the React frontend talks directly to Supabase via its Auth + PostgREST + Row Level
Security (Option B). Option B removes an entire layer to build and host, but moves
authorization into Postgres policies and client logic.

### Decision

We will use **Option A: React + TypeScript → FastAPI → Supabase PostgreSQL**, hosting
frontend and backend on Render. We chose it because it centralizes authentication,
authorization (owner-scoping), and business logic in one backend we can unit-test and
explain, and because it decouples the React UI from the SQL schema.

### Rejected alternative

* **Option:** Option B — React → Supabase directly (Supabase Auth + PostgREST + RLS).
* **Why rejected:** Authorization and the client-read-only rule would be split across
  Row Level Security policies and client code, which is harder to test, harder to
  explain to an assessor, and risks a cross-owner data leak if a policy or check is
  wrong (NFR-3, FR-12). It also couples the client directly to the schema.

### Accepted downside

* **Downside:** We run two services on Render (a static frontend and a FastAPI web
  service) rather than one, and the backend web service sleeps after ~15 minutes of
  inactivity, causing a cold start.
* **Mitigation / acceptance:** Keep within the free tier (one always-on web service
  is inside the 750 free instance hours); document cold-start latency (R-004) and
  warm up the app before a demo; if budget allows, upgrade the backend to `1c-2g`.

### Consequences

* FastAPI owns auth, authorization, validation, and the ≤10 endpoints; Supabase is
  used only as a SQL store (no Auth/Storage/Realtime).
* The frontend never issues SQL, so schema changes that keep the API contract stable
  need no frontend change (satisfies NFR-6).
* Cost on the all-free tier is $0/month; see `cost-model.md`.

### Related ADRs

* `ADR-0002-backend-jwt-auth.md` (how auth is implemented)
* `ADR-0003-owner-scoped-read-only.md` (how authorization is enforced)

### How this gets verified (optional)

* Endpoint count stays ≤10 and roles = 2, checked by a CI test (NFR-7).
* A coupling check in the architecture review confirms no client-to-DB SQL path.
