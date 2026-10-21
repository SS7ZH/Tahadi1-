# Traceability Matrix — Tahadi (تحدي)

> Requirement → story/scenario → ADR → risk → code → test. Use this to prove every
> requirement is designed, decided, de-risked, implemented, and tested. Fill it in
> per milestone. "—" (not yet) is a legitimate placeholder for later milestones.

## How to read

* **Requirement:** FR-n / NFR-n (from `docs/requirements/requirements.md`).
* **Story / scenario:** US-n / S-n / UC-n (from `requirements.md`).
* **ADR:** the ADR that decided how it's built (or "—").
* **Risk:** the risk ID(s) that threaten it (from `docs/risk-register.md`).
* **Code:** file(s)/module that implement it (populated later).
* **Test:** test file(s)/spec that verify it (populated later).

## Matrix

| Req | Story / scenario | ADR | Risk | Code | Test |
| --- | --- | --- | --- | --- | --- |
| FR-1 (sign up, choose role) | US-1, UC-1 | `ADR-0002` | R-002 | — | — |
| FR-2 (authenticate, issue JWT) | US-2, US-8, UC-2 | `ADR-0002` | R-002 | — | — |
| FR-3 (coach adds a client) | US-3, UC-3 | `ADR-0003` | R-002 | — | — |
| FR-4 (coach records a measurement) | US-4, UC-4 | `ADR-0001`, `ADR-0003` | R-011 | — | — |
| FR-5 (coach views measurement history) | US-5, UC-4 | `ADR-0001`, `ADR-0003` | R-011, R-002 | — | — |
| FR-6 (coach replies to a question) | US-6, UC-7 | `ADR-0004` | R-012 | — | — |
| FR-7 (user signs up as client) | US-7, UC-1 | `ADR-0002` | R-002 | — | — |
| FR-8 (client signs in once assigned) | US-8, UC-2 F2 | `ADR-0002`, `ADR-0003` | R-002, R-012 | — | — |
| FR-9 (client read-only own progress) | US-9, UC-5 | `ADR-0003` | R-002 | — | — |
| FR-10 (client sends a question) | US-10, UC-6 | `ADR-0004` | R-012 | — | — |
| FR-11 (client cannot create/update/delete) | US-11, S4 | `ADR-0003` | R-002 | — | — |
| FR-12 (restrict access to resource owner) | US-11, NFR-3 | `ADR-0003` | R-002 | — | — |
| FR-13 (synthetic data only) | — (scope) | `ADR-0006` | R-003 | — | — |
| FR-14 (≤10 API endpoints) | — (scope) | `ADR-0001` | R-001 | — | — |
| FR-15 (≤6 screens, 2 roles) | — (scope) | `ADR-0001`, `ADR-0005` | R-001 | — | — |
| NFR-1 (RTL/UX) | S2, S3 | `ADR-0005` | R-007 | — | — |
| NFR-2 (perf < 500 ms) | — | `ADR-0001` | R-004 | — | — |
| NFR-3 (authorization 403/404) | S4, UC-2 F2 | `ADR-0003` | R-002 | — | — |
| NFR-4 (reject real personal data) | — | `ADR-0006` | R-003 | — | — |
| NFR-5 (availability ≥99%) | — | `ADR-0001` | R-004 | — | — |
| NFR-6 (maintainability ≤2 files) | — | `ADR-0001`, `ADR-0002` | R-011 | — | — |
| NFR-7 (scope compliance) | — | `ADR-0001`, `ADR-0005` | R-001 | — | — |
| NFR-8 (accessibility WCAG AA) | — | `ADR-0005` | R-007 | — | — |
| NFR-9 (secret/config hygiene) | — | `ADR-0006` | R-003 | — | — |

## Coverage check

- [x] Every FR-n appears at least once (FR-1..FR-15).
- [x] Every NFR-n appears at least once (NFR-1..NFR-9).
- [x] Every primary risk (High score) is tied to at least one requirement + mitigation.
- [x] Placeholder `ADR-000x` references replaced with real ADR IDs (`ADR-0001`..`ADR-0006`).
- [ ] Code and Test columns to be populated in M2 (vertical slice + tests).
