# ADR-0009 — Scope change: two deployment targets (Vercel frontend, Render backend)

### Status

* **Proposed** (becomes Accepted once both team members approve the PR)
* **Scope change:** raises the *Deployment targets* cap from **1** to **2** (`RULES.md` §8)
* **Supersedes (deployment only):** the "frontend and backend on Render" part of
  `ADR-0001-choose-three-tier-option-a.md`. The three-tier choice itself (React → FastAPI →
  Supabase) still stands.

### Date

2026-11-09

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Related requirement IDs

* NFR-5 (availability), NFR-7 (scope compliance), FR-14 / FR-15 (other caps unchanged)

### Context

M1 capped the project at one deployment target and put both the static frontend and the
FastAPI backend on Render (`ADR-0001`, `CHARTER.md`). The agent concept (`ADR-0007`) puts
the React frontend on Vercel:

* The form-check agent runs MediaPipe Pose in the browser, so the frontend ships larger
  static assets (the pose model and WebAssembly files). Vercel serves them from a CDN
  with preview deploys per branch, which helps the frontend owner test camera features
  over HTTPS.
* The backend, the Telegram bot route and the agents stay on Render as one web service.

This breaks the M1 cap of one deployment target, so it needs a scope-change ADR.

### Decision

* **Frontend:** React on **Vercel** (Hobby plan).
* **Backend:** FastAPI on **Render** (one web service). The Telegram bot runs as a
  webhook route inside this service, not as a separate deployment.
* **Data:** Supabase stays the managed database (a service, not a deployment target).
* New cap: **Deployment targets ≤ 2.** All other caps are unchanged
  (screens ≤ 6, endpoints ≤ 10, tables ≤ 8, roles = 2).

### Rejected alternative

* **Option:** Keep both on Render (static site + web service), staying at one target.
* **Why rejected:** It works, but the frontend owner gets no per-branch preview URLs and
  the camera/MediaPipe feature is easier to test on Vercel's HTTPS previews. The team
  judged that worth one extra target.

### Accepted downside

* **Downside:** Two platforms to configure, two sets of environment variables, and CORS
  must allow the Vercel domain.
* **Mitigation / acceptance:** Backend CORS reads `FRONTEND_URL`; the README lists both
  platforms' settings; the frontend only needs the public backend URL and the Supabase
  anon key.
* **Downside:** Vercel's Hobby plan is for non-commercial use.
* **Mitigation / acceptance:** This is a course project; a paid plan or a move back to
  Render is needed before any commercial use. Check current Vercel pricing and add it to
  `docs/architecture/cost-model.md`.

### Consequences

* `CHARTER.md`, `README.md` and `docs/architecture/architecture.md` must show the new
  cap (2) and the Vercel + Render split.
* Risk register: `R-017` (cross-platform CORS/config drift). Traceability: NFR-7 now
  also references this ADR.

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md` (deployment part superseded)
* `ADR-0007-pivot-to-agent-assisted-coaching.md`
* `ADR-0008-telegram-instead-of-whatsapp.md`

### How this gets verified

* The Vercel frontend loads and calls `GET /health` on the Render backend without a
  CORS error.
* A count of deployed services shows exactly 2 (Vercel project + Render web service).
