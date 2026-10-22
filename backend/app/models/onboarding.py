from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, utcnow
from app.models.user import User


class SubscriptionPlan(CreatedAtMixin, Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    name_en: Mapped[str] = mapped_column(String(80), nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="SAR", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Subscription(CreatedAtMixin, Base):
    """One subscription period. Renewals and plan changes add rows (history); the newest row is current."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    # snapshot of the plan at the time (plans can be edited later)
    plan_name_ar: Mapped[str] = mapped_column(String(80), nullable=False)
    plan_name_en: Mapped[str] = mapped_column(String(80), nullable=False)
    months: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="SAR", nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="initial", nullable=False)  # initial | renewal | change
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class DocumentTemplate(CreatedAtMixin, Base):
    """Versioned contract / disclaimer text. Editing inserts a new version; signed documents keep their own copy."""

    __tablename__ = "document_templates"
    __table_args__ = (UniqueConstraint("kind", "version", name="uq_document_templates_kind_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # contract | disclaimer
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    body_ar: Mapped[str] = mapped_column(Text, nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    created_by: Mapped[User | None] = relationship(lazy="joined")


class HealthDeclaration(CreatedAtMixin, Base):
    """Append-only: an update inserts a new row, the newest row is current, older ones are history."""

    __tablename__ = "health_declarations"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    has_chronic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    conditions: Mapped[list | None] = mapped_column(JSON)  # ["diabetes", "hypertension", ...]
    details: Mapped[str | None] = mapped_column(Text)
    medications: Mapped[str | None] = mapped_column(Text)
    injuries: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    files: Mapped[list["MedicalFile"]] = relationship(back_populates="declaration", lazy="selectin", order_by="MedicalFile.id")


class MedicalFile(Base):
    """Metadata for a file in the private storage bucket (the bytes never pass through public URLs)."""

    __tablename__ = "medical_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    declaration_id: Mapped[int | None] = mapped_column(ForeignKey("health_declarations.id", ondelete="SET NULL"), index=True)
    storage_path: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    declaration: Mapped[HealthDeclaration | None] = relationship(back_populates="files")


class SignedDocument(Base):
    """Exactly what was signed. Insert-only: no update/delete endpoints, and a Postgres trigger rejects changes."""

    __tablename__ = "signed_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # contract | disclaimer
    template_id: Mapped[int | None] = mapped_column(ForeignKey("document_templates.id", ondelete="SET NULL"))
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    rendered_text: Mapped[str] = mapped_column(Text, nullable=False)
    typed_name: Mapped[str] = mapped_column(String(150), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    subscription_id: Mapped[int | None] = mapped_column(ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True)
    health_declaration_id: Mapped[int | None] = mapped_column(ForeignKey("health_declarations.id", ondelete="SET NULL"))
    # snapshot of names / plan at signing time (shown on PDFs)
    details: Mapped[dict | None] = mapped_column(JSON)
