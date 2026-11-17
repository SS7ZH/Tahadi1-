"""Point the Telegram bot at the backend's webhook, or switch back to the polling worker.

Usage (from backend/, with TELEGRAM_BOT_TOKEN, TELEGRAM_BOT_SECRET and BACKEND_URL in .env):
    python -m scripts.set_webhook            # Telegram -> {BACKEND_URL}/telegram/webhook (production)
    python -m scripts.set_webhook --info     # show the current webhook
    python -m scripts.set_webhook --delete   # remove it (Telegram then stops delivering to the backend)

TELEGRAM_BOT_SECRET must be the same value as in Render: the webhook secret is derived from it.
"""

import os
import sys

from app import config
from app.services import telegram_core, telegram_send


def show() -> None:
    info = telegram_send.webhook_info() or {}
    print("webhook url:", info.get("url") or "(none: polling mode)")
    print("pending updates:", info.get("pending_update_count"))
    if info.get("last_error_message"):
        print("last error:", info.get("last_error_message"))


def main() -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_BOT_SECRET:
        sys.exit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_BOT_SECRET in backend/.env first.")
    if "--info" in sys.argv:
        show()
        return
    if "--delete" in sys.argv:
        print("deleted" if telegram_send.delete_webhook() is not None else "failed")
        show()
        return
    base = os.getenv("BACKEND_URL", "").rstrip("/")
    if not base.startswith("https://"):
        sys.exit("Set BACKEND_URL to the https address of the backend (e.g. https://tahadi1.onrender.com).")
    ok = telegram_send.set_webhook(f"{base}/telegram/webhook", telegram_core.webhook_secret())
    print("webhook set" if ok is not None else "failed to set the webhook")
    show()


if __name__ == "__main__":
    main()
