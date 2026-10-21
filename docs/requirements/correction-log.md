# Correction Log — AI Requirements Draft

> This log records every human correction applied to an **AI-produced** draft of
> the requirements. Each row is evidence of human review. Add a row for each
> correction; do not delete rows.

## How to use

* When the first version of `requirements.md` is drafted (by a human or an AI),
  add a DRAFT row.
* Whenever a human changes, deletes, adds, or overrides something the AI produced,
  add a CORRECTION row with what was wrong and what was corrected.
* Commit the correction as a `fix(human)` commit (see `RULES.md`).

## Log

| Date | Draft/Rev | Section | What the AI produced | Issue | Human correction | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-21 | Draft 1 | §2 Personas | *(e.g. persona described client as able to edit measurements)* | Incorrect: clients are read-only per scope | Changed to read-only; confirmed against FR-5/FR-8 | Applied |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

## Checkboxes per requirements review

- [ ] Personas match the two roles (coach, client) and the secondary assessor.
- [ ] Every user story maps to an FR-n.
- [ ] Every use case has at least one failure path.
- [ ] Non-functional requirements are written as quality-attribute scenarios
      (source, stimulus, environment, response, measure).
- [ ] Screen count ≤ 6; endpoint count ≤ 10; table count ≤ 8; roles = 2.
- [ ] No non-goal (payments, plans, medical advice, mobile, real-time chat, photos) leaked in.
- [ ] No real personal data; data is synthetic.
