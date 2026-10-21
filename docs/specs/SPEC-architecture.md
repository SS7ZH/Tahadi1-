# SPEC-ARCH — M1 Architecture Deliverable

> This is the spec for **what the architecture deliverable must contain**, defined
> from the team's M1 requirements (see `docs/requirements/requirements.md`) and the
> course brief. It is the source of truth for the architecture documents it
> describes. The AI assists with writing; the team defines the intent.

## Goal

Produce the Milestone 1 architecture package for Tahadi: two genuinely distinct
architecture options, each with C4 Context and Container diagrams in Mermaid, a
weighted trade-off matrix, a cost model with verified published rates, a coupling
check, and ≥3 Architecture Decision Records (ADRs) — all aligned with the
requirements, the scope caps, and the non-goals in `CHARTER.md`.

## Scope / non-goals

* **In scope:** `docs/architecture/architecture.md`, `trade-off-matrix-architecture.md`,
  `cost-model.md`; ADRs in `docs/adr/ADR-000N-*.md`; updating
  `docs/traceability-matrix.md` and (if needed) `docs/risk-register.md`.
* **Out of scope for M1:** application code in `backend/` and `frontend/`, test
  suites, and any feature listed as a non-goal (payments, plans, medical advice,
  mobile, real-time chat, photos).

## Constraints

* **Stack (Option A chosen):** React + TypeScript (RTL, Arabic-first) → FastAPI
  (Python 3.12) → Supabase PostgreSQL (persistence only). Hosted on Render.
* **Scope caps (hard):** ≤6 screens, ≤10 API endpoints, ≤8 tables, 2 roles
  (`coach`, `client`), 1 deployment target.
* **Auth:** stateless JWT issued/validated by the FastAPI backend. **No** Supabase
  Auth, Storage, Realtime, or Edge Functions (per `README.md` and `requirements.md` §8).
  This resolves the inconsistency with `CHARTER.md` line 45 (which said "Supabase Auth").
* **Data:** synthetic only; no secrets; `.env` git-ignored with `.env.example` placeholders.
* **Security:** owner-scoped access (client sees only own data; coach sees only own
  clients); cross-owner access returns 403/404.
* **Repository rules:** follow `RULES.md` — write this SPEC first, use short-lived
  branches, commit raw AI output separately with `raw(ai):`, never squash/rebase a
  raw/fix pair, supersede ADRs instead of rewriting them.

## Acceptance criteria (Given–When–Then)

### Happy path

* **Given** the M1 requirements and scope caps,
* **When** the architecture package is produced,
* **Then** it contains exactly two distinct options each with C4 Context + Container
  diagrams in Mermaid, a completed weighted trade-off matrix with a recommended
  option, a cost model with published rates (date + source URL) and arithmetic, a
  coupling check, and at least 3 ADRs each naming a rejected alternative, an accepted
  downside, and related requirement IDs.

### Failure path

* **Given** an architecture that would exceed a scope cap or violate a non-goal,
* **When** it is proposed,
* **Then** it must be rejected or explicitly flagged as requiring a scope-change ADR
  (RULES.md §8).

### Boundary case

* **Given** the chosen option (A),
* **When** the team must name its accepted downside,
* **Then** the ADR and trade-off matrix state it explicitly (e.g. "we run two
  services on Render and must manage the free-tier sleep / cold start").

## Input / output / error contracts

* **Input:** requirements (FR-1..FR-15, NFR-1..NFR-9, screens/endpoints/roles),
  `CHARTER.md` scope, `README.md` stack, published pricing.
* **Output (success):** the files listed under *In scope* above, committed as
  `raw(ai):` on a short-lived branch, traceability matrix updated with real ADR IDs.
* **Error states:** any option that breaks a cap or a non-goal is documented as a
  rejection reason, not left unaddressed.

## Tests / verification (independent oracle)

* **Where:** this is documentation; correctness is judged against the M1 rubric:
  (1) two distinct diagrammed options, (2) computed cost model with verified rates,
  (3) coupling check + residual-risk explanation, (4) ≥3 lint-passing ADRs,
  (5) requirements and traceability integrated, no orphan requirements,
  (6) accurate AI-use disclosure.
* **Independent oracle:** verify each claim against the primary sources (requirements
  doc, CHARTER, README, official pricing pages) rather than trusting the author —
  i.e. recompute the cost arithmetic by hand and cross-check the published rate URL.
