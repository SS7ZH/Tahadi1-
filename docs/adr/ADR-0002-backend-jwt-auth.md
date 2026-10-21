# ADR-0002 — Manage authentication in the backend with stateless JWT

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* FR-1 (sign up, choose role), FR-2 (authenticate, issue JWT), FR-7 (sign up client),
  FR-8 (client can sign in once assigned), NFR-3 (authorization)

### Context

Tahadi needs a small, testable auth model within the endpoint cap. The `README.md`
and `docs/requirements/requirements.md` §8 both state that **Supabase is used only as
a SQL database** and that auth is handled by the backend with a stateless JWT.
`CHARTER.md` line 45 instead said "Authentication through Supabase Auth," which
conflicted with those two documents. We treat `README.md` / `requirements.md` as
authoritative because they are tied to the requirements and standardized on the
Stack table, and reconciled the line by adopting backend-managed JWT.

### Decision

We will implement authentication in the **FastAPI backend using stateless JWT**: a
sign-up and sign-in endpoint validate credentials, issue a JWT, and the role is
chosen at sign-up. No Supabase Auth is used. This keeps auth code in one place, uses
no extra session table, and lets us stay within the 8-table cap.

### Rejected alternative

* **Option:** Use Supabase Auth (the two-tier Option B auth path) for identity.
* **Why rejected:** It would split identity across a managed service and require us to
  verify Supabase tokens rather than our own JWTs, complicates the "no Supabase Auth"
  scope statement, and makes the auth behaviour harder to test and explain. A backend
  JWT also keeps role selection and the assigned-to-coach rule in one place.

### Accepted downside

* **Downside:** We implement and own the password/JWT handling ourselves (hashing,
  expiry, secret rotation), which is more code than letting Supabase do it, and the
  login secret must be rotated and never committed (NFR-9).
* **Mitigation / acceptance:** Use a well-known JWT library and `passlib`/`bcrypt`;
  set an expiry; keep the signing secret in `.env` (git-ignored) with a placeholder in
  `.env.example`; add a secret scan to CI (R-003).

### Consequences

* Two endpoints (`/api/auth/signup`, `/api/auth/signin`) are allocated from the ≤10 cap.
* No session table is needed, reserving table slots for measurements and threads.
* The backend validates the JWT on every protected endpoint and applies owner-scoping
  (see ADR-0003).

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md`
* `ADR-0003-owner-scoped-read-only.md`

### How this gets verified (optional)

* An e2e test signs in and gets a JWT; a request with an invalid/expired token returns 401.
* The sign-up endpoint returns 409 on duplicate email and 422 on invalid input (UC-1).
