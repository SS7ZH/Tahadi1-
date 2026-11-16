from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin


class User(CreatedAtMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Telegram-only players (ADR-0011) have no email and no password: they never log in.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # admin | trainer | client
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A coach's own Telegram account (private chat with the bot): receives drafts to approve.
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)

    profile: Mapped["ClientProfile | None"] = relationship(
        back_populates="user",
        foreign_keys="ClientProfile.user_id",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ClientProfile(Base):
    __tablename__ = "client_profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    sex: Mapped[str] = mapped_column(String(10), nullable=False)  # male | female
    birth_date: Mapped[date | None] = mapped_column(Date)
    height_cm: Mapped[float | None] = mapped_column(Float)
    goal: Mapped[str] = mapped_column(String(20), default="fitness", nullable=False)
    activity_key: Mapped[str | None] = mapped_column(
        ForeignKey("activity_factors.key", ondelete="SET NULL", onupdate="CASCADE")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    # The player's Telegram group (bot + player + coach). Group chat ids are negative.
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    # Invite link the bot created for that group (shown to the coach to send the player).
    telegram_invite_url: Mapped[str | None] = mapped_column(String(255))
    # Profile questions asked by the bot: next field to ask, or None when done/skipped.
    telegram_step: Mapped[str | None] = mapped_column(String(30))

    user: Mapped[User] = relationship(back_populates="profile", foreign_keys=[user_id])
    trainer: Mapped[User | None] = relationship(foreign_keys=[trainer_id], lazy="joined")
