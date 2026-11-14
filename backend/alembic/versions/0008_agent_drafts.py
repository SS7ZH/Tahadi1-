"""Coach-assistant drafts linked to real client accounts.

Revision ID: 0008_agent_drafts
Revises: 0007_telegram_client_link
Create Date: 2026-11-14
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_agent_drafts"
down_revision = "0007_telegram_client_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="template"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status in ('pending', 'approved', 'rejected')", name="ck_agent_drafts_status"),
    )
    op.create_index("ix_agent_drafts_client_id", "agent_drafts", ["client_id"])
    op.create_index("ix_agent_drafts_status", "agent_drafts", ["status"])
    # Same rule as every other table (0001): RLS on, no policies, so Supabase's REST API sees nothing.
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."agent_drafts" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_agent_drafts_status", table_name="agent_drafts")
    op.drop_index("ix_agent_drafts_client_id", table_name="agent_drafts")
    op.drop_table("agent_drafts")
