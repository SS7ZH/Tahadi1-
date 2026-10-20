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
