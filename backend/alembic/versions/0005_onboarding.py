"""Onboarding: subscription plans, subscriptions, versioned document templates, health declarations,
private medical files, immutable signed documents

Revision ID: 0005_onboarding
Revises: 0004_programs
Create Date: 2026-10-22
"""
import sqlalchemy as sa

from alembic import op
from app.db.reference_data import DOCUMENT_TEMPLATES, SUBSCRIPTION_PLANS

revision = "0005_onboarding"
down_revision = "0004_programs"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "subscription_plans",
    "subscriptions",
    "document_templates",
    "health_declarations",
    "medical_files",
    "signed_documents",
]


def _ts(name: str = "created_at") -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    plans = op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name_ar", sa.String(80), nullable=False),
        sa.Column("name_en", sa.String(80), nullable=False),
        sa.Column("months", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        _ts(),
        sa.CheckConstraint("months BETWEEN 1 AND 60", name="plan_months_valid"),
    )
    op.bulk_insert(plans, SUBSCRIPTION_PLANS)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer, sa.ForeignKey("subscription_plans.id", ondelete="SET NULL")),
        sa.Column("plan_name_ar", sa.String(80), nullable=False),
        sa.Column("plan_name_en", sa.String(80), nullable=False),
        sa.Column("months", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(10, 2)),
        sa.Column("currency", sa.String(3), nullable=False, server_default="SAR"),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="initial"),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts(),
        _ts("updated_at"),
        sa.CheckConstraint("end_date >= start_date", name="subscription_dates_valid"),
    )
    op.create_index("ix_subscriptions_client_id", "subscriptions", ["client_id"])

    templates = op.create_table(
        "document_templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("body_ar", sa.Text, nullable=False),
        sa.Column("body_en", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts(),
        sa.UniqueConstraint("kind", "version", name="uq_document_templates_kind_version"),
        sa.CheckConstraint("kind IN ('contract','disclaimer')", name="template_kind_valid"),
    )
    op.bulk_insert(templates, DOCUMENT_TEMPLATES)

    op.create_table(
        "health_declarations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("has_chronic", sa.Boolean, nullable=False),
        sa.Column("conditions", sa.JSON),
        sa.Column("details", sa.Text),
        sa.Column("medications", sa.Text),
        sa.Column("injuries", sa.Text),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        _ts(),
    )
    op.create_index("ix_health_declarations_client_id", "health_declarations", ["client_id"])

    op.create_table(
        "medical_files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("declaration_id", sa.Integer, sa.ForeignKey("health_declarations.id", ondelete="SET NULL")),
        sa.Column("storage_path", sa.String(300), nullable=False),
        sa.Column("original_name", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("storage_path", name="uq_medical_files_storage_path"),
    )
    op.create_index("ix_medical_files_client_id", "medical_files", ["client_id"])
    op.create_index("ix_medical_files_declaration_id", "medical_files", ["declaration_id"])

    op.create_table(
        "signed_documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("template_id", sa.Integer, sa.ForeignKey("document_templates.id", ondelete="SET NULL")),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column("language", sa.String(2), nullable=False),
        sa.Column("rendered_text", sa.Text, nullable=False),
        sa.Column("typed_name", sa.String(150), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(400)),
        sa.Column("subscription_id", sa.Integer, sa.ForeignKey("subscriptions.id", ondelete="SET NULL")),
        sa.Column("health_declaration_id", sa.Integer, sa.ForeignKey("health_declarations.id", ondelete="SET NULL")),
        sa.Column("details", sa.JSON),
        sa.CheckConstraint("kind IN ('contract','disclaimer')", name="signed_kind_valid"),
    )
    op.create_index("ix_signed_documents_client_id", "signed_documents", ["client_id"])
    op.create_index("ix_signed_documents_subscription_id", "signed_documents", ["subscription_id"])

    if op.get_bind().dialect.name == "postgresql":
        for table in NEW_TABLES:
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        # Signed documents are immutable. (FK "SET NULL" updates on referenced rows are still allowed
        # because only the reference columns change; the signed text/name/time can never change.)
        op.execute(
            """
            CREATE OR REPLACE FUNCTION signed_documents_immutable() RETURNS trigger AS $$
            BEGIN
              IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'signed documents cannot be deleted';
              END IF;
              IF NEW.rendered_text IS DISTINCT FROM OLD.rendered_text
                 OR NEW.typed_name IS DISTINCT FROM OLD.typed_name
                 OR NEW.signed_at IS DISTINCT FROM OLD.signed_at
                 OR NEW.client_id IS DISTINCT FROM OLD.client_id
                 OR NEW.kind IS DISTINCT FROM OLD.kind
                 OR NEW.template_version IS DISTINCT FROM OLD.template_version THEN
                RAISE EXCEPTION 'signed documents cannot be edited';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            "CREATE TRIGGER signed_documents_immutable BEFORE UPDATE OR DELETE ON signed_documents "
            "FOR EACH ROW EXECUTE FUNCTION signed_documents_immutable()"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS signed_documents_immutable ON signed_documents")
        op.execute("DROP FUNCTION IF EXISTS signed_documents_immutable()")
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
