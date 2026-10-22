import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.i18n import tr
from app.db.reference_data import HOME_FEATURE_KEYS

_PHONE = re.compile(r"^\+?[0-9 ()-]{6,20}$")


class FeatureIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    title_ar: str = Field(min_length=1, max_length=80)
    title_en: str = Field(min_length=1, max_length=80)
    text_ar: str = Field(min_length=1, max_length=300)
    text_en: str = Field(min_length=1, max_length=300)


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(default="", max_length=30)
    whatsapp: str = Field(default="", max_length=30)
    email: str = Field(default="", max_length=120)

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        if v and not _PHONE.match(v):
            raise ValueError(tr("رقم غير صالح", "Invalid phone number"))
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError(tr("البريد الإلكتروني غير صالح", "Invalid email address"))
        return v


class HomeContentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hero_title_ar: str = Field(min_length=1, max_length=120)
    hero_title_en: str = Field(min_length=1, max_length=120)
    hero_text_ar: str = Field(min_length=1, max_length=400)
    hero_text_en: str = Field(min_length=1, max_length=400)
    features: list[FeatureIn]
    contact: ContactIn

    @model_validator(mode="after")
    def _features(self):
        if [f.key for f in self.features] != list(HOME_FEATURE_KEYS):
            raise ValueError(tr("قائمة المزايا غير مكتملة", "The features list is incomplete"))
        return self
