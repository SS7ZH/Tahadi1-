import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import AppError
from app.core.i18n import tr

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except ValueError:
        return False


def _encode(user_id: int, role: str, kind: str, expires: timedelta, secret: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": kind,
        "iat": now,
        "exp": now + expires,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _encode(user_id, role, "access", timedelta(minutes=settings.ACCESS_TOKEN_MINUTES), settings.JWT_SECRET)


def create_refresh_token(user_id: int, role: str) -> str:
    return _encode(user_id, role, "refresh", timedelta(days=settings.REFRESH_TOKEN_DAYS), settings.JWT_REFRESH_SECRET)


def decode_token(token: str, kind: str) -> dict:
    secret = settings.JWT_SECRET if kind == "access" else settings.JWT_REFRESH_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AppError(401, "TOKEN_EXPIRED", tr("انتهت صلاحية الجلسة، سجّل الدخول مجدداً", "Your session expired, please log in again"))
    except jwt.PyJWTError:
        raise AppError(401, "INVALID_TOKEN", tr("رمز الدخول غير صالح", "Invalid login token"))
    if payload.get("type") != kind or not str(payload.get("sub", "")).isdigit():
        raise AppError(401, "INVALID_TOKEN", tr("رمز الدخول غير صالح", "Invalid login token"))
    return payload
