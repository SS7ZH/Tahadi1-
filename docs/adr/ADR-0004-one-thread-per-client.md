# ADR-0004 — Model messaging as one thread per client (no real-time chat)

### Status

* **Accepted**

### Date

2026-10-21

### Deciders

* Team member 1 (Muhaned)
* Team member 2 (Saeed)

### Related requirement IDs

* FR-6 (coach replies), FR-10 (client sends a question), NFR-7 (scope compliance)
* Non-goal: real-time chat is out of scope (`CHARTER.md`)

### Context

Clients ask their coach a question and the coach replies (FR-10, FR-6). The
requirements specify a Q&A thread per client with back-and-forth messages, and
explicitly exclude real-time chat and push notifications as non-goals. We must model
this within the endpoint cap (≤10) and without a websocket/push dependency.

### Decision

We will model messaging as **one persistent thread per client**, holding an ordered
list of messages, with a `client_id` and `coach_id`. A client appends a question and a
coach appends a reply; both read the thread. There is no push or websocket — the
thread is fetched on demand.

### Rejected alternative

* **Option:** Real-time chat / websockets with presence and push notifications.
* **Why rejected:** It is an explicit non-goal, needs persistent sockets or push, adds
  an external dependency and more endpoints, and would push past the ≤10 endpoint and
  ≤6 screen caps for no academic benefit to the core requirement.

### Accepted downside

* **Downside:** The client must refresh or re-fetch to see a new reply; there is no
  live notification.
* **Mitigation / acceptance:** Accept the pull-to-check behaviour (non-goal); reuse
  `GET /api/threads/{id}` and `POST /api/threads/{id}/messages`, so messaging fits
  within the endpoint cap and 6 screens.

### Consequences

* Thread endpoints consume ≤3 of the ≤10 endpoints (`POST /api/me/threads`,
  `GET /api/threads/{id}`, `POST /api/threads/{id}/messages`).
* Each thread is owner-scoped per ADR-0003; the coach and client can read it, others return 403.
* No websocket, push, or realtime infrastructure is added (keeps deployment on Render simple).

### Related ADRs

* `ADR-0001-choose-three-tier-option-a.md`
* `ADR-0003-owner-scoped-read-only.md`

### How this gets verified (optional)

* e2e test: client sends a question → appears in the thread; coach replies → both see it.
* e2e test: a client other than the thread owner reads the thread → 403.
