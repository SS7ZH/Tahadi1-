# Trade-off Matrix — Architecture Options

> Compare exactly **two** viable architecture options against weighted criteria,
> then record the decision as an ADR in `docs/adr/`. Fill in every cell. Delete
> this template when writing a real comparison, or keep a copy and rename it
> `trade-off-matrix-<topic>.md`.

## Decision context

* **Topic / decision:** *(e.g. "Monolith microservices vs. modular monolith for Tahadi")*
* **Related requirements:** FR-n / NFR-n *(link from `requirements.md`)*
* **Date:** __________
* **Deciders:** ______________

## Options

* **Option A:** *(name + one-line description)*
* **Option B:** *(name + one-line description)*

## Criteria (weighted)

Assign a weight from 0–5 per criterion (5 = most important). Score each option 1–5.
Weighted score = weight × score.

| Criterion | Weight | Why it matters | Option A score | Option B score |
| --- | --- | --- | --- | --- |
| Build effort (team of 2) | 5 | Small team; must ship in scope | | |
| Deployment simplicity (1 target) | 5 | One deploy target on Render | | |
| Cost | 4 | Free/low-cost tiers preferred | | |
| Performance / latency | 3 | History loads < 500 ms | | |
| RTL / UX fit | 4 | Arabic-first experience | | |
| Maintainability | 4 | Course project; extensible | | |
| Risk (data/auth) | 4 | Owner-scoping must be safe | | |
| **Total** | | | **sum** | **sum** |

## Weighted totals

* **Option A total:** ______________
* **Option B total:** ______________
* **Recommended:** *(A / B)*

## Justification

*(2–4 sentences on why the recommended option wins on the most important
criteria, and the main trade-off being accepted.)*

## Trade-offs accepted

Accepted downside of the chosen option (explicitly acknowledge what we lose):

* *(e.g. "Option B splits the deploy into two services, which is more work, but we
  accept it because it keeps a single language/stack on the frontend.")*

## Rejected option — why not

* **Option X** was rejected because: ...

## Related ADR

* `docs/adr/ADR-00N-<title>.md` — "Status: Accepted"
