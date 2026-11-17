"""Telegram: every player chats with the bot privately; the coach answers from his own chat (ADR-0012).

Web app (coach/admin, under /api/v1):
  GET    /me/telegram                     is my own Telegram linked?
  POST   /me/telegram/link                link for my private chat with the bot
  GET    /telegram/clients                my players and whether they started the bot
  GET    /telegram/status                 (admin) bot token / webhook / storage check
  POST   /clients/telegram                add a Telegram-only player (no email/password) + his personal link
  POST   /clients/{id}/telegram/invite    a new personal link for the player
  DELETE /clients/{id}/telegram           unlink the player's Telegram
  GET    /clients/{id}/photos             photos the player sent (short-lived view links)
  GET    /clients/{id}/squat-checks       squat sets (Telegram videos + browser checks)
  POST   /clients/{id}/squat-checks       save a browser squat check for the player
  PATCH  /squat-checks/{id}               add the analysis to a video awaiting review
  GET    /squat-checks/{id}/video         short-lived link to watch the video
  GET    /telegram-files/{kind}/{id}      the photo/video itself, streamed from Telegram (signed link, no login)

Telegram webhook (header X-Telegram-Bot-Api-Secret-Token):
  POST   /telegram/webhook                every update: messages, /start, photos, videos, buttons
"""

import hashlib
import hmac
import time

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config as agent_config
from app.core.config import settings
from app.core.deps import require_role
from app.core.errors import AppError, not_found
from app.core.i18n import tr
from app.db.session import get_db
from app.models import ClientPhoto, SquatCheck, User
from app.schemas.user import TelegramPlayerCreate
from app.services import audit, permissions, storage, telegram_core, telegram_links, telegram_send, telegram_updates, users
from app.services.serializers import user_detail

router = APIRouter(tags=["telegram"])
bot_router = APIRouter(prefix="/telegram", tags=["telegram-bot"])
coach_only = require_role("trainer", "admin")

ERROR_TYPES = {"knees_caving", "shallow_depth", "back_lean"}
FILE_LINK_SECONDS = 600
MEDIA_TYPES = {"video": "video/mp4", "photo": "image/jpeg"}


# ================================================================ helpers

def _invite(client: User) -> dict:
    code, expires_at = telegram_links.make_code(telegram_links.KIND_CLIENT, client.id)
    return {"invite_url": telegram_links.player_start_url(code), "expires_at": expires_at}


def _accessible_client(db: Session, actor: User, client_id: int) -> User:
    client = permissions.get_accessible_client(db, actor, client_id)
    if client.profile is None:
        raise not_found(tr("اللاعب غير موجود", "Player not found"))
    return client


def _file_token(kind: str, item_id: int, expires: int) -> str:
    return hmac.new(settings.JWT_SECRET.encode(), f"tgfile:{kind}:{item_id}:{expires}".encode(), hashlib.sha256).hexdigest()[:32]


def _file_url(request: Request, kind: str, item_id: int) -> str:
    expires = int(time.time()) + FILE_LINK_SECONDS
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/telegram-files/{kind}/{item_id}?expires={expires}&token={_file_token(kind, item_id, expires)}"


def _squat_out(c: SquatCheck) -> dict:
    return {
        "id": c.id, "client_id": c.client_id, "source": c.source, "status": c.status, "reps": c.reps,
        "errors": c.errors or [], "confidence": c.confidence, "has_video": bool(c.video_path or c.telegram_file_id),
        "created_at": c.created_at,
    }


# ================================================================ web app (coach)

@router.get("/me/telegram")
def my_telegram(actor: User = Depends(coach_only)):
    return {"linked": actor.telegram_user_id is not None, "bot_username": agent_config.TELEGRAM_BOT_USERNAME}


@router.post("/me/telegram/link")
def my_telegram_link(actor: User = Depends(coach_only)):
    code, expires_at = telegram_links.make_code(telegram_links.KIND_COACH, actor.id)
    return {"url": telegram_links.coach_start_url(code), "expires_at": expires_at}


@router.get("/telegram/status")
def telegram_status(actor: User = Depends(require_role("admin"))):
    """Admin check: is the bot token valid here, and does Telegram reach the webhook? (never shows secrets)"""
    me = telegram_send._call("getMe", {})
    hook = telegram_send.webhook_info() or {}
    return {
        "token_set": bool(agent_config.TELEGRAM_BOT_TOKEN),
        "token_valid": isinstance(me, dict),
        "bot_username": me.get("username") if isinstance(me, dict) else None,
        "configured_username": agent_config.TELEGRAM_BOT_USERNAME,
        "bot_secret_set": bool(agent_config.TELEGRAM_BOT_SECRET),
        "webhook_url": hook.get("url"),
        "pending_updates": hook.get("pending_update_count"),
        "last_error": hook.get("last_error_message"),
    }


@router.get("/telegram/clients")
def telegram_clients(actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(User).where(User.id.in_(permissions.accessible_client_ids(actor))).order_by(User.full_name)
    ).unique().all()
    return [
        {"id": c.id, "name": c.full_name, "linked": c.profile.telegram_chat_id is not None, "telegram_only": c.email is None}
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
    return {"client": user_detail(client), **_invite(client)}


@router.post("/clients/{client_id}/telegram/invite")
def new_invite(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    return {"linked": client.profile.telegram_chat_id is not None, **_invite(client)}


@router.delete("/clients/{client_id}/telegram", status_code=status.HTTP_204_NO_CONTENT)
def unlink(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    client.profile.telegram_chat_id = None
    client.profile.telegram_invite_url = None
    client.profile.telegram_step = None
    audit.record(db, actor, "update", "client_profile", client.id, {"telegram": "unlinked"})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/clients/{client_id}/photos")
def list_photos(client_id: int, request: Request, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = _accessible_client(db, actor, client_id)
    rows = db.scalars(
        select(ClientPhoto).where(ClientPhoto.client_id == client.id).order_by(ClientPhoto.created_at.desc(), ClientPhoto.id.desc()).limit(60)
    ).all()
    return [{"id": p.id, "caption": p.caption, "created_at": p.created_at, "url": _file_url(request, "photo", p.id)} for p in rows]


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
    if check is None or not (check.video_path or check.telegram_file_id):
        raise not_found(tr("لا يوجد فيديو", "No video"))
    _accessible_client(db, actor, check.client_id)
    if check.telegram_file_id:
        return {"url": _file_url(request, "video", check.id)}
    return {"url": storage.signed_url(check.video_path, str(request.base_url).rstrip("/") + "/api/v1")}


@router.get("/telegram-files/{kind}/{item_id}", include_in_schema=False)
def telegram_file(kind: str, item_id: int, expires: int, token: str, db: Session = Depends(get_db)):
    """Stream a player's photo/video from Telegram. Signed, short-lived link (opened in a new tab / <img>)."""
    if kind not in MEDIA_TYPES or expires < int(time.time()) or not hmac.compare_digest(token, _file_token(kind, item_id, expires)):
        raise not_found(tr("الرابط منتهي أو غير صحيح", "Link expired or invalid"))
    row = db.get(SquatCheck if kind == "video" else ClientPhoto, item_id)
    file_id = getattr(row, "telegram_file_id", None)
    if not file_id:
        raise not_found(tr("الملف غير موجود", "File not found"))
    data = telegram_send.download_file(file_id, telegram_core.MAX_FILE_BYTES)
    if data is None:
        raise AppError(502, "TELEGRAM_FILE_ERROR", tr("تعذر جلب الملف من تيليجرام، حاول مرة أخرى", "Could not fetch the file from Telegram, try again"))
    return Response(content=data, media_type=MEDIA_TYPES[kind], headers={"Cache-Control": "private, max-age=300"})


# ================================================================ Telegram webhook

@bot_router.post("/webhook")
async def telegram_webhook(request: Request, background: BackgroundTasks,
                           x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    """Telegram delivers every update here. Answer at once; do the work after the response."""
    if not agent_config.TELEGRAM_BOT_SECRET:
        raise AppError(503, "BOT_NOT_CONFIGURED", tr("ربط البوت غير مهيأ", "The bot connection is not configured"))
    if not x_telegram_bot_api_secret_token or not hmac.compare_digest(x_telegram_bot_api_secret_token, telegram_core.webhook_secret()):
        raise AppError(401, "BOT_SECRET_INVALID", tr("غير مصرح", "Not authorised"))
    try:
        update = await request.json()
    except ValueError:
        return {"ok": True}
    if isinstance(update, dict):
        background.add_task(telegram_updates.handle_update, update)
    return {"ok": True}
