from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.errors import unprocessable
from app.core.i18n import tr
from app.db.session import get_db
from app.models import ActivityFactor, User
from app.schemas.calculate import BmrTdeeIn, BmrTdeeOut
from app.services import calculations as calc
from app.services import nutrition_plans

router = APIRouter(prefix="/calculate", tags=["calculator"])


@router.post("/bmr-tdee", response_model=BmrTdeeOut)
def bmr_tdee(data: BmrTdeeIn, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    factor = db.scalar(select(ActivityFactor).where(ActivityFactor.key == data.activity_key))
    if factor is None:
        raise unprocessable(tr("مستوى النشاط غير معروف", "Unknown activity level"), "UNKNOWN_ACTIVITY")
    bmr = calc.bmr_mifflin_st_jeor(data.sex, data.weight, data.height, data.age)
    tdee = calc.tdee(bmr, factor.factor)
    bmi_value = calc.bmi(data.weight, data.height)
    key, label = calc.bmi_category(bmi_value)
    return BmrTdeeOut(
        bmr=round(bmr, 2),
        tdee=round(tdee, 2),
        activity_factor=factor.factor,
        activity_name_ar=factor.name_ar,
        activity_name_en=factor.name_en,
        targets=calc.calorie_targets(tdee, *nutrition_plans.calorie_adjustments(db)),
        bmi={"value": round(bmi_value, 1), "category": key, "label": label},
        note=tr("هذه تقديرات عامة وليست بديلاً عن استشارة مختص تغذية", "These are general estimates, not a substitute for advice from a nutrition professional"),
    )
