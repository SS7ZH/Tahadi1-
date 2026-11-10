# Tahadi backend

FastAPI service for the coach agents (`docs/adr/ADR-0007`), with Telegram as the messaging
channel (`ADR-0008`) and Supabase as the database. Spec: `docs/specs/SPEC-agents-backend.md`.

## Layout

| Path | What it does |
| --- | --- |
| `app/main.py` | 9 API endpoints, CORS |
| `app/rules/parsing.py` | Regex measurement parser (Arabic, English, Arabic-Indic digits) |
| `app/rules/progress.py` | Trends and alerts (`stalled`, `no_checkin`), computed in code |
| `app/agents/intake.py` | Agent 1: `handle_message(chat_id, text) -> str` |
| `app/agents/analyst.py` | Agent 4: facts + alerts + bilingual summary |
| `app/agents/coach.py` | Agent 5: drafts, approve, reject |
| `app/agents/text.py` | All wording: your DevAI agents first, fixed templates as fallback |
| `app/llm.py` | Runs the agents built in DevAI Desktop by id (see `docs/devai-agents.md`) |
| `supabase/schema.sql` | 4 tables + RLS |
| `scripts/seed.py` | 3 synthetic clients with different trends |

The three language agents are built in **DevAI Desktop** (`docs/devai-agents.md`). Until
their ids and `DEVAI_API_KEY` are in `.env`, every reply and summary uses the templates in
`app/agents/text.py`, so the whole flow already works for the demo.

## Run locally

Python 3.12.

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env      # then fill SUPABASE_URL and SUPABASE_SERVICE_KEY
```

1. Open Supabase → SQL editor → paste `supabase/schema.sql` → Run.
2. Seed synthetic data: `python -m scripts.seed`
3. Link your own Telegram chat to a client (Supabase table editor → `clients` →
   set `telegram_chat_id`). Get your chat id by messaging the bot and reading
   `message.chat.id` from the update.
4. Start: `uvicorn app.main:app --reload` → open http://localhost:8000/docs
5. In a second terminal, run `python -m app.telegram_bot`. Set `TELEGRAM_BOT_TOKEN`
   and `BACKEND_URL` in `backend/.env`; keep this process running to receive and
   reply to Telegram messages.
6. To link a Telegram account, sign in as a trainer/admin, open `/demo`, create a
   Telegram link for the client, and send it to them. The client opens it and taps
   Start; the signed link expires after 10 minutes and can only be used once.
7. Tests (no network or database needed): `pytest -q`

## Deploy on Render

| Setting | Value |
| --- | --- |
| Service type | Web Service |
| Root directory | `backend` |
| Runtime | Python |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |

Environment variables: `PYTHON_VERSION=3.12.10`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
`TELEGRAM_BOT_TOKEN`, `FRONTEND_URL` (the Vercel URL, for CORS).

DevAI Desktop's host only listens on your own computer, so on Render the agents fall back
to the templates. Run the backend locally next to DevAI Desktop to demo the agents.

The free web service sleeps after ~15 minutes idle (R-004): open `/health` a minute
before the demo.
