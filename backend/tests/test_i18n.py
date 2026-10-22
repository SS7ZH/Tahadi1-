from datetime import date

from app.core.i18n import parse_accept_language

API = "/api/v1"
EN = {"Accept-Language": "en-US,en;q=0.9"}


def test_parse_accept_language():
    assert parse_accept_language(None) == "ar"
    assert parse_accept_language("en-GB,en;q=0.8") == "en"
    assert parse_accept_language("ar-SA,ar;q=0.9,en;q=0.8") == "ar"
    assert parse_accept_language("fr-FR,en;q=0.5") == "en"
    assert parse_accept_language("fr-FR") == "ar"


def test_errors_follow_accept_language(client, users):
    body = {"email": "ca@test.app", "password": "nope"}
    ar = client.post(f"{API}/auth/login", json=body).json()
    en = client.post(f"{API}/auth/login", json=body, headers=EN).json()
    assert ar["code"] == en["code"] == "INVALID_CREDENTIALS"
    assert "كلمة المرور" in ar["detail"]
    assert en["detail"] == "Incorrect email or password"


def test_validation_and_not_found_in_english(client, users, auth):
    h = {**auth("trainer_a"), **EN}
    r = client.get(f"{API}/clients/{users['client_b'].id}", headers=h)
    assert r.status_code == 404 and r.json()["detail"] == "Client not found"
    bad = {"session_date": date.today().isoformat(), "values": [{"key": "weight", "value_number": 500}]}
    r = client.post(f"{API}/clients/{users['client_a'].id}/sessions", json=bad, headers=h)
    assert r.status_code == 422
    assert r.json()["detail"] == "Weight must be between 20 and 300 kg"


def test_definitions_and_values_carry_english(client, users, auth):
    h = auth("trainer_a")
    defs = {d["key"]: d for d in client.get(f"{API}/measurement-definitions", headers=h).json()}
    assert defs["weight"]["name_en"] == "Weight" and defs["weight"]["unit_en"] == "kg"
    assert defs["urine_color"]["choices"][0]["label_en"] == "1 – Clear"
    payload = {"session_date": date.today().isoformat(), "values": [{"key": "squat_assessment", "value_number": 4}]}
    s = client.post(f"{API}/clients/{users['client_a'].id}/sessions", json=payload, headers={**h, **EN}).json()
    squat = s["values"][0]
    assert squat["name_en"] == "Squat assessment"
    assert squat["display"] == "4 – Good"
    factors = client.get(f"{API}/activity-factors", headers=h).json()
    assert factors[0]["name_en"] == "Sedentary"


def test_result_labels_localized(client, users, auth):
    payload = {"session_date": date.today().isoformat(), "values": [{"key": "weight", "value_number": 90}]}
    r = client.post(
        f"{API}/clients/{users['client_a'].id}/sessions", json=payload, headers={**auth("trainer_a"), **EN}
    ).json()
    assert r["results"]["bmi"]["label"] == "Overweight"
