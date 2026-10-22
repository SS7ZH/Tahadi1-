"""Public home page: admin-editable site settings (hero, features, contact)

Revision ID: 0006_site_settings
Revises: 0005_onboarding
Create Date: 2026-10-22
"""
import sqlalchemy as sa
from alembic import op

from app.db.reference_data import DEFAULT_HOME

revision = "0006_site_settings"
down_revision = "0005_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table = op.create_table(
        "site_settings",
        sa.Column("key", sa.String(50), primary_key=True),
        sa.Column("value", sa.JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
    )
    op.bulk_insert(table, [{"key": "home", "value": DEFAULT_HOME}])
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."site_settings" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table("site_settings")
