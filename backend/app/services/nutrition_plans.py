"""Database side of calories & macros: suggestions from the latest measurements, saved plans, history."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import unprocessable
from app.core.i18n import tr
from app.models import ActivityFactor, MeasurementDefinition, MeasurementSession, MeasurementValue, NutritionPlan, User
from app.models.nutrition import NutritionSetting
from app.services import audit
from app.services import calculations as calc
from app.services import nutrition as nut


def load_settings(db: Session) -> dict[str, nut.MacroSettings]:
    rows = {r.goal: r for r in db.scalars(select(NutritionSetting))}
    out = dict(nut.DEFAULT_SETTINGS)
    for goal, r in rows.items():
        out[goal] = nut.MacroSettings(
            r.calorie_adjustment, r.protein_pct, r.carbs_pct, r.fat_pct, r.meals_min, r.meals_max
        )
    return out


def calorie_adjustments(db: Session) -> tuple[int, int]:
    s = load_settings(db)
    return s["weight_loss"].calorie_adjustment, s["weight_gain"].calorie_adjustment


def latest_value(db: Session, client_id: int, key: str) -> tuple[float | None, int | None]:
    row = db.execute(
        select(MeasurementValue.value_number, MeasurementSession.id)
        .join(MeasurementSession, MeasurementSession.id == MeasurementValue.session_id)
        .join(MeasurementDefinition, MeasurementDefinition.id == MeasurementValue.definition_id)
        .where(
            MeasurementSession.client_id == client_id,
            MeasurementDefinition.key == key,
            MeasurementValue.value_number.is_not(None),
        )
        .order_by(MeasurementSession.session_date.desc(), MeasurementSession.id.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else (None, None)


def energy_basis(db: Session, client: User) -> dict:
    """BMR / DCN from the latest weight (and latest height, falling back to the profile)."""
    p = client.profile
    weight, session_id = latest_value(db, client.id, "weight")
    height = latest_value(db, client.id, "height")[0] or (p.height_cm if p else None)
    act = db.scalar(select(ActivityFactor).where(ActivityFactor.key == p.activity_key)) if p and p.activity_key else None
    age = calc.age_on(p.birth_date, date.today()) if p and p.birth_date else None

    missing = []
    if weight is None:
        missing.append("weight")
    if not height:
        missing.append("height")
    if age is None:
        missing.append("birth_date")
    if act is None:
        missing.append("activity")
    bmr = dcn = None
    if not missing and p:
        bmr = calc.bmr_mifflin_st_jeor(p.sex, weight, height, age)
        dcn = calc.tdee(bmr, act.factor)
    return {
        "weight": weight,
        "weight_session_id": session_id,
        "height_cm": height,
        "age": age,
        "activity_factor": act.factor if act else None,
        "bmr": round(bmr, 2) if bmr is not None else None,
        "dcn": round(dcn, 2) if dcn is not None else None,
        "missing": missing,
    }


def current_plan(db: Session, client_id: int) -> NutritionPlan | None:
    return db.scalar(
        select(NutritionPlan)
        .where(NutritionPlan.client_id == client_id)
        .order_by(NutritionPlan.created_at.desc(), NutritionPlan.id.desc())
        .limit(1)
    )


def plan_out(p: NutritionPlan) -> dict:
    grams = {"protein": p.protein_g, "carbs": p.carbs_g, "fat": p.fat_g}
    return {
        "id": p.id,
        "goal": p.goal,
        "nutrition_goal": p.nutrition_goal,
        "based_on_weight": p.based_on_weight,
        "dcn": p.dcn,
        "suggested_calories": p.suggested_calories,
        "calories": p.calories,
        "percentages": {"protein": p.protein_pct, "carbs": p.carbs_pct, "fat": p.fat_pct},
        "grams": grams,
        "macros": nut.macro_breakdown(
            p.calories,
            grams,
            {"protein": p.protein_pct, "carbs": p.carbs_pct, "fat": p.fat_pct},
            {m for m in nut.MACROS if f"{m}_g" in (p.overridden or [])},
        ),
        "meals_per_day": p.meals_per_day,
        "per_meal": nut.per_meal(p.calories, grams, p.meals_per_day),
        "overridden": p.overridden or [],
        "note": p.note,
        "created_at": p.created_at,
        "created_by_name": p.created_by.full_name if p.created_by else None,
    }


def overview(db: Session, client: User, *, include_suggestion: bool) -> dict:
    goal = client.profile.goal if client.profile else "fitness"
    ngoal = nut.nutrition_goal(goal)
    settings = load_settings(db)
    basis = energy_basis(db, client)
    suggestion = nut.build_plan(basis["dcn"], settings[ngoal]) if basis["dcn"] is not None else None
    saved = current_plan(db, client.id)

    changed = False
    if saved and suggestion:
        changed = (
            saved.nutrition_goal != ngoal
            or saved.suggested_calories != suggestion["suggested_calories"]
            or (saved.based_on_weight is not None and basis["weight"] is not None and saved.based_on_weight != basis["weight"])
        )
    return {
        "client_id": client.id,
        "goal": goal,
        "nutrition_goal": ngoal,
        "current": plan_out(saved) if saved else None,
        "suggestion": suggestion if include_suggestion else None,
        "basis": basis if include_suggestion else None,
        "suggestion_changed": changed if include_suggestion else False,
        "settings": {g: s.__dict__ for g, s in settings.items()} if include_suggestion else None,
    }


def save_plan(db: Session, actor: User, client: User, data) -> NutritionPlan:
    p = client.profile
    if data.goal is not None and p is not None:
        p.goal = data.goal
    goal = p.goal if p else "fitness"
    ngoal = nut.nutrition_goal(goal)
    settings = load_settings(db)[ngoal]
    basis = energy_basis(db, client)

    if basis["dcn"] is None and data.calories is None:
        raise unprocessable(
            tr(
                "لا يمكن حساب الاحتياج اليومي: أضف قياس الوزن أو أدخل السعرات يدوياً",
                "Daily calorie need cannot be calculated: add a weight measurement or enter the calories manually",
            ),
            "DCN_UNAVAILABLE",
        )
    if data.meals_per_day is not None and not (settings.meals_min <= data.meals_per_day <= settings.meals_max):
        raise unprocessable(
            tr(
                f"عدد الوجبات لهذا الهدف بين {settings.meals_min} و{settings.meals_max}",
                f"Meals per day for this goal must be between {settings.meals_min} and {settings.meals_max}",
            ),
            "MEALS_OUT_OF_RANGE",
        )

    dcn = basis["dcn"] if basis["dcn"] is not None else data.calories - settings.calorie_adjustment
    plan = nut.build_plan(
        dcn,
        settings,
        calories=data.calories,
        grams_override={"protein": data.protein_g, "carbs": data.carbs_g, "fat": data.fat_g},
        meals_per_day=data.meals_per_day,
    )
    row = NutritionPlan(
        client_id=client.id,
        created_by_id=actor.id,
        goal=goal,
        nutrition_goal=ngoal,
        based_on_weight=basis["weight"],
        based_on_session_id=basis["weight_session_id"],
        dcn=plan["dcn"] if basis["dcn"] is not None else None,
        suggested_calories=plan["suggested_calories"] if basis["dcn"] is not None else None,
        calories=plan["calories"],
        protein_g=plan["grams"]["protein"],
        carbs_g=plan["grams"]["carbs"],
        fat_g=plan["grams"]["fat"],
        protein_pct=settings.protein_pct,
        carbs_pct=settings.carbs_pct,
        fat_pct=settings.fat_pct,
        meals_per_day=plan["meals_per_day"],
        overridden=plan["overridden"],
        note=(data.note or "").strip() or None,
    )
    db.add(row)
    db.flush()
    audit.record(
        db, actor, "create", "nutrition_plan", row.id,
        {"client_id": client.id, "client_name": client.full_name, "calories": row.calories, "overridden": row.overridden},
    )
    db.commit()
    db.refresh(row)
    return row
