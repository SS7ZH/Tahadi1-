from datetime import date, timedelta

from app.rules.progress import compute_facts

TODAY = date(2026, 11, 9)


def weekly(weights, last_days_ago=0, waists=None):
    last = TODAY - timedelta(days=last_days_ago)
    n = len(weights)
    return [
        {
            "date": (last - timedelta(weeks=n - 1 - i)).isoformat(),
            "weight_kg": w,
            "waist_cm": waists[i] if waists else None,
        }
        for i, w in enumerate(weights)
    ]


def test_stalled_when_change_below_threshold_over_3_weeks():
    facts, alerts = compute_facts(weekly([92.4, 92.3, 92.5, 92.3]), TODAY)
    assert "stalled" in alerts
    assert facts["weight_change_2w_kg"] == 0.0  # 92.3 two weeks ago -> 92.3 now


def test_not_stalled_when_losing():
    facts, alerts = compute_facts(weekly([78.0, 77.2, 76.5, 75.6], waists=[88, 87, 86, 85]), TODAY)
    assert alerts == []
    assert facts["weight_change_2w_kg"] == -1.6
    assert facts["weight_change_4w_kg"] is None  # only 3 weeks of history
    assert facts["latest_waist_cm"] == 85.0


def test_exactly_0_3_kg_is_not_stalled():
    _, alerts = compute_facts(weekly([80.0, 80.1, 80.2, 80.3]), TODAY)
    assert "stalled" not in alerts


def test_stalled_needs_three_weeks_of_data():
    _, alerts = compute_facts(weekly([80.0, 80.0, 80.0]), TODAY)  # only 2 weeks
    assert "stalled" not in alerts


def test_no_checkin_at_exactly_10_days():
    facts, alerts = compute_facts(weekly([70.0, 69.0], last_days_ago=10), TODAY)
    assert facts["days_since_last"] == 10
    assert "no_checkin" in alerts


def test_no_alert_at_9_days():
    _, alerts = compute_facts(weekly([70.0, 69.0], last_days_ago=9), TODAY)
    assert "no_checkin" not in alerts


def test_four_week_change():
    facts, _ = compute_facts(weekly([64.0, 64.6, 65.1, 65.8, 66.2]), TODAY)
    assert facts["weight_change_4w_kg"] == 2.2


def test_empty_history():
    facts, alerts = compute_facts([], TODAY)
    assert facts["entries"] == 0
    assert facts["latest_weight_kg"] is None
    assert alerts == []


def test_unsorted_input_and_waist_only_entries():
    rows = weekly([90.0, 89.0, 88.0, 87.0])
    rows.append({"date": TODAY.isoformat(), "weight_kg": None, "waist_cm": 99.0})
    facts, _ = compute_facts(list(reversed(rows)), TODAY)
    assert facts["latest_weight_kg"] == 87.0
    assert facts["latest_waist_cm"] == 99.0
