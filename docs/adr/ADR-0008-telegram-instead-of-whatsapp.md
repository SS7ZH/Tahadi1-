# ADR-0008 — Use the Telegram Bot API instead of the WhatsApp Business Cloud API

### Status

* **Proposed** (becomes Accepted once both team members approve the PR)

### Date

2026-11-09

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Related requirement IDs

* Intake agent and coach-approval flow (`ADR-0007`)
* NFR-9 (secret hygiene), FR-14 (≤10 endpoints)

### Context

The concept deck routes client messages and coach approvals through the official
WhatsApp Business Cloud API. For our timeline and budget that path has real costs:
Meta business verification, a dedicated business phone number, approved message
templates for anything sent outside the 24-hour window, and per-conversation pricing.
None of these can be ready for the demo.

### Decision

Use **Telegram** as the messaging channel:

* Clients message a Tahadi Telegram bot. The bot passes each text to the backend
  (`POST /telegram/message {chat_id, text}`) and sends back the `reply`.
* A client is linked to Tahadi by their Telegram `chat_id`, stored in
  `clients.telegram_chat_id` (unique, nullable until linked).
* When the coach approves a draft, `POST /drafts/{id}/approve` returns the draft plus
  the client's `telegram_chat_id`, and the bot sends it.
* The bot token lives only in environment variables, never in the repository.

### Rejected alternative

* **Option:** WhatsApp Business Cloud API (as in the deck).
* **Why rejected:** Business verification, a dedicated number, template approval and
  per-conversation cost cannot be done in time, and the free test number only reaches
  a few pre-registered phones.

### Accepted downside

* **Downside:** Most clients in our target market use WhatsApp more than Telegram.
* **Mitigation / acceptance:** Channel code is isolated in the bot and the
  `/telegram/message` endpoint; the agents only see `(chat_id, text)`. Moving to
  WhatsApp later means a new adapter and a superseding ADR, not changes to the agents.

### Consequences

* No Meta account, template approval or per-message cost for the demo.
* One extra secret (`TELEGRAM_BOT_TOKEN`) to protect; `.env.example` gets a placeholder.
* The bot runs as a webhook route inside the Render backend service, so it adds no
  deployment target (see `ADR-0009`).

### Related ADRs

* `ADR-0006-synthetic-data-secrets-hygiene.md`
* `ADR-0007-pivot-to-agent-assisted-coaching.md`

### How this gets verified

* Manual demo: send "وزني ٨٢" to the bot from a linked account → a measurement row
  appears with `source = 'telegram'` and the bot replies in Arabic.
* An unlinked chat gets the "account isn't linked yet" reply and nothing is saved.
