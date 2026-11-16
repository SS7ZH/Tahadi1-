"""What the bot does, independent of how Telegram reaches us (ADR-0011).

Used by both:
* the webhook (Telegram -> POST /telegram/webhook on Render; the production path, free), and
* the polling bot worker (app/telegram_bot.py -> /telegram/* endpoints; handy for local testing).
"""

import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config as agent_config
from app.agents import coach
from app.core.errors import AppError
from app.core.i18n import tr
from app.db.session import get_sessionmaker
from app.models import AgentDraft, ClientProfile, Question, SquatCheck, User
from app.rules.profile import next_step, question_for
from app.services import permissions, storage, telegram_links, telegram_send

log = logging.getLogger("tahadi.telegram")
MAX_VIDEO_BYTES = 20 * 1024 * 1024  # Telegram bots can download files up to 20 MB


def webhook_secret() -> str:
    """Secret Telegram sends back on every webhook call (derived: Telegram allows only [A-Za-z0-9_-])."""
    return hashlib.sha256(f"webhook:{agent_config.TELEGRAM_BOT_SECRET}".encode()).hexdigest()


def link_coach(db: Session, code: str, telegram_user_id: int) -> str:
    user = db.get(User, telegram_links.read_code(code, telegram_links.KIND_COACH))
    if user is None or user.role not in ("trainer", "admin") or not user.is_active or user.deleted_at is not None:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    other = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id, User.id != user.id))
    if other is not None:
        other.telegram_user_id = None  # one Telegram account belongs to one coach: move it
    user.telegram_user_id = telegram_user_id
    db.commit()
    return f"تم ربط حسابك يا {user.full_name} ✅\nستصلك هنا مسودات الردود لتعتمدها أو تعدلها أو ترفضها."


def link_group(db: Session, code: str, chat_id: int, from_user_id: int, invite_url: str | None) -> dict:
    client = db.get(User, telegram_links.read_code(code, telegram_links.KIND_GROUP))
    if client is None or client.profile is None or client.deleted_at is not None:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    coach_user = client.profile.trainer
    if coach_user is None or coach_user.telegram_user_id != from_user_id:
        raise AppError(403, "NOT_PLAYER_COACH", tr("فقط مدرب اللاعب (بعد ربط حسابه) يستطيع ربط المجموعة", "Only the player's coach, with a linked Telegram account, can link the group"))
    if client.profile.telegram_chat_id not in (None, chat_id):
        raise AppError(409, "PLAYER_ALREADY_LINKED", tr("هذا اللاعب مرتبط بمجموعة أخرى؛ ألغِ الربط من صفحته أولًا", "This player is linked to another group; unlink it from his page first"))
    client.profile.telegram_chat_id = chat_id
    if invite_url:
        client.profile.telegram_invite_url = invite_url
    client.profile.telegram_step = next_step(client.profile)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "GROUP_ALREADY_LINKED", tr("هذه المجموعة مرتبطة بلاعب آخر", "This group is already linked to another player")) from None
    first = client.full_name.split()[0]
    welcome = f"أهلًا {first} 👋 هذه مجموعتك مع مدربك في تحدي.\nأرسل وزنك أو خصرك متى ما أردت (مثل: وزني 82، خصري 90)، أو اكتب سؤالك لمدربك، أو أرسل فيديو السكوات."
    step_q = question_for(client.profile.telegram_step)
    return {"reply": welcome + (f"\n\nلنبدأ بملفك:\n{step_q}" if step_q else ""), "client_name": client.full_name}


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


def is_video(data: bytes) -> bool:
    return len(data) > 12 and data[4:8] == b"ftyp"  # MP4 / MOV (what Telegram delivers)


def store_video(db: Session, chat_id: int, from_user_id: int | None, data: bytes) -> str | None:
    """Save a player's squat video for the coach to review. Returns the group reply (None = silent)."""
    profile = db.scalar(select(ClientProfile).where(ClientProfile.telegram_chat_id == chat_id))
    if profile is None:
        return "هذه المجموعة غير مرتبطة بلاعب بعد."
    coach_user = profile.trainer
    if coach_user is not None and from_user_id is not None and coach_user.telegram_user_id == from_user_id:
        return None  # the coach's own video: not a player check-in
    if len(data) > MAX_VIDEO_BYTES:
        return "الفيديو أكبر من 20 ميجابايت، أرسل مقطعًا أقصر 🙏"
    if not is_video(data):
        return "أرسل الفيديو بصيغة MP4 من فضلك."
    path = storage.new_path(profile.user_id, "mp4")
    storage.save(path, data, "video/mp4")
    db.add(SquatCheck(client_id=profile.user_id, source="telegram", status="awaiting_review", video_path=path))
    db.commit()
    if coach_user is not None and coach_user.telegram_user_id is not None:
        telegram_send.send_message(coach_user.telegram_user_id, f"🎥 وصل فيديو سكوات جديد من {profile.user.full_name}. حلّله من صفحة اللاعب في تحدي.")
    return "استلمنا فيديو السكوات ✅ سيراجعه مدربك ويرد عليك."


def decide_draft(db: Session, draft_id: int, action: str, from_user_id: int, text: str | None = None) -> tuple[str, str]:
    """The coach pressed Approve / Reject (or sent edited text). Returns (reply for the coach, draft status)."""
    actor = db.scalar(select(User).where(User.telegram_user_id == from_user_id, User.deleted_at.is_(None)))
    draft = db.get(AgentDraft, draft_id)
    if actor is None or actor.role not in ("trainer", "admin") or draft is None:
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    client = db.get(User, draft.client_id)
    if client is None or not permissions.can_access_client(actor, client):
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    try:
        if action == "approve":
            draft = coach.approve(db, draft, client, actor, text, telegram_send.send_telegram_message)
            note = "✅ تم الاعتماد والإرسال للمجموعة" if draft.telegram_sent else "✅ تم الاعتماد (تعذر الإرسال للمجموعة)"
        else:
            draft = coach.reject(db, draft, client, actor)
            note = "❌ تم الرفض، لن تُرسل"
    except coach.DraftNotPending:
        return "تم اتخاذ قرار بشأن هذه المسودة مسبقًا", draft.status
    return note, draft.status
