"""English names for measurement definitions and activity factors

Revision ID: 0002_english_names
Revises: 0001_initial
Create Date: 2026-10-22
"""
import json

import sqlalchemy as sa

from alembic import op
from app.db.reference_data import (
    ACTIVITY_TRANSLATIONS,
    CHOICE_TRANSLATIONS,
    DEFINITION_TRANSLATIONS,
)

revision = "0002_english_names"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Additive, nullable columns only.
    op.add_column("measurement_definitions", sa.Column("name_en", sa.String(120)))
    op.add_column("measurement_definitions", sa.Column("unit_en", sa.String(50)))
    op.add_column("activity_factors", sa.Column("name_en", sa.String(80)))
    op.add_column("activity_factors", sa.Column("description_en", sa.Text))

    conn = op.get_bind()
    for key, (name_en, unit_en) in DEFINITION_TRANSLATIONS.items():
        conn.execute(
            sa.text("UPDATE measurement_definitions SET name_en = :n, unit_en = :u WHERE key = :k"),
            {"n": name_en, "u": unit_en, "k": key},
        )
    # Add label_en to existing choice options (keeps any admin-edited Arabic labels).
    for key, labels in CHOICE_TRANSLATIONS.items():
        row = conn.execute(
            sa.text("SELECT id, choices FROM measurement_definitions WHERE key = :k"), {"k": key}
        ).first()
        if not row or not row.choices:
            continue
        choices = row.choices if isinstance(row.choices, list) else json.loads(row.choices)
        for c in choices:
            c.setdefault("label_en", labels.get(int(c["value"])))
        conn.execute(
            sa.text("UPDATE measurement_definitions SET choices = :c WHERE id = :id").bindparams(
                sa.bindparam("c", type_=sa.JSON)
            ),
            {"c": choices, "id": row.id},
        )
    for key, (name_en, desc_en) in ACTIVITY_TRANSLATIONS.items():
        conn.execute(
            sa.text("UPDATE activity_factors SET name_en = :n, description_en = :d WHERE key = :k"),
            {"n": name_en, "d": desc_en, "k": key},
        )


def downgrade() -> None:
    op.drop_column("activity_factors", "description_en")
    op.drop_column("activity_factors", "name_en")
    op.drop_column("measurement_definitions", "unit_en")
    op.drop_column("measurement_definitions", "name_en")
