"""Pure health/fitness calculations. No database access here, so everything is trivially unit-testable."""
from datetime import date

from app.core.i18n import tr

FAT_LOSS_DEFICIT = 500
MUSCLE_GAIN_SURPLUS = 300


def age_on(birth_date: date, on_date: date) -> int:
    """Whole years between birth_date and on_date (age at the session date, not today)."""
    years = on_date.year - birth_date.year
    if (on_date.month, on_date.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def bmr_mifflin_st_jeor(sex: str, weight_kg: float, height_cm: float, age_years: float) -> float:
    """Mifflin–St Jeor: men +5, women −161."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age_years
    if sex == "male":
        return base + 5
    if sex == "female":
        return base - 161
    raise ValueError("sex must be 'male' or 'female'")


def tdee(bmr: float, activity_factor: float) -> float:
    return bmr * activity_factor


def calorie_targets(tdee_value: float) -> dict:
    return {
        "maintenance": round(tdee_value),
        "fat_loss": round(tdee_value - FAT_LOSS_DEFICIT),
        "muscle_gain": round(tdee_value + MUSCLE_GAIN_SURPLUS),
    }


def bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    return weight_kg / (height_m**2)


def bmi_category(value: float) -> tuple[str, str]:
    if value < 18.5:
        return "underweight", tr("نقص وزن", "Underweight")
    if value < 25:
        return "normal", tr("طبيعي", "Normal")
    if value < 30:
        return "overweight", tr("زيادة وزن", "Overweight")
    return "obese", tr("سمنة", "Obese")


def waist_hip_ratio(waist_cm: float, hip_cm: float) -> float:
    return waist_cm / hip_cm


def whr_risk(value: float, sex: str) -> tuple[str, str]:
    threshold = 0.90 if sex == "male" else 0.85
    if value > threshold:
        return "high", tr("مرتفع", "High")
    return "normal", tr("طبيعي", "Normal")


def blood_pressure_category(systolic: float, diastolic: float) -> tuple[str, str]:
    """AHA categories (the higher of the two readings decides)."""
    if systolic >= 140 or diastolic >= 90:
        return "stage2", tr("ارتفاع درجة ثانية", "Hypertension stage 2")
    if systolic >= 130 or diastolic >= 80:
        return "stage1", tr("ارتفاع درجة أولى", "Hypertension stage 1")
    if systolic >= 120:
        return "elevated", tr("مرتفع قليلاً", "Elevated")
    return "normal", tr("طبيعي", "Normal")


def compute_results(
    *,
    sex: str | None,
    birth_date: date | None,
    on_date: date,
    weight_kg: float | None,
    height_cm: float | None,
    waist_cm: float | None = None,
    hip_cm: float | None = None,
    systolic: float | None = None,
    diastolic: float | None = None,
    activity_factor: float | None = None,
    activity_key: str | None = None,
    activity_name_ar: str | None = None,
    activity_name_en: str | None = None,
) -> dict:
    """Everything derivable from one set of values. Missing inputs yield None, never an error."""
    age = age_on(birth_date, on_date) if birth_date else None

    bmi_out = None
    if weight_kg and height_cm:
        value = bmi(weight_kg, height_cm)
        key, label = bmi_category(value)
        bmi_out = {"value": round(value, 1), "category": key, "label": label}

    whr_out = None
    if waist_cm and hip_cm:
        value = waist_hip_ratio(waist_cm, hip_cm)
        key, label = whr_risk(value, sex or "male")
        whr_out = {"value": round(value, 2), "risk": key, "label": label}

    bp_out = None
    if systolic and diastolic:
        key, label = blood_pressure_category(systolic, diastolic)
        bp_out = {"systolic": systolic, "diastolic": diastolic, "category": key, "label": label}

    bmr_value = tdee_value = targets = None
    if weight_kg and height_cm and age is not None and sex in ("male", "female"):
        bmr_value = bmr_mifflin_st_jeor(sex, weight_kg, height_cm, age)
        if activity_factor:
            tdee_value = tdee(bmr_value, activity_factor)
            targets = calorie_targets(tdee_value)

    return {
        "age": age,
        "weight": weight_kg,
        "height_cm": height_cm,
        "bmi": bmi_out,
        "whr": whr_out,
        "blood_pressure": bp_out,
        "bmr": round(bmr_value, 2) if bmr_value is not None else None,
        "tdee": round(tdee_value, 2) if tdee_value is not None else None,
        "targets": targets,
        "activity": (
            {"key": activity_key, "name_ar": activity_name_ar, "name_en": activity_name_en, "factor": activity_factor} if activity_factor else None
        ),
    }
