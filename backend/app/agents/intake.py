"""Agent 1 - Intake. Turns a Telegram message into a saved measurement."""

from datetime import date

from sqlalchemy import select

from app.agents import text as t
from app.db.session import get_sessionmaker
from app.models import ClientProfile, MeasurementSession, User
from app.rules.parsing import is_arabic, normalize, parse_measurement, validate_measurement
from app.schemas.measurement import ValueIn
from app.services import audit, measurements


def find_client_by_chat(chat_id: int) -> dict | None:
    with get_sessionmaker()() as db:
        row = db.execute(
            select(User.id, User.full_name)
            .join(ClientProfile, ClientProfile.user_id == User.id)
            .where(
                ClientProfile.telegram_chat_id == chat_id,
                User.role == "client",
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            .limit(1)
        ).first()
    return {"id": row.id, "name": row.full_name} if row else None


def save_measurement(client_id: int, values: dict) -> None:
    inputs = [
        ValueIn(key=key, value_number=values[value_key])
        for key, value_key in (("weight", "weight_kg"), ("waist", "waist_cm"))
        if values.get(value_key) is not None
    ]
    with get_sessionmaker()() as db:
        client = db.get(User, client_id)
        if client is None or client.profile is None:
            return
        session = MeasurementSession(
            client_id=client.id,
            trainer_id=None,
            updated_by_id=client.id,
            session_date=date.today(),
            source="telegram",
        )
        session.values = measurements.build_values(db, inputs)
        db.add(session)
        db.flush()
        audit.record(
            db,
            client,
            "create",
            "measurement_session",
            session.id,
            {"client_id": client.id, "source": "telegram", "after": audit.session_snapshot(session)},
        )
        db.commit()


def handle_message(chat_id: int, text: str) -> str:
    client = find_client_by_chat(chat_id)
    if client is None:
        return t.NOT_LINKED

    arabic = is_arabic(text)
    values = parse_measurement(text)
    if values is None:
        values = validate_measurement(t.extract_measurement(normalize(text)))
    if values is None:
        return t.not_a_measurement(arabic)

    save_measurement(client["id"], values)
    return t.confirmation(values, arabic)
