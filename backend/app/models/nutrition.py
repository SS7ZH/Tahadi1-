from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.user import User


class NutritionSetting(Base):
    """Per-goal calorie adjustment, macro split and meal range (admin-editable)."""

    __tablename__ = "nutrition_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # weight_loss | maintenance | weight_gain
    calorie_adjustment: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_pct: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_pct: Mapped[float] = mapped_column(Float, nullable=False)
    fat_pct: Mapped[float] = mapped_column(Float, nullable=False)
    meals_min: Mapped[int] = mapped_column(Integer, nullable=False)
    meals_max: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class NutritionPlan(CreatedAtMixin, Base):
    """A saved plan. Rows are never updated: the newest row per client is the current plan, older rows are history."""

    __tablename__ = "nutrition_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    goal: Mapped[str] = mapped_column(String(20), nullable=False)  # client_profiles.goal at save time
    nutrition_goal: Mapped[str] = mapped_column(String(20), nullable=False)
    based_on_weight: Mapped[float | None] = mapped_column(Float)
    based_on_session_id: Mapped[int | None] = mapped_column(ForeignKey("measurement_sessions.id", ondelete="SET NULL"))
    dcn: Mapped[int | None] = mapped_column(Integer)
    suggested_calories: Mapped[int | None] = mapped_column(Integer)
    calories: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_g: Mapped[int] = mapped_column(Integer, nullable=False)
    carbs_g: Mapped[int] = mapped_column(Integer, nullable=False)
    fat_g: Mapped[int] = mapped_column(Integer, nullable=False)
    protein_pct: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_pct: Mapped[float] = mapped_column(Float, nullable=False)
    fat_pct: Mapped[float] = mapped_column(Float, nullable=False)
    meals_per_day: Mapped[int] = mapped_column(Integer, nullable=False)
    overridden: Mapped[list | None] = mapped_column(JSON)
    note: Mapped[str | None] = mapped_column(Text)

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id], lazy="joined")
