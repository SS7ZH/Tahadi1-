"""Coach-assistant drafts for real client accounts (ADR-0007).

A draft is written by the Coach Assistant agent and is never sent to the client until a
trainer approves it. Only a pending draft can be approved or rejected.
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin

DRAFT_STATUSES = ("pending", "approved", "rejected")


class AgentDraft(CreatedAtMixin, Base):
    __tablename__ = "agent_drafts"
    __table_args__ = (
        CheckConstraint("status in ('pending', 'approved', 'rejected')", name="ck_agent_drafts_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # "agent" when the DevAI Coach Assistant wrote it, "template" when the built-in text was used
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="template")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set when the draft answers a player's question (approving it records the reply).
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), index=True)
    # The private message with Approve / Edit / Reject buttons sent to the coach on Telegram.
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)


class SquatCheck(CreatedAtMixin, Base):
    """A squat set from a player: analysed from a Telegram video, or entered from the browser checker."""

    __tablename__ = "squat_checks"
    __table_args__ = (
        CheckConstraint("status in ('analysed', 'awaiting_review', 'failed')", name="ck_squat_checks_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="telegram")  # telegram | browser
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="analysed")
    reps: Mapped[int | None] = mapped_column()
    # [{"rep": 3, "type": "knees_caving"}, ...]; types: knees_caving, shallow_depth, back_lean
    errors: Mapped[list | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)
    video_path: Mapped[str | None] = mapped_column(String(500))
