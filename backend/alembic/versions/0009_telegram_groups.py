"""Telegram-only players in a group per player (ADR-0011).

- users.email / users.password_hash become optional (players never log in)
- users.telegram_user_id: a coach's own Telegram account (drafts are sent there to approve)
- client_profiles.telegram_invite_url / telegram_step: the player's group invite and profile questions
- questions.source: 'app' or 'telegram'
- agent_drafts.question_id / telegram_message_id: drafts answering a question, approvable on Telegram
- squat_checks: squat sets linked to a real player (Telegram video or browser checker)

Revision ID: 0009_telegram_groups
Revises: 0008_agent_drafts
Create Date: 2026-11-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_telegram_groups"
down_revision = "0008_agent_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as t:
        t.alter_column("email", existing_type=sa.String(255), nullable=True)
        t.alter_column("password_hash", existing_type=sa.String(255), nullable=True)
        t.add_column(sa.Column("telegram_user_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_users_telegram_user_id", "users", ["telegram_user_id"], unique=True)

    op.add_column("client_profiles", sa.Column("telegram_invite_url", sa.String(255), nullable=True))
    op.add_column("client_profiles", sa.Column("telegram_step", sa.String(30), nullable=True))

    op.add_column("questions", sa.Column("source", sa.String(20), nullable=False, server_default="app"))

    op.add_column("agent_drafts", sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id", ondelete="SET NULL"), nullable=True))
    op.add_column("agent_drafts", sa.Column("telegram_message_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_agent_drafts_question_id", "agent_drafts", ["question_id"])

    op.create_table(
        "squat_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="telegram"),
        sa.Column("status", sa.String(20), nullable=False, server_default="analysed"),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("errors", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("video_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status in ('analysed', 'awaiting_review', 'failed')", name="ck_squat_checks_status"),
    )
    op.create_index("ix_squat_checks_client_id", "squat_checks", ["client_id"])
    # Same rule as every other table: RLS on, no policies, so Supabase's REST API sees nothing.
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE public."squat_checks" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_index("ix_squat_checks_client_id", table_name="squat_checks")
    op.drop_table("squat_checks")
    op.drop_index("ix_agent_drafts_question_id", table_name="agent_drafts")
    op.drop_column("agent_drafts", "telegram_message_id")
    op.drop_column("agent_drafts", "question_id")
    op.drop_column("questions", "source")
    op.drop_column("client_profiles", "telegram_step")
    op.drop_column("client_profiles", "telegram_invite_url")
    op.drop_index("ix_users_telegram_user_id", table_name="users")
    with op.batch_alter_table("users") as t:
        t.drop_column("telegram_user_id")
        t.alter_column("password_hash", existing_type=sa.String(255), nullable=False)
        t.alter_column("email", existing_type=sa.String(255), nullable=False)
