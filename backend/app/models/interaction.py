from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.user import User


class Comment(CreatedAtMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_sessions.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped[User | None] = relationship(foreign_keys=[author_id], lazy="joined")


class Question(CreatedAtMixin, Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("measurement_sessions.id", ondelete="SET NULL"), index=True
    )
    # optional link to a program day (v4); a question is about a session OR a day OR neither
    program_day_id: Mapped[int | None] = mapped_column(ForeignKey("program_days.id", ondelete="SET NULL"), index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True, nullable=False)  # open|answered|closed
    # "app" (asked in the web app) or "telegram" (a message in the player's Telegram group)
    source: Mapped[str] = mapped_column(String(20), default="app", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    client: Mapped[User] = relationship(foreign_keys=[client_id], lazy="joined")
    replies: Mapped[list["QuestionReply"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionReply.created_at",
        lazy="selectin",
    )


class QuestionReply(CreatedAtMixin, Base):
    __tablename__ = "question_replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(Text, nullable=False)

    question: Mapped[Question] = relationship(back_populates="replies")
    author: Mapped[User | None] = relationship(foreign_keys=[author_id], lazy="joined")
