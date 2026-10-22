from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.core.errors import AppError, bad_request, not_found
from app.core.i18n import tr
from app.core.security import hash_password
from app.db.session import get_db
from app.models import (
    ActivityFactor,
    AuditLog,
    ClientProfile,
    MeasurementDefinition,
    MeasurementSession,
    Question,
    User,
)
from app.schemas.measurement import (
    ActivityFactorOut,
    ActivityFactorUpdate,
    DefinitionCreate,
    DefinitionOut,
    DefinitionUpdate,
)
from app.schemas.user import AdminUserCreate, AdminUserUpdate, AssignTrainerIn, Role, UserDetailOut
from app.services import audit, users
from app.services.serializers import user_detail

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])
admin_user = require_role("admin")


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found(tr("المستخدم غير موجود", "User not found"))
    return user


# ---------------- users ----------------
@router.get("/users", response_model=list[UserDetailOut])
def list_users(
    role: Role | None = None,
    q: str | None = Query(default=None, max_length=100),
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(User).where(User.deleted_at.is_(None))
    if role:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(like) | func.lower(User.email).like(like))
    return [user_detail(u) for u in db.scalars(stmt.order_by(User.role, User.full_name)).unique()]


@router.post("/users", response_model=UserDetailOut, status_code=status.HTTP_201_CREATED)
def create_user(data: AdminUserCreate, actor: User = Depends(admin_user), db: Session = Depends(get_db)):
    profile = data.model_dump(include={*users.PROFILE_FIELDS, "trainer_id"}) if data.role == "client" else None
    user = users.create_user(
        db,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        password=data.password,
        role=data.role,
        profile=profile,
    )
    audit.record(db, actor, "create", "user", user.id, {"role": user.role, "email": user.email})
    db.commit()
    return user_detail(user)


@router.get("/users/{user_id}", response_model=UserDetailOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_detail(_get_user(db, user_id))


@router.patch("/users/{user_id}", response_model=UserDetailOut)
def update_user(
    user_id: int, data: AdminUserUpdate, actor: User = Depends(admin_user), db: Session = Depends(get_db)
):
    user = _get_user(db, user_id)
    changes = data.model_dump(exclude_unset=True)
    if user.id == actor.id and changes.get("is_active") is False:
        raise bad_request(tr("لا يمكنك إيقاف حسابك", "You cannot deactivate your own account"), "SELF_DEACTIVATE")
    if changes.get("email"):
        users.ensure_email_free(db, changes["email"], exclude_id=user.id)
        user.email = changes["email"].lower()
    if changes.get("full_name"):
        user.full_name = changes["full_name"]
    if "phone" in changes:
        user.phone = (changes["phone"] or "").strip() or None
    if changes.get("is_active") is not None:
        user.is_active = changes["is_active"]
    if changes.get("password"):
        user.password_hash = hash_password(changes["password"])
    users.apply_profile_changes(db, user, changes)
    audit.record(
        db, actor, "update", "user", user.id,
        {"fields": sorted(k for k in changes if k != "password") + (["password"] if "password" in changes else [])},
    )
    db.commit()
    db.refresh(user)
    return user_detail(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, actor: User = Depends(admin_user), db: Session = Depends(get_db)):
    """Soft delete: the account is hidden and cannot log in, but health history is preserved."""
    user = _get_user(db, user_id)
    if user.id == actor.id:
        raise bad_request(tr("لا يمكنك حذف حسابك", "You cannot delete your own account"), "SELF_DELETE")
    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False
    if user.role == "trainer":
        for profile in db.scalars(select(ClientProfile).where(ClientProfile.trainer_id == user.id)):
            profile.trainer_id = None
    audit.record(db, actor, "delete", "user", user.id, {"role": user.role, "email": user.email, "soft": True})
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/clients/{client_id}/assign-trainer", response_model=UserDetailOut)
def assign_trainer(
    client_id: int, data: AssignTrainerIn, actor: User = Depends(admin_user), db: Session = Depends(get_db)
):
    client = _get_user(db, client_id)
    if client.role != "client" or client.profile is None:
        raise not_found(tr("العميل غير موجود", "Client not found"))
    if data.trainer_id is not None:
        users.get_active_trainer(db, data.trainer_id)
    before = client.profile.trainer_id
    client.profile.trainer_id = data.trainer_id
    audit.record(db, actor, "update", "client_assignment", client.id, {"before": before, "after": data.trainer_id})
    db.commit()
    db.refresh(client)
    return user_detail(client)


# ---------------- stats ----------------
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    today = date.today()
    month_start = today.replace(day=1)

    def count_role(role: str) -> int:
        return db.scalar(
            select(func.count()).select_from(User).where(User.role == role, User.deleted_at.is_(None))
        ) or 0

    recent = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(12)).unique()
    return {
        "trainers": count_role("trainer"),
        "clients": count_role("client"),
        "unassigned_clients": db.scalar(
            select(func.count())
            .select_from(ClientProfile)
            .join(User, User.id == ClientProfile.user_id)
            .where(ClientProfile.trainer_id.is_(None), User.deleted_at.is_(None))
        ) or 0,
        "measurements_this_month": db.scalar(
            select(func.count()).select_from(MeasurementSession).where(MeasurementSession.session_date >= month_start)
        ) or 0,
        "open_questions": db.scalar(select(func.count()).select_from(Question).where(Question.status == "open")) or 0,
        "recent_activity": [
            {
                "id": a.id,
                "action": a.action,
                "entity": a.entity,
                "entity_id": a.entity_id,
                "actor_name": a.actor.full_name if a.actor else None,
                "client_name": (a.diff or {}).get("client_name"),
                "timestamp": a.timestamp,
            }
            for a in recent
        ],
    }


# ---------------- measurement definitions ----------------
@router.get("/measurement-definitions", response_model=list[DefinitionOut])
def list_definitions(db: Session = Depends(get_db)):
    return db.scalars(select(MeasurementDefinition).order_by(MeasurementDefinition.sort_order)).all()


@router.post("/measurement-definitions", response_model=DefinitionOut, status_code=status.HTTP_201_CREATED)
def create_definition(data: DefinitionCreate, db: Session = Depends(get_db)):
    if db.scalar(select(MeasurementDefinition.id).where(MeasurementDefinition.key == data.key)):
        raise AppError(409, "KEY_TAKEN", tr("مفتاح القياس مستخدم مسبقاً", "This measurement key already exists"))
    d = MeasurementDefinition(**data.model_dump(exclude={"choices"}), is_active=True)
    d.choices = [c.model_dump() for c in data.choices] if data.choices else None
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.patch("/measurement-definitions/{definition_id}", response_model=DefinitionOut)
def update_definition(definition_id: int, data: DefinitionUpdate, db: Session = Depends(get_db)):
    d = db.get(MeasurementDefinition, definition_id)
    if d is None:
        raise not_found(tr("نوع القياس غير موجود", "Measurement type not found"))
    changes = data.model_dump(exclude_unset=True)
    if "choices" in changes:
        changes["choices"] = [c.model_dump() for c in data.choices] if data.choices else None
    for field, value in changes.items():
        setattr(d, field, value)
    if d.min_value is not None and d.max_value is not None and d.min_value > d.max_value:
        raise bad_request(tr("الحد الأدنى يجب أن يكون أقل من الحد الأعلى", "Minimum must be less than maximum"), "INVALID_RANGE")
    db.commit()
    db.refresh(d)
    return d


# ---------------- activity factors ----------------
@router.get("/activity-factors", response_model=list[ActivityFactorOut])
def list_factors(db: Session = Depends(get_db)):
    return db.scalars(select(ActivityFactor).order_by(ActivityFactor.sort_order)).all()


@router.patch("/activity-factors/{factor_id}", response_model=ActivityFactorOut)
def update_factor(factor_id: int, data: ActivityFactorUpdate, db: Session = Depends(get_db)):
    f = db.get(ActivityFactor, factor_id)
    if f is None:
        raise not_found(tr("معامل النشاط غير موجود", "Activity factor not found"))
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(f, field, value)
    db.commit()
    db.refresh(f)
    return f
