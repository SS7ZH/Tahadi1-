import base64
import hashlib
import hmac
import logging
import struct
import time

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config as agent_config
from app.agents.intake import handle_message
from app.core.config import settings
from app.core.deps import require_role
from app.core.errors import register_exception_handlers
from app.core.i18n import LanguageMiddleware, tr
from app.db.session import get_db
from app.models import ClientProfile, User
from app.routers import (
    admin,
    agents,
    auth,
    calculate,
    clients,
    comments,
    documents,
    nutrition,
    onboarding,
    pdf,
    programs,
    questions,
    reference,
    sessions,
    site,
    telegram,
)
from app.services import permissions

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Tahadi API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

register_exception_handlers(app)

# Added first so CORS (added next) wraps it; sets the per-request language for tr().
app.add_middleware(LanguageMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX or None,
    allow_credentials=False,  # tokens travel in the Authorization header, not cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept-Language"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

api = APIRouter(prefix="/api/v1")


class TelegramMessagePayload(BaseModel):
    chat_id: int
    text: str = Field(min_length=1, max_length=4096)


class TelegramLinkClaim(BaseModel):
    token: str = Field(min_length=32, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    chat_id: int = Field(gt=0)


TELEGRAM_LINK_TTL_SECONDS = 600


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _make_telegram_link_token(client_id: int) -> tuple[str, int]:
    expires_at = int(time.time()) + TELEGRAM_LINK_TTL_SECONDS
    payload = struct.pack(">IQ", client_id, expires_at)
    signature = hmac.new(settings.JWT_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()[:12]
    return _b64url(payload + signature), expires_at


def _read_telegram_link_token(token: str) -> int:
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid Telegram link") from None

    if len(raw) != 24:
        raise HTTPException(status_code=400, detail="Invalid Telegram link")
    payload, supplied_signature = raw[:12], raw[12:]
    expected_signature = hmac.new(settings.JWT_SECRET.encode("utf-8"), payload, hashlib.sha256).digest()[:12]
    if not hmac.compare_digest(supplied_signature, expected_signature):
        raise HTTPException(status_code=400, detail="Invalid Telegram link")
    client_id, expires_at = struct.unpack(">IQ", payload)
    if expires_at <= int(time.time()):
        raise HTTPException(status_code=410, detail="Telegram link expired")
    return client_id


@api.get("/health", tags=["health"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        logging.getLogger("tahadi").exception("Health check failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable", "detail": tr("تعذر الاتصال بقاعدة البيانات", "Cannot reach the database"), "code": "DB_DOWN"},
        )
    return {"status": "ok", "database": "ok"}


@api.get("/telegram/clients")
def list_telegram_clients(
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(User).where(User.id.in_(permissions.accessible_client_ids(actor))).order_by(User.full_name)
    ).unique().all()
    return [
        {"id": client.id, "name": client.full_name, "linked": client.profile.telegram_chat_id is not None}
        for client in rows
        if client.profile is not None
    ]


@api.post("/telegram/clients/{client_id}/link")
def create_telegram_link(
    client_id: int,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)
    if client.profile is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if client.profile.telegram_chat_id is not None:
        raise HTTPException(status_code=409, detail="Client already has a Telegram account")

    token, expires_at = _make_telegram_link_token(client_id)
    username = agent_config.TELEGRAM_BOT_USERNAME
    return {
        "url": f"https://t.me/{username}?start={token}",
        "expires_at": expires_at,
        "expires_in": TELEGRAM_LINK_TTL_SECONDS,
    }


for r in (auth, admin, clients, sessions, comments, questions, calculate, reference, nutrition, programs, onboarding, documents, pdf, site, telegram, agents):
    api.include_router(r.router)

app.include_router(api)
# Also include telegram router at root level for direct /telegram, /summary/{client}, /draft/{client}
app.include_router(telegram.router)


@app.post("/telegram/message")
def telegram_message(payload: TelegramMessagePayload):
    return {"reply": handle_message(payload.chat_id, payload.text)}


@app.post("/telegram/link/claim")
def claim_telegram_link(payload: TelegramLinkClaim, db: Session = Depends(get_db)):
    client_id = _read_telegram_link_token(payload.token)
    try:
        result = db.execute(
            update(ClientProfile)
            .where(ClientProfile.user_id == client_id, ClientProfile.telegram_chat_id.is_(None))
            .values(telegram_chat_id=payload.chat_id)
        )
        if result.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="Link is invalid or already used")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This Telegram account is already linked") from None

    client = db.get(User, client_id)
    if client is None:
        raise HTTPException(status_code=409, detail="Link is invalid or already used")
    return {"reply": f"تم ربط حسابك مع {client.full_name} بنجاح ✅"}


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Tahadi API", "docs": "/api/docs", "health": "/api/v1/health"}
