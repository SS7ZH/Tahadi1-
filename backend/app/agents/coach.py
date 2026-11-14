"""Agent 5 - Coach assistant, on real client accounts.

The DevAI Coach Assistant agent drafts a message (template fallback). Nothing is sent until a
trainer approves it, and only a pending draft can be approved or rejected.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.agents import text as t
from app.agents.analyst import analyze
from app.models import AgentDraft, User
from app.models.base import utcnow


class DraftNotPending(Exception):
    pass


def create_draft(db: Session, client: User, actor: User) -> AgentDraft:
    analysis = analyze(db, client)
    body, source = t.draft_result(client.full_name, analysis["facts"], analysis["alerts"], None)
    draft = AgentDraft(client_id=client.id, text=body, source=source, status="pending", created_by_id=actor.id)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def decide(db: Session, draft: AgentDraft, actor: User, status: str, text: str | None = None) -> AgentDraft:
    """Approve or reject a pending draft. The conditional update stops double decisions."""
    if draft.status != "pending":
        raise DraftNotPending(draft.status)
    changes = {"status": status, "decided_by_id": actor.id, "decided_at": utcnow()}
    if text is not None and text.strip():
        changes["text"] = text.strip()
    result = db.execute(
        update(AgentDraft)
        .where(AgentDraft.id == draft.id, AgentDraft.status == "pending")
        .values(**changes)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise DraftNotPending("changed")
    db.commit()
    db.refresh(draft)
    return draft


def mark_sent(db: Session, draft: AgentDraft, sent: bool) -> AgentDraft:
    draft.telegram_sent = sent
    db.commit()
    db.refresh(draft)
    return draft
