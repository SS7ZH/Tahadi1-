# Backend handoff

## Telegram private chat, no player login (ADR-0012) — current flow

Players never log in and there are no groups. Each player chats with the bot privately; everything he sends is forwarded to the coach's own chat with the bot.

1. **Coach links his own Telegram once:** web app → player page → tab «تيليجرام والمساعد الذكي» → «ربط حسابي بتيليجرام» → Start in the bot.
2. **Coach adds a player:** dashboard → «لاعب جديد (تيليجرام)» (name + sex) → gets the player's personal link (Copy / Open). A new link any time from the player's tab.
3. **Player opens the link → Start** → bot asks age / height / goal (skippable) → player sends «وزني 92», questions, photos, squat videos. The coach is told when the player starts.
4. **Everything reaches the coach** in his chat with the bot, tagged `👤 name · #c<id>`. **Reply** on any of those messages answers that player.
5. **Questions** → AI draft sent to the coach with Approve / Edit / Reject buttons (also in the web tab). Only approved text reaches the player.
6. **Web app (player tab):** chat status, drafts, AI summary, squat videos (watch + review), photos. Media is streamed from Telegram via short-lived signed links (no file storage needed).

**How the bot runs (production): webhook inside the backend on Render — free, nothing else to host.**
Telegram sends every update to `POST /telegram/webhook` (checked with the `X-Telegram-Bot-Api-Secret-Token` header, derived from `TELEGRAM_BOT_SECRET`).
Register it once (from `backend/`, with the same `TELEGRAM_BOT_SECRET` as Render and `BACKEND_URL=https://tahadi1.onrender.com` in `.env`):
`python -m scripts.set_webhook` · check: `--info` · remove: `--delete`.
Render's free instance sleeps after 15 min idle: the first message after that is answered late (Telegram retries, nothing is lost). A free uptime pinger on `/api/v1/health` every 10 min keeps it awake.

**Re-run `python -m scripts.set_webhook` after every bot token change** (a new token has no webhook).
**Backend env (Render):** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_BOT_SECRET`.

Telegram endpoint: `POST /telegram/webhook` only.
Coach endpoints (`/api/v1`, logged in): `/me/telegram`, `/me/telegram/link`, `/telegram/clients`, `/clients/telegram`, `/clients/{id}/telegram/invite`, `DELETE /clients/{id}/telegram`, `/clients/{id}/photos`, `/clients/{id}/agent-summary`, `/clients/{id}/agent-drafts`, `/questions/{id}/agent-draft`, `/agent-drafts/{id}/approve|reject`, `/clients/{id}/squat-checks`, `/squat-checks/{id}`, `/squat-checks/{id}/video`, `/telegram-files/{kind}/{id}` (signed, no login).

---

## Earlier notes (before ADR-0011)

# Backend handoff — for Muhanad

**Base URL:** `https://<render-service>.onrender.com` (locally `http://localhost:8000`).
Interactive docs at `/docs`. All bodies are JSON. No auth for the demo (synthetic data only).
The frontend can also read the four tables directly from Supabase with the anon key (read-only).

## Telegram bot

For every text message the bot receives, call the backend and send back `reply`:

```
POST /telegram/message
{"chat_id": 123456789, "text": "وزني ٨٢٫٥"}
→ 200 {"reply": "تم تسجيل الوزن 82.5 كجم ✅ شكرًا لك!"}
```

Unlinked chats get `"Your account isn't linked yet. Ask your coach for a code."` and
nothing is saved. If the bot runs inside the backend instead, import it directly:
`from app.agents.intake import handle_message` → `reply = handle_message(chat_id, text)`.

When the coach approves a draft, send `draft.text` to `telegram_chat_id` from the approve
response (skip it if `telegram_chat_id` is null).

## Endpoints

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/health` | — | `{"status": "ok"}` |
| GET | `/clients` | — | `[{"id": "uuid", "name": "Omar Haddad", "telegram_chat_id": null}]` |
| POST | `/telegram/message` | `{"chat_id": 1, "text": "weight 82"}` | `{"reply": "Saved weight 82 kg ✅ Thank you!"}` |
| GET | `/summary/{client_id}` | — | see below |
| POST | `/draft/{client_id}` | — | `201` draft (status `pending`) |
| GET | `/drafts?status=pending` | `status` optional: `pending` / `approved` / `rejected` | `[{...draft, "client_name": "Omar Haddad"}]` |
| POST | `/drafts/{id}/approve` | — | `{"draft": {...status "approved", "sent_at": "..."}, "telegram_chat_id": 123}` |
| POST | `/drafts/{id}/reject` | — | draft with status `rejected` |
| POST | `/form-checks` | `{"client_id": "uuid", "exercise": "squat", "reps": 8, "errors": [{"rep": 3, "type": "knees_caving"}], "confidence": 0.82}` | `201` saved row |

Summary example:

```json
{
  "client_id": "uuid",
  "facts": {
    "entries": 4, "latest_date": "2026-11-07", "latest_weight_kg": 92.3, "latest_waist_cm": 101.0,
    "weight_change_2w_kg": 0.0, "weight_change_4w_kg": null, "waist_change_4w_cm": null,
    "days_since_last": 2
  },
  "alerts": ["stalled"],
  "summary_ar": "آخر وزن مسجل لـ Omar Haddad هو 92.3 كجم. الوزن ثابت تقريبًا منذ 3 أسابيع.",
  "summary_en": "Omar Haddad's latest weight is 92.3 kg. Weight has barely moved for 3 weeks."
}
```

Form-check error `type` values the draft understands: `knees_caving`, `shallow_depth`,
`back_lean`. Other types are saved but not mentioned in the draft.

Errors: `404` unknown client/draft, `409` draft already approved/rejected,
`422` bad body or id. If the DevAI agents are unavailable, summaries
and drafts still return, using template text.
