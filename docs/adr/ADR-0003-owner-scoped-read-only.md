# ADR-0003 — Enforce owner-scoped access; clients are read-only

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* FR-5 (coach views client history), FR-9 (client read-only own), FR-11 (client cannot
  create/update/delete), FR-12 (restrict every access to resource owner)
* NFR-3 (authorization, 403/404)

### Context

The core integrity rule of Tahadi is that a client sees **only their own** measurements
and a coach sees **only their own clients**, and that clients can never create, update,
or delete a measurement (US-11, FR-9, FR-11, FR-12). With the backend owning all data
access (ADR-0001), the natural place to enforce this is a single authorization layer in
FastAPI rather than scattered client checks.

### Decision

We will enforce owner-scoping in the FastAPI backend on every data endpoint: the
logged-in role and the requested resource owner determine access, and any cross-owner
read or write returns **403/404**. The client-facing data endpoints are **read-only** —
there is no client write path for measurements.

### Rejected alternative

* **Option:** Enforce ownership in the client only, or rely on Supabase Row Level
  Security rules.
* **Why rejected:** Client-only checks are trivially bypassable and untestable at the
  server; RLS with the "no Supabase Auth" decision would require managing tokens and
  policies we cannot easily test. A backend check is authoritative and e2e-testable.

### Accepted downside

* **Downside:** Every data endpoint must explicitly carry an owner-scoping check, which
  is repetitive and easy to forget on a new endpoint.
* **Mitigation / acceptance:** Put the check in a shared FastAPI dependency (e.g. a
  `require_owner` dependency) so new endpoints reuse it; add e2e tests that attempt
  cross-owner reads and assert 403/404 (NFR-3).

### Consequences

* `/api/me/measurements` returns only the caller's measurements, oldest first (FR-9).
* `/api/clients/{id}/measurements` and `/api/threads/{id}` verify the caller owns the
  resource before returning (FR-12).
* A client has no endpoint that creates, updates, or deletes a measurement (FR-11).

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md`
* `ADR-0002-backend-jwt-auth.md`

### How this gets verified (optional)

* e2e test: client A requests client B's measurement list → 403/404.
* e2e test: a client POSTs to a measurement create endpoint → 403/404 (no write path).
