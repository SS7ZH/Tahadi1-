# Requirements Specification — Tahadi (تحدي)

> Milestone 1. This file defines personas, scenarios, user stories, use cases
> (with failure paths), numbered functional requirements (FR-n), and
> non-functional requirements written as quality-attribute scenarios.

## 1. Glossary

* **Coach** — a fitness professional who records measurements for their clients.
* **Client** — the person whose measurements are recorded; views own progress.
* **Measurement** — a body metric recorded on a date (weight, waist, skinfold, etc.).
* **Session/Visit** — one dated set of measurements for a client.
* **Thread** — a message conversation between one client and their coach.
* **Synthetic data** — generated fictitious records; never real personal data.

## 2. Personas

### P1 — Coach (primary)
* **Name:** Aya
* **Context:** Personal trainer with ~20 clients. Records measurements after each
  session; occasionally needs to recall last month's waist measurement.
* **Frustrations:** Spreadsheets get messy; no single view of a client's trend.
* **Goals:** Record fast, see progress trends, answer client questions in one place.

### P2 — Client (primary)
* **Name:** Omar
* **Context:** Follows a training program; wants to see whether numbers are moving.
* **Frustrations:** Does not know what the coach recorded; has to ask in person.
* **Goals:** See own progress (read-only), ask the coach a question.

### P3 — Instructor / Assessor (secondary)
* Wants verifiable scope compliance, traceability, and honest AI disclosure.

## 3. Scenarios

* **S1 (Coach records):** After a session, Aya opens Client Omar's record, enters
  today's weight and waist, and saves. The new measurement appears with a date.
* **S2 (Client views progress):** Omar logs in and sees a table/trend of his own
  measurements. He cannot see other clients or edit values.
* **S3 (Client asks a question):** Omar asks "Is my waist progress normal?" The
  coach replies. Omar sees the reply in the thread.
* **S4 (Client tries to edit):** Omar attempts to modify a measurement; the UI has
  no edit control and the API rejects write access (403).

## 4. User stories

* **US-1:** As a coach, I can log into the app so that I can manage my own clients.
* **US-2:** As a coach, I can create/record a client measurement so that I can track progress.
* **US-3:** As a coach, I can view a client's measurement history/trend so that I can coach them.
* **US-4:** As a coach, I can reply to a client's question so that the thread is answered.
* **US-5:** As a client, I can log in so that I can see only my own data.
* **US-6:** As a client, I can view my measurement history (read-only) so that I can see progress.
* **US-7:** As a client, I can send a question to my coach so that I can get guidance.
* **US-8:** As a client, I cannot see or change other users' data (security requirement).

## 5. Use cases (with failure paths)

### UC-1: Coach records a measurement
* **Actor:** Coach
* **Precondition:** Coach is authenticated; client exists and belongs to the coach.
* **Main flow:**
  1. Coach selects a client.
  2. Coach enters measurement values and a date.
  3. System validates the values.
  4. System persists the measurement and returns the created record.
  5. Coach sees the updated history.
* **Failure paths:**
  * *F1:* Values invalid (negative weight, date in the future) → system returns a
    422 validation error and does **not** save.
  * *F2:* Client not found or not coach's client → 404.
  * *F3:* Database write fails → 500, no partial write (transaction).
  * *F4:* Coach not authenticated or token expired → 401, no save.

### UC-2: Client views own progress
* **Actor:** Client
* **Precondition:** Client is authenticated.
* **Main flow:** 1. Client opens their progress screen. 2. System returns only the
  client's own measurements, oldest first. 3. Client sees the list/trend.
* **Failure paths:**
  * *F1:* No measurements yet → system shows an empty state, not an error.
  * *F2:* Client requests another user's data → system returns 403 (or 404).
  * *F3:* Auth missing/expired → 401.

### UC-3: Client asks the coach a question
* **Actor:** Client
* **Precondition:** Client is authenticated.
* **Main flow:** 1. Client writes a question. 2. System creates a message in the
  client–coach thread. 3. Client sees the confirmed message.
* **Failure paths:**
  * *F1:* Empty/blank question → 422, not saved.
  * *F2:* Message too long (over limit) → 422.
  * *F3:* No coach assigned → 409 (conflict) and a clear message.

### UC-4: Coach replies to a client question
* **Actor:** Coach
* **Precondition:** Coach is authenticated and owns the client.
* **Main flow:** 1. Coach selects a thread. 2. Coach replies. 3. System appends the
  reply. 4. Coach sees the updated thread.
* **Failure paths:**
  * *F1:* Thread belongs to a client not owned by the coach → 403.
  * *F2:* Empty reply → 422.

### UC-5: Coach accounts are seeded
* **Actor:** Seeding script (team-run, not an end-user feature).
* **Main flow:** 1. Run `seed` command. 2. It creates the configured coaches
  idempotently (no duplicates on re-run). 3. It may create synthetic clients and
  measurements for demo data.
* **Failure paths:** *F1:* Duplicate seed run does not create duplicate coaches
  (idempotency). *F2:* Seed fails mid-way → leaves no partial coach (or is clearly
  documented as non-atomic but idempotent).

## 6. Functional requirements (FR-n)

| ID | Requirement |
| --- | --- |
| FR-1 | The system shall authenticate users (coach/client) and issue a JWT. |
| FR-2 | A coach shall be able to create a measurement record for one of their clients. |
| FR-3 | A measurement record shall include a date and at least one metric value. |
| FR-4 | A coach shall be able to list a client's measurements (ordered by date). |
| FR-5 | A client shall be able to list **only their own** measurements in read-only mode. |
| FR-6 | A client shall be able to send a question to their coach (one thread per client). |
| FR-7 | A coach shall be able to reply to a client's question. |
| FR-8 | A client shall not be able to create/update/delete any measurement. |
| FR-9 | Coaches shall be created by an idempotent seeding script (no admin role). |
| FR-10 | All data used/committed shall be synthetic (no real personal data). |
| FR-11 | The system shall expose 10 or fewer API endpoints. |
| FR-12 | The system shall use a maximum of 8 database tables and 2 roles. |

## 7. Non-functional requirements (quality-attribute scenarios)

Each NFR is written as a scenario: **source, stimulus, environment, response,
measure**.

| ID | Source | Stimulus | Environment | Response | Measure |
| --- | --- | --- | --- | --- | --- |
| NFR-1 (RTL/UX) | Client | Opens any screen in Arabic | Desktop browser, `dir=rtl` | UI renders right-to-left, text fully visible | No horizontal overflow; all text right-aligned; verified on the RTL baseline |
| NFR-2 (Performance) | Coach | Loads a client's full measurement history | Production on Render, >= 50 measurements | History returns in a single response | P95 response time < 500 ms under concurrent load of 20 users |
| NFR-3 (Security — authorization) | Client | Attempts to read another client's data | Authenticated as client | Request is denied | 100% of cross-owner read/write attempts return 403/404; e2e tests cover it |
| NFR-4 (Data safety) | Team | A real personal identifier is pasted into a field | Any environment | System prevents persistence of real data (validation/redaction) | No unintended rows persisted; tested with forbidden-value fixtures |
| NFR-5 (Availability) | Client | Requests their progress page | Production | Page loads or a clear error is shown | Availability >= 99% during the demo window (verified via uptime check) |
| NFR-6 (Maintainability) | Team | A new metric type is added | Dev environment | Adding a metric requires ≤ 1 table change + 1 endpoint change | Measured by the number of files touched to add a metric |
| NFR-7 (Scope compliance) | Instructor | Confirms the app meets the cap | Code review | Screens/endpoints/tables/roles within caps | Screens ≤ 6, endpoints ≤ 10, tables ≤ 8, roles ≤ 2 |
| NFR-8 (Accessibility) | Client | Uses keyboard + screen reader | Any screen | All controls focusable and labelled | WCAG 2.2 AA baseline: focus visible, labels on all inputs, adequate contrast |
| NFR-9 (Config/secret hygiene) | Team | Checks the repository for secrets | CI scan | No secrets/real data committed | Secret scan passes; `.env` ignored, `.env.example` committed with placeholders |

## 8. Screen inventory (target ≤ 6)

1. **Login** (both roles)
2. **Coach — client list**
3. **Coach — client detail + measurement entry/history**
4. **Coach — threads / question reply**
5. **Client — my progress** (read-only)
6. **Client — ask a question / thread**

## 9. API endpoint inventory (target ≤ 10)

| # | Method | Path | Role | Purpose |
| --- | --- | --- | --- | --- |
| 1 | POST | `/api/auth/login` | both | Authenticate, return JWT |
| 2 | GET | `/api/coach/clients` | coach | List own clients |
| 3 | POST | `/api/coach/clients` | coach | Create a client |
| 4 | GET | `/api/clients/{id}` | coach/client | Read a client (owner-scoped) |
| 5 | POST | `/api/coach/clients/{id}/measurements` | coach | Record a measurement |
| 6 | GET | `/api/clients/{id}/measurements` | coach/client | List a client's measurements (owner-scoped) |
| 7 | GET | `/api/me/measurements` | client | Own progress (read-only) |
| 8 | POST | `/api/me/threads` | client | Send a question |
| 9 | GET | `/api/threads/{id}` | coach/client | Read a thread |
| 10 | POST | `/api/threads/{id}/messages` | coach | Reply in a thread |

> Keep to 10. If an endpoint must be added, it must replace/merge another within
> the cap and be recorded as an ADR.

## 10. Data model (target ≤ 8 tables)

1. `users` (id, role, name, email, password_hash, coach_id)
2. `coaches` (id, user_id, specialty)
3. `clients` (id, user_id, coach_id)
4. `measurement_metrics` (id, name, unit, sort_order) — the metric catalogue
5. `measurements` (id, client_id, metric_id, value, date)
6. `threads` (id, client_id, coach_id)
7. `messages` (id, thread_id, author_id, body, created_at)
8. `sessions` (id, user_id, token, created_at, expires_at) — refresh/token store (or JWT stateless)

> Adjust to fit within 8 tables. Placeholder; refine in the schema ADR.

## 11. Assumptions & open questions

* **Auth:** assumed JWT (stateless) — if a session table is needed, confirm the
  8-table cap still holds (can drop a table or reuse).
* **Measurement types:** only the common types (weight, waist, skinfold, etc.) in
  Milestone 1.
* **Message one-per-thread vs. reply-only:** client sends a question; coach replies;
  may allow continued back-and-forth in the same thread (still one thread per client).
* **Reset/password recovery:** treat as out of scope unless within endpoint cap.
