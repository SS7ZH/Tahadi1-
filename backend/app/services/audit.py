from sqlalchemy.orm import Session

from app.models import AuditLog, MeasurementSession, User


def session_snapshot(session: MeasurementSession) -> dict:
    return {
        "session_date": session.session_date.isoformat(),
        "notes": session.notes,
        "values": {
            v.definition.key: {
                k: val
                for k, val in (("number", v.value_number), ("text", v.value_text), ("json", v.value_json))
                if val is not None
            }
            for v in session.values
        },
    }


def record(db: Session, actor: User, action: str, entity: str, entity_id: int | None, diff: dict | None) -> None:
    db.add(AuditLog(actor_id=actor.id, action=action, entity=entity, entity_id=entity_id, diff=diff))
