from datetime import date, timedelta

API = "/api/v1"


def _weigh(client, headers, client_id, weight, days_ago=0):
    payload = {
        "session_date": (date.today() - timedelta(days=days_ago)).isoformat(),
        "values": [{"key": "weight", "value_number": weight}],
    }
    r = client.post(f"{API}/clients/{client_id}/sessions", json=payload, headers=headers)
    assert r.status_code == 201, r.text


def test_suggestion_save_and_client_read_only(client, users, auth):
    """Client A: male, born 1995-01-01, 180 cm, moderate (1.5), goal fat_loss."""
    cid = users["client_a"].id
    coach = auth("trainer_a")
    _weigh(client, coach, cid, 80)

    view = client.get(f"{API}/clients/{cid}/nutrition", headers=coach).json()
    assert view["nutrition_goal"] == "weight_loss"
    s = view["suggestion"]
    assert s["calories"] == s["suggested_calories"] == s["dcn"] - 500
    assert s["meals_per_day"] == 4 and s["meals_range"] == [4, 5]
    assert view["current"] is None

    r = client.post(f"{API}/clients/{cid}/nutrition", json={"note": "accepted"}, headers=coach)
    assert r.status_code == 201, r.text
    saved = r.json()["current"]
    assert saved["calories"] == s["calories"] and saved["grams"] == s["grams"] and saved["overridden"] == []

    # player: sees the saved plan only, no suggestion, cannot write
    player = auth("client_a")
    pv = client.get(f"{API}/clients/{cid}/nutrition", headers=player).json()
    assert pv["current"]["calories"] == saved["calories"]
    assert pv["suggestion"] is None and pv["basis"] is None
    assert client.post(f"{API}/clients/{cid}/nutrition", json={}, headers=player).status_code == 403


def test_override_calories_recalculates_grams_unless_grams_overridden(client, users, auth):
    cid = users["client_a"].id
    coach = auth("trainer_a")
    _weigh(client, coach, cid, 80)
    r = client.post(
        f"{API}/clients/{cid}/nutrition", json={"calories": 2000, "protein_g": 160, "meals_per_day": 5}, headers=coach
    ).json()["current"]
    assert r["calories"] == 2000
    assert r["grams"] == {"protein": 160, "carbs": 250, "fat": 56}  # carbs 50%, fat 25% of 2000
    assert set(r["overridden"]) == {"calories", "protein_g", "meals_per_day"}
    assert r["per_meal"]["calories"] == 400


def test_meals_must_be_in_goal_range(client, users, auth):
    cid = users["client_a"].id
    _weigh(client, auth("trainer_a"), cid, 80)
    r = client.post(f"{API}/clients/{cid}/nutrition", json={"meals_per_day": 7}, headers=auth("trainer_a"))
    assert r.status_code == 422 and r.json()["code"] == "MEALS_OUT_OF_RANGE"


def test_new_weight_flags_suggestion_changed_and_history_kept(client, users, auth):
    cid = users["client_a"].id
    coach = auth("trainer_a")
    _weigh(client, coach, cid, 80, days_ago=14)
    client.post(f"{API}/clients/{cid}/nutrition", json={}, headers=coach)
    first = client.get(f"{API}/clients/{cid}/nutrition", headers=coach).json()
    assert first["suggestion_changed"] is False

    _weigh(client, coach, cid, 76)
    after = client.get(f"{API}/clients/{cid}/nutrition", headers=coach).json()
    assert after["suggestion_changed"] is True
    assert after["current"]["calories"] == first["current"]["calories"]  # saved plan unchanged until applied
    assert after["suggestion"]["calories"] < first["current"]["calories"]

    client.post(f"{API}/clients/{cid}/nutrition", json={}, headers=coach)
    history = client.get(f"{API}/clients/{cid}/nutrition/history", headers=coach).json()
    assert len(history) == 2 and history[0]["based_on_weight"] == 76 and history[1]["based_on_weight"] == 80
    assert client.get(f"{API}/clients/{cid}/nutrition", headers=coach).json()["suggestion_changed"] is False


def test_goal_change_and_performance(client, users, auth):
    cid = users["client_a"].id
    coach = auth("trainer_a")
    _weigh(client, coach, cid, 80)
    r = client.post(f"{API}/clients/{cid}/nutrition", json={"goal": "muscle_gain"}, headers=coach).json()
    assert r["nutrition_goal"] == "weight_gain" and r["current"]["meals_per_day"] == 5
    assert r["current"]["calories"] == r["suggestion"]["dcn"] + 500
    r = client.post(f"{API}/clients/{cid}/nutrition", json={"goal": "performance"}, headers=coach).json()
    assert r["nutrition_goal"] == "maintenance" and r["current"]["calories"] == r["suggestion"]["dcn"]


def test_no_weight_needs_manual_calories(client, users, auth):
    cid = users["client_a"].id
    r = client.post(f"{API}/clients/{cid}/nutrition", json={}, headers=auth("trainer_a"))
    assert r.status_code == 422 and r.json()["code"] == "DCN_UNAVAILABLE"
    r = client.post(f"{API}/clients/{cid}/nutrition", json={"calories": 2200}, headers=auth("trainer_a"))
    assert r.status_code == 201 and r.json()["current"]["calories"] == 2200


def test_other_trainer_and_other_client_get_404(client, users, auth):
    cid = users["client_a"].id
    assert client.get(f"{API}/clients/{cid}/nutrition", headers=auth("trainer_b")).status_code == 404
    assert client.post(f"{API}/clients/{cid}/nutrition", json={"calories": 2000}, headers=auth("trainer_b")).status_code == 404
    assert client.get(f"{API}/clients/{cid}/nutrition", headers=auth("client_b")).status_code == 404


def test_admin_edits_settings_and_validation(client, users, auth):
    admin = auth("admin")
    rows = {r["goal"]: r for r in client.get(f"{API}/nutrition-settings", headers=admin).json()}
    gain = rows["weight_gain"]
    assert gain["calorie_adjustment"] == 500 and (gain["protein_pct"], gain["carbs_pct"], gain["fat_pct"]) == (15, 60, 25)
    bad = client.patch(f"{API}/admin/nutrition-settings/{gain['id']}", json={"protein_pct": 30}, headers=admin)
    assert bad.status_code == 400 and bad.json()["code"] == "PERCENTAGES_SUM"
    ok = client.patch(f"{API}/admin/nutrition-settings/{gain['id']}", json={"calorie_adjustment": 400}, headers=admin)
    assert ok.status_code == 200 and ok.json()["calorie_adjustment"] == 400
    assert client.patch(f"{API}/admin/nutrition-settings/{gain['id']}", json={}, headers=auth("trainer_a")).status_code == 403


def test_calculator_nutrition_endpoint(client, users, auth):
    body = {"sex": "male", "age": 30, "weight": 80, "height": 180, "activity_key": "moderate", "goal": "weight_loss"}
    r = client.post(f"{API}/calculate/nutrition", json=body, headers=auth("client_a")).json()
    assert r["bmr"] == 1780 and r["tdee"] == 2670 and r["plan"]["calories"] == 2170
    assert r["plan"]["grams"] == {"protein": 136, "carbs": 271, "fat": 60}
