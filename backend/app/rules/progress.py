"""Deterministic progress facts and alerts. Pure functions; tested in tests/test_progress.py.

Rules (SPEC-agents-backend):
* stalled     - weight changed by less than 0.3 kg over the last 3 weeks; needs >= 3 weeks of data.
* no_checkin  - the last entry is 10 or more days old.
"""

from datetime import date, timedelta

STALL_KG = 0.3
STALL_WEEKS = 3
NO_CHECKIN_DAYS = 10


def _as_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _anchor(entries: list[dict], key: str, latest: date, weeks: int) -> dict | None:
    """Most recent entry with a value for `key`, dated at least `weeks` before `latest`."""
    cutoff = latest - timedelta(weeks=weeks)
    older = [e for e in entries if e["date"] <= cutoff and e.get(key) is not None]
    return older[-1] if older else None


def _change(entries, key, latest_entry, weeks):
    if latest_entry is None:
        return None
    anchor = _anchor(entries, key, latest_entry["date"], weeks)
    if anchor is None:
        return None
    return round(float(latest_entry[key]) - float(anchor[key]), 2)


def compute_facts(measurements: list[dict], today: date) -> tuple[dict, list[str]]:
    entries = sorted(
        ({**m, "date": _as_date(m["date"])} for m in measurements), key=lambda m: m["date"]
    )
    facts = {
        "entries": len(entries),
        "latest_date": None,
        "latest_weight_kg": None,
        "latest_waist_cm": None,
        "weight_change_2w_kg": None,
        "weight_change_4w_kg": None,
        "waist_change_4w_cm": None,
        "days_since_last": None,
    }
    alerts: list[str] = []
    if not entries:
        return facts, alerts

    last = entries[-1]
    last_weight = next((e for e in reversed(entries) if e.get("weight_kg") is not None), None)
    last_waist = next((e for e in reversed(entries) if e.get("waist_cm") is not None), None)

    facts["latest_date"] = last["date"].isoformat()
    facts["days_since_last"] = (today - last["date"]).days
    if last_weight:
        facts["latest_weight_kg"] = float(last_weight["weight_kg"])
    if last_waist:
        facts["latest_waist_cm"] = float(last_waist["waist_cm"])
    facts["weight_change_2w_kg"] = _change(entries, "weight_kg", last_weight, 2)
    facts["weight_change_4w_kg"] = _change(entries, "weight_kg", last_weight, 4)
    facts["waist_change_4w_cm"] = _change(entries, "waist_cm", last_waist, 4)

    change_3w = _change(entries, "weight_kg", last_weight, STALL_WEEKS)
    if change_3w is not None and abs(change_3w) < STALL_KG:
        alerts.append("stalled")
    if facts["days_since_last"] >= NO_CHECKIN_DAYS:
        alerts.append("no_checkin")
    return facts, alerts
