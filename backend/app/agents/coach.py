"""Agent 5 - Coach assistant, on real client accounts.

The Coach Assistant agent drafts a message (template fallback). Nothing is sent until the coach
approves it (ADR-0007), from the web app or from the Approve / Edit / Reject buttons the bot sends
the coach in a private chat (ADR-0011). Only a pending draft can be approved or rejected, once.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.agents import text as t
from app.agents.analyst import analyze
from app.models import AgentDraft, Question, QuestionReply, SquatCheck, User
from app.models.base import utcnow
from app.services import telegram_send


class DraftNotPending(Exception):
    pass


def latest_squat_check(db: Session, client_id: int) -> dict | None:
    check = db.scalar(
        select(SquatCheck)
        .where(SquatCheck.client_id == client_id, SquatCheck.status == "analysed")
        .order_by(SquatCheck.created_at.desc(), SquatCheck.id.desc())
        .limit(1)
    )
    if check is None:
        return None
    return {"exercise": "squat", "reps": check.reps, "errors": check.errors or [], "confidence": check.confidence}


def create_draft(db: Session, client: User, actor: User | None, question: Question | None = None) -> AgentDraft:
    """Write a pending draft. `actor` is None when the bot created it for a player's question."""
    analysis = analyze(db, client)
    body, source = t.draft_result(
        client.full_name, analysis["facts"], analysis["alerts"], latest_squat_check(db, client.id),
        question.body if question else None,
    )
    draft = AgentDraft(
        client_id=client.id, text=body, source=source, status="pending",
        created_by_id=actor.id if actor else None, question_id=question.id if question else None,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def coach_of(client: User) -> User | None:
    return client.profile.trainer if client.profile else None


def notify_coach(db: Session, draft: AgentDraft, client: User, question: Question | None = None) -> bool:
    """Send the draft privately to the coach's Telegram with Approve / Edit / Reject buttons."""
    coach = coach_of(client)
    if coach is None or coach.telegram_user_id is None:
        return False
    header = f"📝 مسودة رد لـ {client.full_name}"
    if question is not None:
        header += f"\n❓ سؤاله: {question.body}"
    message_id = telegram_send.send_message(
        coach.telegram_user_id, f"{header}\n\n{draft.text}", telegram_send.draft_buttons(draft.id)
    )
    if message_id is None:
        return False
    draft.telegram_message_id = message_id
    db.commit()
    return True


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


def _close_coach_message(draft: AgentDraft, client: User, note: str) -> None:
    coach = coach_of(client)
    if draft.telegram_message_id and coach is not None and coach.telegram_user_id is not None:
        telegram_send.edit_message(coach.telegram_user_id, draft.telegram_message_id, f"{note}\n\n{draft.text}")


def approve(db: Session, draft: AgentDraft, client: User, actor: User, text: str | None, send) -> AgentDraft:
    """Approve, post to the player's group, record the reply on the question, close the coach's message.

    `send(chat_id, text) -> bool` is passed in so callers (and tests) control the Telegram send.
    """
    draft = decide(db, draft, actor, "approved", text)
    chat_id = client.profile.telegram_chat_id if client.profile else None
    if chat_id is not None:
        draft = mark_sent(db, draft, send(chat_id, draft.text))
    if draft.question_id is not None:
        question = db.get(Question, draft.question_id)
        if question is not None:
            question.replies.append(QuestionReply(author_id=actor.id, body=draft.text))
            question.status = "answered"
            db.commit()
    _close_coach_message(draft, client, "✅ تم الاعتماد والإرسال" if draft.telegram_sent else "✅ تم الاعتماد")
    return draft


def reject(db: Session, draft: AgentDraft, client: User, actor: User) -> AgentDraft:
    draft = decide(db, draft, actor, "rejected")
    _close_coach_message(draft, client, "❌ تم رفض المسودة (لم تُرسل)")
    return draft
