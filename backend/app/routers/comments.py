from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user, require_role
from app.core.errors import forbidden
from app.core.i18n import tr
from app.db.session import get_db
from app.models import Comment, User
from app.schemas.interaction import CommentIn
from app.schemas.measurement import CommentOut
from app.services import permissions
from app.services.serializers import comment_out

router = APIRouter(tags=["comments"])


@router.get("/clients/{client_id}/comments", response_model=list[CommentOut])
def list_comments(
    session_id: int | None = Query(default=None),
    client: User = Depends(get_accessible_client),
    db: Session = Depends(get_db),
):
    stmt = select(Comment).where(Comment.client_id == client.id)
    if session_id is not None:
        stmt = stmt.where(Comment.session_id == session_id)
    return [comment_out(c) for c in db.scalars(stmt.order_by(Comment.created_at.desc())).unique()]


@router.post("/clients/{client_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    client_id: int,
    data: CommentIn,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)
    permissions.ensure_session_belongs(db, data.session_id, client.id)
    comment = Comment(client_id=client.id, session_id=data.session_id, author_id=actor.id, body=data.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_out(comment)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    comment = permissions.get_accessible_comment(db, user, comment_id)
    if not (user.role == "admin" or comment.author_id == user.id):
        raise forbidden(tr("يمكن حذف التعليق من كاتبه أو من المدير فقط", "Only the author or an admin can delete this comment"))
    db.delete(comment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
