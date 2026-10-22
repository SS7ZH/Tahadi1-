import pytest

from app.services import calculations as calc
from app.services import nutrition as nut

S = nut.DEFAULT_SETTINGS


# ---- coach's example, DCN = 3500 kcal (section 1.6) ----
@pytest.mark.parametrize(
    "goal, calories, protein, carbs, fat",
    [
        # (kcal, g) pairs
        ("weight_loss", 3000, (750, 188), (1500, 375), (750, 83)),
        ("maintenance", 3500, (700, 175), (1925, 481), (875, 97)),
        ("weight_gain", 4000, (600, 150), (2400, 600), (1000, 111)),
    ],
)
def test_coach_example_dcn_3500(goal, calories, protein, carbs, fat):
    plan = nut.build_plan(3500, S[goal])
    assert plan["calories"] == calories
    for macro, (kcal, grams) in (("protein", protein), ("carbs", carbs), ("fat", fat)):
        pct = plan["percentages"][macro]
        assert calories * pct / 100 == pytest.approx(kcal)
        assert plan["grams"][macro] == grams
        assert plan["macros"][macro] == {"g": grams, "kcal": kcal, "pct": pct}


def test_full_chain_man_30_80kg_180cm_moderate():
    bmr = calc.bmr_mifflin_st_jeor("male", 80, 180, 30)
    dcn = calc.tdee(bmr, 1.5)
    assert bmr == pytest.approx(1780)
    assert dcn == pytest.approx(2670)
    assert nut.build_plan(dcn, S["weight_loss"])["calories"] == 2170


def test_goal_mapping():
    assert nut.nutrition_goal("fat_loss") == "weight_loss"
    assert nut.nutrition_goal("muscle_gain") == "weight_gain"
    assert nut.nutrition_goal("performance") == "maintenance"
    assert nut.nutrition_goal("health") == "maintenance"
    assert nut.nutrition_goal(None) == "maintenance"


def test_meals_default_to_lower_bound_and_split_equally():
    plan = nut.build_plan(3500, S["weight_gain"])
    assert plan["meals_per_day"] == 5 and plan["meals_range"] == [5, 6]
    assert plan["per_meal"] == {"calories": 800, "protein": 30, "carbs": 120, "fat": 22}


def test_calorie_override_recalculates_grams_from_same_percentages():
    plan = nut.build_plan(3500, S["weight_loss"], calories=2800)
    assert plan["suggested_calories"] == 3000 and plan["calories"] == 2800
    assert plan["grams"] == {"protein": 175, "carbs": 350, "fat": 78}
    assert plan["overridden"] == ["calories"]


def test_gram_override_wins_over_recalculation():
    plan = nut.build_plan(3500, S["weight_loss"], calories=2800, grams_override={"protein": 200})
    assert plan["grams"]["protein"] == 200  # kept
    assert plan["grams"]["carbs"] == 350  # recalculated from 50% of 2800
    assert plan["macros"]["protein"]["kcal"] == 800
    assert plan["macros"]["protein"]["pct"] == pytest.approx(28.6)
    assert set(plan["overridden"]) == {"calories", "protein_g"}


def test_round_half_up():
    assert nut.round_half_up(187.5) == 188
    assert nut.round_half_up(182.5) == 183
    assert nut.round_half_up(83.33) == 83
