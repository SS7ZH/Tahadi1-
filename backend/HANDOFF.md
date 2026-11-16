# Backend handoff

## Telegram groups, no player login (ADR-0011) — current flow

Players never log in. Each player has a Telegram group: the bot, the player and the coach.

1. **Coach links his own Telegram once:** web app → player page → tab «تيليجرام والمساعد الذكي» → «ربط حسابي بتيليجرام» → Start in the bot.
2. **Coach adds a player:** dashboard → «لاعب جديد (تيليجرام)» (name + sex) → gets `/link <code>`.
3. **Coach creates a group** «تحدي – <name>», adds `@tahadi_coach_bot` **as admin**, sends `/link <code>` in the group. The bot privately sends the coach the group invite link for the player.
4. **Player joins** → bot asks age / height / goal (skippable) → player sends «وزني 92», questions, squat videos.
5. **Questions** → AI draft sent privately to the coach with Approve / Edit / Reject buttons (also in the web tab). Only approved text is posted in the group. The coach can also just write in the group.

**Bot setup:** in @BotFather `/setprivacy` → Disable (the bot must read group messages).
**Run the bot** (any PC or an always-on host): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_SECRET`, `BACKEND_URL` → `python -m app.telegram_bot`.
**Backend env (Render):** `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `TELEGRAM_BOT_SECRET` (same value as the bot).

Bot-only endpoints (header `X-Bot-Secret`): `POST /telegram/link/coach`, `/telegram/link/group`, `/telegram/message`, `/telegram/video`, `/telegram/draft-decision`.
Coach endpoints (`/api/v1`, logged in): `/me/telegram`, `/me/telegram/link`, `/telegram/clients`, `/clients/telegram`, `/clients/{id}/telegram/group-code`, `DELETE /clients/{id}/telegram`, `/clients/{id}/agent-summary`, `/clients/{id}/agent-drafts`, `/questions/{id}/agent-draft`, `/agent-drafts/{id}/approve|reject`, `/clients/{id}/squat-checks`, `/squat-checks/{id}`, `/squat-checks/{id}/video`.

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
