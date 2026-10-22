from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.i18n import tr
from app.schemas.user import Goal, Sex

NutritionGoal = Literal["weight_loss", "maintenance", "weight_gain"]


class NutritionPlanIn(BaseModel):
    """Coach saves a plan. Every number is optional: omitted = use the suggested value."""

    model_config = ConfigDict(extra="forbid")

    goal: Goal | None = None
    calories: int | None = Field(default=None, ge=800, le=10000)
    protein_g: int | None = Field(default=None, ge=0, le=1500)
    carbs_g: int | None = Field(default=None, ge=0, le=1500)
    fat_g: int | None = Field(default=None, ge=0, le=1500)
    meals_per_day: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=2000)


class NutritionSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goal: NutritionGoal
    calorie_adjustment: int
    protein_pct: float
    carbs_pct: float
    fat_pct: float
    meals_min: int
    meals_max: int


class NutritionSettingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calorie_adjustment: int | None = Field(default=None, ge=-2000, le=2000)
    protein_pct: float | None = Field(default=None, ge=0, le=100)
    carbs_pct: float | None = Field(default=None, ge=0, le=100)
    fat_pct: float | None = Field(default=None, ge=0, le=100)
    meals_min: int | None = Field(default=None, ge=1, le=10)
    meals_max: int | None = Field(default=None, ge=1, le=10)


class NutritionCalcIn(BaseModel):
    sex: Sex
    age: int = Field(ge=10, le=100)
    weight: float = Field(ge=20, le=300)
    height: float = Field(ge=100, le=250)
    activity_key: str
    goal: NutritionGoal | Literal["performance"] = "maintenance"
    meals_per_day: int | None = Field(default=None, ge=1, le=10)

    @model_validator(mode="after")
    def _goal(self):
        if self.goal == "performance":
            self.goal = "maintenance"
        return self


def check_percentages(protein: float, carbs: float, fat: float) -> None:
    if abs(protein + carbs + fat - 100) > 0.01:
        raise ValueError(tr("مجموع النسب يجب أن يساوي 100%", "Percentages must add up to 100%"))
