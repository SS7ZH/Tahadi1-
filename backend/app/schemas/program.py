import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.core.i18n import tr
from app.db.reference_data import CARDIO_TYPES, EQUIPMENT, MUSCLE_GROUPS

ItemKind = Literal["resistance", "cardio"]
LoadUnit = Literal["kg", "pct_1rm", "rpe"]
ProgramStatus = Literal["draft", "active", "archived"]

_REPS = re.compile(r"^\d{1,3}(\s*[-–]\s*\d{1,3})?$")


def _url(v: str | None) -> str | None:
    if v is None:
        return v
    v = v.strip()
    if not v:
        return None
    # Only http(s) links: blocks javascript:/data: URLs from being rendered as links.
    if not re.match(r"^https?://[^\s]+$", v, re.IGNORECASE):
        raise ValueError(tr("رابط الفيديو يجب أن يبدأ بـ http:// أو https://", "The video link must start with http:// or https://"))
    return v


def _reps(v: str | None) -> str | None:
    if v is None or not v.strip():
        return None
    v = v.strip().replace("–", "-")
    if not _REPS.match(v):
        raise ValueError(tr("التكرارات رقم أو نطاق مثل 8-12", "Reps must be a number or a range like 8-12"))
    return re.sub(r"\s*-\s*", "-", v)


def _choice(allowed: tuple[str, ...], ar: str, en: str):
    def check(v: str | None) -> str | None:
        if v is not None and v not in allowed:
            raise ValueError(tr(ar, en))
        return v

    return check


Url = Annotated[str | None, AfterValidator(_url)]
Reps = Annotated[str | None, AfterValidator(_reps)]
Muscle = Annotated[str | None, AfterValidator(_choice(MUSCLE_GROUPS, "مجموعة عضلية غير معروفة", "Unknown muscle group"))]
Equipment = Annotated[str | None, AfterValidator(_choice(EQUIPMENT, "أداة غير معروفة", "Unknown equipment"))]
CardioType = Annotated[str | None, AfterValidator(_choice(CARDIO_TYPES, "نوع كارديو غير معروف", "Unknown cardio type"))]


class ItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ItemKind
    exercise_id: int | None = None
    custom_name: str | None = Field(default=None, max_length=150)
    muscle_group: Muscle = None
    # resistance
    sets: int | None = Field(default=None, ge=1, le=20)
    reps: Reps = None
    load_value: float | None = Field(default=None, ge=0, le=1000)
    load_unit: LoadUnit | None = None
    rest_seconds: int | None = Field(default=None, ge=0, le=900)
    tempo: str | None = Field(default=None, max_length=20)
    # cardio
    cardio_type: CardioType = None
    duration_min: float | None = Field(default=None, gt=0, le=600)
    hr_zone: int | None = Field(default=None, ge=1, le=5)
    speed: float | None = Field(default=None, ge=0, le=50)
    incline: float | None = Field(default=None, ge=0, le=40)
    work_seconds: int | None = Field(default=None, ge=1, le=3600)
    interval_rest_seconds: int | None = Field(default=None, ge=0, le=3600)
    rounds: int | None = Field(default=None, ge=1, le=100)
    # shared
    notes: str | None = Field(default=None, max_length=2000)
    video_url: Url = None

    @model_validator(mode="after")
    def _check(self):
        if self.kind == "resistance" and not self.exercise_id and not (self.custom_name or "").strip():
            raise ValueError(tr("اختر تمريناً من المكتبة أو اكتب اسماً", "Choose an exercise from the library or type a name"))
        if self.kind == "cardio" and not self.cardio_type:
            raise ValueError(tr("اختر نوع الكارديو", "Choose a cardio type"))
        if self.load_value is not None and self.load_unit is None:
            self.load_unit = "kg"
        if self.load_unit == "rpe" and self.load_value is not None and self.load_value > 10:
            raise ValueError(tr("قيمة RPE من 1 إلى 10", "RPE must be between 1 and 10"))
        if self.load_unit == "pct_1rm" and self.load_value is not None and self.load_value > 100:
            raise ValueError(tr("نسبة 1RM لا تتجاوز 100%", "% of 1RM cannot exceed 100"))
        return self


class DayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day_number: int = Field(ge=1, le=7)
    week_number: int | None = Field(default=None, ge=1, le=52)
    title: str = Field(min_length=1, max_length=150)
    is_rest: bool = False
    warmup: str | None = Field(default=None, max_length=2000)
    cooldown: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    items: list[ItemIn] = Field(default_factory=list, max_length=40)


class ProgramIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150)
    goal: str | None = Field(default=None, max_length=150)
    start_date: date | None = None
    weeks: int = Field(default=4, ge=1, le=52)
    days_per_week: int = Field(default=3, ge=1, le=7)
    notes: str | None = Field(default=None, max_length=5000)
    days: list[DayIn] = Field(default_factory=list, max_length=60)

    @model_validator(mode="after")
    def _check(self):
        seen = set()
        for d in self.days:
            if d.week_number is not None and d.week_number > self.weeks:
                raise ValueError(
                    tr(f"الأسبوع {d.week_number} خارج مدة البرنامج", f"Week {d.week_number} is outside the program length")
                )
            key = (d.week_number, d.day_number)
            if key in seen:
                raise ValueError(tr("يوجد يومان بنفس الرقم في نفس الأسبوع", "Two days share the same day number in the same week"))
            seen.add(key)
        return self


class DuplicateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int | None = None  # copy to this client (as a draft)
    as_template: bool = False  # or save as a template
    title: str | None = Field(default=None, max_length=150)

    @model_validator(mode="after")
    def _check(self):
        if (self.client_id is None) == (not self.as_template):
            raise ValueError(tr("اختر عميلاً أو احفظ كقالب", "Choose a client or save as a template"))
        return self


class ExerciseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str = Field(min_length=1, max_length=120)
    name_en: str = Field(min_length=1, max_length=120)
    muscle_group: Annotated[str, AfterValidator(_choice(MUSCLE_GROUPS, "مجموعة عضلية غير معروفة", "Unknown muscle group"))]
    equipment: Equipment = None
    video_url: Url = None


class ExerciseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name_ar: str | None = Field(default=None, min_length=1, max_length=120)
    name_en: str | None = Field(default=None, min_length=1, max_length=120)
    muscle_group: Muscle = None
    equipment: Equipment = None
    video_url: Url = None
    is_active: bool | None = None


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name_ar: str
    name_en: str
    muscle_group: str
    equipment: str | None
    video_url: str | None
    is_active: bool
