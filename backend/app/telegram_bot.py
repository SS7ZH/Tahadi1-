"""Tahadi Telegram bot worker (polling). One group per player: bot + player + coach (ADR-0011).

Private chat with a coach:
  /start <code>      links the coach's Telegram account (code from the web app)
  draft messages     arrive here with Approve / Edit / Reject buttons; Edit = send the new text next
Player's group:
  /link <code>       (coach only) links the group to the player and creates the group invite link
  text messages      forwarded to the backend: measurements, profile answers, questions
  videos             forwarded to the backend for squat review

Every backend call carries the X-Bot-Secret header. In @BotFather turn privacy mode off
(/setprivacy -> Disable) and make the bot an admin of each group so it can read messages
and create invite links.

Env: TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_SECRET, BACKEND_URL (e.g. https://tahadi1.onrender.com).
"""

import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

logger = logging.getLogger("tahadi.telegram_bot")
MAX_VIDEO_BYTES = 20 * 1024 * 1024
SERVER_DOWN = "تعذر الاتصال بالخادم الآن. حاول مرة أخرى بعد قليل."

COACH_HELP = (
    "أهلًا بك في تحدي 👋\n"
    "• للمدرب: افتح رابط ربط حسابك من صفحتك في تحدي.\n"
    "• للاعب: مدربك سيضيفك إلى مجموعتك الخاصة."
)


async def call_backend(context: ContextTypes.DEFAULT_TYPE, path: str, **kwargs) -> tuple[int, dict]:
    """POST to the backend with the bot secret. Returns (status, json body); (0, {}) when unreachable."""
    data = context.application.bot_data
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(f"{data['backend_url']}{path}", headers={"X-Bot-Secret": data["secret"]}, **kwargs)
        try:
            return r.status_code, r.json()
        except ValueError:
            return r.status_code, {}
    except httpx.HTTPError:
        logger.exception("Backend call %s failed", path)
        return 0, {}


def _error_text(status: int, body: dict) -> str:
    if status == 0:
        return SERVER_DOWN
    return body.get("detail") or "تعذر إكمال الطلب."


# ------------------------------------------------------------------ private chat (coach)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.type != "private":
        await message.reply_text("لربط هذه المجموعة بلاعب، يرسل المدرب: /link <الرمز>")
        return
    if not context.args:
        await message.reply_text(COACH_HELP)
        return
    status, body = await call_backend(context, "/telegram/link/coach", json={"code": context.args[0], "telegram_user_id": user.id})
    await message.reply_text(body.get("reply") if status == 200 else _error_text(status, body))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query, user = update.callback_query, update.effective_user
    if query is None or user is None or not query.data or ":" not in query.data:
        return
    action, _, draft_id = query.data.partition(":")
    if action == "edit":
        context.user_data["editing_draft"] = int(draft_id)
        await query.answer()
        await context.bot.send_message(user.id, "✏️ أرسل الآن نص الرد بعد التعديل، وسيُرسل للاعب مباشرة.")
        return
    status, body = await call_backend(
        context, "/telegram/draft-decision", json={"draft_id": int(draft_id), "action": action, "from_user_id": user.id}
    )
    await query.answer(body.get("reply") if status == 200 else _error_text(status, body), show_alert=status != 200)


async def private_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, user = update.effective_message, update.effective_user
    if message is None or user is None or not message.text:
        return
    draft_id = context.user_data.pop("editing_draft", None)
    if draft_id is None:
        await message.reply_text(COACH_HELP)
        return
    status, body = await call_backend(
        context, "/telegram/draft-decision",
        json={"draft_id": draft_id, "action": "approve", "from_user_id": user.id, "text": message.text},
    )
    await message.reply_text(body.get("reply") if status == 200 else _error_text(status, body))


# ------------------------------------------------------------------ player's group

async def link_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if message is None or chat is None or user is None:
        return
    if chat.type not in ("group", "supergroup"):
        await message.reply_text("أرسل /link <الرمز> داخل مجموعة اللاعب.")
        return
    if not context.args:
        await message.reply_text("اكتب الأمر مع الرمز من صفحة اللاعب: /link <الرمز>")
        return
    invite_url = None
    try:
        invite = await context.bot.create_chat_invite_link(chat.id, name="تحدي")
        invite_url = invite.invite_link
    except Exception:  # noqa: BLE001 - the bot is not an admin yet; linking still works
        logger.info("Could not create an invite link for chat %s (bot not admin?)", chat.id)
    status, body = await call_backend(
        context, "/telegram/link/group",
        json={"code": context.args[0], "chat_id": chat.id, "from_user_id": user.id, "invite_url": invite_url},
    )
    if status != 200:
        await message.reply_text(_error_text(status, body))
        return
    await message.reply_text(body["reply"])
    note = f"✅ تم ربط المجموعة باللاعب {body.get('client_name', '')}."
    note += f"\nأرسل له رابط الانضمام:\n{invite_url}" if invite_url else "\nاجعل البوت مشرفًا في المجموعة ليُنشئ رابط دعوة، أو أضف اللاعب يدويًا."
    try:
        await context.bot.send_message(user.id, note)
    except Exception:  # noqa: BLE001 - coach has not started the bot privately
        pass


async def group_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if message is None or chat is None or not message.text:
        return
    status, body = await call_backend(
        context, "/telegram/message",
        json={"chat_id": chat.id, "text": message.text, "from_user_id": user.id if user else None},
    )
    if status != 200:
        await message.reply_text("تعذر معالجة رسالتك الآن. حاول مرة أخرى لاحقًا." if status else SERVER_DOWN)
        return
    if body.get("reply"):
        await message.reply_text(body["reply"])


async def group_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message, chat, user = update.effective_message, update.effective_chat, update.effective_user
    if message is None or chat is None:
        return
    media = message.video or message.document
    if media is None:
        return
    if (media.file_size or 0) > MAX_VIDEO_BYTES:
        await message.reply_text("الفيديو أكبر من 20 ميجابايت، أرسل مقطعًا أقصر 🙏")
        return
    file = await context.bot.get_file(media.file_id)
    data = bytes(await file.download_as_bytearray())
    status, body = await call_backend(
        context, "/telegram/video",
        data={"chat_id": str(chat.id), "from_user_id": str(user.id) if user else ""},
        files={"file": ("squat.mp4", data, "video/mp4")},
    )
    if status != 200:
        await message.reply_text("تعذر استلام الفيديو الآن. حاول مرة أخرى لاحقًا." if status else SERVER_DOWN)
        return
    if body.get("reply"):
        await message.reply_text(body["reply"])


def main() -> None:
    load_dotenv()
    token, secret = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_BOT_SECRET")
    if not token or not secret:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_SECRET before starting the bot")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    timeouts = {"connect_timeout": 30, "read_timeout": 30, "write_timeout": 60, "pool_timeout": 30}
    app = (
        Application.builder().token(token)
        .request(HTTPXRequest(**timeouts)).get_updates_request(HTTPXRequest(**timeouts)).build()
    )
    app.bot_data["backend_url"] = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    app.bot_data["secret"] = secret

    groups = filters.ChatType.GROUPS
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("link", link_group))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, private_text))
    app.add_handler(MessageHandler(groups & filters.TEXT & ~filters.COMMAND, group_text))
    app.add_handler(MessageHandler(groups & (filters.VIDEO | filters.Document.VIDEO), group_video))
    app.run_polling(bootstrap_retries=5, allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
