import logging

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.intake import handle_message
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.i18n import LanguageMiddleware, tr
from app.db.session import get_db
from app.routers import (
    admin,
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


for r in (auth, admin, clients, sessions, comments, questions, calculate, reference, nutrition, programs, onboarding, documents, pdf, site, telegram):
    api.include_router(r.router)

app.include_router(api)
# Also include telegram router at root level for direct /telegram, /summary/{client}, /draft/{client}
app.include_router(telegram.router)


@app.post("/telegram/message")
def telegram_message(payload: TelegramMessagePayload):
    return {"reply": handle_message(payload.chat_id, payload.text)}


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Tahadi API", "docs": "/api/docs", "health": "/api/v1/health"}
