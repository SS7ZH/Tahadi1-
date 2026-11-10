"""Add Telegram identity to real client profiles and mark measurement source.

Revision ID: 0007_telegram_client_link
Revises: 0006_site_settings
Create Date: 2026-11-10
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_telegram_client_link"
down_revision = "0006_site_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("client_profiles", sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True))
    op.create_index(
        "ix_client_profiles_telegram_chat_id",
        "client_profiles",
        ["telegram_chat_id"],
        unique=True,
    )
    op.add_column(
        "measurement_sessions",
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("measurement_sessions", "source")
    op.drop_index("ix_client_profiles_telegram_chat_id", table_name="client_profiles")
    op.drop_column("client_profiles", "telegram_chat_id")