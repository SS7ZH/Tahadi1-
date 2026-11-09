"""Deterministic measurement parsing for Arabic and English check-in messages.

Pure functions only: no database, no network. Tested in tests/test_parsing.py.
"""

import re

WEIGHT_RANGE = (30.0, 300.0)
WAIST_RANGE = (40.0, 200.0)

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_ARABIC_LETTERS = re.compile(r"[؀-ۿ]")

_NUM = r"(\d{1,3}(?:[.,]\d{1,2})?)"
_WEIGHT_PATTERNS = [
    re.compile(r"(?:weight|weigh|wt|وزني|الوزن|وزن)\s*(?:is|=|:|-)?\s*" + _NUM, re.IGNORECASE),
    re.compile(_NUM + r"\s*(?:kg|kgs|kilo|kilos|كيلو|كيلوجرام|كجم|كغ|كلغ)", re.IGNORECASE),
]
_WAIST_PATTERNS = [
    re.compile(r"(?:waist|خصري|الخصر|خصر|وسطي)\s*(?:is|=|:|-)?\s*" + _NUM, re.IGNORECASE),
    re.compile(_NUM + r"\s*(?:cm|سم|سنتي)", re.IGNORECASE),
]


def normalize(text: str) -> str:
    """Convert Arabic-Indic digits and the Arabic decimal mark to ASCII."""
    return text.translate(_DIGITS).replace("٫", ".")


def is_arabic(text: str) -> bool:
    return bool(_ARABIC_LETTERS.search(text))


def _first(patterns: list[re.Pattern], text: str, lo: float, hi: float) -> float | None:
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = float(match.group(1).replace(",", "."))
            if lo <= value <= hi:
                return value
    return None


def parse_measurement(text: str) -> dict | None:
    """Return {"weight_kg": float|None, "waist_cm": float|None}, or None if nothing valid was found."""
    clean = normalize(text)
    weight = _first(_WEIGHT_PATTERNS, clean, *WEIGHT_RANGE)
    waist = _first(_WAIST_PATTERNS, clean, *WAIST_RANGE)
    if weight is None and waist is None:
        return None
    return {"weight_kg": weight, "waist_cm": waist}


def validate_measurement(values: dict | None) -> dict | None:
    """Range-check a measurement from any source (used for the language-model fallback too)."""
    if not values:
        return None
    out = {}
    for key, (lo, hi) in (("weight_kg", WEIGHT_RANGE), ("waist_cm", WAIST_RANGE)):
        try:
            v = float(values.get(key)) if values.get(key) is not None else None
        except (TypeError, ValueError):
            v = None
        out[key] = v if v is not None and lo <= v <= hi else None
    return out if out["weight_kg"] is not None or out["waist_cm"] is not None else None
