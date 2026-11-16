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
