# Risk Register — Tahadi (تحدي)

> Columns: **ID, risk, likelihood, impact, measurable alert threshold, mitigation,
> owner.** Likelihood and impact are rated **Low / Medium / High**. A risk score
> (L×I) can be added for prioritization. Review this register each milestone.

## Ratings

* **Likelihood:** Low / Medium / High
* **Impact:** Low / Medium / High
* **Score:** e.g. Medium×High = HIGH attention.

## Register

| ID | Risk | Likelihood | Impact | Measurable alert threshold | Mitigation | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| R-001 | Scope creep — feature added that breaks a cap (≤6 screens / ≤10 endpoints / ≤8 tables / 2 roles) | Medium | High | Endpoint count > 10, screen count > 6, table count > 8, or a 3rd role introduced | Enforce cap in CI (a test counts endpoints/screens/tables); any change needs a scope-change ADR; review in code review | Team |
| R-002 | Auth/authorization bug lets a client read another client's data | Medium | High | Any cross-owner read/write returns 200 instead of 403/404 in e2e tests | Owner-scoping enforced in every query; e2e tests for cross-owner access; code review | Backend lead |
| R-003 | Real personal data or a secret accidentally committed | Low | High | Secret scanner flags a key/pattern; any non-synthetic value found in data files | `.env` git-ignored; `.env.example` placeholders only; pre-commit secret scan; only synthetic fixtures | Team |
| R-004 | Render free tier sleeps/inactivity → slow first load or downtime during demo | Medium | Medium | Cold-start latency > 500 ms after idle; uptime < 99% | Keep on a paid/tier if budget allows; document cold start; ping health endpoint; warm-up script | Team |
| R-005 | Supabase database connection/limits (free tier) | Medium | Medium | DB pool exhaustion / connection errors under load; storage limit hit | Use single instance; limit connections; monitor error rate; know tier limits | Backend lead |
| R-006 | Synthetic data doesn't reflect real usage → poor demo / unrealistic metrics | Medium | Low | Data appears obviously fake, or missing edge cases | Use a defined generator with realistic ranges and edge cases; cover empty state | Team |
| R-007 | Arabic RTL layout breaks (overflow, misalignment) | Medium | Medium | A screen has horizontal overflow or left-aligned text in RTL | RTL baseline check; set `dir=rtl` + `lang=ar`; visual regression on key screens | Frontend lead |
| R-008 | Team of 2 falls behind schedule (scope too large) | Medium | Medium | Milestone tasks slip past planned date | Keep to the hard caps; break work into SPECs; short-lived branches; review test-first | Team |
| R-009 | AI use not clearly disclosed → academic integrity concern | Low | High | Dishonest/missing disclosure in `AI_USE_DISCLOSURE.md` | Follow `RULES.md`; commit raw/fix separately; every AI contribution disclosed; team signs | Team |
| R-010 | Dependency/licensing or library breakage | Low | Medium | Build fails on a dependency update | Pin versions; lockfiles committed; CI build on push | Team |
| R-011 | Database schema grows beyond 8 tables or is hard to change | Medium | Medium | Table count > 8; adding a metric requires many file changes | Keep schema narrow; metric catalogue table; add metrics via config; NFR-6 monitor | Backend lead |
| R-012 | Messaging thread ownership model confuses coach/client boundaries | Medium | Medium | A message from the wrong author appears; thread access wrong | Thread has `client_id` + `coach_id`; owner-scoped queries; tests for author checks | Backend lead |

## Review cadence

* Reviewed after each milestone.
* Update likelihood/impact when evidence changes.
* Add a row when a new risk is identified.

## M1 architecture review notes

* **Top three risks for the M1 review:** R-002 (auth/authorization leak),
  R-003 (secret/real data committed), R-004 (Render free tier sleeps → demo
  availability). All three have owners and measurable thresholds above.
* **Coherence break resolved:** `CHARTER.md` line 45 said "Authentication through
  Supabase Auth," which conflicted with `README.md` and `requirements.md` §8 (both say
  backend-managed JWT, Supabase is SQL only). Resolved in `ADR-0002` (backend JWT);
  `README.md`/`requirements.md` were treated as authoritative.
* **Residual risk the coupling detector cannot reveal:** the component diagram shows
  topology (which component calls which) but not the runtime data-flow invariant that
  every measurement and message is scoped to the logged-in owner. That invariant is
  enforced by owner-scoping logic in FastAPI (`ADR-0003`), not by the topology, so a
  static coupling check cannot flag it. Only end-to-end tests that attempt cross-owner
  reads (NFR-3) prove it holds. Tracked under R-002; owned by the backend lead.
* **Architecture accepted downside:** two services on Render; the backend web service
  sleeps after ~15 min of inactivity (cold start). See `architecture.md` §5, `R-004`,
  and `cost-model.md` §5.
* **Chosen option:** Option A (React → FastAPI → Supabase), per `ADR-0001`.
  Option B (React → Supabase directly) was rejected; see `trade-off-matrix-architecture.md`.
