# Requirements Specification — Tahadi (تحدي)

| Field | Value |
| --- | --- |
| Version | 0.3.0 |
| Status | Draft — Milestone 1 |
| Date | 2026-10-21 |
| Source | CHARTER.md (scope: 2 roles, ≤6 screens, ≤10 endpoints) |

> This document uses one simulated persona, scenarios in Given–When–Then form,
> user stories for both roles, use cases with failure paths, functional
> requirements (each linked to a user story), and non-functional requirements as
> quality-attribute scenarios. It stays within the hard caps and respects the
> non-goals in `CHARTER.md`.
>
> **Account model:** a user signs up and chooses a role — `coach` or `client`.
> A coach can add clients (which creates/assigns their accounts); a client can
> sign in and access data once a coach has added them.

---

## 1. Persona (one simulated)

### P1 — Aya, the fitness coach

* **Profile:** Personal trainer in Riyadh with about 20 clients, aged 28. She
  trains clients 1-to-1 and in small groups.
* **Context:** She signed up to Tahadi, chose the **coach** role, then added her
  clients so each one could sign in. After each session she records body
  measurements (weight, waist, skinfolds). Today she keeps them in a spreadsheet
  and paper notes.
* **Pain:** Notes get lost or mistyped; there is no single view of a client's
  trend; clients cannot see their own numbers and keep asking in person.
* **Goal:** Register quickly, add her clients, record a client's measurements in
  under a minute, see progress trends, and answer client questions without losing
  track.
* **Attitude to tech:** Comfortable with mobile/web apps but not a power user;
  wants a simple, Arabic, right-to-left interface.

> A client persona is not modelled separately here — clients are represented
> through the user stories, use cases and scenarios below.

---

## 2. Scenarios (Given–When–Then)

### S1 — A user signs up and chooses a role

* **Given** a new user is on the sign-up screen,
* **When** they choose the **coach** role, enter name, email and a password, and
  submit,
* **Then** a coach account is created, they are signed in, and they land on the
  coach client list.

### S2 — Coach records a measurement

* **Given** Aya is logged in as a coach and has a client named Omar,
* **When** she enters today's weight (82.5 kg) and waist (92 cm) for Omar and
  saves,
* **Then** the measurement is stored with today's date and appears at the top of
  Omar's measurement history.

### S3 — Coach adds a client, who then signs in

* **Given** Aya is logged in as a coach,
* **When** she adds a new client (name and email) on the client list screen,
* **Then** a client account is created and assigned to Aya, and that client can
  now sign in with the account and view their progress.

### S4 — Client views his own progress (read-only)

* **Given** Omar is logged in as a client (added by coach Aya),
* **When** he opens his progress screen,
* **Then** he sees only his own measurements ordered by date, with no edit
  controls, and no way to view another client's data.

### S5 — Client asks the coach a question

* **Given** Omar is logged in as a client and is assigned to coach Aya,
* **When** he sends the question "Is my waist progress normal?",
* **Then** it is saved to the Omar–Aya thread and Aya can read and reply to it.

---

## 3. User stories

### Coach

* **US-1** — As a user, I can sign up and choose my role (coach or client).
* **US-2** — As a coach, I can log in so that I can access my own clients.
* **US-3** — As a coach, I can add a client, which creates their account and
  assigns them to me.
* **US-4** — As a coach, I can record a client's body measurement so that I can
  track their progress.
* **US-5** — As a coach, I can view a client's measurement history so that I can
  coach them.
* **US-6** — As a coach, I can reply to a client's question so that it is answered.

### Client

* **US-7** — As a user, I can sign up choosing the client role.
* **US-8** — As a client, I can sign in once my coach has added me.
* **US-9** — As a client, I can view my measurement history (read-only) so that I
  can see my progress.
* **US-10** — As a client, I can send a question to my coach so that I can get
  guidance.
* **US-11** — As a client, I cannot see or change any other user's data.

---

## 4. Use cases (actor, main flow, failure path)

### UC-1 — Sign up (choose a role)
* **Actor:** Guest user
* **Precondition:** No existing account for the given email.
* **Main flow:**
  1. The user enters name, email, and password.
  2. The user selects a role: `coach` or `client`.
  3. The system creates the account and issues a JWT; the UI routes by role.
* **Failure path:**
  * *F1:* Email already registered → 409.
  * *F2:* Missing/invalid name, email, password, or role → 422.

### UC-2 — Sign in
* **Actor:** Coach or Client
* **Precondition:** The account exists.
* **Main flow:**
  1. The user enters credentials.
  2. The system validates them and issues a JWT.
  3. The system returns the user's role and profile; the UI routes by role.
* **Failure path:**
  * *F1:* Invalid credentials → 401, generic message (no user enumeration).
  * *F2:* Client account not yet added/assigned to a coach → 403, "Wait until your
    coach adds you."

### UC-3 — Coach adds a client
* **Actor:** Coach
* **Precondition:** Coach is authenticated.
* **Main flow:**
  1. Coach enters the client's name and email.
  2. System creates (or links) the client account and assigns it to the coach.
  3. The client can now sign in.
* **Failure path:**
  * *F1:* Email already belongs to another coach's client → 409.
  * *F2:* Invalid email/blank name → 422.

### UC-4 — Coach records a measurement
* **Actor:** Coach
* **Precondition:** Coach is authenticated; the client belongs to the coach.
* **Main flow:**
  1. Coach selects the client.
  2. Coach enters metric values and a date.
  3. System validates and persists the record.
* **Failure path:**
  * *F1:* Negative value / future date / missing value → 422, nothing saved.
  * *F2:* Client not found or not the coach's client → 404.
  * *F3:* Database write fails → 500, no partial write (transaction).

### UC-5 — Client views own progress
* **Actor:** Client
* **Precondition:** Client is authenticated and has been added by a coach.
* **Main flow:**
  1. Client opens the progress screen.
  2. System returns only the client's own measurements, oldest first.
  3. Client sees the list/trend (read-only).
* **Failure path:**
  * *F1:* No measurements yet → empty state, not an error.
  * *F2:* Client requests another user's data → 403/404.
  * *F3:* Token missing/expired → 401.

### UC-6 — Client sends a question
* **Actor:** Client
* **Precondition:** Client is authenticated and assigned to a coach.
* **Main flow:**
  1. Client writes a question.
  2. System appends it to the client's thread with the coach.
* **Failure path:**
  * *F1:* Blank/empty question → 422.
  * *F2:* Message exceeds max length → 422.
  * *F3:* No coach assigned → 409 with a clear message.

### UC-7 — Coach replies to a question
* **Actor:** Coach
* **Precondition:** Coach is authenticated and owns the client.
* **Main flow:**
  1. Coach opens the thread.
  2. Coach writes a reply.
  3. System appends the reply to the thread.
* **Failure path:**
  * *F1:* Thread belongs to a client not owned by the coach → 403.
  * *F2:* Empty reply → 422.

---

## 5. Functional requirements (linked to user stories)

| ID | Functional requirement | User story |
| --- | --- | --- |
| FR-1 | The system shall let a new user sign up with name, email, password, and a chosen role (`coach` or `client`). | US-1 |
| FR-2 | The system shall authenticate a user (sign in) and issue a JWT. | US-2, US-8 |
| FR-3 | A coach shall be able to add a client, creating the client's account and assigning the client to the coach. | US-3 |
| FR-4 | A coach shall be able to record a body measurement (a date and at least one metric value) for one of their clients. | US-4 |
| FR-5 | A coach shall be able to view a client's measurement history ordered by date. | US-5 |
| FR-6 | A coach shall be able to reply to a client's question in the client's thread. | US-6 |
| FR-7 | A user shall be able to sign up choosing the **client** role. | US-7 |
| FR-8 | A client shall be able to sign in once assigned to a coach; an unassigned client cannot access data (403). | US-8 |
| FR-9 | A client shall be able to view **only** their own measurements in **read-only** mode. | US-9 |
| FR-10 | A client shall be able to send a question to their coach (one thread per client). | US-10 |
| FR-11 | A client shall not be able to create, update, or delete any measurement. | US-11 |
| FR-12 | The system shall restrict every data access to the resource owner (client sees own data; coach sees own clients). | US-11 |
| FR-13 | The system shall persist only synthetic data; no real personal data may be entered or committed. | All (scope) |
| FR-14 | The system shall expose at most 10 API endpoints. | All (scope) |
| FR-15 | The system shall use at most 6 screens and exactly 2 roles (coach, client). | All (scope) |

---

## 6. Non-functional requirements (quality-attribute scenarios)

| ID | Source | Stimulus | Environment | Response | Measure |
| --- | --- | --- | --- | --- | --- |
| NFR-1 (RTL/UX) | Client | Opens any screen in Arabic | Desktop browser, `dir=rtl`, `lang=ar` | UI renders right-to-left and text is fully visible | No horizontal overflow on all 6 screens; all text right-aligned; passes the RTL baseline check |
| NFR-2 (Performance) | Coach | Loads a client's history with ≥50 measurements | Production on Render, 20 concurrent users | History returned in one response | P95 response time < 500 ms |
| NFR-3 (Authorization) | Client | Requests another client's data | Authenticated as a client | Request is denied | 100% of cross-owner read/write attempts return 403/404 (covered by e2e tests) |
| NFR-4 (Data safety) | Team/fixture | A real personal identifier is submitted | Any environment | System rejects it and persists nothing | 0 unintended rows persisted; forbidden-value fixture test passes |
| NFR-5 (Availability) | Client | Requests the progress page | Production | Page loads or a clear error is shown | Uptime ≥ 99% during the demo window |
| NFR-6 (Maintainability) | Team | Adds a new measurement metric type | Development | Small, localized change | Adding a metric touches ≤ 2 files (1 schema + 1 config/endpoint) |
| NFR-7 (Scope compliance) | Instructor/reviewer | Confirms the app meets the caps | Code review + CI | App stays within caps | Screens ≤ 6, endpoints ≤ 10, tables ≤ 8, roles = 2 |
| NFR-8 (Accessibility) | Client | Uses keyboard and screen reader | Any screen | Every control is focusable and labelled | WCAG 2.2 AA baseline: visible focus, labelled inputs, contrast ≥ 4.5:1 |
| NFR-9 (Secret/config hygiene) | Team | Scans the repository for secrets | CI secret scan | No secrets or real data are found | Scan passes; `.env` ignored; `.env.example` contains placeholders only |

---

## 7. Scope compliance (supporting)

### Screen inventory (target ≤ 6)

| # | Screen | Role |
| --- | --- | --- |
| 1 | Auth — sign in / sign up (choose role) | both |
| 2 | Coach — client list (+ add client) | coach |
| 3 | Coach — client detail (history + add measurement) | coach |
| 4 | Coach — threads / reply | coach |
| 5 | Client — my progress (read-only) | client |
| 6 | Client — ask a question / my thread | client |

### API endpoint inventory (target ≤ 10)

| # | Method | Path | Role | Purpose |
| --- | --- | --- | --- | --- |
| 1 | POST | `/api/auth/signup` | guest | Create account with chosen role |
| 2 | POST | `/api/auth/signin` | both | Authenticate, issue JWT |
| 3 | GET | `/api/coach/clients` | coach | List own clients |
| 4 | POST | `/api/coach/clients` | coach | Add a client (create/assign account) |
| 5 | POST | `/api/coach/clients/{id}/measurements` | coach | Record a measurement |
| 6 | GET | `/api/clients/{id}/measurements` | coach/client | List measurements (owner-scoped) |
| 7 | GET | `/api/me/measurements` | client | Own progress (read-only) |
| 8 | POST | `/api/me/threads` | client | Send a question |
| 9 | GET | `/api/threads/{id}` | coach/client | Read a thread |
| 10 | POST | `/api/threads/{id}/messages` | coach | Reply in a thread |

### Roles (exactly 2)

`coach`, `client`. No admin role.

### Non-goals (respected)

Payments, workout/nutrition plans, medical advice, mobile app, real-time chat, and
photo upload are **out of scope**. They are not represented in any screen,
endpoint, or user story above.

---

## 8. Assumptions & open questions

* **Auth** is assumed to be stateless JWT (no separate session table is required
  to stay within 8 tables). Sign-up and sign-in are two endpoints; role is chosen
  at sign-up.
* **Client provisioning:** a client account may be created by the client signing
  up (client role) *or* by a coach adding them. In both cases the client becomes
  usable once a coach has added/assigned them (FR-8).
* **Message model** is one thread per client; clients ask and coaches reply,
  possibly back-and-forth, within that thread.
* **Password reset / recovery** is out of scope unless it fits within the
  endpoint cap (currently not allocated).
* **Measurement metric set** for Milestone 1 is limited to weight, waist, and
  skinfolds; extending it is covered by NFR-6.
