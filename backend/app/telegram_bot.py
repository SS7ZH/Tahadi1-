"""Run the Telegram polling worker and forward messages to the Tahadi API."""

import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

logger = logging.getLogger("tahadi.telegram_bot")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is not None:
        chat = update.effective_chat
        if chat is None or chat.type != "private":
            await message.reply_text("افتح رابط الربط في محادثة خاصة مع البوت.")
            return
        if context.args:
            backend_url = context.application.bot_data["backend_url"]
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    response = await client.post(
                        f"{backend_url}/telegram/link/claim",
                        json={"token": context.args[0], "chat_id": chat.id},
                    )
                    response.raise_for_status()
                    reply = response.json().get("reply", "تم ربط حساب تيليجرام بنجاح ✅")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 410:
                    reply = "انتهت صلاحية رابط الربط. اطلب رابطاً جديداً من مدربك."
                elif exc.response.status_code == 409:
                    reply = "هذا الرابط مستخدم أو أن حساب العميل مربوط مسبقاً."
                else:
                    reply = "تعذر إكمال الربط. اطلب رابطاً جديداً من مدربك."
            except httpx.HTTPError:
                logger.exception("Could not complete Telegram account linking")
                reply = "تعذر الاتصال بالخادم لإكمال الربط. حاول مرة أخرى."
            await message.reply_text(reply)
            return
        await message.reply_text("أهلًا بك في تحدي! أرسل وزنك بهذا الشكل: وزني ٨٢٫٥")


async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    if chat.type != "private":
        await message.reply_text("أرسل /id في محادثة خاصة مع البوت.")
        return
    await message.reply_text(f"رقم محادثتك في تيليجرام: {chat.id}")


async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None or not message.text:
        return

    backend_url = context.application.bot_data["backend_url"]
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{backend_url}/telegram/message",
                json={"chat_id": chat.id, "text": message.text},
            )
            response.raise_for_status()
            reply = response.json().get("reply")
            if not isinstance(reply, str) or not reply:
                raise ValueError("Backend response did not contain a reply")
    except (httpx.HTTPError, ValueError):
        logger.exception("Could not forward Telegram message to the backend")
        await message.reply_text("تعذر معالجة رسالتك الآن. حاول مرة أخرى لاحقًا.")
        return

    await message.reply_text(reply)


def main() -> None:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before starting the bot")

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    request_settings = {
        "connect_timeout": 30,
        "read_timeout": 30,
        "write_timeout": 30,
        "pool_timeout": 30,
    }
    application = (
        Application.builder()
        .token(token)
        .request(HTTPXRequest(**request_settings))
        .get_updates_request(HTTPXRequest(**request_settings))
        .build()
    )
    application.bot_data["backend_url"] = backend_url
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("id", show_chat_id))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message)
    )
    application.run_polling(bootstrap_retries=5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()