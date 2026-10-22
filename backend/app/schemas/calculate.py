from typing import Literal

from pydantic import BaseModel, Field


class BmrTdeeIn(BaseModel):
    sex: Literal["male", "female"]
    age: int = Field(ge=10, le=100)
    weight: float = Field(ge=20, le=300)
    height: float = Field(ge=100, le=250)
    activity_key: str


class BmrTdeeOut(BaseModel):
    bmr: float
    tdee: float
    activity_factor: float
    activity_name_ar: str
    activity_name_en: str | None = None
    targets: dict
    bmi: dict | None
    note: str
