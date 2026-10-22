"""Public home page content and the data the public calorie calculator needs (no login)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_role
from app.db.reference_data import DEFAULT_HOME
from app.db.session import get_db
from app.models import ActivityFactor, SiteSetting, User
from app.models.nutrition import NutritionSetting
from app.schemas.measurement import ActivityFactorOut
from app.schemas.nutrition import NutritionSettingOut
from app.schemas.site import HomeContentIn
from app.services import audit

router = APIRouter(tags=["site"])


def _home(db: Session) -> dict:
    row = db.get(SiteSetting, "home")
    return row.value if row else DEFAULT_HOME


@router.get("/public/site")
def public_site(db: Session = Depends(get_db)):
    return {"home": _home(db)}


@router.get("/public/activity-factors", response_model=list[ActivityFactorOut])
def public_activity_factors(db: Session = Depends(get_db)):
    return db.scalars(select(ActivityFactor).order_by(ActivityFactor.sort_order)).all()


@router.get("/public/nutrition-settings", response_model=list[NutritionSettingOut])
def public_nutrition_settings(db: Session = Depends(get_db)):
    return db.scalars(select(NutritionSetting).order_by(NutritionSetting.calorie_adjustment)).all()


@router.put("/admin/site/home")
def update_home(data: HomeContentIn, actor: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    value = data.model_dump()
    row = db.get(SiteSetting, "home")
    if row is None:
        db.add(SiteSetting(key="home", value=value, updated_by_id=actor.id))
    else:
        row.value = value
        row.updated_by_id = actor.id
    audit.record(db, actor, "update", "site_settings", None, {"key": "home"})
    db.commit()
    return {"home": value}
