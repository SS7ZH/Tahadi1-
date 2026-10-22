"""Create/update/delete measurement sessions with validation and audit logging."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import unprocessable
from app.core.i18n import tr
from app.db.reference_data import BP_LIMITS
from app.models import MeasurementDefinition, MeasurementSession, MeasurementValue, User
from app.schemas.measurement import SessionIn, ValueIn
from app.services import audit


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _range_error(d: MeasurementDefinition) -> None:
    unit = f" {d.unit}" if d.unit else ""
    unit_en = f" {d.unit_en or d.unit}" if (d.unit_en or d.unit) else ""
    raise unprocessable(
        tr(f"قيمة «{d.name_ar}» يجب أن تكون بين {_fmt(d.min_value)} و{_fmt(d.max_value)}{unit}", f"{d.name_en or d.name_ar} must be between {_fmt(d.min_value)} and {_fmt(d.max_value)}{unit_en}"), "OUT_OF_RANGE"
    )


def _check_range(d: MeasurementDefinition, value: float) -> None:
    if d.min_value is not None and value < d.min_value:
        _range_error(d)
    if d.max_value is not None and value > d.max_value:
        _range_error(d)


def build_value(d: MeasurementDefinition, v: ValueIn) -> MeasurementValue | None:
    """Validate one input against its definition. Returns None for an empty (skipped) field."""
    text = (v.value_text or "").strip() or None

    if d.value_type == "number":
        if v.value_number is None:
            return None
        _check_range(d, v.value_number)
        return MeasurementValue(definition=d, value_number=v.value_number)

    if d.value_type == "choice":
        if v.value_number is None:
            if text:
                raise unprocessable(tr(f"يجب اختيار قيمة لـ«{d.name_ar}» قبل إضافة الملاحظات", f"Choose a value for {d.name_en or d.name_ar} before adding notes"), "CHOICE_REQUIRED")
            return None
        allowed = {float(c["value"]) for c in (d.choices or [])}
        if allowed and float(v.value_number) not in allowed:
            raise unprocessable(tr(f"الاختيار غير صالح لـ«{d.name_ar}»", f"Invalid choice for {d.name_en or d.name_ar}"), "INVALID_CHOICE")
        return MeasurementValue(definition=d, value_number=v.value_number, value_text=text)

    if d.value_type == "text":
        if not text:
            return None
        return MeasurementValue(definition=d, value_text=text)

    if d.value_type == "blood_pressure":
        if v.systolic is None and v.diastolic is None:
            return None
        if v.systolic is None or v.diastolic is None:
            raise unprocessable(tr("يجب إدخال الضغط الانقباضي والانبساطي معاً", "Enter both systolic and diastolic pressure"), "BP_INCOMPLETE")
        (s_lo, s_hi), (d_lo, d_hi) = BP_LIMITS["systolic"], BP_LIMITS["diastolic"]
        if not (s_lo <= v.systolic <= s_hi):
            raise unprocessable(tr(f"الضغط الانقباضي يجب أن يكون بين {s_lo} و{s_hi} mmHg", f"Systolic pressure must be between {s_lo} and {s_hi} mmHg"), "OUT_OF_RANGE")
        if not (d_lo <= v.diastolic <= d_hi):
            raise unprocessable(tr(f"الضغط الانبساطي يجب أن يكون بين {d_lo} و{d_hi} mmHg", f"Diastolic pressure must be between {d_lo} and {d_hi} mmHg"), "OUT_OF_RANGE")
        if v.diastolic >= v.systolic:
            raise unprocessable(tr("الضغط الانقباضي يجب أن يكون أعلى من الانبساطي", "Systolic must be higher than diastolic"), "BP_INVALID")
        return MeasurementValue(
            definition=d,
            value_number=v.systolic,
            value_json={"systolic": v.systolic, "diastolic": v.diastolic},
        )
    return None


def build_values(db: Session, values_in: list[ValueIn]) -> list[MeasurementValue]:
    defs = {d.key: d for d in db.scalars(select(MeasurementDefinition))}
    out: list[MeasurementValue] = []
    for v in values_in:
        d = defs.get(v.key)
        if d is None:
            raise unprocessable(tr(f"نوع قياس غير معروف: {v.key}", f"Unknown measurement type: {v.key}"), "UNKNOWN_MEASUREMENT")
        mv = build_value(d, v)
        if mv is not None:
            out.append(mv)
    return out


def create_session(db: Session, actor: User, client: User, data: SessionIn) -> MeasurementSession:
    session = MeasurementSession(
        client_id=client.id,
        trainer_id=actor.id,
        updated_by_id=actor.id,
        session_date=data.session_date,
        notes=(data.notes or "").strip() or None,
    )
    session.values = build_values(db, data.values)
    db.add(session)
    db.flush()
    audit.record(
        db, actor, "create", "measurement_session", session.id,
        {"client_id": client.id, "client_name": client.full_name, "after": audit.session_snapshot(session)},
    )
    db.commit()
    db.refresh(session)
    return session


def update_session(db: Session, actor: User, session: MeasurementSession, data: SessionIn) -> MeasurementSession:
    before = audit.session_snapshot(session)
    new_values = build_values(db, data.values)
    sent_keys = {v.key for v in data.values}
    # Keep values of definitions that were deactivated (the form no longer shows them) unless explicitly sent.
    kept = kept_copy(
        [v for v in session.values if not v.definition.is_active and v.definition.key not in sent_keys]
    )

    session.values.clear()
    db.flush()  # delete old rows before inserting, the (session, definition) pair is unique
    session.values.extend(kept + new_values)
    session.session_date = data.session_date
    session.notes = (data.notes or "").strip() or None
    session.updated_by_id = actor.id
    db.flush()
    client = db.get(User, session.client_id)
    audit.record(
        db, actor, "update", "measurement_session", session.id,
        {
            "client_id": session.client_id,
            "client_name": client.full_name if client else None,
            "before": before,
            "after": audit.session_snapshot(session),
        },
    )
    db.commit()
    db.refresh(session)
    return session


def kept_copy(values: list[MeasurementValue]) -> list[MeasurementValue]:
    return [
        MeasurementValue(
            definition=v.definition, value_number=v.value_number, value_text=v.value_text, value_json=v.value_json
        )
        for v in values
    ]


def delete_session(db: Session, actor: User, session: MeasurementSession) -> None:
    client = db.get(User, session.client_id)
    audit.record(
        db, actor, "delete", "measurement_session", session.id,
        {
            "client_id": session.client_id,
            "client_name": client.full_name if client else None,
            "before": audit.session_snapshot(session),
        },
    )
    db.delete(session)
    db.commit()
