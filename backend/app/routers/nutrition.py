from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_accessible_client, get_current_user, require_role
from app.core.errors import bad_request, not_found, unprocessable
from app.core.i18n import tr
from app.db.session import get_db
from app.models import ActivityFactor, NutritionPlan, User
from app.models.nutrition import NutritionSetting
from app.schemas.nutrition import (
    NutritionCalcIn,
    NutritionPlanIn,
    NutritionSettingOut,
    NutritionSettingUpdate,
    check_percentages,
)
from app.services import calculations as calc
from app.services import nutrition as nut
from app.services import nutrition_plans, permissions

router = APIRouter(tags=["nutrition"])


@router.get("/clients/{client_id}/nutrition")
def get_nutrition(client: User = Depends(get_accessible_client), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Players see only the saved plan; coaches/admins also get the live suggestion.
    return nutrition_plans.overview(db, client, include_suggestion=user.role != "client")


@router.get("/clients/{client_id}/nutrition/history")
def nutrition_history(client: User = Depends(get_accessible_client), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(NutritionPlan)
        .where(NutritionPlan.client_id == client.id)
        .order_by(NutritionPlan.created_at.desc(), NutritionPlan.id.desc())
    ).unique()
    return [nutrition_plans.plan_out(r) for r in rows]


@router.post("/clients/{client_id}/nutrition", status_code=status.HTTP_201_CREATED)
def save_nutrition(
    client_id: int,
    data: NutritionPlanIn,
    actor: User = Depends(require_role("trainer", "admin")),  # role first → players get 403
    db: Session = Depends(get_db),
):
    client = permissions.get_accessible_client(db, actor, client_id)
    nutrition_plans.save_plan(db, actor, client, data)
    return nutrition_plans.overview(db, client, include_suggestion=True)


@router.get("/nutrition-settings", response_model=list[NutritionSettingOut])
def list_settings(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(NutritionSetting).order_by(NutritionSetting.calorie_adjustment)).all()


@router.patch("/admin/nutrition-settings/{setting_id}", response_model=NutritionSettingOut)
def update_setting(
    setting_id: int,
    data: NutritionSettingUpdate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    row = db.get(NutritionSetting, setting_id)
    if row is None:
        raise not_found(tr("إعداد التغذية غير موجود", "Nutrition setting not found"))
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(row, field, value)
    try:
        check_percentages(row.protein_pct, row.carbs_pct, row.fat_pct)
    except ValueError as e:
        db.rollback()
        raise bad_request(str(e), "PERCENTAGES_SUM")
    if row.meals_min > row.meals_max:
        db.rollback()
        raise bad_request(tr("الحد الأدنى للوجبات أكبر من الحد الأعلى", "Minimum meals is greater than maximum"), "INVALID_RANGE")
    db.commit()
    db.refresh(row)
    return row


@router.post("/calculate/nutrition")
def calculate_nutrition(data: NutritionCalcIn, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    factor = db.scalar(select(ActivityFactor).where(ActivityFactor.key == data.activity_key))
    if factor is None:
        raise unprocessable(tr("مستوى النشاط غير معروف", "Unknown activity level"), "UNKNOWN_ACTIVITY")
    settings = nutrition_plans.load_settings(db)[data.goal]
    if data.meals_per_day is not None and not (settings.meals_min <= data.meals_per_day <= settings.meals_max):
        raise unprocessable(
            tr(
                f"عدد الوجبات لهذا الهدف بين {settings.meals_min} و{settings.meals_max}",
                f"Meals per day for this goal must be between {settings.meals_min} and {settings.meals_max}",
            ),
            "MEALS_OUT_OF_RANGE",
        )
    bmr = calc.bmr_mifflin_st_jeor(data.sex, data.weight, data.height, data.age)
    dcn = calc.tdee(bmr, factor.factor)
    return {
        "bmr": round(bmr, 2),
        "tdee": round(dcn, 2),
        "activity_factor": factor.factor,
        "goal": data.goal,
        "plan": nut.build_plan(dcn, settings, meals_per_day=data.meals_per_day),
    }
