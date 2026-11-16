"""ORM → response dicts. Centralised so password_hash can never slip into a response."""
from datetime import date

from app.core.i18n import pick
from app.models import Comment, MeasurementSession, MeasurementValue, Question, User
from app.schemas.user import ClientProfileOut, UserDetailOut
from app.services.calculations import age_on


def user_detail(user: User) -> UserDetailOut:
    profile = user.profile if user.role == "client" else None
    return UserDetailOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=user.role,  # type: ignore[arg-type]
        is_active=user.is_active,
        created_at=user.created_at,
        profile=ClientProfileOut.model_validate(profile) if profile else None,
        trainer_name=profile.trainer.full_name if profile and profile.trainer else None,
        age=age_on(profile.birth_date, date.today()) if profile and profile.birth_date else None,
    )


def _fmt_number(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}".rstrip("0").rstrip(".")


def value_display(mv: MeasurementValue) -> str:
    d = mv.definition
    if d.value_type == "blood_pressure" and mv.value_json:
        return f"{_fmt_number(mv.value_json['systolic'])}/{_fmt_number(mv.value_json['diastolic'])}"
    if d.value_type == "choice" and mv.value_number is not None:
        opt = next((c for c in (d.choices or []) if float(c["value"]) == mv.value_number), None)
        label = pick(opt.get("label"), opt.get("label_en")) if opt else None
        return label or _fmt_number(mv.value_number)
    if d.value_type == "text":
        return mv.value_text or ""
    if mv.value_number is not None:
        return _fmt_number(mv.value_number)
    return mv.value_text or ""


def value_out(mv: MeasurementValue) -> dict:
    d = mv.definition
    return {
        "key": d.key,
        "name_ar": d.name_ar,
        "name_en": d.name_en,
        "category": d.category,
        "unit": d.unit,
        "unit_en": d.unit_en,
        "value_type": d.value_type,
        "value_number": mv.value_number,
        "value_text": mv.value_text,
        "value_json": mv.value_json,
        "display": value_display(mv),
    }


def session_out(session: MeasurementSession, comments_count: int = 0) -> dict:
    values = sorted(session.values, key=lambda v: v.definition.sort_order)
    return {
        "id": session.id,
        "client_id": session.client_id,
        "session_date": session.session_date,
        "notes": session.notes,
        "trainer_id": session.trainer_id,
        "trainer_name": session.trainer.full_name if session.trainer else None,
        "updated_by_name": session.updated_by.full_name if session.updated_by else None,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "values": [value_out(v) for v in values],
        "comments_count": comments_count,
    }


def comment_out(c: Comment) -> dict:
    return {
        "id": c.id,
        "client_id": c.client_id,
        "session_id": c.session_id,
        "author_id": c.author_id,
        "author_name": c.author.full_name if c.author else None,
        "author_role": c.author.role if c.author else None,
        "body": c.body,
        "created_at": c.created_at,
    }


def question_out(q: Question, session_date: date | None = None, day: dict | None = None) -> dict:
    return {
        "id": q.id,
        "client_id": q.client_id,
        "client_name": q.client.full_name,
        "session_id": q.session_id,
        "session_date": session_date,
        "program_day_id": q.program_day_id,
        "program_day_title": day["title"] if day else None,
        "program_id": day["program_id"] if day else None,
        "body": q.body,
        "status": q.status,
        "source": q.source,
        "created_at": q.created_at,
        "updated_at": q.updated_at,
        "replies": [
            {
                "id": r.id,
                "author_id": r.author_id,
                "author_name": r.author.full_name if r.author else None,
                "author_role": r.author.role if r.author else None,
                "body": r.body,
                "created_at": r.created_at,
            }
            for r in q.replies
        ],
    }
