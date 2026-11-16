"""Profile questions the bot asks a new player in his Telegram group (ADR-0011). Pure functions.

Order: age -> height -> goal. Age and height are asked only if missing; goal is always asked once.
Every answer can be skipped ("تخطي" / "skip"); the coach can fill it in the web app later.
"""

import re
from datetime import date

from app.rules.parsing import normalize

# step -> ClientProfile attribute it fills
PROFILE_STEPS = {"age": "birth_date", "height": "height_cm", "goal": "goal"}
ORDER = ["age", "height", "goal"]

QUESTIONS = {
    "age": "كم عمرك؟ (مثال: 28) — أو اكتب «تخطي»",
    "height": "كم طولك بالسنتيمتر؟ (مثال: 175) — أو اكتب «تخطي»",
    "goal": "ما هدفك؟ اكتب رقمًا:\n1) خسارة دهون\n2) بناء عضل\n3) لياقة عامة\n4) صحة\n— أو اكتب «تخطي»",
}

SKIP_WORDS = {"تخطي", "تخطى", "skip", "لا", "no"}
GOALS_BY_NUMBER = {"1": "fat_loss", "2": "muscle_gain", "3": "fitness", "4": "health"}
GOAL_KEYWORDS = (
    ("fat_loss", ("دهون", "خسارة", "تنحيف", "نزول", "fat", "lose")),
    ("muscle_gain", ("عضل", "تضخيم", "muscle", "bulk")),
    ("health", ("صحة", "صحي", "health")),
    ("fitness", ("لياقة", "fitness")),
)


def question_for(step: str | None) -> str:
    return QUESTIONS.get(step or "", "")


def _missing(profile, step: str) -> bool:
    return step == "goal" or getattr(profile, PROFILE_STEPS[step]) is None


def next_step(profile, after: str | None = None) -> str | None:
    """The next step to ask after `after` (or the first one), or None when nothing is left."""
    start = ORDER.index(after) + 1 if after in ORDER else 0
    for step in ORDER[start:]:
        if _missing(profile, step):
            return step
    return None


def parse_answer(step: str, text: str, today: date | None = None) -> tuple[bool, object]:
    """(understood, value). value None means skipped."""
    today = today or date.today()
    clean = normalize(text).strip().lower()
    if clean in SKIP_WORDS:
        return True, None
    numbers = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", clean)]

    if step == "age":
        if len(numbers) != 1:
            return False, None
        n = int(numbers[0])
        if 5 <= n <= 100:
            return True, date(today.year - n, 1, 1)
        if today.year - 100 <= n <= today.year - 5:  # a birth year such as 1996
            return True, date(n, 1, 1)
        return False, None

    if step == "height":
        if len(numbers) != 1:
            return False, None
        h = numbers[0]
        if 1.0 <= h <= 2.5:  # metres, e.g. 1.75
            h *= 100
        return (True, round(h, 1)) if 100 <= h <= 250 else (False, None)

    if step == "goal":
        if clean in GOALS_BY_NUMBER:
            return True, GOALS_BY_NUMBER[clean]
        for goal, words in GOAL_KEYWORDS:
            if any(w in clean for w in words):
                return True, goal
        return False, None

    return False, None
