"""DevAI agents on real client accounts (trainer/admin only, owner-scoped).

GET  /clients/{client_id}/agent-summary   Progress Analyst: facts, alerts, Arabic + English summary
POST /clients/{client_id}/agent-drafts    Coach Assistant: new pending draft
POST /agent-drafts/{draft_id}/approve     approve a pending draft (optionally edited) and send it on Telegram
POST /agent-drafts/{draft_id}/reject      reject a pending draft; nothing is sent
"""

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents import analyst, coach
from app.core.deps import require_role
from app.core.errors import AppError, not_found
from app.core.i18n import tr
from app.db.session import get_db
from app.models import AgentDraft, User
from app.routers.telegram import send_telegram_message
from app.services import permissions

router = APIRouter(tags=["agents"])
coach_only = require_role("trainer", "admin")


class ApproveIn(BaseModel):
    text: str | None = Field(default=None, max_length=2000)


def _draft_out(d: AgentDraft) -> dict:
    return {
        "id": d.id,
        "client_id": d.client_id,
        "text": d.text,
        "source": d.source,
        "status": d.status,
        "created_at": d.created_at,
        "decided_at": d.decided_at,
        "telegram_sent": d.telegram_sent,
    }


def _accessible_draft(db: Session, actor: User, draft_id: int) -> tuple[AgentDraft, User]:
    draft = db.get(AgentDraft, draft_id)
    if draft is None:
        raise not_found(tr("المسودة غير موجودة", "Draft not found"))
    # 404 (not 403) when the draft belongs to someone else's client, like every other resource
    client = permissions.get_accessible_client(db, actor, draft.client_id)
    return draft, client


def _decide(db: Session, actor: User, draft_id: int, decision: str, text: str | None = None):
    draft, client = _accessible_draft(db, actor, draft_id)
    try:
        return coach.decide(db, draft, actor, decision, text), client
    except coach.DraftNotPending:
        raise AppError(
            409, "DRAFT_NOT_PENDING", tr("تم اتخاذ قرار بشأن هذه المسودة مسبقاً", "This draft was already decided")
        ) from None


@router.get("/clients/{client_id}/agent-summary")
def agent_summary(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = permissions.get_accessible_client(db, actor, client_id)
    return analyst.analyze(db, client)


@router.post("/clients/{client_id}/agent-drafts", status_code=status.HTTP_201_CREATED)
def create_agent_draft(client_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    client = permissions.get_accessible_client(db, actor, client_id)
    return _draft_out(coach.create_draft(db, client, actor))


@router.post("/agent-drafts/{draft_id}/approve")
def approve_agent_draft(
    draft_id: int, payload: ApproveIn | None = None, actor: User = Depends(coach_only), db: Session = Depends(get_db)
):
    draft, client = _decide(db, actor, draft_id, "approved", payload.text if payload else None)
    chat_id = client.profile.telegram_chat_id if client.profile else None
    if chat_id is not None:
        draft = coach.mark_sent(db, draft, send_telegram_message(chat_id, draft.text))
    return {**_draft_out(draft), "telegram_linked": chat_id is not None}


@router.post("/agent-drafts/{draft_id}/reject")
def reject_agent_draft(draft_id: int, actor: User = Depends(coach_only), db: Session = Depends(get_db)):
    draft, _ = _decide(db, actor, draft_id, "rejected")
    return _draft_out(draft)
