"""Calories & macros from the coach's General Dietary Advice Chart. Pure functions, no database access.

Calories:  weight loss = DCN − 500 · maintenance/performance = DCN · weight gain = DCN + 500
Macros (% of calories → grams): protein and carbs 4 kcal/g, fat 9 kcal/g.
The numbers come from NutritionSetting rows (admin-editable); DEFAULT_SETTINGS mirrors the seed.
"""
import math
from dataclasses import asdict, dataclass

KCAL_PER_G = {"protein": 4, "carbs": 4, "fat": 9}
MACROS = ("protein", "carbs", "fat")

# client_profiles.goal → nutrition goal
GOAL_MAP = {
    "fat_loss": "weight_loss",
    "muscle_gain": "weight_gain",
    "fitness": "maintenance",
    "health": "maintenance",
    "performance": "maintenance",  # performance uses the maintenance numbers
}
NUTRITION_GOALS = ("weight_loss", "maintenance", "weight_gain")


@dataclass(frozen=True)
class MacroSettings:
    calorie_adjustment: int
    protein_pct: float
    carbs_pct: float
    fat_pct: float
    meals_min: int
    meals_max: int


DEFAULT_SETTINGS: dict[str, MacroSettings] = {
    "weight_loss": MacroSettings(-500, 25, 50, 25, 4, 5),
    "maintenance": MacroSettings(0, 20, 55, 25, 4, 5),
    "weight_gain": MacroSettings(500, 15, 60, 25, 5, 6),
}


def round_half_up(x: float) -> int:
    """188 for 187.5 (Python's round() would give banker's rounding)."""
    return int(math.floor(x + 0.5))


def nutrition_goal(profile_goal: str | None) -> str:
    return GOAL_MAP.get(profile_goal or "", "maintenance")


def target_calories(dcn: float, settings: MacroSettings) -> int:
    return round_half_up(dcn + settings.calorie_adjustment)


def grams_from_calories(calories: float, pct: float, macro: str) -> int:
    return round_half_up(calories * pct / 100 / KCAL_PER_G[macro])


def macro_breakdown(
    calories: int, grams: dict[str, int], pcts: dict[str, float], overridden: set[str] | frozenset = frozenset()
) -> dict:
    """{protein: {g, kcal, pct}, ...}

    From the chart: kcal = calories × %, grams = kcal ÷ 4 (or 9), rounded. For a macro whose grams
    the coach overrode, kcal and % are derived from those grams instead.
    """
    out = {}
    for m in MACROS:
        if m in overridden:
            kcal = grams[m] * KCAL_PER_G[m]
            pct = round(kcal / calories * 100, 1) if calories else 0.0
        else:
            kcal = round_half_up(calories * pcts[m] / 100)
            pct = pcts[m]
        out[m] = {"g": grams[m], "kcal": kcal, "pct": pct}
    return out


def per_meal(calories: int, grams: dict[str, int], meals: int) -> dict:
    meals = max(1, meals)
    return {
        "calories": round_half_up(calories / meals),
        **{m: round_half_up(grams[m] / meals) for m in MACROS},
    }


def build_plan(
    dcn: float,
    settings: MacroSettings,
    *,
    calories: int | None = None,
    grams_override: dict[str, int | None] | None = None,
    meals_per_day: int | None = None,
) -> dict:
    """Suggested plan, optionally with coach overrides.

    - calories override: grams are recalculated from the goal's percentages
    - a gram override wins for that macro only
    - meals default to the lower end of the goal's range
    """
    suggested = target_calories(dcn, settings)
    cal = int(calories) if calories is not None else suggested
    pcts = {"protein": settings.protein_pct, "carbs": settings.carbs_pct, "fat": settings.fat_pct}
    grams_override = grams_override or {}
    grams = {
        m: int(grams_override[m]) if grams_override.get(m) is not None else grams_from_calories(cal, pcts[m], m)
        for m in MACROS
    }
    meals = meals_per_day if meals_per_day is not None else settings.meals_min
    overridden = [k for k, v in (("calories", calories), *((f"{m}_g", grams_override.get(m)) for m in MACROS)) if v is not None]
    if meals_per_day is not None and meals_per_day != settings.meals_min:
        overridden.append("meals_per_day")
    return {
        "dcn": round_half_up(dcn),
        "suggested_calories": suggested,
        "calories": cal,
        "percentages": pcts,
        "grams": grams,
        "macros": macro_breakdown(cal, grams, pcts, {m for m in MACROS if grams_override.get(m) is not None}),
        "meals_per_day": meals,
        "meals_range": [settings.meals_min, settings.meals_max],
        "per_meal": per_meal(cal, grams, meals),
        "overridden": overridden,
        "settings": asdict(settings),
    }
