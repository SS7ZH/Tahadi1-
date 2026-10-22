from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError, forbidden
from app.core.i18n import tr
from app.core.security import decode_token
from app.db.session import get_db
from app.models import MeasurementSession, User
from app.services import permissions

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AppError(401, "NOT_AUTHENTICATED", tr("يجب تسجيل الدخول", "You need to log in"))
    payload = decode_token(creds.credentials, "access")
    user = db.get(User, int(payload["sub"]))
    if user is None or user.deleted_at is not None:
        raise AppError(401, "INVALID_TOKEN", tr("الحساب غير موجود", "Account not found"))
    if not user.is_active:
        raise AppError(401, "ACCOUNT_DISABLED", tr("الحساب موقوف، تواصل مع الإدارة", "This account is disabled, contact the administrator"))
    return user


def require_role(*roles: str) -> Callable[..., User]:
    """Usage: user: User = Depends(require_role("trainer", "admin"))"""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        return user

    return _dep


def get_accessible_client(
    client_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Resolves {client_id} from the path, 404 if the caller may not see that client."""
    return permissions.get_accessible_client(db, user, client_id)


def get_accessible_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeasurementSession:
    return permissions.get_accessible_session(db, user, session_id)
