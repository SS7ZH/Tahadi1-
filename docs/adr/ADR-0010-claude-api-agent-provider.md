# ADR-0010 — Run the agents on the Claude API, with DevAI Desktop as the local option

### Status

* **Proposed** (becomes Accepted once both team members approve the PR)
* **Amends:** `ADR-0007-pivot-to-agent-assisted-coaching.md` decision 7 (where the agents run)

### Date

2026-11-14

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Related requirement IDs

* Agents 1, 4 and 5 (`ADR-0007`), NFR-5 (availability), NFR-9 (secret hygiene)

### Context

The three agents (Intake, Progress Analyst, Coach Assistant) were built in DevAI Desktop and
the backend ran them through DevAI's local host (`127.0.0.1:7588`). Two problems:

* DevAI's host only exists on the machine where DevAI Desktop is open, so the deployed
  backend on Render could never use the agents.
* On 2026-11-14 DevAI's model calls started failing (`model-failed`) for all three agents,
  so even the local demo fell back to template text.

### Decision

* The backend gets a second agent provider: the **Claude API** (official `anthropic` Python SDK).
* The agents are still **designed and edited in DevAI Desktop**. Their instructions are exported
  into the repo (`backend/app/agents/prompts/*.md`) by `scripts/export_devai_prompts.py`, and the
  Claude provider sends them as the system prompt, so both providers run the same agent.
* `LLM_PROVIDER` picks `claude` or `devai`; when unset, Claude is used if `ANTHROPIC_API_KEY`
  is set, otherwise DevAI. Model `claude-opus-5-5` at `low` effort (short, rule-bound tasks),
  both configurable (`CLAUDE_MODEL`, `CLAUDE_EFFORT`).
* Server-side refusal fallbacks are enabled (`fallbacks: "default"`).
* Unchanged: numbers and alerts are computed in code, every reply is a coach-approved draft,
  and any provider failure falls back to template text.

### Rejected alternative

* **Option:** Wait for DevAI and keep DevAI-only.
* **Why rejected:** Production could never use the agents, and the demo depends on a desktop app
  being open and connected.

### Accepted downside

* **Downside:** A paid API key and per-call cost (a few thousand tokens per summary or draft).
* **Mitigation / acceptance:** Low effort, short prompts, regex-first intake; the key lives only in
  `backend/.env` and Render's environment (R-016). Template fallback if the key is missing or spent.
* **Downside:** The prompt files in the repo can drift from the agents in DevAI.
* **Mitigation / acceptance:** Re-run `scripts/export_devai_prompts.py` after editing an agent;
  a test checks every agent has its prompt file.

### Related ADRs

* `ADR-0006-synthetic-data-secrets-hygiene.md`
* `ADR-0007-pivot-to-agent-assisted-coaching.md`

### How this gets verified

* `tests/test_claude_provider.py` (no network): provider choice, request shape, refusal and
  missing-key fallbacks, and the summary endpoint running on Claude.
* `python -m scripts.check_agents` with a real key: the same 6 checks the DevAI agents passed.
