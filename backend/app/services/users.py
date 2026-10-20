from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found, unprocessable
from app.core.security import hash_password
from app.models import ActivityFactor, ClientProfile, MeasurementDefinition, MeasurementSession, MeasurementValue, Question, User
from app.services.progress import effective_direction, trend

PROFILE_FIELDS = ("sex", "birth_date", "height_cm", "goal", "activity_key", "notes")


def ensure_email_free(db: Session, email: str, exclude_id: int | None = None) -> None:
    stmt = select(User.id).where(func.lower(User.email) == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise AppError(409, "EMAIL_TAKEN", "البريد الإلكتروني مستخدم مسبقاً")


def ensure_activity_key(db: Session, key: str | None) -> None:
    if key is not None and db.scalar(select(ActivityFactor.id).where(ActivityFactor.key == key)) is None:
        raise unprocessable("مستوى النشاط غير معروف", "UNKNOWN_ACTIVITY")


def get_active_trainer(db: Session, trainer_id: int) -> User:
    trainer = db.get(User, trainer_id)
    if trainer is None or trainer.role != "trainer" or trainer.deleted_at is not None:
        raise not_found("المدرب غير موجود")
    if not trainer.is_active:
        raise unprocessable("لا يمكن ربط عميل بمدرب موقوف", "TRAINER_INACTIVE")
    return trainer


def create_user(
    db: Session,
    *,
    full_name: str,
    email: str,
    phone: str | None,
    password: str,
    role: str,
    profile: dict | None = None,
) -> User:
    ensure_email_free(db, email)
    user = User(
        full_name=full_name,
        email=email.lower(),
        phone=(phone or "").strip() or None,
        password_hash=hash_password(password),
        role=role,
    )
    if role == "client":
        profile = profile or {}
        missing = [f for f in ("sex", "birth_date", "height_cm") if profile.get(f) is None]
        if missing:
            labels = {"sex": "الجنس", "birth_date": "تاريخ الميلاد", "height_cm": "الطول"}
            raise unprocessable("بيانات العميل ناقصة: " + "، ".join(labels[m] for m in missing), "PROFILE_REQUIRED")
        ensure_activity_key(db, profile.get("activity_key"))
        if profile.get("trainer_id") is not None:
            get_active_trainer(db, profile["trainer_id"])
        user.profile = ClientProfile(
            trainer_id=profile.get("trainer_id"),
            sex=profile["sex"],
            birth_date=profile["birth_date"],
            height_cm=profile["height_cm"],
            goal=profile.get("goal") or "fitness",
            activity_key=profile.get("activity_key") or "moderate",
            notes=profile.get("notes"),
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def apply_profile_changes(db: Session, user: User, changes: dict) -> None:
    if user.profile is None:
        return
    if "activity_key" in changes:
        ensure_activity_key(db, changes["activity_key"])
    for field in PROFILE_FIELDS:
        if field in changes and (changes[field] is not None or field == "notes"):
            setattr(user.profile, field, changes[field])


def client_list_items(db: Session, clients: list[User]) -> list[dict]:
    if not clients:
        return []
    ids = [c.id for c in clients]

    counts = {
        cid: (n, last)
        for cid, n, last in db.execute(
            select(MeasurementSession.client_id, func.count(), func.max(MeasurementSession.session_date))
            .where(MeasurementSession.client_id.in_(ids))
            .group_by(MeasurementSession.client_id)
        )
    }
    open_q = dict(
        db.execute(
            select(Question.client_id, func.count())
            .where(Question.client_id.in_(ids), Question.status == "open")
            .group_by(Question.client_id)
        ).all()
    )
    weights: dict[int, list[float]] = defaultdict(list)
    for cid, value in db.execute(
        select(MeasurementSession.client_id, MeasurementValue.value_number)
        .join(MeasurementValue, MeasurementValue.session_id == MeasurementSession.id)
        .join(MeasurementDefinition, MeasurementDefinition.id == MeasurementValue.definition_id)
        .where(MeasurementSession.client_id.in_(ids), MeasurementDefinition.key == "weight")
        .order_by(MeasurementSession.session_date, MeasurementSession.id)
    ):
        if value is not None:
            weights[cid].append(value)

    items = []
    for c in clients:
        p = c.profile
        w = weights.get(c.id, [])
        first, latest = (w[0], w[-1]) if w else (None, None)
        change = round(latest - first, 2) if w and len(w) > 1 else None
        bmi = None
        if latest and p and p.height_cm:
            bmi = latest / (p.height_cm / 100) ** 2
        direction = effective_direction("weight", "none", p.goal if p else None, bmi)
        n, last = counts.get(c.id, (0, None))
        items.append(
            {
                "id": c.id,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "is_active": c.is_active,
                "sex": p.sex if p else None,
                "goal": p.goal if p else None,
                "trainer_id": p.trainer_id if p else None,
                "trainer_name": p.trainer.full_name if p and p.trainer else None,
                "sessions_count": n,
                "last_session_date": last,
                "weight_first": first,
                "weight_latest": latest,
                "weight_change": change,
                "weight_trend": trend(direction, change),
                "open_questions": open_q.get(c.id, 0),
            }
        )
    return items
