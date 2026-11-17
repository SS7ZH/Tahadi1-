# ADR-0011 — Players use a Telegram group only; no player login

### Status

* **Superseded in part** by `ADR-0012-telegram-private-chat-per-player.md` (groups replaced by a private chat per player; "no player login" still holds)
* **Supersedes:** the player-login parts of the M1 requirements (players sign in and complete web onboarding)
* **Amends:** `ADR-0008-telegram-instead-of-whatsapp.md` (private chat → one group per player)

### Date

2026-11-15

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Context

Players had to create an account, log in, and complete onboarding (subscription, health
declaration, contract) before anything worked, and Telegram was an optional add-on linked
through a private chat. In practice players live in chat apps: asking them to log in to a
website is friction, and the coach could not see the conversation the bot had with the player.

### Decision

1. **Players never log in.** The coach adds a player in the web app with name and sex only
   (email and password are now optional in the database and absent for these players).
2. **One Telegram group per player:** the bot, the player and the coach. The coach links his own
   Telegram once (private chat, `/start <code>`), creates the group, adds the bot as admin and sends
   `/link <code>`; the bot creates the group invite link for the player.
3. **Messages in the group:** the player's measurements are saved; free-text messages become
   questions for the coach; videos are stored for squat review; on first contact the bot asks the
   player's age, height and goal (each skippable). The coach's own messages are never processed as
   the player's data and count as replies to his open questions.
4. **AI drafts go to the coach privately** (Approve / Edit / Reject buttons) and are also listed in
   the web app; only approved text is posted in the group. Nothing AI-written reaches the player
   without the coach (ADR-0007 unchanged).
5. **The bot runs inside the backend via Telegram's webhook** (`POST /telegram/webhook`, verified with Telegram's secret-token header), so it needs no separate (paid) worker on Render; the polling worker `app/telegram_bot.py` remains for local testing.
6. **Bot ↔ backend is authenticated** with a shared secret header (`X-Bot-Secret`); the old public
   demo endpoints were removed.
7. **Squat videos** are stored privately and reviewed by the coach (reps and errors entered in the
   web app). Server-side pose analysis is not done on Render's free instance (memory); the browser
   squat checker saves results to real players.

### Rejected alternatives

* **Private chat + web inbox:** the coach would have to read and answer from the web app only and
  could not see the conversation in Telegram.
* **One group for all players:** players would see each other's weights and questions.

### Accepted downsides

* One group per player: a coach with many players has many groups.
* Bot privacy mode must be off (`/setprivacy` → Disable) and the bot must be an admin of each group.
* Existing web logins for players keep working, but new players are Telegram-only.

### Verification

* `backend/tests/test_telegram_groups.py` (31 tests): players without login, linking rules,
  message routing, drafts to the coach, approve/reject from Telegram and web, profile questions,
  videos, bot secret, removed endpoints.
