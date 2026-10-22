from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user, require_role
from app.core.errors import AppError
from app.core.i18n import tr
from app.db.session import get_db
from app.models import MeasurementSession, ProgramDay, Question, QuestionReply, User
from app.schemas.interaction import QuestionIn, QuestionOut, QuestionStatus, QuestionStatusIn, ReplyIn
from app.services import permissions
from app.services.serializers import question_out

router = APIRouter(tags=["questions"])


def _out_many(db: Session, questions: list[Question]) -> list[dict]:
    session_ids = {q.session_id for q in questions if q.session_id}
    dates = (
        dict(db.execute(select(MeasurementSession.id, MeasurementSession.session_date).where(
            MeasurementSession.id.in_(session_ids))).all())
        if session_ids
        else {}
    )
    day_ids = {q.program_day_id for q in questions if q.program_day_id}
    days = (
        {
            r.id: {"title": r.title, "program_id": r.program_id}
            for r in db.execute(select(ProgramDay.id, ProgramDay.title, ProgramDay.program_id).where(ProgramDay.id.in_(day_ids)))
        }
        if day_ids
        else {}
    )
    return [question_out(q, dates.get(q.session_id), days.get(q.program_day_id)) for q in questions]


@router.get("/clients/{client_id}/questions", response_model=list[QuestionOut])
def list_questions(
    status_filter: QuestionStatus | None = Query(default=None, alias="status"),
    client: User = Depends(get_accessible_client),
    db: Session = Depends(get_db),
):
    stmt = select(Question).where(Question.client_id == client.id)
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    return _out_many(db, list(db.scalars(stmt.order_by(Question.created_at.desc())).unique()))


@router.post("/clients/{client_id}/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def ask_question(
    client_id: int,
    data: QuestionIn,
    actor: User = Depends(require_role("client")),
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)  # a client can only reach themselves
    permissions.ensure_session_belongs(db, data.session_id, client.id)
    permissions.ensure_program_day_belongs(db, data.program_day_id, client.id)
    question = Question(
        client_id=client.id, session_id=data.session_id, program_day_id=data.program_day_id, body=data.body, status="open"
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return _out_many(db, [question])[0]


@router.post("/questions/{question_id}/replies", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
def reply(question_id: int, data: ReplyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Access = trainer of that client, admin, or the client themselves (follow-up).
    question = permissions.get_accessible_question(db, user, question_id)
    if question.status == "closed" and user.role == "client":
        raise AppError(409, "QUESTION_CLOSED", tr("هذا السؤال مغلق، يمكنك طرح سؤال جديد", "This question is closed, you can ask a new one"))
    question.replies.append(QuestionReply(author_id=user.id, body=data.body))
    # Staff reply → answered; client follow-up → back to open so it shows in the trainer's inbox.
    question.status = "open" if user.role == "client" else "answered"
    db.commit()
    db.refresh(question)
    return _out_many(db, [question])[0]


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def set_status(
    question_id: int,
    data: QuestionStatusIn,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    question = permissions.get_accessible_question(db, actor, question_id)
    question.status = data.status
    db.commit()
    db.refresh(question)
    return _out_many(db, [question])[0]


@router.get("/trainer/questions", response_model=list[QuestionOut])
def trainer_inbox(
    status_filter: QuestionStatus | None = Query(default="open", alias="status"),
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    stmt = select(Question).where(Question.client_id.in_(permissions.accessible_client_ids(actor)))
    if status_filter:
        stmt = stmt.where(Question.status == status_filter)
    return _out_many(db, list(db.scalars(stmt.order_by(Question.created_at.desc())).unique()))
