"""Agent 4 - Progress analyst, on real client accounts.

Facts and alerts are computed in code (app.rules.progress) from the client's measurement
sessions; the DevAI Progress Analyst agent only turns them into words (template fallback).
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import text as t
from app.models import MeasurementSession, User
from app.rules.progress import compute_facts

_KEYS = {"weight": "weight_kg", "waist": "waist_cm"}


def measurement_rows(db: Session, client_id: int) -> list[dict]:
    """One row per session that has a weight or waist value, oldest first."""
    sessions = db.scalars(
        select(MeasurementSession)
        .where(MeasurementSession.client_id == client_id)
        .order_by(MeasurementSession.session_date, MeasurementSession.created_at, MeasurementSession.id)
    ).all()
    rows = []
    for s in sessions:
        row = {"date": s.session_date, "weight_kg": None, "waist_cm": None}
        for v in s.values:
            field = _KEYS.get(v.definition.key)
            if field and v.value_number is not None:
                row[field] = float(v.value_number)
        if row["weight_kg"] is not None or row["waist_cm"] is not None:
            rows.append(row)
    return rows


def analyze(db: Session, client: User, today: date | None = None) -> dict:
    facts, alerts = compute_facts(measurement_rows(db, client.id), today or date.today())
    result = t.summary_result(client.full_name, facts, alerts)
    return {"client_id": client.id, "client_name": client.full_name, "facts": facts, "alerts": alerts, **result}
