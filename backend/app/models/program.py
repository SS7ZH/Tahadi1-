from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.user import User


class Exercise(CreatedAtMixin, Base):
    """Shared exercise library."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    muscle_group: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    equipment: Mapped[str | None] = mapped_column(String(30))
    video_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Program(CreatedAtMixin, Base):
    """A client's training program, or a reusable template (client_id NULL, is_template TRUE)."""

    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    goal: Mapped[str | None] = mapped_column(String(150))
    start_date: Mapped[date | None] = mapped_column(Date)
    weeks: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True, nullable=False)  # draft|active|archived
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    days: Mapped[list["ProgramDay"]] = relationship(
        back_populates="program",
        cascade="all, delete-orphan",
        order_by="ProgramDay.sort_order",
        lazy="selectin",
    )
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id], lazy="joined")


class ProgramDay(Base):
    __tablename__ = "program_days"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"), index=True, nullable=False)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..7, counted from the program start date
    week_number: Mapped[int | None] = mapped_column(Integer)  # NULL = repeats every week
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    is_rest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    warmup: Mapped[str | None] = mapped_column(Text)
    cooldown: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    program: Mapped[Program] = relationship(back_populates="days")
    items: Mapped[list["ProgramItem"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="ProgramItem.sort_order", lazy="selectin"
    )


class ProgramItem(Base):
    """One exercise in a day: resistance (sets × reps) or cardio (duration, HR zone, intervals)."""

    __tablename__ = "program_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    day_id: Mapped[int] = mapped_column(ForeignKey("program_days.id", ondelete="CASCADE"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)  # resistance | cardio
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    exercise_id: Mapped[int | None] = mapped_column(ForeignKey("exercises.id", ondelete="SET NULL"))
    custom_name: Mapped[str | None] = mapped_column(String(150))
    muscle_group: Mapped[str | None] = mapped_column(String(30))
    # resistance
    sets: Mapped[int | None] = mapped_column(Integer)
    reps: Mapped[str | None] = mapped_column(String(20))  # "10" or "8-12"
    load_value: Mapped[float | None] = mapped_column(Float)
    load_unit: Mapped[str | None] = mapped_column(String(10))  # kg | pct_1rm | rpe
    rest_seconds: Mapped[int | None] = mapped_column(Integer)
    tempo: Mapped[str | None] = mapped_column(String(20))
    # cardio
    cardio_type: Mapped[str | None] = mapped_column(String(20))
    duration_min: Mapped[float | None] = mapped_column(Float)
    hr_zone: Mapped[int | None] = mapped_column(Integer)
    speed: Mapped[float | None] = mapped_column(Float)
    incline: Mapped[float | None] = mapped_column(Float)
    work_seconds: Mapped[int | None] = mapped_column(Integer)
    interval_rest_seconds: Mapped[int | None] = mapped_column(Integer)
    rounds: Mapped[int | None] = mapped_column(Integer)
    # shared
    notes: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))

    day: Mapped[ProgramDay] = relationship(back_populates="items")
    exercise: Mapped[Exercise | None] = relationship(lazy="joined")
