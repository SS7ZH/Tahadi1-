"""Private chat with the bot instead of groups (ADR-0012): Telegram file ids, player photos.

Revision ID: 0010_telegram_private_chat
Revises: 0009_telegram_groups
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_telegram_private_chat"
down_revision = "0009_telegram_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("squat_checks", sa.Column("telegram_file_id", sa.String(255), nullable=True))
    op.create_table(
        "client_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telegram_file_id", sa.String(255), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_client_photos_client_id", "client_photos", ["client_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."client_photos" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_client_photos_client_id", table_name="client_photos")
    op.drop_table("client_photos")
    op.drop_column("squat_checks", "telegram_file_id")
