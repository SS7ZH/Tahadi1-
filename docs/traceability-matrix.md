# Traceability Matrix — Tahadi (تحدي)

> Requirement → story/scenario → ADR → risk → code → test. Use this to prove every
> requirement is designed, decided, de-risked, implemented, and tested. Fill it in
> per milestone. "—" (not yet) is a legitimate placeholder for later milestones.

## How to read

* **Requirement:** FR-n / NFR-n (from `docs/requirements/requirements.md`).
* **Story / scenario:** US-n / S-n (from `requirements.md`).
* **ADR:** the ADR that decided how it's built (or "—").
* **Risk:** the risk ID(s) that threaten it (from `docs/risk-register.md`).
* **Code:** file(s)/module that implement it (populated later).
* **Test:** test file(s)/spec that verify it (populated later).

## Matrix

| Req | Story / scenario | ADR | Risk | Code | Test |
| --- | --- | --- | --- | --- | --- |
| FR-1 (auth, JWT) | US-1, US-5 | `ADR-0001-*` | R-002 | — | — |
| FR-2 (coach creates measurement) | US-2 / S1 | `ADR-0002-*` | R-011 | — | — |
| FR-3 (measurement has date + value) | S1 | `ADR-0002-*` | R-011 | — | — |
| FR-4 (coach lists client measurements) | US-3 | `ADR-0002-*` | R-011 | — | — |
| FR-5 (client read-only own) | US-6 / S2 | `ADR-0003-*` | R-002 | — | — |
| FR-6 (client sends question) | US-7 / S3 | `ADR-0004-*` | R-012 | — | — |
| FR-7 (coach replies) | US-4 | `ADR-0004-*` | R-012 | — | — |
| FR-8 (client can't edit) | S4 | `ADR-0003-*` | R-002 | — | — |
| FR-9 (seed coaches) | UC-5 | `ADR-0005-*` | R-001 | — | — |
| FR-10 (synthetic data only) | — | `ADR-0006-*` | R-003 | — | — |
| FR-11 (≤10 endpoints) | — | `ADR-0001-*` | R-001 | — | — |
| FR-12 (≤8 tables, 2 roles) | — | `ADR-0002-*` | R-001 | — | — |
| NFR-1 (RTL) | S2, S3 | `ADR-0007-*` | R-007 | — | — |
| NFR-2 (perf < 500 ms) | — | `ADR-0001-*` | R-004 | — | — |
| NFR-3 (authorization) | S4, UC-2 F2 | `ADR-0003-*` | R-002 | — | — |
| NFR-4 (no real data) | — | `ADR-0006-*` | R-003 | — | — |
| NFR-5 (availability) | — | `ADR-0001-*` | R-004 | — | — |
| NFR-6 (maintainability) | — | `ADR-0002-*` | R-011 | — | — |
| NFR-7 (scope compliance) | — | `ADR-0001-*` | R-001 | — | — |
| NFR-8 (accessibility) | — | `ADR-0007-*` | R-007 | — | — |
| NFR-9 (config/secret hygiene) | — | `ADR-0006-*` | R-003 | — | — |

## Coverage check

- [ ] Every FR-n appears at least once.
- [ ] Every NFR-n appears at least once.
- [ ] Every primary risk (High score) is tied to at least one requirement + mitigation.
- [ ] Placeholder ADR ids will be replaced once ADRs are actually created
      (currently referencing intended ADR-000x numbers).
