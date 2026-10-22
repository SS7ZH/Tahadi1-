from datetime import date

import pytest

from app.services import calculations as calc


def test_bmr_male_known_value():
    # 800 + 1125 − 150 + 5
    assert calc.bmr_mifflin_st_jeor("male", 80, 180, 30) == pytest.approx(1780)


def test_tdee_moderate():
    assert calc.tdee(1780, 1.5) == pytest.approx(2670)


def test_bmr_female_known_value():
    # 600 + 1031.25 − 125 − 161
    assert calc.bmr_mifflin_st_jeor("female", 60, 165, 25) == pytest.approx(1345.25)


def test_bmr_rejects_unknown_sex():
    with pytest.raises(ValueError):
        calc.bmr_mifflin_st_jeor("x", 60, 165, 25)


def test_calorie_targets():
    assert calc.calorie_targets(2670) == {"maintenance": 2670, "fat_loss": 2170, "muscle_gain": 3170}


@pytest.mark.parametrize(
    "birth, on, expected",
    [
        (date(1996, 6, 15), date(2026, 6, 14), 29),  # day before birthday
        (date(1996, 6, 15), date(2026, 6, 15), 30),  # on birthday
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # leap-day birthday
    ],
)
def test_age_at_session_date(birth, on, expected):
    assert calc.age_on(birth, on) == expected


@pytest.mark.parametrize(
    "bmi, key, label",
    [(17.0, "underweight", "نقص وزن"), (18.5, "normal", "طبيعي"), (24.9, "normal", "طبيعي"),
     (25.0, "overweight", "زيادة وزن"), (29.9, "overweight", "زيادة وزن"), (30.0, "obese", "سمنة")],
)
def test_bmi_categories(bmi, key, label):
    assert calc.bmi_category(bmi) == (key, label)


def test_bmi_value():
    assert calc.bmi(80, 180) == pytest.approx(24.69, abs=0.01)


def test_whr_risk_by_sex():
    assert calc.whr_risk(0.91, "male") == ("high", "مرتفع")
    assert calc.whr_risk(0.90, "male") == ("normal", "طبيعي")
    assert calc.whr_risk(0.86, "female") == ("high", "مرتفع")
    assert calc.whr_risk(0.85, "female") == ("normal", "طبيعي")


@pytest.mark.parametrize(
    "s, d, key",
    [(115, 75, "normal"), (125, 75, "elevated"), (132, 75, "stage1"), (118, 85, "stage1"),
     (145, 80, "stage2"), (120, 95, "stage2")],
)
def test_blood_pressure_categories(s, d, key):
    assert calc.blood_pressure_category(s, d)[0] == key


def test_compute_results_uses_session_date_for_age():
    r = calc.compute_results(
        sex="male", birth_date=date(1996, 6, 15), on_date=date(2026, 6, 15),
        weight_kg=80, height_cm=180, activity_factor=1.5,
    )
    assert r["age"] == 30
    assert r["bmr"] == 1780
    assert r["tdee"] == 2670
    assert r["bmi"]["category"] == "normal"


def test_compute_results_tolerates_missing_inputs():
    r = calc.compute_results(sex="female", birth_date=None, on_date=date(2026, 1, 1), weight_kg=None, height_cm=None)
    assert r["bmr"] is None and r["bmi"] is None and r["tdee"] is None
