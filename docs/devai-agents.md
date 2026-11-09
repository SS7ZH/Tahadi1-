# Building the Tahadi agents in DevAI Desktop

The three language agents are built and edited in **DevAI Desktop**. The backend only runs
them by id and checks what they return. Numbers, trends and alerts are always computed in
code (`backend/app/rules/`); the agents only read them and write text.

| Agent | DevAI id | Env var | Temperature | Called when |
| --- | --- | --- | --- | --- |
| Tahadi Intake | `tahadi-intake` | `DEVAI_INTAKE_AGENT_ID` | Precise (0) | A Telegram message the regex parser could not read |
| Tahadi Progress Analyst | `tahadi-progress-analyst` | `DEVAI_ANALYST_AGENT_ID` | Precise (0) | `GET /summary/{client_id}` |
| Tahadi Coach Assistant | `tahadi-coach-assistant` | `DEVAI_COACH_AGENT_ID` | Balanced (0.7) | `POST /draft/{client_id}` |

All three have no tools, no rule files and no MCP servers, and run on `DeepSeek-V4.1-Flash`
(`DEVAI_MODEL`). Check them through the backend with `python -m scripts.check_agents`
(from `backend/`, DevAI Desktop open); last run 6/6 passed, about 4–6 s per call.

If an agent is not set up, DevAI is closed, or the reply is not in the expected format,
the backend uses its built-in template text instead. The demo never breaks.

## The contract each agent must follow

The backend sends each agent **one message** and reads its **whole reply**. Give the agents
**no tools**: a tool that needs approval stops the run.

### 1. Intake

* **Receives:** the client's raw message, e.g. `صباح الخير، وزني اثنين وثمانين ونص`
* **Must reply with JSON only:** `{"weight_kg": 82.5, "waist_cm": null}`
* Use `null` for anything not clearly stated. Never guess.
* The backend rejects weight outside 30–300 kg and waist outside 40–200 cm.

### 2. Progress Analyst

* **Receives:**
  ```json
  {"client": "Omar Haddad",
   "facts": {"entries": 4, "latest_date": "2026-11-07", "latest_weight_kg": 92.3,
             "latest_waist_cm": 101.0, "weight_change_2w_kg": 0.0,
             "weight_change_4w_kg": null, "waist_change_4w_cm": null, "days_since_last": 2},
   "alerts": ["stalled"]}
  ```
  `stalled` = weight moved < 0.3 kg in 3 weeks. `no_checkin` = no entry for 10+ days.
* **Must reply with JSON only:** `{"summary_ar": "...", "summary_en": "..."}`, 2–3 sentences
  each, written for the coach, using only numbers from `facts`.

### 3. Coach Assistant

* **Receives:** the same `client`, `facts` and `alerts`, plus `latest_form_check`
  (or `null`):
  ```json
  {"exercise": "squat", "reps": 8, "confidence": 0.82,
   "errors": [{"rep": 3, "type": "knees_caving"}, {"rep": 6, "type": "shallow_depth"}]}
  ```
  Error types: `knees_caving`, `shallow_depth`, `back_lean`.
* **Must reply with:** plain Arabic text only, at most 4 short lines, addressed to a male
  client. The coach approves it before it is sent.

## Steps

1. Open **DevAI Desktop** → Agents → **Agent Creator** (or "New agent").
2. Create each agent from its contract above. Give it no tools and a low temperature
   (0–0.3 for Intake and Analyst).
3. Test each agent in DevAI's chat with the sample input above and check that the reply
   matches the required format exactly.
4. Copy each agent's **id** into `backend/.env`. To list ids with DevAI open:
   ```bash
   curl -s -H "x-api-key: $DEVAI_API_KEY" http://127.0.0.1:7588/api/agents
   ```
5. Put your DevAI API key in `backend/.env` as `DEVAI_API_KEY`.
6. Restart the backend, then call `GET /summary/{client_id}`. If the summary still reads
   like the template, check the backend log for an `agent ... failed` warning.

## Where it runs

DevAI's host listens only on this computer (`127.0.0.1:7588`). The agents work when the
backend runs on the **same machine** as DevAI Desktop, which is how the demo runs. The
Render deployment cannot reach it and uses the templates.
