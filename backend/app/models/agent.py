"""Coach-assistant drafts for real client accounts (ADR-0007).

A draft is written by the Coach Assistant agent and is never sent to the client until a
trainer approves it. Only a pending draft can be approved or rejected.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text
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
