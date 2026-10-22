"""Exercise programs: exercise library, programs, days, items; questions can reference a program day

Revision ID: 0004_programs
Revises: 0003_nutrition
Create Date: 2026-10-22
"""
import sqlalchemy as sa

from alembic import op
from app.db.reference_data import EXERCISES

revision = "0004_programs"
down_revision = "0003_nutrition"
branch_labels = None
depends_on = None

NEW_TABLES = ["exercises", "programs", "program_days", "program_items"]


def upgrade() -> None:
    exercises = op.create_table(
        "exercises",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name_ar", sa.String(120), nullable=False),
        sa.Column("name_en", sa.String(120), nullable=False),
        sa.Column("muscle_group", sa.String(30), nullable=False),
        sa.Column("equipment", sa.String(30)),
        sa.Column("video_url", sa.String(500)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_exercises_muscle_group", "exercises", ["muscle_group"])
    op.bulk_insert(exercises, EXERCISES)

    op.create_table(
        "programs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("goal", sa.String(150)),
        sa.Column("start_date", sa.Date),
        sa.Column("weeks", sa.Integer, nullable=False, server_default="4"),
        sa.Column("days_per_week", sa.Integer, nullable=False, server_default="3"),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft','active','archived')", name="program_status_valid"),
        sa.CheckConstraint("is_template OR client_id IS NOT NULL", name="program_owner_valid"),
    )
    op.create_index("ix_programs_client_id", "programs", ["client_id"])
    op.create_index("ix_programs_status", "programs", ["status"])

    op.create_table(
        "program_days",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("program_id", sa.Integer, sa.ForeignKey("programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_number", sa.Integer, nullable=False),
        sa.Column("week_number", sa.Integer),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("is_rest", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("warmup", sa.Text),
        sa.Column("cooldown", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.CheckConstraint("day_number BETWEEN 1 AND 7", name="program_day_number_valid"),
    )
    op.create_index("ix_program_days_program_id", "program_days", ["program_id"])

    op.create_table(
        "program_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("day_id", sa.Integer, sa.ForeignKey("program_days.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("exercise_id", sa.Integer, sa.ForeignKey("exercises.id", ondelete="SET NULL")),
        sa.Column("custom_name", sa.String(150)),
        sa.Column("muscle_group", sa.String(30)),
        sa.Column("sets", sa.Integer),
        sa.Column("reps", sa.String(20)),
        sa.Column("load_value", sa.Float),
        sa.Column("load_unit", sa.String(10)),
        sa.Column("rest_seconds", sa.Integer),
        sa.Column("tempo", sa.String(20)),
        sa.Column("cardio_type", sa.String(20)),
        sa.Column("duration_min", sa.Float),
        sa.Column("hr_zone", sa.Integer),
        sa.Column("speed", sa.Float),
        sa.Column("incline", sa.Float),
        sa.Column("work_seconds", sa.Integer),
        sa.Column("interval_rest_seconds", sa.Integer),
        sa.Column("rounds", sa.Integer),
        sa.Column("notes", sa.Text),
        sa.Column("video_url", sa.String(500)),
        sa.CheckConstraint("kind IN ('resistance','cardio')", name="program_item_kind_valid"),
    )
    op.create_index("ix_program_items_day_id", "program_items", ["day_id"])

    # Additive: questions can be about a program day.
    with op.batch_alter_table("questions") as batch:
        batch.add_column(sa.Column("program_day_id", sa.Integer))
        batch.create_foreign_key(
            "fk_questions_program_day_id_program_days", "program_days", ["program_day_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index("ix_questions_program_day_id", ["program_day_id"])

    if op.get_bind().dialect.name == "postgresql":
        for table in NEW_TABLES:
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_index("ix_questions_program_day_id")
        batch.drop_constraint("fk_questions_program_day_id_program_days", type_="foreignkey")
        batch.drop_column("program_day_id")
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
