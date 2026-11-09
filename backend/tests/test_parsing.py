import pytest

from app.rules.parsing import is_arabic, normalize, parse_measurement, validate_measurement


@pytest.mark.parametrize(
    "text, expected",
    [
        ("weight 82", {"weight_kg": 82.0, "waist_cm": None}),
        ("Weight: 82.5", {"weight_kg": 82.5, "waist_cm": None}),
        ("82kg", {"weight_kg": 82.0, "waist_cm": None}),
        ("today 81.4 kg, waist 90", {"weight_kg": 81.4, "waist_cm": 90.0}),
        ("waist 88cm", {"weight_kg": None, "waist_cm": 88.0}),
        ("وزني 82", {"weight_kg": 82.0, "waist_cm": None}),
        ("وزني ٨٢", {"weight_kg": 82.0, "waist_cm": None}),
        ("وزني ٨٢٫٥", {"weight_kg": 82.5, "waist_cm": None}),
        ("٧٩ كيلو", {"weight_kg": 79.0, "waist_cm": None}),
        ("الوزن 80 وخصري ٩٥", {"weight_kg": 80.0, "waist_cm": 95.0}),
        ("خصري 91 سم", {"weight_kg": None, "waist_cm": 91.0}),
    ],
)
def test_parses_measurements(text, expected):
    assert parse_measurement(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "hi coach, my knee hurts",
        "متى التمرين القادم؟",
        "weight 900",       # out of range
        "weight 12",        # out of range
        "waist 5",          # out of range
        "",
    ],
)
def test_rejects_non_measurements(text):
    assert parse_measurement(text) is None


def test_normalize_arabic_digits():
    assert normalize("٠١٢٣٤٥٦٧٨٩٫٥") == "0123456789.5"


def test_language_detection():
    assert is_arabic("وزني 82")
    assert not is_arabic("weight 82")


def test_validate_rejects_bad_llm_output():
    assert validate_measurement({"weight_kg": "abc", "waist_cm": None}) is None
    assert validate_measurement({"weight_kg": 1000}) is None
    assert validate_measurement({"weight_kg": 80, "waist_cm": 500}) == {"weight_kg": 80.0, "waist_cm": None}
    assert validate_measurement(None) is None
