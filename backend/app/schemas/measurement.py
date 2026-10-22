from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.i18n import tr

Category = Literal["vital", "body", "movement", "physical"]
ValueType = Literal["number", "text", "choice", "blood_pressure"]
Direction = Literal["up", "down", "none"]


class ChoiceOption(BaseModel):
    value: float
    label: str = Field(min_length=1, max_length=80)
    label_en: str | None = Field(default=None, max_length=80)


class DefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name_ar: str
    name_en: str | None = None
    category: Category
    unit: str | None
    unit_en: str | None = None
    value_type: ValueType
    choices: list[ChoiceOption] | None
    better_direction: Direction
    min_value: float | None
    max_value: float | None
    is_active: bool
    sort_order: int


class DefinitionCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,49}$")
    name_ar: str = Field(min_length=1, max_length=120)
    name_en: str | None = Field(default=None, max_length=120)
    category: Category
    unit: str | None = Field(default=None, max_length=50)
    unit_en: str | None = Field(default=None, max_length=50)
    value_type: ValueType
    choices: list[ChoiceOption] | None = None
    better_direction: Direction = "none"
    min_value: float | None = None
    max_value: float | None = None
    sort_order: int = 1000

    @model_validator(mode="after")
    def _check(self):
        if self.value_type == "choice" and not self.choices:
            raise ValueError(tr("يجب إضافة خيارات لنوع القياس «اختيار»", "Add options for a choice measurement"))
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError(tr("الحد الأدنى يجب أن يكون أقل من الحد الأعلى", "Minimum must be less than maximum"))
        return self


class DefinitionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str | None = Field(default=None, min_length=1, max_length=120)
    name_en: str | None = Field(default=None, max_length=120)
    category: Category | None = None
    unit: str | None = Field(default=None, max_length=50)
    unit_en: str | None = Field(default=None, max_length=50)
    choices: list[ChoiceOption] | None = None
    better_direction: Direction | None = None
    min_value: float | None = None
    max_value: float | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class ActivityFactorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    name_ar: str
    name_en: str | None = None
    description_ar: str | None
    description_en: str | None = None
    factor: float
    sort_order: int


class ActivityFactorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str | None = Field(default=None, min_length=1, max_length=80)
    name_en: str | None = Field(default=None, max_length=80)
    description_ar: str | None = Field(default=None, max_length=300)
    description_en: str | None = Field(default=None, max_length=300)
    factor: float | None = Field(default=None, ge=1.0, le=2.5)


class ValueIn(BaseModel):
    key: str
    value_number: float | None = None
    value_text: str | None = Field(default=None, max_length=4000)
    systolic: float | None = None
    diastolic: float | None = None


class SessionIn(BaseModel):
    session_date: date
    notes: str | None = Field(default=None, max_length=5000)
    values: list[ValueIn] = Field(default_factory=list, max_length=100)

    @field_validator("session_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today() + timedelta(days=1):
            raise ValueError(tr("تاريخ القياس لا يمكن أن يكون في المستقبل", "The measurement date cannot be in the future"))
        if v.year < 2000:
            raise ValueError(tr("تاريخ القياس غير صالح", "Invalid measurement date"))
        return v

    @field_validator("values")
    @classmethod
    def _unique(cls, v: list[ValueIn]) -> list[ValueIn]:
        keys = [x.key for x in v]
        if len(keys) != len(set(keys)):
            raise ValueError(tr("تم إرسال نفس القياس أكثر من مرة", "The same measurement was sent more than once"))
        return v


class ValueOut(BaseModel):
    key: str
    name_ar: str
    name_en: str | None = None
    category: Category
    unit: str | None
    unit_en: str | None = None
    value_type: ValueType
    value_number: float | None
    value_text: str | None
    value_json: dict | None
    display: str


class CommentOut(BaseModel):
    id: int
    client_id: int
    session_id: int | None
    author_id: int | None
    author_name: str | None
    author_role: str | None
    body: str
    created_at: datetime


class SessionOut(BaseModel):
    id: int
    client_id: int
    session_date: date
    notes: str | None
    trainer_id: int | None
    trainer_name: str | None
    updated_by_name: str | None
    created_at: datetime
    updated_at: datetime
    values: list[ValueOut]
    comments_count: int = 0


class SessionDetailOut(SessionOut):
    results: dict
    comments: list[CommentOut]
