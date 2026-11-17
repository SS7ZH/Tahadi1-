"""What the bot does (ADR-0012): every player talks to the bot in a private chat.

* The coach links his own Telegram once (/start <coach code>).
* Each player gets a personal link (/start <player code>) and chats with the bot privately.
* Everything the player sends is processed (measurements, profile answers, questions, photos,
  videos) and forwarded to the coach's private chat with a "👤 name · #c<id>" header.
* The coach answers a player by replying (Telegram "Reply") to that forwarded message.
* AI drafts for questions reach the coach with Approve / Edit / Reject buttons.
"""

import hashlib
import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config as agent_config
from app.agents import coach
from app.core.errors import AppError
from app.core.i18n import tr
from app.db.session import get_sessionmaker
from app.models import AgentDraft, ClientPhoto, ClientProfile, Question, SquatCheck, User
from app.rules.profile import next_step, question_for
from app.services import permissions, telegram_links, telegram_send

log = logging.getLogger("tahadi.telegram")
MAX_FILE_BYTES = 20 * 1024 * 1024  # Telegram bots can download files up to 20 MB
_CLIENT_TAG = re.compile(r"#c(\d+)")


def webhook_secret() -> str:
    """Secret Telegram sends back on every webhook call (derived: Telegram allows only [A-Za-z0-9_-])."""
    return hashlib.sha256(f"webhook:{agent_config.TELEGRAM_BOT_SECRET}".encode()).hexdigest()


def client_tag(client: User) -> str:
    """Header on everything forwarded to the coach; replying to it answers this player."""
    return f"👤 {client.full_name} · #c{client.id}"


def client_id_from(text: str | None) -> int | None:
    match = _CLIENT_TAG.search(text or "")
    return int(match.group(1)) if match else None


def coach_by_telegram(db: Session, telegram_user_id: int | None) -> User | None:
    if telegram_user_id is None:
        return None
    return db.scalar(
        select(User).where(User.telegram_user_id == telegram_user_id, User.role.in_(("trainer", "admin")), User.deleted_at.is_(None))
    )


def client_by_chat(db: Session, chat_id: int) -> User | None:
    profile = db.scalar(select(ClientProfile).where(ClientProfile.telegram_chat_id == chat_id))
    if profile is None or profile.user.deleted_at is not None or not profile.user.is_active:
        return None
    return profile.user


# ------------------------------------------------------------------ linking

def link_coach(db: Session, code: str, telegram_user_id: int) -> str:
    user = db.get(User, telegram_links.read_code(code, telegram_links.KIND_COACH))
    if user is None or user.role not in ("trainer", "admin") or not user.is_active or user.deleted_at is not None:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    other = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id, User.id != user.id))
    if other is not None:
        other.telegram_user_id = None  # one Telegram account belongs to one coach: move it
    user.telegram_user_id = telegram_user_id
    db.commit()
    return (
        f"تم ربط حسابك يا {user.full_name} ✅\n"
        "ستصلك هنا رسائل لاعبيك وصورهم وفيديوهاتهم.\n"
        "للرد على لاعب: اضغط «رد» (Reply) على رسالته واكتب ردك.\n"
        "ومسودات الردود الذكية تصلك بأزرار اعتماد / تعديل / رفض."
    )


def link_client(db: Session, code: str, chat_id: int) -> tuple[str, User]:
    """The player opened his personal link. Returns (welcome text, player)."""
    client = db.get(User, telegram_links.read_code(code, telegram_links.KIND_CLIENT))
    if client is None or client.profile is None or client.deleted_at is not None or not client.is_active:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرابط غير صحيح، اطلب رابطًا جديدًا من مدربك", "Invalid link, ask your coach for a new one"))
    if client.profile.telegram_chat_id not in (None, chat_id):
        raise AppError(409, "PLAYER_ALREADY_LINKED", tr("هذا اللاعب مربوط بحساب تيليجرام آخر؛ اطلب من مدربك إلغاء الربط أولًا", "This player is linked to another Telegram account; ask your coach to unlink it first"))
    other = db.scalar(select(ClientProfile).where(ClientProfile.telegram_chat_id == chat_id, ClientProfile.user_id != client.id))
    if other is not None:
        raise AppError(409, "CHAT_ALREADY_LINKED", tr("حساب تيليجرام هذا مربوط بلاعب آخر", "This Telegram account is already linked to another player"))
    first_time = client.profile.telegram_chat_id is None
    client.profile.telegram_chat_id = chat_id
    if first_time:
        client.profile.telegram_step = next_step(client.profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "CHAT_ALREADY_LINKED", tr("حساب تيليجرام هذا مربوط بلاعب آخر", "This Telegram account is already linked to another player")) from None
    coach_user = client.profile.trainer
    coach_name = f" {coach_user.full_name}" if coach_user else ""
    welcome = (
        f"أهلًا {client.full_name.split()[0]} 👋 أنا مساعد مدربك{coach_name} في تحدي.\n"
        "أرسل لي هنا وزنك أو خصرك متى ما أردت (مثل: وزني 82، خصري 90)، أو اكتب سؤالك لمدربك، أو أرسل صورة أو فيديو السكوات."
    )
    step_q = question_for(client.profile.telegram_step)
    return welcome + (f"\n\nلنبدأ بملفك:\n{step_q}" if step_q else ""), client


# ------------------------------------------------------------------ to the coach

def forward_text(client: User, text: str, bot_reply: str | None) -> None:
    coach_user = coach.coach_of(client)
    if coach_user is None or coach_user.telegram_user_id is None:
        return
    body = f"{client_tag(client)}\n{text}"
    if bot_reply:
        body += f"\n\n🤖 {bot_reply}"
    telegram_send.send_message(coach_user.telegram_user_id, body)


def forward_media(client: User, chat_id: int, message_id: int, note: str, caption: str | None = None) -> None:
    coach_user = coach.coach_of(client)
    if coach_user is None or coach_user.telegram_user_id is None:
        return
    header = f"{client_tag(client)}\n{note}" + (f"\n{caption}" if caption else "")
    telegram_send.copy_message(coach_user.telegram_user_id, chat_id, message_id, header)


def coach_reply(db: Session, coach_user: User, client_id: int, text: str) -> str:
    """The coach replied to a forwarded message: send it to that player and record it."""
    from app.agents.intake import record_coach_reply  # local import avoids an import cycle

    client = db.get(User, client_id)
    if client is None or client.profile is None or not permissions.can_access_client(coach_user, client):
        return "لا يمكنك الرد على هذا اللاعب."
    chat_id = client.profile.telegram_chat_id
    if chat_id is None:
        return f"{client.full_name} غير مربوط بتيليجرام."
    if not telegram_send.send_telegram_message(chat_id, text):
        return f"تعذر الإرسال إلى {client.full_name}، حاول مرة أخرى."
    record_coach_reply(client.id, coach_user.id, text)
    return f"✅ أُرسل إلى {client.full_name}"


def draft_for_question(question_id: int) -> None:
    """Write an AI draft for a player's question and send it to the coach privately."""
    with get_sessionmaker()() as db:
        question = db.get(Question, question_id)
        if question is None:
            return
        client = db.get(User, question.client_id)
        try:
            draft = coach.create_draft(db, client, None, question)
            coach.notify_coach(db, draft, client, question)
        except Exception:  # noqa: BLE001 - never break the bot reply because of the draft
            log.exception("Could not draft a reply for question %s", question_id)


# ------------------------------------------------------------------ media

def record_video(db: Session, client: User, file_id: str) -> str:
    db.add(SquatCheck(client_id=client.id, source="telegram", status="awaiting_review", telegram_file_id=file_id))
    db.commit()
    return "استلمنا فيديو السكوات ✅ سيراجعه مدربك ويرد عليك."


def record_photo(db: Session, client: User, file_id: str, caption: str | None) -> str:
    db.add(ClientPhoto(client_id=client.id, telegram_file_id=file_id, caption=(caption or "")[:2000] or None))
    db.commit()
    return "استلمنا صورتك ✅ سيطّلع عليها مدربك."


# ------------------------------------------------------------------ drafts

def decide_draft(db: Session, draft_id: int, action: str, from_user_id: int, text: str | None = None) -> tuple[str, str]:
    """The coach pressed Approve / Reject (or sent edited text). Returns (reply for the coach, draft status)."""
    actor = coach_by_telegram(db, from_user_id)
    draft = db.get(AgentDraft, draft_id)
    if actor is None or draft is None:
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    client = db.get(User, draft.client_id)
    if client is None or not permissions.can_access_client(actor, client):
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    try:
        if action == "approve":
            draft = coach.approve(db, draft, client, actor, text, telegram_send.send_telegram_message)
            note = f"✅ تم الاعتماد والإرسال إلى {client.full_name}" if draft.telegram_sent else "✅ تم الاعتماد (تعذر الإرسال)"
        else:
            draft = coach.reject(db, draft, client, actor)
            note = "❌ تم الرفض، لن تُرسل"
    except coach.DraftNotPending:
        return "تم اتخاذ قرار بشأن هذه المسودة مسبقًا", draft.status
    return note, draft.status
