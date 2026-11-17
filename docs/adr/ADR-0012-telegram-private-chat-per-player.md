# ADR-0012 — Each player chats with the bot privately; the coach answers from his own chat

### Status

* **Proposed** (becomes Accepted once both team members approve the PR)
* **Supersedes:** the group parts of `ADR-0011-telegram-groups-no-player-login.md` (one group per player)
* **Keeps:** ADR-0011's "players never log in" and ADR-0007's "nothing AI-written reaches the player without the coach"

### Date

2026-11-17

### Deciders

* Saeed Alzahrani
* Muhanad Alhilal

### Context

With one Telegram group per player (ADR-0011) the coach had to create a group, add the bot as
admin, send `/link <code>` and then invite the player: many steps for every new player. Coaches
want to add a player and send him one link.

### Decision

1. **Personal link per player.** The coach adds a player in the web app (name and sex) and gets a
   personal link `https://t.me/<bot>?start=<code>` (signed, kind `CLIENT`, valid 7 days by default).
   The player opens it, presses Start, and chats with the bot in a private chat. No group, no admin
   rights, no `/link` command, no bot privacy setting.
2. **Everything is forwarded to the coach's private chat with the bot**, tagged `👤 name · #c<id>`:
   the player's text (with the bot's automatic reply), photos and videos (copied with
   `copyMessage`). The coach is told when a player opens his link.
3. **The coach answers with Telegram's Reply** on any forwarded message (or on a draft); the bot
   sends the text to that player and records it as the answer to his open question.
4. **AI drafts** still go to the coach privately with Approve / Edit / Reject buttons and are listed
   in the web app; only approved text reaches the player.
5. **Photos and videos stay on Telegram.** The database keeps Telegram's `file_id`
   (`client_photos`, `squat_checks.telegram_file_id`); the web app shows them through short-lived
   signed links (`/api/v1/telegram-files/...`, 10 minutes) that stream the file from Telegram. No
   file storage is needed.
6. **Groups are removed** from the app: group messages are ignored, the group-code endpoint and the
   polling worker `app/telegram_bot.py` are deleted. The bot runs only via the webhook.

### Rejected alternatives

* **Keep groups as an option:** two flows to support and explain; the group flow was the friction.
* **Store media in Supabase Storage:** extra setup and cost; Telegram already keeps the files.

### Accepted downsides

* The coach sees players' messages in one chat with the bot, not one chat per player; the
  `#c<id>` tag and Reply keep answers going to the right player.
* Bots can download files up to 20 MB, so larger videos are forwarded but cannot be shown in the
  web app.
* Media links depend on Telegram keeping the file; old file ids can expire on Telegram's side.

### Verification

* `backend/tests/test_telegram_webhook.py` (31 tests): webhook secret, removed endpoints, personal
  links and linking rules, unlink and relink, forwarding to the coach, Reply routing (including
  another coach being refused), draft buttons and web approval, photos and videos recorded and
  served through signed links (tampered links refused), profile questions.
