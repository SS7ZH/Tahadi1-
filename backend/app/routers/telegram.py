"""Telegram groups: a coach, a player and the bot in one group per player (ADR-0011).

Web app (coach/admin, under /api/v1):
  GET    /me/telegram                       is my own Telegram linked?
  POST   /me/telegram/link                  link for my private chat with the bot
  GET    /telegram/clients                  my players and whether their group is linked
  POST   /clients/telegram                  add a Telegram-only player (no email/password) + group code
  POST   /clients/{id}/telegram/group-code  new group code
  DELETE /clients/{id}/telegram             unlink the player's group
  GET    /clients/{id}/squat-checks         squat sets (Telegram videos + browser checks)
  POST   /clients/{id}/squat-checks         save a browser squat check for the player
  PATCH  /squat-checks/{id}                 add the analysis to a video awaiting review
  GET    /squat-checks/{id}/video           short-lived link to watch the video

Bot worker only (header X-Bot-Secret, at /telegram):
  POST /telegram/link/coach     /start <code> in a private chat
  POST /telegram/link/group     /link <code> in a player's group
  POST /telegram/message        a text message in a group
  POST /telegram/video          a video in a group
  POST /telegram/draft-decision the coach pressed Approve / Edit / Reject
"""

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, Request, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config as agent_config
from app.agents import coach
from app.agents.intake import process_message
from app.core.deps import require_role
from app.core.errors import AppError, not_found
from app.core.i18n import tr
from app.db.session import get_db, get_sessionmaker
from app.models import AgentDraft, ClientProfile, Question, SquatCheck, User
from app.rules.profile import next_step, question_for
from app.schemas.user import TelegramPlayerCreate
from app.services import audit, permissions, storage, telegram_links, telegram_send, users
from app.services.serializers import user_detail

log = logging.getLogger("tahadi.telegram")
router = APIRouter(tags=["telegram"])
bot_router = APIRouter(prefix="/telegram", tags=["telegram-bot"])
coach_only = require_role("trainer", "admin")

MAX_VIDEO_BYTES = 20 * 1024 * 1024  # Telegram bots can download files up to 20 MB
ERROR_TYPES = {"knees_caving", "shallow_depth", "back_lean"}


# ================================================================ helpers

def _group_code(client: User) -> dict:
    code, expires_at = telegram_links.make_code(telegram_links.KIND_GROUP, client.id)
    return {"group_code": code, "link_command": f"/link {code}", "expires_at": expires_at}


def _accessible_client(db: Session, actor: User, client_id: int) -> User:
    client = permissions.get_accessible_client(db, actor, client_id)
    if client.profile is None:
        raise not_found(tr("اللاعب غير موجود", "Player not found"))
    return client


def _squat_out(c: SquatCheck) -> dict:
    return {
        "id": c.id, "client_id": c.client_id, "source": c.source, "status": c.status, "reps": c.reps,
        "errors": c.errors or [], "confidence": c.confidence, "has_video": bool(c.video_path), "created_at": c.created_at,
    }


def require_bot(x_bot_secret: str | None = Header(default=None)) -> None:
    secret = agent_config.TELEGRAM_BOT_SECRET
    if not secret:
        raise AppError(503, "BOT_NOT_CONFIGURED", tr("ربط البوت غير مهيأ", "The bot connection is not configured"))
    if not x_bot_secret or not hmac.compare_digest(x_bot_secret, secret):
        raise AppError(401, "BOT_SECRET_INVALID", tr("غير مصرح", "Not authorised"))


# ================================================================ web app (coach)

@router.get("/me/telegram")
def my_telegram(actor: User = Depends(coach_only)):
    return {"linked": actor.telegram_user_id is not None, "bot_username": agent_config.TELEGRAM_BOT_USERNAME}


@router.post("/me/telegram/link")
def my_telegram_link(actor: User = Depends(coach_only)):
    code, expires_at = telegram_links.make_code(telegram_links.KIND_COACH, actor.id)
    return {"url": telegram_links.coach_start_url(code), "expires_at": expires_at}


@router.get("/telegram/clients")
def telegram_clients(actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(User).where(User.id.in_(permissions.accessible_client_ids(actor))).order_by(User.full_name)
    ).unique().all()
    return [
        {
            "id": c.id, "name": c.full_name, "linked": c.profile.telegram_chat_id is not None,
            "invite_url": c.profile.telegram_invite_url, "telegram_only": c.email is None,
        }
        for c in rows
        if c.profile is not None
    ]


@router.post("/clients/telegram", status_code=status.HTTP_201_CREATED)
def create_telegram_player(data: TelegramPlayerCreate, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    profile = data.model_dump(include={"sex", "birth_date", "height_cm", "goal", "notes"})
    profile["trainer_id"] = actor.id if actor.role == "trainer" else data.trainer_id
    client = users.create_user(
        db, full_name=data.full_name, email=None, phone=data.phone, password=None, role="client",
        profile=profile, telegram_only=True,
    )
    audit.record(db, actor, "create", "user", client.id, {"role": "client", "telegram_only": True})
    db.commit()
    return {"client": user_detail(client), **_group_code(client)}


@router.post("/clients/{client_id}/telegram/group-code")
def new_group_code(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    return {"linked": client.profile.telegram_chat_id is not None, **_group_code(client)}


@router.delete("/clients/{client_id}/telegram", status_code=status.HTTP_204_NO_CONTENT)
def unlink_group(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    client.profile.telegram_chat_id = None
    client.profile.telegram_invite_url = None
    client.profile.telegram_step = None
    audit.record(db, actor, "update", "client_profile", client.id, {"telegram": "unlinked"})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class SquatCheckIn(BaseModel):
    reps: int = Field(ge=0, le=500)
    errors: list[dict] = Field(default_factory=list, max_length=100)
    confidence: float | None = Field(default=None, ge=0, le=1)


def _clean_errors(errors: list[dict]) -> list[dict]:
    return [{"rep": e.get("rep"), "type": e["type"]} for e in errors if isinstance(e, dict) and e.get("type") in ERROR_TYPES]


@router.get("/clients/{client_id}/squat-checks")
def list_squat_checks(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    rows = db.scalars(
        select(SquatCheck).where(SquatCheck.client_id == client.id).order_by(SquatCheck.created_at.desc(), SquatCheck.id.desc())
    ).all()
    return [_squat_out(c) for c in rows]


@router.post("/clients/{client_id}/squat-checks", status_code=status.HTTP_201_CREATED)
def create_squat_check(client_id: int, data: SquatCheckIn, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    check = SquatCheck(client_id=client.id, source="browser", status="analysed", reps=data.reps,
                       errors=_clean_errors(data.errors), confidence=data.confidence)
    db.add(check)
    db.commit()
    db.refresh(check)
    return _squat_out(check)


@router.patch("/squat-checks/{check_id}")
def review_squat_check(check_id: int, data: SquatCheckIn, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    check = db.get(SquatCheck, check_id)
    if check is None:
        raise not_found(tr("الفحص غير موجود", "Squat check not found"))
    _accessible_client(db, actor, check.client_id)
    check.reps, check.errors, check.confidence, check.status = data.reps, _clean_errors(data.errors), data.confidence, "analysed"
    db.commit()
    db.refresh(check)
    return _squat_out(check)


@router.get("/squat-checks/{check_id}/video")
def squat_video(check_id: int, request: Request, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    check = db.get(SquatCheck, check_id)
    if check is None or not check.video_path:
        raise not_found(tr("لا يوجد فيديو", "No video"))
    _accessible_client(db, actor, check.client_id)
    return {"url": storage.signed_url(check.video_path, str(request.base_url).rstrip("/") + "/api/v1")}


# ================================================================ bot worker

class CoachLinkIn(BaseModel):
    code: str = Field(min_length=10, max_length=64)
    telegram_user_id: int = Field(gt=0)


class GroupLinkIn(BaseModel):
    code: str = Field(min_length=10, max_length=64)
    chat_id: int = Field(lt=0)  # group chat ids are negative
    from_user_id: int = Field(gt=0)
    invite_url: str | None = Field(default=None, max_length=255)


class MessageIn(BaseModel):
    chat_id: int
    text: str = Field(min_length=1, max_length=4096)
    from_user_id: int | None = None


class DecisionIn(BaseModel):
    draft_id: int
    action: str = Field(pattern=r"^(approve|reject)$")
    from_user_id: int = Field(gt=0)
    text: str | None = Field(default=None, max_length=4000)


@bot_router.post("/link/coach", dependencies=[Depends(require_bot)])
def link_coach(data: CoachLinkIn, db: Session = Depends(get_db)):
    user = db.get(User, telegram_links.read_code(data.code, telegram_links.KIND_COACH))
    if user is None or user.role not in ("trainer", "admin") or not user.is_active or user.deleted_at is not None:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    other = db.scalar(select(User).where(User.telegram_user_id == data.telegram_user_id, User.id != user.id))
    if other is not None:
        other.telegram_user_id = None  # one Telegram account belongs to one coach: move it
    user.telegram_user_id = data.telegram_user_id
    db.commit()
    return {"reply": f"تم ربط حسابك يا {user.full_name} ✅\nستصلك هنا مسودات الردود لتعتمدها أو تعدلها أو ترفضها."}


@bot_router.post("/link/group", dependencies=[Depends(require_bot)])
def link_group(data: GroupLinkIn, db: Session = Depends(get_db)):
    client = db.get(User, telegram_links.read_code(data.code, telegram_links.KIND_GROUP))
    if client is None or client.profile is None or client.deleted_at is not None:
        raise AppError(400, "TELEGRAM_CODE_INVALID", tr("الرمز غير صحيح", "Invalid code"))
    coach_user = client.profile.trainer
    if coach_user is None or coach_user.telegram_user_id != data.from_user_id:
        raise AppError(403, "NOT_PLAYER_COACH", tr("فقط مدرب اللاعب (بعد ربط حسابه) يستطيع ربط المجموعة", "Only the player's coach, with a linked Telegram account, can link the group"))
    if client.profile.telegram_chat_id not in (None, data.chat_id):
        raise AppError(409, "PLAYER_ALREADY_LINKED", tr("هذا اللاعب مرتبط بمجموعة أخرى؛ ألغِ الربط من صفحته أولًا", "This player is linked to another group; unlink it from his page first"))
    client.profile.telegram_chat_id = data.chat_id
    if data.invite_url:
        client.profile.telegram_invite_url = data.invite_url
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


def _draft_for_question(question_id: int) -> None:
    """After replying in the group: write an AI draft for the coach and send it to him privately."""
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


@bot_router.post("/message", dependencies=[Depends(require_bot)])
def bot_message(data: MessageIn, background: BackgroundTasks):
    result = process_message(data.chat_id, data.text, data.from_user_id)
    if result.question_id is not None:
        background.add_task(_draft_for_question, result.question_id)
    return {"reply": result.reply}


def _is_video(data: bytes) -> bool:
    return len(data) > 12 and data[4:8] == b"ftyp"  # MP4 / MOV (what Telegram delivers)


@bot_router.post("/video", dependencies=[Depends(require_bot)])
async def bot_video(
    chat_id: int = Form(...), from_user_id: int | None = Form(default=None), file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    profile = db.scalar(select(ClientProfile).where(ClientProfile.telegram_chat_id == chat_id))
    if profile is None:
        return {"reply": "هذه المجموعة غير مرتبطة بلاعب بعد."}
    coach_user = profile.trainer
    if coach_user is not None and from_user_id is not None and coach_user.telegram_user_id == from_user_id:
        return {"reply": None}  # the coach's own video: not a player check-in
    data = await file.read(MAX_VIDEO_BYTES + 1)
    if len(data) > MAX_VIDEO_BYTES:
        return {"reply": "الفيديو أكبر من 20 ميجابايت، أرسل مقطعًا أقصر 🙏"}
    if not _is_video(data):
        return {"reply": "أرسل الفيديو بصيغة MP4 من فضلك."}
    path = storage.new_path(profile.user_id, "mp4")
    storage.save(path, data, "video/mp4")
    check = SquatCheck(client_id=profile.user_id, source="telegram", status="awaiting_review", video_path=path)
    db.add(check)
    db.commit()
    if coach_user is not None and coach_user.telegram_user_id is not None:
        name = profile.user.full_name
        telegram_send.send_message(coach_user.telegram_user_id, f"🎥 وصل فيديو سكوات جديد من {name}. حلّله من صفحة اللاعب في تحدي.")
    return {"reply": "استلمنا فيديو السكوات ✅ سيراجعه مدربك ويرد عليك."}


@bot_router.post("/draft-decision", dependencies=[Depends(require_bot)])
def draft_decision(data: DecisionIn, db: Session = Depends(get_db)):
    actor = db.scalar(select(User).where(User.telegram_user_id == data.from_user_id, User.deleted_at.is_(None)))
    draft = db.get(AgentDraft, data.draft_id)
    if actor is None or actor.role not in ("trainer", "admin") or draft is None:
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    client = db.get(User, draft.client_id)
    if client is None or not permissions.can_access_client(actor, client):
        raise AppError(403, "NOT_ALLOWED", tr("غير مسموح", "Not allowed"))
    try:
        if data.action == "approve":
            draft = coach.approve(db, draft, client, actor, data.text, telegram_send.send_telegram_message)
            note = "✅ تم الاعتماد والإرسال للمجموعة" if draft.telegram_sent else "✅ تم الاعتماد (تعذر الإرسال للمجموعة)"
        else:
            draft = coach.reject(db, draft, client, actor)
            note = "❌ تم الرفض، لن تُرسل"
    except coach.DraftNotPending:
        return {"reply": "تم اتخاذ قرار بشأن هذه المسودة مسبقًا", "status": draft.status}
    return {"reply": note, "status": draft.status}
