# ADR-0006 — Synthetic data only; no secrets or real personal data

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* FR-13 (persist only synthetic data; no real personal data), NFR-4 (reject real
  personal identifiers), NFR-9 (secret/config hygiene)
* R-003 (real data/secret committed), R-009 (AI-use disclosure), R-010 (dependencies)

### Context

The repository may contain no real personal data and no secrets. All data is synthetic
(generated coaches, clients, measurements), environment variables live in `.env`
(git-ignored), and `.env.example` holds placeholders only. This is a course pass
condition and a hard rule in `RULES.md` §5.

### Decision

We will generate **only synthetic** data via an idempotent seed script (and a synthetic
data generator), never commit real personal records, and keep all configuration in a
git-ignored `.env` with placeholder `.env.example`. We will add a secret scan and a
dependency/lockfile check to CI and exclude AI tooling paths from scanning.

### Rejected alternative

* **Option:** Seed with realistic/real client data, or commit `.env` with real values.
* **Why rejected:** Committing real personal data or real secrets violates NFR-4, R-003,
  and the course pass condition; it would fail the secret scan and inspection.

### Accepted downside

* **Downside:** Synthetic data may look artificial in a demo and may not cover all edge
  cases (R-006).
* **Mitigation / acceptance:** Use a defined generator with realistic ranges and edge
  cases, cover the empty state, and disclose the synthetic nature in the README and
  disclosure so nobody mistakes it for real data.

### Consequences

* Seed script is idempotent; no admin role is needed (coaches are seeded).
* `.env` is git-ignored; `.env.example` contains fake values only.
* A pre-commit / CI secret scan runs on every push; any non-synthetic value is a blocker.

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md`

### How this gets verified (optional)

* Secret scan passes with no keys/patterns; `.env` is NOT tracked; `.env.example` has placeholders only.
* A forbidden-value fixture test confirms a real-looking identifier is rejected and persists nothing (NFR-4).
