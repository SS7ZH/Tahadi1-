from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user, require_role
from app.core.errors import AppError, not_found
from app.core.i18n import tr
from app.db.session import get_db
from app.models import Exercise, Program, User
from app.schemas.program import DuplicateIn, ExerciseIn, ExerciseOut, ExerciseUpdate, ProgramIn
from app.services import audit, permissions
from app.services import programs as svc

router = APIRouter(tags=["programs"])
staff = require_role("trainer", "admin")


# ---------------- exercise library ----------------
@router.get("/exercises", response_model=list[ExerciseOut])
def list_exercises(
    q: str | None = Query(default=None, max_length=100),
    muscle_group: str | None = None,
    include_inactive: bool = False,
    _: User = Depends(staff),
    db: Session = Depends(get_db),
):
    stmt = select(Exercise).order_by(Exercise.muscle_group, Exercise.name_en)
    if not include_inactive:
        stmt = stmt.where(Exercise.is_active.is_(True))
    if muscle_group:
        stmt = stmt.where(Exercise.muscle_group == muscle_group)
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Exercise.name_en).like(like), Exercise.name_ar.like(f"%{q.strip()}%")))
    return db.scalars(stmt).all()


@router.post("/admin/exercises", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(data: ExerciseIn, _: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    ex = Exercise(**data.model_dump())
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


@router.patch("/admin/exercises/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, data: ExerciseUpdate, _: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    ex = db.get(Exercise, exercise_id)
    if ex is None:
        raise not_found(tr("التمرين غير موجود", "Exercise not found"))
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None or field == "video_url":
            setattr(ex, field, value)
    db.commit()
    db.refresh(ex)
    return ex


# ---------------- client programs ----------------
@router.get("/clients/{client_id}/programs")
def list_client_programs(client: User = Depends(get_accessible_client), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Program).where(Program.client_id == client.id, Program.is_template.is_(False))
    if user.role == "client":
        stmt = stmt.where(Program.status != "draft")
    rows = db.scalars(stmt.order_by(Program.created_at.desc(), Program.id.desc())).unique()
    return [svc.program_summary(p) for p in rows]


@router.get("/clients/{client_id}/program/current")
def current_program(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    program = db.scalar(select(Program).where(Program.client_id == client.id, Program.status == "active"))
    return svc.program_out(program, client) if program else None


@router.post("/clients/{client_id}/programs", status_code=status.HTTP_201_CREATED)
def create_client_program(client_id: int, data: ProgramIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    client = permissions.get_accessible_client(db, actor, client_id)
    program = svc.create_program(db, actor, data, client=client, is_template=False)
    return svc.program_out(program, client)


# ---------------- templates ----------------
@router.get("/program-templates")
def list_templates(_: User = Depends(staff), db: Session = Depends(get_db)):
    rows = db.scalars(select(Program).where(Program.is_template.is_(True)).order_by(Program.title)).unique()
    return [svc.program_summary(p) for p in rows]


@router.post("/program-templates", status_code=status.HTTP_201_CREATED)
def create_template(data: ProgramIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    return svc.program_out(svc.create_program(db, actor, data, client=None, is_template=True))


# ---------------- single program ----------------
@router.get("/programs/{program_id}")
def get_program(program_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    program, client = svc.get_accessible_program(db, user, program_id)
    return svc.program_out(program, client)


@router.put("/programs/{program_id}")
def update_program(program_id: int, data: ProgramIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    program, client = svc.get_accessible_program(db, actor, program_id, write=True)
    svc.apply_tree(db, program, data)
    db.flush()
    audit.record(db, actor, "update", "program", program.id, {"client_id": program.client_id, "client_name": client.full_name if client else None})
    db.commit()
    db.refresh(program)
    return svc.program_out(program, client)


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: int, actor: User = Depends(staff), db: Session = Depends(get_db)):
    program, client = svc.get_accessible_program(db, actor, program_id, write=True)
    if not program.is_template and program.status != "draft":
        raise AppError(409, "PROGRAM_NOT_DRAFT", tr("يمكن حذف المسودات والقوالب فقط؛ أرشف البرنامج بدلاً من ذلك", "Only drafts and templates can be deleted; archive the program instead"))
    audit.record(db, actor, "delete", "program", program.id, {"client_id": program.client_id, "client_name": client.full_name if client else None, "title": program.title})
    db.delete(program)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/programs/{program_id}/activate")
def activate_program(program_id: int, actor: User = Depends(staff), db: Session = Depends(get_db)):
    program, client = svc.get_accessible_program(db, actor, program_id, write=True)
    if program.is_template:
        raise AppError(409, "TEMPLATE", tr("لا يمكن تفعيل قالب؛ انسخه لعميل أولاً", "A template cannot be activated; copy it to a client first"))
    return svc.program_out(svc.activate(db, actor, program, client), client)


@router.post("/programs/{program_id}/archive")
def archive_program(program_id: int, actor: User = Depends(staff), db: Session = Depends(get_db)):
    program, client = svc.get_accessible_program(db, actor, program_id, write=True)
    if program.is_template:
        raise AppError(409, "TEMPLATE", tr("القوالب لا تُؤرشف", "Templates are not archived"))
    program.status = "archived"
    audit.record(db, actor, "update", "program", program.id, {"client_id": client.id, "client_name": client.full_name, "status": "archived"})
    db.commit()
    db.refresh(program)
    return svc.program_out(program, client)


@router.post("/programs/{program_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_program(program_id: int, data: DuplicateIn, actor: User = Depends(staff), db: Session = Depends(get_db)):
    source, _ = svc.get_accessible_program(db, actor, program_id)
    target = permissions.get_accessible_client(db, actor, data.client_id) if data.client_id else None
    copy = svc.copy_program(db, actor, source, client=target, as_template=data.as_template, title=data.title)
    return svc.program_out(copy, target)
