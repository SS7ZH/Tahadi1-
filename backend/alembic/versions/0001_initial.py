"""initial schema, reference data and row level security

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-20
"""
import sqlalchemy as sa

from alembic import op
from app.db.reference_data import ACTIVITY_FACTORS, MEASUREMENT_DEFINITIONS

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    "activity_factors",
    "users",
    "client_profiles",
    "measurement_definitions",
    "measurement_sessions",
    "measurement_values",
    "comments",
    "questions",
    "question_replies",
    "audit_log",
]


def _ts(name: str, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=nullable)


def upgrade() -> None:
    activity = op.create_table(
        "activity_factors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(30), nullable=False),
        sa.Column("name_ar", sa.String(80), nullable=False),
        sa.Column("description_ar", sa.Text),
        sa.Column("factor", sa.Float, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("key", name="uq_activity_factors_key"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("full_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        _ts("created_at"),
        sa.CheckConstraint("role IN ('admin','trainer','client')", name="role_valid"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "client_profiles",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("trainer_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("birth_date", sa.Date),
        sa.Column("height_cm", sa.Float),
        sa.Column("goal", sa.String(20), nullable=False, server_default="fitness"),
        sa.Column(
            "activity_key",
            sa.String(30),
            sa.ForeignKey("activity_factors.key", ondelete="SET NULL", onupdate="CASCADE"),
        ),
        sa.Column("notes", sa.Text),
        sa.CheckConstraint("sex IN ('male','female')", name="sex_valid"),
        sa.CheckConstraint("goal IN ('fat_loss','muscle_gain','fitness','health')", name="goal_valid"),
    )
    op.create_index("ix_client_profiles_trainer_id", "client_profiles", ["trainer_id"])

    definitions = op.create_table(
        "measurement_definitions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(50), nullable=False),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("value_type", sa.String(20), nullable=False),
        sa.Column("choices", sa.JSON),
        sa.Column("better_direction", sa.String(10), nullable=False, server_default="none"),
        sa.Column("min_value", sa.Float),
        sa.Column("max_value", sa.Float),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("key", name="uq_measurement_definitions_key"),
    )

    op.create_table(
        "measurement_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trainer_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("session_date", sa.Date, nullable=False),
        sa.Column("notes", sa.Text),
        _ts("created_at"),
        _ts("updated_at"),
    )
    op.create_index("ix_measurement_sessions_client_id", "measurement_sessions", ["client_id"])
    op.create_index("ix_measurement_sessions_session_date", "measurement_sessions", ["session_date"])

    op.create_table(
        "measurement_values",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "session_id", sa.Integer, sa.ForeignKey("measurement_sessions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "definition_id",
            sa.Integer,
            sa.ForeignKey("measurement_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value_number", sa.Float),
        sa.Column("value_text", sa.Text),
        sa.Column("value_json", sa.JSON),
        sa.UniqueConstraint("session_id", "definition_id", name="uq_measurement_values_session_definition"),
    )
    op.create_index("ix_measurement_values_session_id", "measurement_values", ["session_id"])
    op.create_index("ix_measurement_values_definition_id", "measurement_values", ["definition_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("measurement_sessions.id", ondelete="CASCADE")),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text, nullable=False),
        _ts("created_at"),
    )
    op.create_index("ix_comments_client_id", "comments", ["client_id"])
    op.create_index("ix_comments_session_id", "comments", ["session_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("measurement_sessions.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        _ts("created_at"),
        _ts("updated_at"),
        sa.CheckConstraint("status IN ('open','answered','closed')", name="status_valid"),
    )
    op.create_index("ix_questions_client_id", "questions", ["client_id"])
    op.create_index("ix_questions_session_id", "questions", ["session_id"])
    op.create_index("ix_questions_status", "questions", ["status"])

    op.create_table(
        "question_replies",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text, nullable=False),
        _ts("created_at"),
    )
    op.create_index("ix_question_replies_question_id", "question_replies", ["question_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Integer),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("diff", sa.JSON),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_timestamp", "audit_log", ["timestamp"])

    # ---- reference data ----
    op.bulk_insert(activity, ACTIVITY_FACTORS)
    op.bulk_insert(definitions, MEASUREMENT_DEFINITIONS)

    # ---- Supabase: block the auto-generated public REST API ----
    # RLS enabled with NO policies => anon/authenticated roles see nothing.
    # The backend connects as the table owner (postgres), which bypasses RLS.
    if op.get_bind().dialect.name == "postgresql":
        for table in TABLES + ["alembic_version"]:
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_table(table)
