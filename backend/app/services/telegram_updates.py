"""Handle one Telegram update delivered by webhook (ADR-0012): private chats only, no groups.

A private chat is one of:
* a coach (his Telegram is linked)  - receives players' messages, drafts and media; answers with Reply
* a player (his chat is linked)     - measurements, profile answers, questions, photos, videos
* anyone else                       - /start <code> links a coach or a player; otherwise a short help text
Buttons (callback_query): approve:<id> / reject:<id> / edit:<id> on AI drafts.
"""

import logging
import re

from app.agents.intake import process_message
from app.core.errors import AppError
from app.db.session import get_sessionmaker
from app.services import telegram_core, telegram_links, telegram_send

log = logging.getLogger("tahadi.telegram")

HELP = (
    "أهلًا بك في تحدي 👋\n"
    "• للاعب: افتح الرابط الخاص الذي أرسله لك مدربك.\n"
    "• للمدرب: اربط حسابك من صفحتك في موقع تحدي."
)
COACH_HELP = (
    "للرد على لاعب: اضغط «رد» (Reply) على رسالته أو على مسودة الرد، واكتب ردك وسيصله مباشرة.\n"
    "مسودات الردود الذكية تصلك بأزرار ✅ اعتماد / ✏️ تعديل / ❌ رفض."
)
EDIT_PROMPT = "✏️ تعديل المسودة #{id}\nاكتب نص الرد بعد التعديل كردّ (Reply) على هذه الرسالة، وسيُرسل للاعب مباشرة."
_EDIT_RE = re.compile(r"تعديل المسودة #(\d+)")


def _error_text(exc: AppError) -> str:
    return str(exc.detail) if getattr(exc, "detail", None) else "تعذر إكمال الطلب."


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
    sender = message.get("from") or {}
    if chat.get("type") != "private" or sender.get("is_bot") or chat.get("id") is None:
        return  # groups are no longer used (ADR-0012)
    chat_id, user_id = chat["id"], sender.get("id")
    text = (message.get("text") or "").strip()

    if text.startswith("/start"):
        _start(chat_id, user_id, text.partition(" ")[2].strip())
        return

    with get_sessionmaker()() as db:
        coach_user = telegram_core.coach_by_telegram(db, user_id)
        if coach_user is not None:
            _from_coach(db, coach_user, chat_id, message, text)
            return
        client = telegram_core.client_by_chat(db, chat_id)
        if client is None:
            telegram_send.send_message(chat_id, HELP)
            return
        _from_player(db, client, chat_id, message, text)


def _start(chat_id: int, user_id: int | None, code: str) -> None:
    if not code:
        telegram_send.send_message(chat_id, HELP)
        return
    kind = telegram_links.kind_of(code)
    with get_sessionmaker()() as db:
        try:
            if kind == telegram_links.KIND_COACH:
                telegram_send.send_message(chat_id, telegram_core.link_coach(db, code, user_id))
                return
            welcome, client = telegram_core.link_client(db, code, chat_id)
        except AppError as exc:
            telegram_send.send_message(chat_id, _error_text(exc))
            return
        telegram_send.send_message(chat_id, welcome)
        telegram_core.forward_text(client, "✅ فتح رابطه وبدأ المحادثة مع البوت.", None)


def _from_coach(db, coach_user, chat_id: int, message: dict, text: str) -> None:
    replied = (message.get("reply_to_message") or {})
    replied_text = replied.get("text") or replied.get("caption") or ""
    edit = _EDIT_RE.search(replied_text)
    if edit and text:
        try:
            note, _ = telegram_core.decide_draft(db, int(edit.group(1)), "approve", coach_user.telegram_user_id, text)
        except AppError as exc:
            note = _error_text(exc)
        telegram_send.send_message(chat_id, note)
        return
    client_id = telegram_core.client_id_from(replied_text)
    if client_id is not None and text:
        telegram_send.send_message(chat_id, telegram_core.coach_reply(db, coach_user, client_id, text))
        return
    telegram_send.send_message(chat_id, COACH_HELP)


def _from_player(db, client, chat_id: int, message: dict, text: str) -> None:
    message_id = message.get("message_id")
    caption = message.get("caption")
    if text:
        result = process_message(chat_id, text)
        if result.reply:
            telegram_send.send_message(chat_id, result.reply)
        telegram_core.forward_text(client, text, result.reply if result.question_id is None else None)
        if result.question_id is not None:
            telegram_core.draft_for_question(result.question_id)
        return
    if message.get("photo"):
        file_id = message["photo"][-1]["file_id"]  # the largest size
        reply = telegram_core.record_photo(db, client, file_id, caption)
        telegram_send.send_message(chat_id, reply)
        telegram_core.forward_media(client, chat_id, message_id, "📷 صورة", caption)
        return
    media = message.get("video") or message.get("document")
    if media and (message.get("video") or (media.get("mime_type") or "").startswith("video/")):
        reply = telegram_core.record_video(db, client, media["file_id"])
        telegram_send.send_message(chat_id, reply)
        telegram_core.forward_media(client, chat_id, message_id, "🎥 فيديو سكوات (سجّل التحليل من صفحة اللاعب)", caption)
        return
    telegram_send.send_message(chat_id, "أرسل نصًا أو صورة أو فيديو من فضلك 🙏")
