"""Time series, summaries and trend colouring (good = toward the goal, bad = away, neutral = no change)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityFactor, MeasurementDefinition, MeasurementSession, MeasurementValue, User
from app.services.calculations import (
    bmi as calc_bmi,
    compute_results,
    waist_hip_ratio,
)

NEUTRAL_EPS = 1e-9

# Derived (calculated) series that can be charted alongside raw measurements.
DERIVED = {
    "bmi": {"name_ar": "مؤشر كتلة الجسم", "unit": "كجم/م²", "category": "body", "better_direction": "goal"},
    "whr": {"name_ar": "نسبة الوسط إلى الأرداف", "unit": None, "category": "body", "better_direction": "down"},
}

GOAL_DIRECTION = {"fat_loss": "down", "muscle_gain": "up"}


def effective_direction(key: str, better_direction: str, goal: str | None, latest_bmi: float | None) -> str:
    """Weight/BMI direction depends on the client's goal; everything else on the definition."""
    if key in ("weight", "bmi"):
        if goal in GOAL_DIRECTION:
            return GOAL_DIRECTION[goal]
        if latest_bmi is not None:
            if latest_bmi >= 25:
                return "down"
            if latest_bmi < 18.5:
                return "up"
        return "none"
    return better_direction


def trend(direction: str, change: float | None) -> str:
    if change is None or abs(change) < NEUTRAL_EPS or direction == "none":
        return "neutral"
    if (change < 0 and direction == "down") or (change > 0 and direction == "up"):
        return "good"
    return "bad"


def load_sessions(
    db: Session, client_id: int, date_from: date | None = None, date_to: date | None = None
) -> list[MeasurementSession]:
    stmt = select(MeasurementSession).where(MeasurementSession.client_id == client_id)
    if date_from:
        stmt = stmt.where(MeasurementSession.session_date >= date_from)
    if date_to:
        stmt = stmt.where(MeasurementSession.session_date <= date_to)
    stmt = stmt.order_by(MeasurementSession.session_date, MeasurementSession.id)
    return list(db.scalars(stmt).unique())


def value_map(session: MeasurementSession) -> dict[str, MeasurementValue]:
    return {v.definition.key: v for v in session.values}


def _num(vm: dict[str, MeasurementValue], key: str) -> float | None:
    v = vm.get(key)
    return v.value_number if v is not None else None


def _height_for(vm: dict[str, MeasurementValue], client: User) -> float | None:
    return _num(vm, "height") or (client.profile.height_cm if client.profile else None)


def _activity(db: Session, client: User) -> ActivityFactor | None:
    if client.profile and client.profile.activity_key:
        return db.scalar(select(ActivityFactor).where(ActivityFactor.key == client.profile.activity_key))
    return None


def session_results(db: Session, client: User, session: MeasurementSession) -> dict:
    vm = value_map(session)
    bp = vm.get("blood_pressure")
    act = _activity(db, client)
    profile = client.profile
    return compute_results(
        sex=profile.sex if profile else None,
        birth_date=profile.birth_date if profile else None,
        on_date=session.session_date,
        weight_kg=_num(vm, "weight"),
        height_cm=_height_for(vm, client),
        waist_cm=_num(vm, "waist"),
        hip_cm=_num(vm, "hip"),
        systolic=bp.value_json["systolic"] if bp and bp.value_json else None,
        diastolic=bp.value_json["diastolic"] if bp and bp.value_json else None,
        activity_factor=act.factor if act else None,
        activity_key=act.key if act else None,
        activity_name_ar=act.name_ar if act else None,
    )


def _derived_value(key: str, vm: dict[str, MeasurementValue], client: User) -> float | None:
    if key == "bmi":
        w, h = _num(vm, "weight"), _height_for(vm, client)
        return round(calc_bmi(w, h), 2) if w and h else None
    if key == "whr":
        waist, hip = _num(vm, "waist"), _num(vm, "hip")
        return round(waist_hip_ratio(waist, hip), 3) if waist and hip else None
    return None


def chartable_definitions(db: Session) -> list[MeasurementDefinition]:
    return list(
        db.scalars(
            select(MeasurementDefinition)
            .where(MeasurementDefinition.value_type.in_(("number", "choice", "blood_pressure")))
            .order_by(MeasurementDefinition.sort_order)
        )
    )


def build_progress(
    db: Session,
    client: User,
    keys: list[str] | None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    sessions = load_sessions(db, client.id, date_from, date_to)
    defs = {d.key: d for d in chartable_definitions(db)}
    goal = client.profile.goal if client.profile else None
    maps = [(s, value_map(s)) for s in sessions]

    available = [
        {"key": d.key, "name_ar": d.name_ar, "unit": d.unit, "category": d.category, "derived": False}
        for d in defs.values()
    ] + [
        {"key": k, "name_ar": meta["name_ar"], "unit": meta["unit"], "category": meta["category"], "derived": True}
        for k, meta in DERIVED.items()
    ]
    keys = keys or [k["key"] for k in available]

    latest_bmi = None
    for _, vm in reversed(maps):
        latest_bmi = _derived_value("bmi", vm, client)
        if latest_bmi:
            break

    series = {}
    for key in keys:
        if key in DERIVED:
            meta = {**DERIVED[key], "key": key}
            base_direction = meta["better_direction"]  # "goal" for bmi, resolved below
        elif key in defs:
            d = defs[key]
            meta = {"key": key, "name_ar": d.name_ar, "unit": d.unit, "category": d.category}
            base_direction = d.better_direction
        else:
            continue
        direction = effective_direction(key, base_direction, goal, latest_bmi)

        points = []
        for s, vm in maps:
            if key in DERIVED:
                value = _derived_value(key, vm, client)
                extra = {}
            else:
                mv = vm.get(key)
                value = mv.value_number if mv else None
                extra = {"diastolic": mv.value_json.get("diastolic")} if mv and mv.value_json else {}
            if value is not None:
                points.append({"date": s.session_date, "session_id": s.id, "value": value, **extra})

        first = points[0]["value"] if points else None
        latest = points[-1]["value"] if points else None
        change = round(latest - first, 3) if points else None
        series[key] = {
            **{k: meta[k] for k in ("key", "name_ar", "unit", "category")},
            "better_direction": direction,
            "points": points,
            "first": first,
            "latest": latest,
            "change": change,
            "change_pct": round(change / first * 100, 1) if change is not None and first else None,
            "trend": trend(direction, change),
        }
    return {"client_id": client.id, "available": available, "series": series}


def build_summary(db: Session, client: User) -> dict:
    sessions = load_sessions(db, client.id)
    goal = client.profile.goal if client.profile else None
    first: dict[str, MeasurementValue] = {}
    latest: dict[str, tuple[MeasurementValue, MeasurementSession]] = {}
    for s in sessions:
        for v in s.values:
            first.setdefault(v.definition.key, v)
            latest[v.definition.key] = (v, s)

    # Calculations use the most recent value of each input (they may come from different sessions).
    def num(key: str) -> float | None:
        item = latest.get(key)
        return item[0].value_number if item else None

    height = num("height") or (client.profile.height_cm if client.profile else None)
    bp = latest.get("blood_pressure")
    act = _activity(db, client)
    profile = client.profile
    results = compute_results(
        sex=profile.sex if profile else None,
        birth_date=profile.birth_date if profile else None,
        on_date=date.today(),
        weight_kg=num("weight"),
        height_cm=height,
        waist_cm=num("waist"),
        hip_cm=num("hip"),
        systolic=bp[0].value_json["systolic"] if bp and bp[0].value_json else None,
        diastolic=bp[0].value_json["diastolic"] if bp and bp[0].value_json else None,
        activity_factor=act.factor if act else None,
        activity_key=act.key if act else None,
        activity_name_ar=act.name_ar if act else None,
    )
    latest_bmi = results["bmi"]["value"] if results["bmi"] else None

    from app.services.serializers import value_out  # local import avoids a cycle

    latest_values = []
    for key, (mv, s) in latest.items():
        d = mv.definition
        f = first.get(key)
        change = None
        if mv.value_number is not None and f is not None and f.value_number is not None and f is not mv:
            change = round(mv.value_number - f.value_number, 3)
        direction = effective_direction(key, d.better_direction, goal, latest_bmi)
        latest_values.append(
            {
                **value_out(mv),
                "session_id": s.id,
                "session_date": s.session_date,
                "first_value": f.value_number if f else None,
                "change": change,
                "better_direction": direction,
                "trend": trend(direction, change),
                "sort_order": d.sort_order,
            }
        )
    latest_values.sort(key=lambda x: x["sort_order"])

    # BMI change since the first session that had enough data
    first_bmi = None
    for s in sessions:
        first_bmi = _derived_value("bmi", value_map(s), client)
        if first_bmi:
            break
    bmi_change = round(latest_bmi - first_bmi, 2) if latest_bmi and first_bmi else None

    return {
        "client_id": client.id,
        "sessions_count": len(sessions),
        "first_session_date": sessions[0].session_date if sessions else None,
        "last_session_date": sessions[-1].session_date if sessions else None,
        "latest_values": latest_values,
        "results": results,
        "bmi_change": bmi_change,
        "bmi_trend": trend(effective_direction("bmi", "none", goal, latest_bmi), bmi_change),
    }
