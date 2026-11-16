"""Signed, expiring codes for Telegram linking (ADR-0011).

* coach code  - opened as t.me/<bot>?start=<code> in a private chat: links the coach's own Telegram account
* group code  - sent by the coach as "/link <code>" inside the player's group: links that group to the player

Codes are HMAC-signed with JWT_SECRET, carry their kind, subject id and expiry, and use only
[A-Za-z0-9_-] (Telegram's allowed characters for /start parameters).
"""

import base64
import hashlib
import hmac
import struct
import time

from app import config as agent_config
from app.core.config import settings
from app.core.errors import AppError
from app.core.i18n import tr

KIND_COACH = 1
KIND_GROUP = 2
_LAYOUT = ">BIQ"  # kind, subject id, expires_at
_PAYLOAD = struct.calcsize(_LAYOUT)  # 13 bytes
_SIG = 12


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _sign(payload: bytes) -> bytes:
    return hmac.new(settings.JWT_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()[:_SIG]


def make_code(kind: int, subject_id: int, now: int | None = None) -> tuple[str, int]:
    expires_at = (now or int(time.time())) + agent_config.TELEGRAM_LINK_TTL_HOURS * 3600
    payload = struct.pack(_LAYOUT, kind, subject_id, expires_at)
    return _b64(payload + _sign(payload)), expires_at


def read_code(code: str, kind: int, now: int | None = None) -> int:
    """Subject id of a valid code of this kind. 400 if invalid or of another kind, 410 if expired."""
    invalid = AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    try:
        raw = base64.urlsafe_b64decode(code + "=" * (-len(code) % 4))
    except (ValueError, TypeError):
        raise invalid from None
    if len(raw) != _PAYLOAD + _SIG:
        raise invalid
    payload, signature = raw[:_PAYLOAD], raw[_PAYLOAD:]
    if not hmac.compare_digest(signature, _sign(payload)):
        raise invalid
    code_kind, subject_id, expires_at = struct.unpack(_LAYOUT, payload)
    if code_kind != kind:
        raise invalid
    if expires_at <= (now or int(time.time())):
        raise AppError(410, "TELEGRAM_CODE_EXPIRED", tr("انتهت صلاحية الرمز، اطلب رمزًا جديدًا", "This code has expired, ask for a new one"))
    return subject_id


def coach_start_url(code: str) -> str:
    return f"https://t.me/{agent_config.TELEGRAM_BOT_USERNAME}?start={code}"
