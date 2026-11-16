from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.i18n import tr
from app.core.rate_limit import RateLimiter, client_ip
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import User
from app.schemas.user import LoginIn, MeUpdate, RefreshIn, TokenPair, UserDetailOut
from app.services.serializers import user_detail

router = APIRouter(prefix="/auth", tags=["auth"])

login_limiter = RateLimiter(settings.LOGIN_RATE_LIMIT, settings.LOGIN_RATE_WINDOW_SECONDS)

# Verifying against a dummy hash when the email is unknown keeps response times uniform.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-password")


def token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id, user.role),
        user=user_detail(user),
    )


@router.post("/login", response_model=TokenPair)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    login_limiter.hit(client_ip(request))
    user = db.scalar(select(User).where(func.lower(User.email) == data.email.lower(), User.deleted_at.is_(None)))
    # Telegram-only players have no password: they always get the same "invalid" answer.
    valid = verify_password(data.password, user.password_hash if user and user.password_hash else _DUMMY_HASH)
    valid = valid and bool(user and user.password_hash)
    if user is None or not valid:
        raise AppError(401, "INVALID_CREDENTIALS", tr("البريد الإلكتروني أو كلمة المرور غير صحيحة", "Incorrect email or password"))
    if not user.is_active:
        raise AppError(403, "ACCOUNT_DISABLED", tr("الحساب موقوف، تواصل مع الإدارة", "This account is disabled, contact the administrator"))
    return token_pair(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    payload = decode_token(data.refresh_token, "refresh")
    user = db.get(User, int(payload["sub"]))
    if user is None or user.deleted_at is not None or not user.is_active:
        raise AppError(401, "INVALID_TOKEN", tr("انتهت الجلسة، سجّل الدخول مجدداً", "Your session ended, please log in again"))
    return token_pair(user)


@router.get("/me", response_model=UserDetailOut)
def me(user: User = Depends(get_current_user)):
    return user_detail(user)


@router.patch("/me", response_model=UserDetailOut)
def update_me(data: MeUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone.strip() or None
    if data.new_password:
        if not data.current_password or not verify_password(data.current_password, user.password_hash):
            raise AppError(400, "WRONG_PASSWORD", tr("كلمة المرور الحالية غير صحيحة", "Current password is incorrect"))
        user.password_hash = hash_password(data.new_password)
    db.commit()
    db.refresh(user)
    return user_detail(user)
