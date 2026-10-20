"""Single source of truth for "who may see which client".

Rules:
- admin: every (non-deleted) client
- trainer: only clients whose profile.trainer_id == trainer.id
- client: only themselves
Anything else is reported as 404 so the existence of other clients is never leaked.
"""
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import not_found
from app.models import ClientProfile, Comment, MeasurementSession, Question, User

CLIENT_NOT_FOUND = "العميل غير موجود"


def can_access_client(user: User, client: User) -> bool:
    if client.role != "client" or client.deleted_at is not None:
        return False
    if user.role == "admin":
        return True
    if user.role == "trainer":
        return client.profile is not None and client.profile.trainer_id == user.id
    if user.role == "client":
        return client.id == user.id
    return False


def get_accessible_client(db: Session, user: User, client_id: int) -> User:
    client = db.get(User, client_id)
    if client is None or not can_access_client(user, client):
        raise not_found(CLIENT_NOT_FOUND)
    return client


def accessible_client_ids(user: User) -> Select:
    """A SELECT of client ids the user may access (for use in IN (...) filters)."""
    stmt = select(User.id).where(User.role == "client", User.deleted_at.is_(None))
    if user.role == "admin":
        return stmt
    if user.role == "trainer":
        return stmt.join(ClientProfile, ClientProfile.user_id == User.id).where(ClientProfile.trainer_id == user.id)
    return stmt.where(User.id == user.id)


def get_accessible_session(db: Session, user: User, session_id: int) -> MeasurementSession:
    session = db.get(MeasurementSession, session_id)
    if session is None:
        raise not_found("جلسة القياس غير موجودة")
    client = db.get(User, session.client_id)
    if client is None or not can_access_client(user, client):
        raise not_found("جلسة القياس غير موجودة")
    return session


def get_accessible_question(db: Session, user: User, question_id: int) -> Question:
    question = db.get(Question, question_id)
    if question is None or not can_access_client(user, question.client):
        raise not_found("السؤال غير موجود")
    return question


def get_accessible_comment(db: Session, user: User, comment_id: int) -> Comment:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise not_found("التعليق غير موجود")
    client = db.get(User, comment.client_id)
    if client is None or not can_access_client(user, client):
        raise not_found("التعليق غير موجود")
    return comment


def ensure_session_belongs(db: Session, session_id: int | None, client_id: int) -> MeasurementSession | None:
    """Optional session_id on comments/questions must belong to the same client."""
    if session_id is None:
        return None
    session = db.get(MeasurementSession, session_id)
    if session is None or session.client_id != client_id:
        raise not_found("جلسة القياس غير موجودة")
    return session
