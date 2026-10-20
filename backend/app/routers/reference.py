"""Read-only reference data for every logged-in role (forms, charts, calculator)."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import ActivityFactor, MeasurementDefinition
from app.schemas.measurement import ActivityFactorOut, DefinitionOut

router = APIRouter(tags=["reference"], dependencies=[Depends(get_current_user)])


@router.get("/measurement-definitions", response_model=list[DefinitionOut])
def definitions(include_inactive: bool = False, db: Session = Depends(get_db)):
    stmt = select(MeasurementDefinition).order_by(MeasurementDefinition.sort_order)
    if not include_inactive:
        stmt = stmt.where(MeasurementDefinition.is_active.is_(True))
    return db.scalars(stmt).all()


@router.get("/activity-factors", response_model=list[ActivityFactorOut])
def activity_factors(db: Session = Depends(get_db)):
    return db.scalars(select(ActivityFactor).order_by(ActivityFactor.sort_order)).all()
