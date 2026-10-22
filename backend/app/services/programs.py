"""Training programs: serialization, today's workout, heart-rate zones, access and saving the program tree."""
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, not_found, unprocessable
from app.core.i18n import tr
from app.models import Exercise, Program, ProgramDay, ProgramItem, User
from app.schemas.program import ProgramIn
from app.services import audit
from app.services.calculations import age_on
from app.services.permissions import can_access_client

# Heart-rate zones as % of max HR (max HR = 220 − age)
HR_ZONES = {1: (50, 60), 2: (60, 70), 3: (70, 80), 4: (80, 90), 5: (90, 100)}
ITEM_FIELDS = (
    "kind", "exercise_id", "custom_name", "muscle_group", "sets", "reps", "load_value", "load_unit",
    "rest_seconds", "tempo", "cardio_type", "duration_min", "hr_zone", "speed", "incline",
    "work_seconds", "interval_rest_seconds", "rounds", "notes", "video_url",
)


def max_heart_rate(age: int | None) -> int | None:
    return 220 - age if age is not None else None


def hr_target(age: int | None, zone: int | None) -> dict | None:
    hr_max = max_heart_rate(age)
    if hr_max is None or zone not in HR_ZONES:
        return None
    lo, hi = HR_ZONES[zone]
    return {"zone": zone, "min_bpm": round(hr_max * lo / 100), "max_bpm": round(hr_max * hi / 100), "pct": [lo, hi]}


def client_age(client: User | None) -> int | None:
    p = client.profile if client else None
    return age_on(p.birth_date, date.today()) if p and p.birth_date else None


def today_position(program: Program, today: date | None = None) -> dict:
    """Which week/day of the program today is (days are counted from the start date)."""
    today = today or date.today()
    if not program.start_date:
        return {"state": "no_start_date", "week": None, "day_number": None, "day_id": None}
    offset = (today - program.start_date).days
    if offset < 0:
        return {"state": "not_started", "week": 1, "day_number": 1, "day_id": _day_for(program, 1, 1), "starts_in_days": -offset}
    week, day_number = offset // 7 + 1, offset % 7 + 1
    if week > program.weeks:
        return {"state": "finished", "week": None, "day_number": None, "day_id": None}
    return {"state": "running", "week": week, "day_number": day_number, "day_id": _day_for(program, week, day_number)}


def _day_for(program: Program, week: int, day_number: int) -> int | None:
    """A day defined for a specific week wins over a day that repeats every week."""
    specific = next((d for d in program.days if d.week_number == week and d.day_number == day_number), None)
    if specific:
        return specific.id
    repeating = next((d for d in program.days if d.week_number is None and d.day_number == day_number), None)
    return repeating.id if repeating else None


def item_out(it: ProgramItem, age: int | None) -> dict:
    ex = it.exercise
    return {
        "id": it.id,
        **{f: getattr(it, f) for f in ITEM_FIELDS},
        "exercise_name_ar": ex.name_ar if ex else None,
        "exercise_name_en": ex.name_en if ex else None,
        "muscle_group": it.muscle_group or (ex.muscle_group if ex else None),
        "video_url": it.video_url or (ex.video_url if ex else None),
        "hr_target": hr_target(age, it.hr_zone) if it.kind == "cardio" else None,
    }


def program_out(program: Program, client: User | None = None, *, include_today: bool = True) -> dict:
    age = client_age(client)
    days = sorted(program.days, key=lambda d: (d.week_number or 0, d.day_number, d.sort_order))
    return {
        "id": program.id,
        "client_id": program.client_id,
        "client_name": client.full_name if client else None,
        "is_template": program.is_template,
        "title": program.title,
        "goal": program.goal,
        "start_date": program.start_date,
        "weeks": program.weeks,
        "days_per_week": program.days_per_week,
        "notes": program.notes,
        "status": program.status,
        "created_at": program.created_at,
        "updated_at": program.updated_at,
        "activated_at": program.activated_at,
        "created_by_id": program.created_by_id,
        "created_by_name": program.created_by.full_name if program.created_by else None,
        "max_hr": max_heart_rate(age),
        "today": today_position(program) if include_today and not program.is_template else None,
        "days": [
            {
                "id": d.id,
                "day_number": d.day_number,
                "week_number": d.week_number,
                "title": d.title,
                "is_rest": d.is_rest,
                "warmup": d.warmup,
                "cooldown": d.cooldown,
                "notes": d.notes,
                "items": [item_out(i, age) for i in sorted(d.items, key=lambda i: i.sort_order)],
            }
            for d in days
        ],
    }


def program_summary(program: Program) -> dict:
    return {
        "id": program.id,
        "client_id": program.client_id,
        "is_template": program.is_template,
        "title": program.title,
        "goal": program.goal,
        "start_date": program.start_date,
        "weeks": program.weeks,
        "days_per_week": program.days_per_week,
        "status": program.status,
        "days_count": len(program.days),
        "created_at": program.created_at,
        "updated_at": program.updated_at,
        "created_by_id": program.created_by_id,
        "created_by_name": program.created_by.full_name if program.created_by else None,
    }


def get_accessible_program(db: Session, user: User, program_id: int, *, write: bool = False) -> tuple[Program, User | None]:
    """Templates: any coach/admin may read; only the author or an admin may change.
    Client programs: same rules as the client (404 otherwise); players never see drafts."""
    program = db.get(Program, program_id)
    missing = not_found(tr("البرنامج غير موجود", "Program not found"))
    if program is None:
        raise missing
    if program.is_template:
        if user.role not in ("trainer", "admin"):
            raise missing
        if write and user.role != "admin" and program.created_by_id != user.id:
            raise AppError(403, "FORBIDDEN", tr("يمكن تعديل القالب من كاتبه أو من المدير فقط", "Only the author or an admin can change this template"))
        return program, None
    client = db.get(User, program.client_id)
    if client is None or not can_access_client(user, client):
        raise missing
    if user.role == "client" and program.status == "draft":
        raise missing
    return program, client


def _check_exercises(db: Session, data: ProgramIn) -> None:
    ids = {i.exercise_id for d in data.days for i in d.items if i.exercise_id}
    if ids:
        found = set(db.scalars(select(Exercise.id).where(Exercise.id.in_(ids))))
        if ids - found:
            raise unprocessable(tr("تمرين غير موجود في المكتبة", "Exercise not found in the library"), "UNKNOWN_EXERCISE")


def apply_tree(db: Session, program: Program, data: ProgramIn) -> None:
    """Replace details, days and items in one go (the builder saves the whole program)."""
    _check_exercises(db, data)
    program.title = data.title.strip()
    program.goal = (data.goal or "").strip() or None
    program.start_date = data.start_date
    program.weeks = data.weeks
    program.days_per_week = data.days_per_week
    program.notes = (data.notes or "").strip() or None
    program.days.clear()
    db.flush()
    for d_index, d in enumerate(data.days):
        day = ProgramDay(
            day_number=d.day_number,
            week_number=d.week_number,
            title=d.title.strip(),
            is_rest=d.is_rest,
            warmup=(d.warmup or "").strip() or None,
            cooldown=(d.cooldown or "").strip() or None,
            notes=(d.notes or "").strip() or None,
            sort_order=d_index,
        )
        if not d.is_rest:
            for i_index, it in enumerate(d.items):
                values = it.model_dump(include=set(ITEM_FIELDS))
                values["custom_name"] = (values.get("custom_name") or "").strip() or None
                day.items.append(ProgramItem(sort_order=i_index, **values))
        program.days.append(day)


def create_program(db: Session, actor: User, data: ProgramIn, *, client: User | None, is_template: bool) -> Program:
    program = Program(client_id=client.id if client else None, is_template=is_template, status="draft", created_by_id=actor.id, title=data.title)
    db.add(program)
    apply_tree(db, program, data)
    db.flush()
    audit.record(db, actor, "create", "program", program.id, {"client_id": program.client_id, "client_name": client.full_name if client else None, "template": is_template})
    db.commit()
    db.refresh(program)
    return program


def activate(db: Session, actor: User, program: Program, client: User) -> Program:
    """One active program per client: the previous one is archived (and stays viewable)."""
    if not program.start_date:
        raise unprocessable(tr("حدد تاريخ البداية قبل التفعيل", "Set a start date before activating"), "START_DATE_REQUIRED")
    if not any(not d.is_rest and d.items for d in program.days):
        raise unprocessable(tr("أضف يوماً واحداً على الأقل فيه تمارين قبل التفعيل", "Add at least one day with exercises before activating"), "EMPTY_PROGRAM")
    for other in db.scalars(select(Program).where(Program.client_id == client.id, Program.status == "active", Program.id != program.id)):
        other.status = "archived"
    program.status = "active"
    program.activated_at = datetime.now(timezone.utc)
    audit.record(db, actor, "update", "program", program.id, {"client_id": client.id, "client_name": client.full_name, "status": "active"})
    db.commit()
    db.refresh(program)
    return program


def copy_program(db: Session, actor: User, source: Program, *, client: User | None, as_template: bool, title: str | None) -> Program:
    data = ProgramIn(
        title=title or source.title,
        goal=source.goal,
        start_date=None if as_template else source.start_date,
        weeks=source.weeks,
        days_per_week=source.days_per_week,
        notes=source.notes,
        days=[
            {
                "day_number": d.day_number,
                "week_number": d.week_number,
                "title": d.title,
                "is_rest": d.is_rest,
                "warmup": d.warmup,
                "cooldown": d.cooldown,
                "notes": d.notes,
                "items": [{f: getattr(i, f) for f in ITEM_FIELDS} for i in sorted(d.items, key=lambda i: i.sort_order)],
            }
            for d in sorted(source.days, key=lambda d: d.sort_order)
        ],
    )
    return create_program(db, actor, data, client=client, is_template=as_template)
