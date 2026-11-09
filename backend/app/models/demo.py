"""Demo models corresponding to the 3 agreed Supabase tables in the 2-hour build plan:
- measurements (client, date, weight_kg)
- form_checks (client, reps, errors)
- drafts (client, text, status)
"""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DemoMeasurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(20), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)


class DemoFormCheck(Base):
    __tablename__ = "form_checks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text)


class DemoDraft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

