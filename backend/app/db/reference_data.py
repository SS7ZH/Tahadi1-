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


# v4: shared exercise library (applied by migration 0004).
MUSCLE_GROUPS = (
    "chest", "back", "shoulders", "biceps", "triceps", "quads", "hamstrings",
    "glutes", "calves", "core", "full_body", "cardio",
)
EQUIPMENT = ("barbell", "dumbbell", "machine", "cable", "bodyweight", "kettlebell", "band", "other")
CARDIO_TYPES = ("walking", "running", "cycling", "treadmill", "jump_rope", "swimming", "hiit")

_EX = [
    # chest
    ("ضغط البنش بالبار", "Barbell bench press", "chest", "barbell"),
    ("ضغط البنش المائل بالدمبل", "Incline dumbbell press", "chest", "dumbbell"),
    ("تفتيح بالدمبل", "Dumbbell fly", "chest", "dumbbell"),
    ("تفتيح بالكيبل", "Cable crossover", "chest", "cable"),
    ("تمرين الضغط", "Push-up", "chest", "bodyweight"),
    ("ضغط الصدر بالجهاز", "Machine chest press", "chest", "machine"),
    # back
    ("السحب العلوي", "Lat pulldown", "back", "cable"),
    ("العقلة", "Pull-up", "back", "bodyweight"),
    ("التجديف بالبار", "Barbell row", "back", "barbell"),
    ("التجديف بالدمبل بيد واحدة", "One-arm dumbbell row", "back", "dumbbell"),
    ("السحب الأرضي بالكيبل", "Seated cable row", "back", "cable"),
    ("الرفعة الميتة", "Deadlift", "back", "barbell"),
    # shoulders
    ("ضغط الكتف بالدمبل", "Dumbbell shoulder press", "shoulders", "dumbbell"),
    ("ضغط الكتف العسكري بالبار", "Barbell overhead press", "shoulders", "barbell"),
    ("رفرفة جانبية", "Lateral raise", "shoulders", "dumbbell"),
    ("رفرفة أمامية", "Front raise", "shoulders", "dumbbell"),
    ("رفرفة خلفية", "Reverse fly", "shoulders", "dumbbell"),
    ("سحب الوجه بالكيبل", "Face pull", "shoulders", "cable"),
    # biceps / triceps
    ("ثني الذراع بالبار", "Barbell curl", "biceps", "barbell"),
    ("ثني الذراع بالدمبل", "Dumbbell curl", "biceps", "dumbbell"),
    ("ثني المطرقة", "Hammer curl", "biceps", "dumbbell"),
    ("سحب الترايسبس بالكيبل", "Triceps pushdown", "triceps", "cable"),
    ("التمديد فوق الرأس", "Overhead triceps extension", "triceps", "dumbbell"),
    ("الغطس على المتوازي", "Dips", "triceps", "bodyweight"),
    # legs
    ("القرفصاء بالبار", "Barbell back squat", "quads", "barbell"),
    ("القرفصاء الأمامية بالدمبل (جوبلت)", "Goblet squat", "quads", "dumbbell"),
    ("دفع الأرجل بالجهاز", "Leg press", "quads", "machine"),
    ("تمديد الأرجل", "Leg extension", "quads", "machine"),
    ("الطعنات", "Walking lunge", "quads", "dumbbell"),
    ("الرفعة الرومانية", "Romanian deadlift", "hamstrings", "barbell"),
    ("ثني الأرجل بالجهاز", "Lying leg curl", "hamstrings", "machine"),
    ("دفع الحوض بالبار", "Barbell hip thrust", "glutes", "barbell"),
    ("الجسر الأرضي", "Glute bridge", "glutes", "bodyweight"),
    ("رفع السمانة واقفاً", "Standing calf raise", "calves", "machine"),
    # core
    ("البلانك", "Plank", "core", "bodyweight"),
    ("البلانك الجانبي", "Side plank", "core", "bodyweight"),
    ("الكرنش", "Crunch", "core", "bodyweight"),
    ("رفع الأرجل معلقاً", "Hanging leg raise", "core", "bodyweight"),
    ("الدوران الروسي", "Russian twist", "core", "bodyweight"),
    # full body
    ("تأرجح الكيتل بل", "Kettlebell swing", "full_body", "kettlebell"),
    ("البيربي", "Burpee", "full_body", "bodyweight"),
    ("متسلق الجبال", "Mountain climber", "full_body", "bodyweight"),
]

EXERCISES = [
    {"name_ar": a, "name_en": e, "muscle_group": m, "equipment": q, "is_active": True} for a, e, m, q in _EX
]


# v5: subscription plans and the first contract / disclaimer templates (applied by migration 0005).
SUBSCRIPTION_PLANS = [
    {"name_ar": "شهر واحد", "name_en": "1 month", "months": 1, "price": None, "currency": "SAR", "is_active": True, "sort_order": 10},
    {"name_ar": "3 أشهر", "name_en": "3 months", "months": 3, "price": None, "currency": "SAR", "is_active": True, "sort_order": 20},
    {"name_ar": "6 أشهر", "name_en": "6 months", "months": 6, "price": None, "currency": "SAR", "is_active": True, "sort_order": 30},
    {"name_ar": "سنة", "name_en": "1 year", "months": 12, "price": None, "currency": "SAR", "is_active": True, "sort_order": 40},
]

# Placeholders available in templates (filled when the client signs).
TEMPLATE_PLACEHOLDERS = ("client_name", "coach_name", "plan", "start_date", "end_date", "price", "today")

# SAMPLE TEXT ONLY: must be reviewed by a legal advisor before real use (shown in the admin screen too).
CONTRACT_V1_AR = """عقد اشتراك في برنامج تدريب شخصي – منصة تحدي

تاريخ العقد: {today}

الطرف الأول (المدرب): {coach_name}
الطرف الثاني (المتدرب): {client_name}

أولاً: مدة الاشتراك
خطة الاشتراك: {plan}
تاريخ البداية: {start_date}
تاريخ النهاية: {end_date}
قيمة الاشتراك: {price}

ثانياً: التزامات المدرب
1. تسجيل قياسات المتدرب بشكل دوري ومتابعة تقدمه على منصة تحدي.
2. إعداد برنامج تدريبي وتوصيات غذائية عامة مناسبة لهدف المتدرب.
3. الرد على أسئلة المتدرب عبر المنصة في وقت معقول.
4. المحافظة على سرية بيانات المتدرب الصحية وعدم مشاركتها مع أي طرف ثالث.

ثالثاً: التزامات المتدرب
1. تقديم معلومات صحية صحيحة وكاملة، وإبلاغ المدرب فوراً بأي تغير في حالته الصحية.
2. الالتزام بالبرنامج قدر الإمكان، وإيقاف التمرين عند الشعور بأي ألم أو أعراض غير طبيعية.
3. استشارة الطبيب قبل البدء عند وجود أي مرض مزمن أو إصابة.

رابعاً: التجديد والإلغاء
يتم التجديد أو تغيير الخطة بالاتفاق مع المدرب، ويتطلب ذلك توقيع عقد جديد.

خامساً: إقرار
أقر أنا {client_name} بأنني قرأت هذا العقد وفهمت جميع بنوده ووافقت عليها.
"""

CONTRACT_V1_EN = """Personal Training Subscription Agreement – Tahadi

Agreement date: {today}

Party one (Coach): {coach_name}
Party two (Client): {client_name}

1. Subscription period
Plan: {plan}
Start date: {start_date}
End date: {end_date}
Price: {price}

2. Coach obligations
1. Record the client's measurements regularly and follow their progress on Tahadi.
2. Prepare a training program and general nutrition guidance suited to the client's goal.
3. Answer the client's questions through the platform within a reasonable time.
4. Keep the client's health information confidential and never share it with third parties.

3. Client obligations
1. Provide accurate and complete health information and tell the coach immediately about any change in health.
2. Follow the program as far as possible, and stop exercising if they feel pain or unusual symptoms.
3. Consult a doctor before starting if they have any chronic condition or injury.

4. Renewal and cancellation
Renewing or changing the plan is agreed with the coach and requires signing a new agreement.

5. Acknowledgement
I, {client_name}, confirm that I have read this agreement, understood all of its terms, and agree to them.
"""

DISCLAIMER_V1_AR = """الإقرار الصحي وإخلاء المسؤولية – منصة تحدي

أقر أنا {client_name} بما يلي:

1. أن المعلومات الصحية التي قدمتها صحيحة وكاملة حسب علمي، وأنني سأبلغ مدربي {coach_name} بأي تغير في حالتي الصحية.
2. أن البرامج التدريبية والتوصيات الغذائية المقدمة عبر المنصة إرشادات عامة، ولا تُعد تشخيصاً طبياً أو بديلاً عن استشارة الطبيب أو أخصائي التغذية.
3. أنني استشرت طبيباً، أو سأستشيره، قبل البدء في أي برنامج رياضي إذا كنت أعاني من مرض مزمن أو إصابة أو أتناول أدوية.
4. أنني سأتوقف عن التمرين فوراً وأطلب المساعدة الطبية عند الشعور بألم في الصدر أو دوار أو ضيق تنفس أو أي أعراض غير طبيعية.
5. أنني أتحمل مسؤولية مشاركتي في التمارين، وأن المدرب والمنصة لا يتحملان مسؤولية أي إصابة ناتجة عن عدم الالتزام بالتعليمات أو عن معلومات صحية غير صحيحة.

التاريخ: {today}
"""

DISCLAIMER_V1_EN = """Health Declaration and Disclaimer – Tahadi

I, {client_name}, confirm that:

1. The health information I have provided is accurate and complete to the best of my knowledge, and I will tell my coach {coach_name} about any change in my health.
2. The training programs and nutrition guidance on this platform are general guidance; they are not a medical diagnosis and do not replace advice from a doctor or dietitian.
3. I have consulted, or will consult, a doctor before starting any exercise program if I have a chronic condition or injury, or take medication.
4. I will stop exercising immediately and seek medical help if I feel chest pain, dizziness, shortness of breath or any unusual symptoms.
5. I take responsibility for my participation in exercise, and the coach and the platform are not responsible for injuries caused by not following instructions or by inaccurate health information.

Date: {today}
"""

DOCUMENT_TEMPLATES = [
    {"kind": "contract", "version": 1, "body_ar": CONTRACT_V1_AR, "body_en": CONTRACT_V1_EN, "is_active": True},
    {"kind": "disclaimer", "version": 1, "body_ar": DISCLAIMER_V1_AR, "body_en": DISCLAIMER_V1_EN, "is_active": True},
]

CHRONIC_CONDITIONS = ("diabetes", "hypertension", "heart_disease", "asthma", "joint_back", "other")
