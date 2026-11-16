"""Messages the backend sends through the Telegram Bot API (approved replies, drafts to the coach).

Without TELEGRAM_BOT_TOKEN nothing is sent and every call reports failure, so callers can say so.
"""

import logging

import httpx

from app import config as agent_config

log = logging.getLogger("tahadi.telegram")
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def _call(method: str, payload: dict) -> dict | None:
    token = agent_config.TELEGRAM_BOT_TOKEN
    if not token:
        log.info("TELEGRAM_BOT_TOKEN not set; not calling %s", method)
        return None
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=_TIMEOUT)
        body = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("Telegram %s failed: %s", method, type(exc).__name__)
        return None
    if not body.get("ok"):
        log.warning("Telegram %s refused: %s", method, body.get("description"))
        return None
    return body.get("result")


def send_message(chat_id: int, text: str, buttons: list[list[dict]] | None = None) -> int | None:
    """Send a message; returns its message_id, or None if it could not be sent."""
    payload: dict = {"chat_id": chat_id, "text": text}
    if buttons:
        payload["reply_markup"] = {"inline_keyboard": buttons}
    result = _call("sendMessage", payload)
    return result.get("message_id") if isinstance(result, dict) else None


def send_telegram_message(chat_id: int, text: str) -> bool:
    return send_message(chat_id, text) is not None


def edit_message(chat_id: int, message_id: int, text: str) -> bool:
    """Replace a message's text and remove its buttons."""
    return _call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text}) is not None


def draft_buttons(draft_id: int) -> list[list[dict]]:
    return [[
        {"text": "✅ اعتماد وإرسال", "callback_data": f"approve:{draft_id}"},
        {"text": "✏️ تعديل", "callback_data": f"edit:{draft_id}"},
        {"text": "❌ رفض", "callback_data": f"reject:{draft_id}"},
    ]]


def send_force_reply(chat_id: int, text: str) -> int | None:
    """A message the coach answers with Telegram's "reply" (used for editing a draft)."""
    result = _call("sendMessage", {"chat_id": chat_id, "text": text, "reply_markup": {"force_reply": True}})
    return result.get("message_id") if isinstance(result, dict) else None


def answer_callback(callback_id: str, text: str, alert: bool = False) -> bool:
    return _call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:190], "show_alert": alert}) is not None


def create_invite_link(chat_id: int) -> str | None:
    """Needs the bot to be an admin of the group."""
    result = _call("createChatInviteLink", {"chat_id": chat_id, "name": "تحدي"})
    return result.get("invite_link") if isinstance(result, dict) else None


def download_file(file_id: str, max_bytes: int) -> bytes | None:
    """Download a file the player sent (Telegram bots can download up to 20 MB)."""
    info = _call("getFile", {"file_id": file_id})
    token = agent_config.TELEGRAM_BOT_TOKEN
    if not isinstance(info, dict) or not info.get("file_path") or not token:
        return None
    if (info.get("file_size") or 0) > max_bytes:
        return None
    try:
        r = httpx.get(f"https://api.telegram.org/file/bot{token}/{info['file_path']}", timeout=httpx.Timeout(60.0, connect=5.0))
    except httpx.HTTPError as exc:
        log.warning("Telegram file download failed: %s", type(exc).__name__)
        return None
    return r.content if r.status_code == 200 else None


def set_webhook(url: str, secret: str) -> dict | None:
    return _call("setWebhook", {"url": url, "secret_token": secret, "allowed_updates": ["message", "callback_query"]})


def delete_webhook() -> dict | None:
    return _call("deleteWebhook", {})


def webhook_info() -> dict | None:
    return _call("getWebhookInfo", {})
