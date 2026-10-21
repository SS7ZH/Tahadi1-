# SPEC-TEMPLATE

> Copy this to `docs/specs/SPEC-<feature>.md` for each feature. The team writes the
> spec **before** prompting an AI to implement it (see `RULES.md` §1). The spec is
> the source of truth; the AI only implements it.

## SPEC-<n> — <Feature name>

### Goal

*(1–2 sentences: what the feature does and why.)*

### Scope / non-goals

* **In scope:** ...
* **Out of scope for this SPEC:** ... *(e.g. payments, plans, medical advice,
  mobile, real-time chat, photos — per CHARTER.md)*

### Constraints

* **Stack / environment:** ...
* **Relation to scope caps:** *(does it affect screen/endpoint/table/role count?)*
* **Security:** ...

### Acceptance criteria (Given–When–Then)

#### Happy path

* **Given** ...
* **When** ...
* **Then** ...

#### Failure path

* **Given** ...
* **When** ...
* **Then** ... *(what error/behavior is expected — codes, messages)*

#### Boundary case

* **Given** ... *(empty input, max length, min/max values, duplicate, missing
  resource, future date, etc.)*
* **When** ...
* **Then** ...

### Input / output / error contracts

* **Input:** *(endpoint/function + fields, types, valid ranges)*
* **Output (success):** *(shape/status code)*
* **Error codes:** *(400/401/403/404/409/422/500 — when each happens)*

### Worked example

```
Request:
  POST /api/coach/clients/{id}/measurements
  { "value": 82.5, "metric_id": 2, "date": "2026-10-20" }

Response (201):
  { "id": 101, "client_id": 5, "metric_id": 2, "value": 82.5, "date": "2026-10-20" }

Error (422):
  { "detail": [ { "loc": ["body","value"], "msg": "value must be >= 0" } ] }
```

### Source files (populate when implemented)

| File | Role |
| --- | --- |
| `frontend/src/...|.tsx` / `.ts` | UI or API client |
| `backend/app/...` | Handler / service / model |

### Security constraints

* Owner-scoping: the logged-in user may only access their own data (client) or
  their own clients (coach). Cross-owner access must return 403/404.
* Role check: endpoints declare which role may call them.
* Secrets: none in code; use `.env` (git-ignored) with `.env.example` placeholders.
* Auth: JWT from login required on protected endpoints.

### Tests (with an independent oracle)

* **Where:** *(test file paths)*
* **Independent oracle:** how do we know the tests are correct? Not by trusting the
  implementation — compute the expected result by hand, from a known dataset, or by
  a rule. State it here.
* **Cases:** map to the Given–When–Then above (happy, failure, boundary).

### Verification

* Run the tests and paste/read the output before claiming success
  (see `verification-before-completion` / `RULES.md` §6).
