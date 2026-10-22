from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.core.i18n import tr

Role = Literal["admin", "trainer", "client"]
Sex = Literal["male", "female"]
Goal = Literal["fat_loss", "muscle_gain", "fitness", "health", "performance"]

PASSWORD_MIN = 8


def _check_height(v: float | None) -> float | None:
    if v is not None and not (100 <= v <= 250):
        raise ValueError(tr("الطول يجب أن يكون بين 100 و250 سم", "Height must be between 100 and 250 cm"))
    return v


def _check_birth_date(v: date | None) -> date | None:
    if v is None:
        return v
    today = date.today()
    if v >= today:
        raise ValueError(tr("تاريخ الميلاد يجب أن يكون في الماضي", "Birth date must be in the past"))
    if today.year - v.year > 100 or today.year - v.year < 5:
        raise ValueError(tr("تاريخ الميلاد غير منطقي (العمر بين 5 و100 سنة)", "Unrealistic birth date (age must be 5 to 100)"))
    return v


def _clean_name(v: str | None) -> str | None:
    if v is None:
        return v
    v = " ".join(v.split())
    if len(v) < 2:
        raise ValueError(tr("الاسم قصير جداً", "Name is too short"))
    return v


Name = Annotated[str, Field(max_length=120), AfterValidator(_clean_name)]
Height = Annotated[float, AfterValidator(_check_height)]
BirthDate = Annotated[date, AfterValidator(_check_birth_date)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClientProfileOut(ORMModel):
    trainer_id: int | None
    sex: Sex
    birth_date: date | None
    height_cm: float | None
    goal: Goal
    activity_key: str | None
    notes: str | None


class UserOut(ORMModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    role: Role
    is_active: bool
    created_at: datetime


class UserDetailOut(UserOut):
    profile: ClientProfileOut | None = None
    trainer_name: str | None = None
    age: int | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserDetailOut


class MeUpdate(BaseModel):
    """What any user may change about themselves. Role/trainer/height/sex/birth date are NOT here."""

    model_config = ConfigDict(extra="forbid")

    full_name: Name | None = None
    phone: str | None = Field(default=None, max_length=30)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=200)



class ClientCreate(BaseModel):
    full_name: Name
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=PASSWORD_MIN, max_length=200)
    sex: Sex
    birth_date: BirthDate
    height_cm: Height
    goal: Goal = "fitness"
    activity_key: str | None = "moderate"
    notes: str | None = Field(default=None, max_length=5000)
    trainer_id: int | None = None  # honoured for admins only; trainers always own the client they create


class ClientUpdate(BaseModel):
    """Trainer/admin edit of a client. trainer_id is changed through the admin assign endpoint."""

    model_config = ConfigDict(extra="forbid")

    full_name: Name | None = None
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    sex: Sex | None = None
    birth_date: BirthDate | None = None
    height_cm: Height | None = None
    goal: Goal | None = None
    activity_key: str | None = None
    notes: str | None = Field(default=None, max_length=5000)


class AdminUserCreate(BaseModel):
    full_name: Name
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=PASSWORD_MIN, max_length=200)
    role: Role
    # client-only
    sex: Sex | None = None
    birth_date: BirthDate | None = None
    height_cm: Height | None = None
    goal: Goal | None = None
    activity_key: str | None = None
    notes: str | None = Field(default=None, max_length=5000)
    trainer_id: int | None = None


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Name | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=PASSWORD_MIN, max_length=200)
    sex: Sex | None = None
    birth_date: BirthDate | None = None
    height_cm: Height | None = None
    goal: Goal | None = None
    activity_key: str | None = None
    notes: str | None = Field(default=None, max_length=5000)


class AssignTrainerIn(BaseModel):
    trainer_id: int | None


class ClientListItem(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    is_active: bool
    sex: Sex | None
    goal: Goal | None
    trainer_id: int | None
    trainer_name: str | None
    sessions_count: int
    last_session_date: date | None
    weight_first: float | None
    weight_latest: float | None
    weight_change: float | None
    weight_trend: str  # good | bad | neutral
    open_questions: int
    has_chronic: bool = False
    health_update_pending: bool = False
    subscription_end_date: date | None = None
    subscription_days_left: int | None = None
    subscription_status: str | None = None
