from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user, require_role
from app.db.session import get_db
from app.models import ClientProfile, Comment, MeasurementSession, User
from app.schemas.measurement import SessionDetailOut, SessionIn, SessionOut
from app.schemas.user import ClientCreate, ClientListItem, ClientUpdate, UserDetailOut
from app.services import measurements, permissions, progress, users
from app.services.serializers import comment_out, session_out, user_detail

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientListItem])
def list_clients(
    trainer_id: int | None = None,
    q: str | None = Query(default=None, max_length=100),
    include_inactive: bool = True,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(User)
        .where(User.id.in_(permissions.accessible_client_ids(user)))
        .order_by(User.full_name)
    )
    if trainer_id is not None and user.role == "admin":
        stmt = stmt.join(ClientProfile, ClientProfile.user_id == User.id).where(ClientProfile.trainer_id == trainer_id)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(User.full_name).like(like) | func.lower(User.email).like(like))
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    return users.client_list_items(db, list(db.scalars(stmt).unique()))


@router.post("", response_model=UserDetailOut, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    profile = data.model_dump(include=set(users.PROFILE_FIELDS))
    # A trainer always owns the client they create; only admins may choose (or leave empty).
    profile["trainer_id"] = actor.id if actor.role == "trainer" else data.trainer_id
    client = users.create_user(
        db,
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        password=data.password,
        role="client",
        profile=profile,
    )
    return user_detail(client)


@router.get("/{client_id}", response_model=UserDetailOut)
def get_client(client: User = Depends(get_accessible_client)):
    return user_detail(client)


@router.patch("/{client_id}", response_model=UserDetailOut)
def update_client(
    client_id: int,
    data: ClientUpdate,
    actor: User = Depends(require_role("trainer", "admin")),
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)
    changes = data.model_dump(exclude_unset=True)
    if "full_name" in changes and changes["full_name"]:
        client.full_name = changes["full_name"]
    if "phone" in changes:
        client.phone = (changes["phone"] or "").strip() or None
    if "is_active" in changes and changes["is_active"] is not None:
        client.is_active = changes["is_active"]
    users.apply_profile_changes(db, client, changes)
    db.commit()
    db.refresh(client)
    return user_detail(client)


@router.get("/{client_id}/progress")
def client_progress(
    keys: str | None = Query(default=None, description="comma-separated keys, e.g. weight,waist,bmi"),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    client: User = Depends(get_accessible_client),
    db: Session = Depends(get_db),
):
    key_list = [k.strip() for k in keys.split(",") if k.strip()] if keys else None
    return progress.build_progress(db, client, key_list, date_from, date_to)


@router.get("/{client_id}/summary")
def client_summary(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    return progress.build_summary(db, client)


@router.get("/{client_id}/sessions", response_model=list[SessionOut])
def list_sessions(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    sessions = db.scalars(
        select(MeasurementSession)
        .where(MeasurementSession.client_id == client.id)
        .order_by(MeasurementSession.session_date.desc(), MeasurementSession.id.desc())
    ).unique()
    counts = dict(
        db.execute(
            select(Comment.session_id, func.count())
            .where(Comment.client_id == client.id, Comment.session_id.is_not(None))
            .group_by(Comment.session_id)
        ).all()
    )
    return [session_out(s, counts.get(s.id, 0)) for s in sessions]


@router.post("/{client_id}/sessions", response_model=SessionDetailOut, status_code=status.HTTP_201_CREATED)
def create_session(
    client_id: int,
    data: SessionIn,
    actor: User = Depends(require_role("trainer", "admin")),  # role check first → clients get 403
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)
    session = measurements.create_session(db, actor, client, data)
    return {**session_out(session), "results": progress.session_results(db, client, session), "comments": []}
