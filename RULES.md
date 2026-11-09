# RULES — Team rules for AI-assisted development

> These rules govern how this team uses AI tools so that our submission is
> traceable, honest, and safe. They are binding. If a tool or workflow conflicts
> with a rule below, the rule wins.

## 1. Write a SPEC.md before prompting the AI

Before you ask an AI agent to build or change anything, write a short
`docs/specs/SPEC-*.md` (or a `SPEC.md` at the relevant module) that defines:

* the goal,
* Given–When–Then acceptance criteria (happy path, failure path, boundary case),
* constraints and non-goals,
* input/output/error contracts,
* the tests and how we know they are correct (an independent oracle).

The AI must not be the source of the specification. The team defines intent; the
AI assists with implementation.

## 2. Commit raw AI output separately from human fixes

* A commit that is **unmodified AI output** uses the prefix:
  `raw(ai): ...`
* A commit with **human review/fixes** uses the prefix:
  `fix(human): ...`
* A mixed commit (AI output + their own edits in the same change) uses the
  honest label `fix(human): ...` and the message lists what the human changed.

The point is that a reviewer (and the instructor) can tell which lines came from
an AI and which were written/corrected by a human.

## 3. Never squash or rebase away raw/fix pairs

* Do **not** squash, rebase, or otherwise collapse a `raw(ai)` commit into a
  later `fix(human)` commit.
* Keep the history linear and honest. If you must reorganize, do so only while
  preserving every pair as separate commits with their original messages.
* The `raw(ai)` → `fix(human)` sequence is part of the submission evidence.

## 4. Short-lived branches

* Create a short-lived feature branch for each task:
  `feature/<short-description>` or `fix/<short-description>`.
* Branches are merged as soon as the task is done and verified.
* Do not keep long-lived branches that drift from `main`.

## 5. No secrets or real data

* Never commit secrets (API keys, DB passwords, JWTs, tokens).
* Environment variables live in `.env` (git-ignored). Provide a placeholder
  `.env.example` in the repo (fake values only).
* Only **synthetic** data is committed. No real personal data, no real client or
  coach records, no real bundled SQL dumps with real values.

## 6. Run tests and lint yourself

* Never claim "it works" or "tests pass" from reading code or from an AI saying so.
* Run the project's lint, typecheck, and test commands yourself and paste/read the
  output before making a success claim.
* Fix what those report. Report anything you could not run.

## 7. Supersede ADRs instead of rewriting them

* Once an Architecture Decision Record is accepted, do not rewrite it in place.
* To change course, write a new ADR that explicitly **supersedes** the old one and
  references it (e.g. `Supersedes ADR-0002`).
* Keep the old ADR with its original status for history.

## 8. Respect the hard scope limits

| Dimension | Cap |
| --- | --- |
| Screens | 6 |
| API endpoints | 10 |
| Database tables | 8 |
| Roles | 2 |
| Deployment targets | 2 (raised from 1 by ADR-0009) |

* Any new feature must fit within these caps.
* Adding anything that pushes past a cap requires an explicit scope-change ADR
  approved by the team, and a note in `docs/risk-register.md` and
  `docs/traceability-matrix.md`.

## 9. Non-goals are non-negotiable by default

Payments, workout/nutrition plans, medical advice, mobile app, real-time chat,
and photo upload are **out of scope**. Do not add them unless a scope-change ADR
lifts the ban.

## 10. Review before merge

* Before merging a branch, run the relevant checks and, where a reviewer is
  available, request a review of the diff.
* Ensure `AI_USE_DISCLOSURE.md` is updated whenever AI materially contributed.

## Consequence of breaking a rule

If a rule is broken, stop and fix the commit history / files before continuing.
Honesty in the AI-usage disclosure is part of the grade; do not hide AI work.
