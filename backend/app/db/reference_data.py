"""Static reference data inserted by the initial migration (and by the test fixtures).

Kept as plain dicts so the migration does not depend on ORM models.
"""

URINE_CHOICES = [
    {"value": 1, "label": "1 – صافٍ"},
    {"value": 2, "label": "2 – أصفر فاتح جداً"},
    {"value": 3, "label": "3 – أصفر فاتح"},
    {"value": 4, "label": "4 – أصفر"},
    {"value": 5, "label": "5 – أصفر غامق"},
    {"value": 6, "label": "6 – كهرماني"},
    {"value": 7, "label": "7 – بني فاتح"},
    {"value": 8, "label": "8 – داكن جداً"},
]

SQUAT_CHOICES = [
    {"value": 1, "label": "1 – ضعيف جداً"},
    {"value": 2, "label": "2 – ضعيف"},
    {"value": 3, "label": "3 – مقبول"},
    {"value": 4, "label": "4 – جيد"},
    {"value": 5, "label": "5 – ممتاز"},
]

BODY_SHAPE_CHOICES = [
    {"value": 1, "label": "نحيف"},
    {"value": 2, "label": "رياضي"},
    {"value": 3, "label": "متوسط"},
    {"value": 4, "label": "ممتلئ"},
    {"value": 5, "label": "بدين"},
]


def _d(key, name_ar, category, unit, value_type, better="none", lo=None, hi=None, choices=None):
    return {
        "key": key,
        "name_ar": name_ar,
        "category": category,
        "unit": unit,
        "value_type": value_type,
        "better_direction": better,
        "min_value": lo,
        "max_value": hi,
        "choices": choices,
    }


_DEFS = [
    # ---- vital ----
    _d("pulse", "النبض", "vital", "نبضة/دقيقة", "number", "down", 30, 220),
    _d("blood_pressure", "الضغط", "vital", "mmHg", "blood_pressure", "down"),
    _d("blood_sugar", "السكر", "vital", "mg/dL", "number", "none", 20, 600),
    _d("hemoglobin", "الهيموجلوبين", "vital", "g/dL", "number", "none", 3, 25),
    _d("urine_color", "لون البول", "vital", "درجة 1–8", "choice", "down", 1, 8, URINE_CHOICES),
    # ---- body ----
    _d("height", "الطول", "body", "سم", "number", "none", 100, 250),
    _d("weight", "الوزن", "body", "كجم", "number", "none", 20, 300),  # direction depends on the client's goal
    _d("waist", "محيط الوسط", "body", "سم", "number", "down", 30, 250),
    _d("hip", "محيط الخصر / الأرداف", "body", "سم", "number", "none", 40, 250),
    _d("body_fat", "نسبة الدهون", "body", "%", "number", "down", 2, 75),
    _d("chest", "محيط الصدر", "body", "سم", "number", "none", 40, 200),
    _d("arm", "محيط الذراع", "body", "سم", "number", "none", 10, 80),
    _d("thigh", "محيط الفخذ", "body", "سم", "number", "none", 20, 120),
    _d("skinfold_triceps", "ثنايا الجلد – العضلة ثلاثية الرؤوس", "body", "مم", "number", "down", 1, 80),
    _d("skinfold_subscapular", "ثنايا الجلد – تحت اللوح", "body", "مم", "number", "down", 1, 80),
    _d("skinfold_suprailiac", "ثنايا الجلد – فوق الحرقفة", "body", "مم", "number", "down", 1, 80),
    _d("body_shape", "استدارة الجسم / نمط الجسم", "body", None, "choice", "none", 1, 5, BODY_SHAPE_CHOICES),
    # ---- movement ----
    _d("squat_assessment", "تقييم القرفصاء", "movement", "درجة 1–5", "choice", "up", 1, 5, SQUAT_CHOICES),
    _d("posture_analysis", "تحليل الوقوف (القوام)", "movement", None, "text"),
    # ---- physical ----
    _d("grip_strength", "قوة القبضة", "physical", "كجم", "number", "up", 0, 150),
    _d("cardio_endurance", "التحمل الدوري التنفسي", "physical", "مل/كجم/دقيقة", "number", "up", 0, 100),
    _d("push_ups", "الضغط", "physical", "عدد التكرارات", "number", "up", 0, 500),
    _d("sit_ups", "البطن", "physical", "تكرار/دقيقة", "number", "up", 0, 500),
    _d("agility", "الرشاقة", "physical", "ثانية", "number", "down", 1, 120),
    _d("flexibility", "المرونة (الجلوس والوصول)", "physical", "سم", "number", "up", -50, 80),
]

MEASUREMENT_DEFINITIONS = [{**d, "is_active": True, "sort_order": (i + 1) * 10} for i, d in enumerate(_DEFS)]

ACTIVITY_FACTORS = [
    {"key": "sedentary", "name_ar": "قليل الحركة", "description_ar": "لا يوجد تمارين", "factor": 1.2, "sort_order": 10},
    {"key": "light", "name_ar": "نشاط خفيف", "description_ar": "تمارين 1–3 أيام بالأسبوع", "factor": 1.3, "sort_order": 20},
    {"key": "moderate", "name_ar": "نشاط متوسط", "description_ar": "تمارين 3–5 أيام بالأسبوع", "factor": 1.5, "sort_order": 30},
    {"key": "high", "name_ar": "نشاط عالي", "description_ar": "تمارين 6–7 أيام بالأسبوع", "factor": 1.7, "sort_order": 40},
    {"key": "very_high", "name_ar": "نشاط عالي جداً", "description_ar": "تمارين مكثفة + عمل بدني", "factor": 1.9, "sort_order": 50},
]

# Blood pressure has two components; validated separately.
BP_LIMITS = {"systolic": (60, 260), "diastolic": (30, 160)}


# ---------------------------------------------------------------------------
# v2: English translations. Kept separate so migration 0001 (which inserts the
# lists above into the v1 schema) stays unchanged; migration 0002 applies these.
# ---------------------------------------------------------------------------

DEFINITION_TRANSLATIONS = {
    "pulse": ("Pulse", "bpm"),
    "blood_pressure": ("Blood pressure", "mmHg"),
    "blood_sugar": ("Blood sugar", "mg/dL"),
    "hemoglobin": ("Hemoglobin", "g/dL"),
    "urine_color": ("Urine color", "scale 1–8"),
    "height": ("Height", "cm"),
    "weight": ("Weight", "kg"),
    "waist": ("Waist circumference", "cm"),
    "hip": ("Hip circumference", "cm"),
    "body_fat": ("Body fat", "%"),
    "chest": ("Chest circumference", "cm"),
    "arm": ("Arm circumference", "cm"),
    "thigh": ("Thigh circumference", "cm"),
    "skinfold_triceps": ("Skinfold – triceps", "mm"),
    "skinfold_subscapular": ("Skinfold – subscapular", "mm"),
    "skinfold_suprailiac": ("Skinfold – suprailiac", "mm"),
    "body_shape": ("Body shape", None),
    "squat_assessment": ("Squat assessment", "score 1–5"),
    "posture_analysis": ("Posture analysis", None),
    "grip_strength": ("Grip strength", "kg"),
    "cardio_endurance": ("Cardiorespiratory endurance", "ml/kg/min"),
    "push_ups": ("Push-ups", "reps"),
    "sit_ups": ("Sit-ups", "reps/min"),
    "agility": ("Agility", "s"),
    "flexibility": ("Flexibility (sit and reach)", "cm"),
}

CHOICE_TRANSLATIONS = {
    "urine_color": {
        1: "1 – Clear", 2: "2 – Very pale yellow", 3: "3 – Pale yellow", 4: "4 – Yellow",
        5: "5 – Dark yellow", 6: "6 – Amber", 7: "7 – Light brown", 8: "8 – Very dark",
    },
    "squat_assessment": {1: "1 – Very poor", 2: "2 – Poor", 3: "3 – Fair", 4: "4 – Good", 5: "5 – Excellent"},
    "body_shape": {1: "Slim", 2: "Athletic", 3: "Average", 4: "Full", 5: "Heavy"},
}

ACTIVITY_TRANSLATIONS = {
    "sedentary": ("Sedentary", "No exercise"),
    "light": ("Lightly active", "Exercise 1–3 days a week"),
    "moderate": ("Moderately active", "Exercise 3–5 days a week"),
    "high": ("Very active", "Exercise 6–7 days a week"),
    "very_high": ("Extremely active", "Intense exercise + physical work"),
}


def translated_choices(key: str, choices: list | None) -> list | None:
    if not choices:
        return choices
    en = CHOICE_TRANSLATIONS.get(key, {})
    return [{**c, "label_en": en.get(int(c["value"]), c.get("label_en"))} for c in choices]


def definitions_v2() -> list[dict]:
    """Reference rows for the current schema (used by tests)."""
    out = []
    for d in MEASUREMENT_DEFINITIONS:
        name_en, unit_en = DEFINITION_TRANSLATIONS.get(d["key"], (None, None))
        out.append({**d, "name_en": name_en, "unit_en": unit_en, "choices": translated_choices(d["key"], d["choices"])})
    return out


def activity_factors_v2() -> list[dict]:
    out = []
    for f in ACTIVITY_FACTORS:
        name_en, desc_en = ACTIVITY_TRANSLATIONS.get(f["key"], (None, None))
        out.append({**f, "name_en": name_en, "description_en": desc_en})
    return out


# v3: calories & macros per goal (coach's General Dietary Advice Chart). Applied by migration 0003.
NUTRITION_SETTINGS = [
    {"goal": "weight_loss", "calorie_adjustment": -500, "protein_pct": 25, "carbs_pct": 50, "fat_pct": 25, "meals_min": 4, "meals_max": 5},
    {"goal": "maintenance", "calorie_adjustment": 0, "protein_pct": 20, "carbs_pct": 55, "fat_pct": 25, "meals_min": 4, "meals_max": 5},
    {"goal": "weight_gain", "calorie_adjustment": 500, "protein_pct": 15, "carbs_pct": 60, "fat_pct": 25, "meals_min": 5, "meals_max": 6},
]
