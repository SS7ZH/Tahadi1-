from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.reference import MeasurementDefinition
from app.models.user import User


class MeasurementSession(CreatedAtMixin, Base):
    __tablename__ = "measurement_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    # who recorded the session
    trainer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # who changed it last
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    session_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    values: Mapped[list["MeasurementValue"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", lazy="selectin"
    )
    trainer: Mapped[User | None] = relationship(foreign_keys=[trainer_id], lazy="joined")
    updated_by: Mapped[User | None] = relationship(foreign_keys=[updated_by_id], lazy="joined")


class MeasurementValue(Base):
    __tablename__ = "measurement_values"
    __table_args__ = (UniqueConstraint("session_id", "definition_id", name="uq_measurement_values_session_definition"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    definition_id: Mapped[int] = mapped_column(
        ForeignKey("measurement_definitions.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    value_number: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict | None] = mapped_column(JSON)  # blood pressure: {"systolic": 120, "diastolic": 80}

    session: Mapped[MeasurementSession] = relationship(back_populates="values")
    definition: Mapped[MeasurementDefinition] = relationship(lazy="joined")
