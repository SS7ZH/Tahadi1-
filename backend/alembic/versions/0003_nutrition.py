"""Calories & macros: nutrition settings per goal, saved nutrition plans, 'performance' goal

Revision ID: 0003_nutrition
Revises: 0002_english_names
Create Date: 2026-10-22
"""
import sqlalchemy as sa

from alembic import op
from app.db.reference_data import NUTRITION_SETTINGS

revision = "0003_nutrition"
down_revision = "0002_english_names"
branch_labels = None
depends_on = None

NEW_TABLES = ["nutrition_settings", "nutrition_plans"]
GOALS_V1 = "'fat_loss','muscle_gain','fitness','health'"
GOALS_V3 = "'fat_loss','muscle_gain','fitness','health','performance'"


def upgrade() -> None:
    settings = op.create_table(
        "nutrition_settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("goal", sa.String(20), nullable=False),
        sa.Column("calorie_adjustment", sa.Integer, nullable=False),
        sa.Column("protein_pct", sa.Float, nullable=False),
        sa.Column("carbs_pct", sa.Float, nullable=False),
        sa.Column("fat_pct", sa.Float, nullable=False),
        sa.Column("meals_min", sa.Integer, nullable=False),
        sa.Column("meals_max", sa.Integer, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("goal", name="uq_nutrition_settings_goal"),
        sa.CheckConstraint("goal IN ('weight_loss','maintenance','weight_gain')", name="nutrition_goal_valid"),
    )
    op.bulk_insert(settings, NUTRITION_SETTINGS)

    op.create_table(
        "nutrition_plans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("goal", sa.String(20), nullable=False),
        sa.Column("nutrition_goal", sa.String(20), nullable=False),
        sa.Column("based_on_weight", sa.Float),
        sa.Column("based_on_session_id", sa.Integer, sa.ForeignKey("measurement_sessions.id", ondelete="SET NULL")),
        sa.Column("dcn", sa.Integer),
        sa.Column("suggested_calories", sa.Integer),
        sa.Column("calories", sa.Integer, nullable=False),
        sa.Column("protein_g", sa.Integer, nullable=False),
        sa.Column("carbs_g", sa.Integer, nullable=False),
        sa.Column("fat_g", sa.Integer, nullable=False),
        sa.Column("protein_pct", sa.Float, nullable=False),
        sa.Column("carbs_pct", sa.Float, nullable=False),
        sa.Column("fat_pct", sa.Float, nullable=False),
        sa.Column("meals_per_day", sa.Integer, nullable=False),
        sa.Column("overridden", sa.JSON),
        sa.Column("note", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_nutrition_plans_client_id", "nutrition_plans", ["client_id"])

    if op.get_bind().dialect.name == "postgresql":
        # Widen the allowed goals (additive): existing rows stay valid.
        op.execute("ALTER TABLE client_profiles DROP CONSTRAINT IF EXISTS goal_valid")
        op.execute(f"ALTER TABLE client_profiles ADD CONSTRAINT goal_valid CHECK (goal IN ({GOALS_V3}))")
        for table in NEW_TABLES:
            op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("UPDATE client_profiles SET goal = 'fitness' WHERE goal = 'performance'")
        op.execute("ALTER TABLE client_profiles DROP CONSTRAINT IF EXISTS goal_valid")
        op.execute(f"ALTER TABLE client_profiles ADD CONSTRAINT goal_valid CHECK (goal IN ({GOALS_V1}))")
    op.drop_table("nutrition_plans")
    op.drop_table("nutrition_settings")
