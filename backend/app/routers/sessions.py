from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_session, require_role
from app.db.session import get_db
from app.models import Comment, MeasurementSession, User
from app.schemas.measurement import SessionDetailOut, SessionIn
from app.services import measurements, permissions, progress
from app.services.serializers import comment_out, session_out

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _detail(db: Session, session: MeasurementSession) -> dict:
    client = db.get(User, session.client_id)
    comments = list(
        db.scalars(select(Comment).where(Comment.session_id == session.id).order_by(Comment.created_at)).unique()
    )
    return {
        **session_out(session, len(comments)),
        "results": progress.session_results(db, client, session),
        "comments": [comment_out(c) for c in comments],
    }


@router.get("/{session_id}", response_model=SessionDetailOut)
def get_session(session: MeasurementSession = Depends(get_accessible_session), db: Session = Depends(get_db)):
    return _detail(db, session)


@router.put("/{session_id}", response_model=SessionDetailOut)
def update_session(
    session_id: int,
    data: SessionIn,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    session = permissions.get_accessible_session(db, actor, session_id)
    session = measurements.update_session(db, actor, session, data)
    return _detail(db, session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    session = permissions.get_accessible_session(db, actor, session_id)
    measurements.delete_session(db, actor, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
