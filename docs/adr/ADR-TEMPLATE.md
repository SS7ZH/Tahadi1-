# ADR-TEMPLATE

> Copy this file to `docs/adr/ADR-00N-<short-title>.md` for each decision. Name
> files with an incrementing number and a short kebab-case title, e.g.
> `ADR-0001-use-fastapi-and-react.md`. Never rewrite an accepted ADR; to change
> course, create a new ADR that supersedes the old one (see `RULES.md` §7).

## ADR-00N — <Title>

### Status

* Proposed | Accepted | **Superseded**

*(Superseded by ADR-00M-...)*

### Date

YYYY-MM-DD

### Deciders

* *(team member)*
* *(team member)*

### Related requirement IDs

* FR-n / NFR-n, or "none" — link back to `docs/requirements/requirements.md`.

### Context

Describe the situation and the forces at play:

* What problem or constraint drove this decision?
* What are the trade-offs? (options considered)
* What is the current state (if any)?

### Decision

State the decision in one or two sentences. Be decisive and specific:
"We will ... because ..."

### Rejected alternative

Describe the main alternative that was **not** chosen and why:

* **Option:** ...
* **Why rejected:** ...

### Accepted downside

Name the cost this decision imposes and how you will live with it:

* **Downside:** ...
* **Mitigation / acceptance:** ...

### Consequences

What will be done because of this decision (positive and negative)?

### Related ADRs

* `ADR-00N-...` (if this depends on or updates another ADR)

### How this gets verified (optional)

* *(test, check, or metric that confirms the decision holds, e.g. "endpoint count
  stays ≤ 10, verified by CI test").*
