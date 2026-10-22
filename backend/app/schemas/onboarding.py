from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.i18n import tr
from app.db.reference_data import CHRONIC_CONDITIONS

TemplateKind = Literal["contract", "disclaimer"]


class SubscriptionStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: int
    start_date: date

    @field_validator("start_date")
    @classmethod
    def _not_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError(tr("تاريخ البداية لا يمكن أن يكون في الماضي", "The start date cannot be in the past"))
        return v


class SubscriptionCreateIn(BaseModel):
    """Coach/admin: renew or change plan (a new contract must be signed)."""

    model_config = ConfigDict(extra="forbid")

    plan_id: int
    start_date: date
    kind: Literal["renewal", "change"] = "renewal"


class SubscriptionUpdateIn(BaseModel):
    """Coach/admin: correct dates or extend (no new contract needed)."""

    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    end_date: date | None = None


class HealthFields(BaseModel):
    has_chronic: bool
    conditions: list[str] = Field(default_factory=list, max_length=10)
    details: str | None = Field(default=None, max_length=3000)
    medications: str | None = Field(default=None, max_length=2000)
    injuries: str | None = Field(default=None, max_length=2000)
    file_ids: list[int] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def _check(self):
        unknown = [c for c in self.conditions if c not in CHRONIC_CONDITIONS]
        if unknown:
            raise ValueError(tr("حالة صحية غير معروفة", "Unknown condition"))
        if self.has_chronic:
            if not self.conditions:
                raise ValueError(tr("اختر الحالة المزمنة", "Choose the chronic condition"))
            if not (self.details or "").strip():
                raise ValueError(tr("اكتب تفاصيل الحالة", "Describe the condition"))
        else:
            self.conditions = []
        return self


class HealthOnboardingIn(HealthFields):
    model_config = ConfigDict(extra="forbid")

    template_id: int
    typed_name: str = Field(max_length=150)
    agreed: bool


class HealthUpdateIn(HealthFields):
    model_config = ConfigDict(extra="forbid")


class ContractSignIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: int
    typed_name: str = Field(max_length=150)
    agreed: bool


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str = Field(min_length=1, max_length=80)
    name_en: str = Field(min_length=1, max_length=80)
    months: int = Field(ge=1, le=60)
    price: float | None = Field(default=None, ge=0, le=1_000_000)
    currency: str = Field(default="SAR", min_length=3, max_length=3)
    sort_order: int = 100


class PlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str | None = Field(default=None, min_length=1, max_length=80)
    name_en: str | None = Field(default=None, min_length=1, max_length=80)
    months: int | None = Field(default=None, ge=1, le=60)
    price: float | None = Field(default=None, ge=0, le=1_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    sort_order: int | None = None
    clear_price: bool = False


class TemplateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: TemplateKind
    body_ar: str = Field(min_length=20, max_length=50_000)
    body_en: str = Field(min_length=20, max_length=50_000)
