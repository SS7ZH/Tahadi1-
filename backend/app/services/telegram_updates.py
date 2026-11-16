"""Handle one Telegram update delivered by webhook (ADR-0011): the bot runs inside the backend.

Private chat with a coach:
  /start <code>                 link the coach's Telegram
  ✏️ on a draft                 the bot asks for the new text as a reply ("#<draft id>" in the prompt)
  reply to that prompt          approve the draft with the edited text
Player's group:
  /link <code>                  (coach) link the group to the player, create the invite link
  text                          measurements / profile answers / questions
  video                         squat video for review
Buttons (callback_query):       approve:<id> / reject:<id> / edit:<id>
"""

import logging
import re

from app.agents.intake import process_message
from app.core.errors import AppError
from app.db.session import get_sessionmaker
from app.services import telegram_core, telegram_send

log = logging.getLogger("tahadi.telegram")

COACH_HELP = (
    "أهلًا بك في تحدي 👋\n"
    "• للمدرب: افتح رابط ربط حسابك من صفحتك في تحدي.\n"
    "• للاعب: مدربك سيضيفك إلى مجموعتك الخاصة."
)
EDIT_PROMPT = "✏️ تعديل المسودة #{id}\nاكتب نص الرد بعد التعديل كردّ (Reply) على هذه الرسالة، وسيُرسل للاعب مباشرة."
_EDIT_RE = re.compile(r"تعديل المسودة #(\d+)")


def _error_text(exc: AppError) -> str:
    return str(exc.detail) if getattr(exc, "detail", None) else "تعذر إكمال الطلب."


def _command(text: str) -> tuple[str, str]:
    """('/link', 'CODE') from '/link@tahadi_coach_bot CODE'."""
    head, _, rest = text.strip().partition(" ")
    return head.split("@", 1)[0].lower(), rest.strip()


def handle_update(update: dict) -> None:
    try:
        if "callback_query" in update:
            _on_button(update["callback_query"])
        elif "message" in update:
            _on_message(update["message"])
    except Exception:  # noqa: BLE001 - one bad update must never break the webhook
        log.exception("Telegram update %s failed", update.get("update_id"))


# ------------------------------------------------------------------ buttons

def _on_button(query: dict) -> None:
    user_id = (query.get("from") or {}).get("id")
    action, _, raw_id = (query.get("data") or "").partition(":")
    if not user_id or not raw_id.isdigit() or action not in ("approve", "reject", "edit"):
        return
    draft_id = int(raw_id)
    if action == "edit":
        telegram_send.answer_callback(query["id"], "اكتب النص المعدّل كرد على الرسالة التالية")
        telegram_send.send_force_reply(user_id, EDIT_PROMPT.format(id=draft_id))
        return
    with get_sessionmaker()() as db:
        try:
            note, _ = telegram_core.decide_draft(db, draft_id, action, user_id)
            telegram_send.answer_callback(query["id"], note)
        except AppError as exc:
            telegram_send.answer_callback(query["id"], _error_text(exc), alert=True)


# ------------------------------------------------------------------ messages

def _on_message(message: dict) -> None:
    chat = message.get("chat") or {}
    chat_id, chat_type = chat.get("id"), chat.get("type")
    user_id = (message.get("from") or {}).get("id")
    if chat_id is None or (message.get("from") or {}).get("is_bot"):
        return
    if chat_type == "private":
        _on_private(chat_id, user_id, message)
    elif chat_type in ("group", "supergroup"):
        _on_group(chat_id, user_id, message)


def _on_private(chat_id: int, user_id: int | None, message: dict) -> None:
    text = message.get("text") or ""
    if text.startswith("/"):
        cmd, arg = _command(text)
        if cmd == "/start" and arg:
            with get_sessionmaker()() as db:
                try:
                    telegram_send.send_message(chat_id, telegram_core.link_coach(db, arg, user_id))
                except AppError as exc:
                    telegram_send.send_message(chat_id, _error_text(exc))
            return
        telegram_send.send_message(chat_id, COACH_HELP)
        return
    replied = (message.get("reply_to_message") or {}).get("text") or ""
    match = _EDIT_RE.search(replied)
    if match and text.strip():
        with get_sessionmaker()() as db:
            try:
                note, _ = telegram_core.decide_draft(db, int(match.group(1)), "approve", user_id, text)
            except AppError as exc:
                note = _error_text(exc)
        telegram_send.send_message(chat_id, note)
        return
    telegram_send.send_message(chat_id, COACH_HELP)


def _on_group(chat_id: int, user_id: int | None, message: dict) -> None:
    text = message.get("text")
    if text and text.startswith("/"):
        cmd, arg = _command(text)
        if cmd == "/link":
            _link_group(chat_id, user_id, arg)
        return  # other commands are ignored in groups
    if text:
        result = process_message(chat_id, text, user_id)
        if result.reply:
            telegram_send.send_message(chat_id, result.reply)
        if result.question_id is not None:
            telegram_core.draft_for_question(result.question_id)
        return
    media = message.get("video") or message.get("document")
    if media and (message.get("video") or (media.get("mime_type") or "").startswith("video/")):
        _video(chat_id, user_id, media)


def _link_group(chat_id: int, user_id: int | None, code: str) -> None:
    if not code:
        telegram_send.send_message(chat_id, "اكتب الأمر مع الرمز من صفحة اللاعب: /link <الرمز>")
        return
    invite_url = telegram_send.create_invite_link(chat_id)
    with get_sessionmaker()() as db:
        try:
            result = telegram_core.link_group(db, code, chat_id, user_id, invite_url)
        except AppError as exc:
            telegram_send.send_message(chat_id, _error_text(exc))
            return
    telegram_send.send_message(chat_id, result["reply"])
    note = f"✅ تم ربط المجموعة باللاعب {result['client_name']}."
    note += f"\nأرسل له رابط الانضمام:\n{invite_url}" if invite_url else "\nاجعل البوت مشرفًا في المجموعة ليُنشئ رابط دعوة، أو أضف اللاعب يدويًا."
    telegram_send.send_message(user_id, note)


def _video(chat_id: int, user_id: int | None, media: dict) -> None:
    if (media.get("file_size") or 0) > telegram_core.MAX_VIDEO_BYTES:
        telegram_send.send_message(chat_id, "الفيديو أكبر من 20 ميجابايت، أرسل مقطعًا أقصر 🙏")
        return
    data = telegram_send.download_file(media["file_id"], telegram_core.MAX_VIDEO_BYTES)
    if data is None:
        telegram_send.send_message(chat_id, "تعذر استلام الفيديو الآن. حاول مرة أخرى لاحقًا.")
        return
    with get_sessionmaker()() as db:
        reply = telegram_core.store_video(db, chat_id, user_id, data)
    if reply:
        telegram_send.send_message(chat_id, reply)
