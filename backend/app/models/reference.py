from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MeasurementDefinition(Base):
    __tablename__ = "measurement_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # vital | body | movement | physical
    unit: Mapped[str | None] = mapped_column(String(50))
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)  # number | text | choice | blood_pressure
    # choice: [{"value": 1, "label": "..."}]
    choices: Mapped[list | None] = mapped_column(JSON)
    better_direction: Mapped[str] = mapped_column(String(10), default="none", nullable=False)  # up | down | none
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ActivityFactor(Base):
    __tablename__ = "activity_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    description_ar: Mapped[str | None] = mapped_column(Text)
    factor: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
