from datetime import date, timedelta

from app.models import AuditLog

API = "/api/v1"
TODAY = date.today().isoformat()


def _session_payload(weight=90, **extra):
    values = [
        {"key": "weight", "value_number": weight},
        {"key": "waist", "value_number": 95},
        {"key": "hip", "value_number": 100},
        {"key": "blood_pressure", "systolic": 125, "diastolic": 78},
        {"key": "squat_assessment", "value_number": 3, "value_text": "ركبة تميل للداخل"},
    ]
    return {"session_date": TODAY, "notes": "ملاحظة", "values": values, **extra}


def _create_session(client, headers, client_id, **kw):
    r = client.post(f"{API}/clients/{client_id}/sessions", json=_session_payload(**kw), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------- health / auth ----------------
def test_health(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["database"] == "ok"


def test_login_never_returns_password_hash(client, users, auth):
    r = client.post(f"{API}/auth/login", json={"email": "ca@test.app", "password": "Passw0rd!"})
    assert r.status_code == 200
    assert "password" not in r.text
    me = client.get(f"{API}/auth/me", headers=auth("admin"))
    assert "password_hash" not in me.text
    listing = client.get(f"{API}/admin/users", headers=auth("admin"))
    assert "password_hash" not in listing.text


def test_login_wrong_password_arabic_error(client, users):
    r = client.post(f"{API}/auth/login", json={"email": "ca@test.app", "password": "nope"})
    assert r.status_code == 401
    assert r.json()["code"] == "INVALID_CREDENTIALS"
    assert "كلمة المرور" in r.json()["detail"]


def test_login_rate_limited(client, users):
    codes = [
        client.post(f"{API}/auth/login", json={"email": "ca@test.app", "password": "bad"}).status_code
        for _ in range(12)
    ]
    assert codes[-1] == 429


def test_refresh_flow(client, users):
    tokens = client.post(f"{API}/auth/login", json={"email": "ta@test.app", "password": "Passw0rd!"}).json()
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    # an access token is not accepted as a refresh token
    bad = client.post(f"{API}/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert bad.status_code == 401


def test_unauthenticated_is_401(client):
    r = client.get(f"{API}/clients")
    assert r.status_code == 401
    assert r.json()["code"] == "NOT_AUTHENTICATED"


# ---------------- permissions ----------------
def test_trainer_sees_only_own_clients(client, users, auth):
    r = client.get(f"{API}/clients", headers=auth("trainer_a"))
    assert [c["id"] for c in r.json()] == [users["client_a"].id]


def test_trainer_cannot_access_other_trainers_client(client, users, auth):
    other = users["client_b"].id
    h = auth("trainer_a")
    for path in ("", "/summary", "/progress", "/sessions", "/comments", "/questions"):
        assert client.get(f"{API}/clients/{other}{path}", headers=h).status_code == 404, path
    r = client.post(f"{API}/clients/{other}/sessions", json=_session_payload(), headers=h)
    assert r.status_code == 404


def test_trainer_cannot_touch_other_trainers_session(client, users, auth):
    s = _create_session(client, auth("trainer_b"), users["client_b"].id)
    h = auth("trainer_a")
    assert client.get(f"{API}/sessions/{s['id']}", headers=h).status_code == 404
    assert client.put(f"{API}/sessions/{s['id']}", json=_session_payload(), headers=h).status_code == 404
    assert client.delete(f"{API}/sessions/{s['id']}", headers=h).status_code == 404


def test_client_cannot_see_other_client(client, users, auth):
    h = auth("client_a")
    assert client.get(f"{API}/clients/{users['client_b'].id}", headers=h).status_code == 404
    assert client.get(f"{API}/clients/{users['client_b'].id}/sessions", headers=h).status_code == 404
    own = client.get(f"{API}/clients", headers=h).json()
    assert [c["id"] for c in own] == [users["client_a"].id]


def test_client_cannot_write_measurements(client, users, auth):
    s = _create_session(client, auth("trainer_a"), users["client_a"].id)
    h = auth("client_a")
    cid = users["client_a"].id
    assert client.post(f"{API}/clients/{cid}/sessions", json=_session_payload(), headers=h).status_code == 403
    assert client.put(f"{API}/sessions/{s['id']}", json=_session_payload(), headers=h).status_code == 403
    assert client.delete(f"{API}/sessions/{s['id']}", headers=h).status_code == 403
    # ...but can read them
    assert client.get(f"{API}/sessions/{s['id']}", headers=h).status_code == 200


def test_client_cannot_use_admin_or_trainer_endpoints(client, users, auth):
    h = auth("client_a")
    assert client.get(f"{API}/admin/users", headers=h).status_code == 403
    assert client.get(f"{API}/trainer/questions", headers=h).status_code == 403
    assert client.post(f"{API}/clients/{users['client_a'].id}/comments", json={"body": "x"}, headers=h).status_code == 403
    assert client.patch(f"{API}/clients/{users['client_a'].id}", json={"height_cm": 190}, headers=h).status_code == 403


def test_client_profile_update_cannot_change_protected_fields(client, users, auth):
    h = auth("client_a")
    r = client.patch(f"{API}/auth/me", json={"full_name": "اسم جديد", "phone": "0555"}, headers=h)
    assert r.status_code == 200 and r.json()["full_name"] == "اسم جديد"
    for forbidden in ({"role": "admin"}, {"height_cm": 150}, {"trainer_id": 1}, {"sex": "female"}):
        assert client.patch(f"{API}/auth/me", json=forbidden, headers=h).status_code == 422


def test_trainer_created_client_is_auto_assigned(client, users, auth):
    payload = {
        "full_name": "عميل جديد", "email": "new@test.app", "password": "Passw0rd!",
        "sex": "male", "birth_date": "1990-01-01", "height_cm": 175, "trainer_id": users["trainer_b"].id,
    }
    r = client.post(f"{API}/clients", json=payload, headers=auth("trainer_a"))
    assert r.status_code == 201, r.text
    assert r.json()["profile"]["trainer_id"] == users["trainer_a"].id


# ---------------- measurements ----------------
def test_session_crud_results_and_audit(client, users, auth, db_session):
    h = auth("trainer_a")
    s = _create_session(client, h, users["client_a"].id)
    assert s["results"]["bmi"]["value"] == round(90 / 1.8**2, 1)
    assert s["results"]["bmr"] is not None and s["results"]["tdee"] is not None
    assert s["results"]["blood_pressure"]["category"] == "elevated"
    squat = next(v for v in s["values"] if v["key"] == "squat_assessment")
    assert squat["value_number"] == 3 and squat["value_text"] == "ركبة تميل للداخل"

    upd = client.put(f"{API}/sessions/{s['id']}", json=_session_payload(weight=88), headers=h)
    assert upd.status_code == 200
    assert next(v for v in upd.json()["values"] if v["key"] == "weight")["value_number"] == 88

    assert client.delete(f"{API}/sessions/{s['id']}", headers=h).status_code == 204
    assert client.get(f"{API}/sessions/{s['id']}", headers=h).status_code == 404

    db, Session = db_session
    actions = [a.action for a in Session().query(AuditLog).order_by(AuditLog.id)]
    assert actions == ["create", "update", "delete"]


def test_measurement_range_validation_in_arabic(client, users, auth):
    bad = {"session_date": TODAY, "values": [{"key": "weight", "value_number": 500}]}
    r = client.post(f"{API}/clients/{users['client_a'].id}/sessions", json=bad, headers=auth("trainer_a"))
    assert r.status_code == 422
    assert r.json()["code"] == "OUT_OF_RANGE"
    assert "الوزن" in r.json()["detail"]

    bp = {"session_date": TODAY, "values": [{"key": "blood_pressure", "systolic": 120}]}
    r = client.post(f"{API}/clients/{users['client_a'].id}/sessions", json=bp, headers=auth("trainer_a"))
    assert r.status_code == 422


def test_future_session_date_rejected(client, users, auth):
    future = (date.today() + timedelta(days=10)).isoformat()
    r = client.post(
        f"{API}/clients/{users['client_a'].id}/sessions",
        json={"session_date": future, "values": []},
        headers=auth("trainer_a"),
    )
    assert r.status_code == 422
    assert "المستقبل" in r.json()["detail"]


def test_progress_and_summary(client, users, auth):
    h = auth("trainer_a")
    cid = users["client_a"].id
    old = (date.today() - timedelta(days=30)).isoformat()
    client.post(f"{API}/clients/{cid}/sessions", json=_session_payload(weight=95, session_date=old), headers=h)
    _create_session(client, h, cid, weight=90)

    p = client.get(f"{API}/clients/{cid}/progress?keys=weight,bmi,blood_pressure", headers=auth("client_a")).json()
    w = p["series"]["weight"]
    assert [pt["value"] for pt in w["points"]] == [95, 90]
    assert w["change"] == -5
    assert w["trend"] == "good"  # client goal is fat_loss
    assert p["series"]["bmi"]["points"]
    assert p["series"]["blood_pressure"]["points"][0]["diastolic"] == 78

    s = client.get(f"{API}/clients/{cid}/summary", headers=h).json()
    assert s["sessions_count"] == 2
    weight = next(v for v in s["latest_values"] if v["key"] == "weight")
    assert weight["change"] == -5 and weight["trend"] == "good"
    assert s["results"]["tdee"] is not None


# ---------------- comments & questions ----------------
def test_comment_visible_to_client(client, users, auth):
    s = _create_session(client, auth("trainer_a"), users["client_a"].id)
    r = client.post(
        f"{API}/clients/{users['client_a'].id}/comments",
        json={"body": "عمل رائع", "session_id": s["id"]},
        headers=auth("trainer_a"),
    )
    assert r.status_code == 201
    detail = client.get(f"{API}/sessions/{s['id']}", headers=auth("client_a")).json()
    assert [c["body"] for c in detail["comments"]] == ["عمل رائع"]


def test_comment_session_must_belong_to_client(client, users, auth):
    s = _create_session(client, auth("trainer_b"), users["client_b"].id)
    r = client.post(
        f"{API}/clients/{users['client_a'].id}/comments",
        json={"body": "x", "session_id": s["id"]},
        headers=auth("trainer_a"),
    )
    assert r.status_code == 404


def test_question_reply_flow(client, users, auth):
    cid = users["client_a"].id
    q = client.post(f"{API}/clients/{cid}/questions", json={"body": "هل أزيد البروتين؟"}, headers=auth("client_a"))
    assert q.status_code == 201
    qid = q.json()["id"]

    # trainers cannot ask on behalf of the client; another client cannot ask for this one
    assert client.post(f"{API}/clients/{cid}/questions", json={"body": "x"}, headers=auth("trainer_a")).status_code == 403
    assert client.post(f"{API}/clients/{cid}/questions", json={"body": "x"}, headers=auth("client_b")).status_code == 404

    inbox = client.get(f"{API}/trainer/questions?status=open", headers=auth("trainer_a")).json()
    assert [x["id"] for x in inbox] == [qid]
    assert client.get(f"{API}/trainer/questions", headers=auth("trainer_b")).json() == []
    assert client.post(f"{API}/questions/{qid}/replies", json={"body": "x"}, headers=auth("trainer_b")).status_code == 404

    r = client.post(f"{API}/questions/{qid}/replies", json={"body": "نعم، 1.6 جم لكل كجم"}, headers=auth("trainer_a"))
    assert r.json()["status"] == "answered"

    mine = client.get(f"{API}/clients/{cid}/questions", headers=auth("client_a")).json()
    assert mine[0]["replies"][0]["body"] == "نعم، 1.6 جم لكل كجم"

    follow = client.post(f"{API}/questions/{qid}/replies", json={"body": "شكراً"}, headers=auth("client_a"))
    assert follow.json()["status"] == "open"

    closed = client.patch(f"{API}/questions/{qid}", json={"status": "closed"}, headers=auth("trainer_a"))
    assert closed.json()["status"] == "closed"
    assert client.patch(f"{API}/questions/{qid}", json={"status": "open"}, headers=auth("client_a")).status_code == 403


# ---------------- admin ----------------
def test_admin_assign_and_soft_delete(client, users, auth):
    h = auth("admin")
    cid = users["client_a"].id
    r = client.patch(f"{API}/admin/clients/{cid}/assign-trainer", json={"trainer_id": users["trainer_b"].id}, headers=h)
    assert r.status_code == 200 and r.json()["profile"]["trainer_id"] == users["trainer_b"].id
    # trainer A lost access, trainer B gained it
    assert client.get(f"{API}/clients/{cid}", headers=auth("trainer_a")).status_code == 404
    assert client.get(f"{API}/clients/{cid}", headers=auth("trainer_b")).status_code == 200

    assert client.delete(f"{API}/admin/users/{cid}", headers=h).status_code == 204
    assert client.get(f"{API}/admin/users/{cid}", headers=h).status_code == 404
    login = client.post(f"{API}/auth/login", json={"email": "ca@test.app", "password": "Passw0rd!"})
    assert login.status_code == 401


def test_admin_stats_and_settings(client, users, auth):
    h = auth("admin")
    _create_session(client, auth("trainer_a"), users["client_a"].id)
    stats = client.get(f"{API}/admin/stats", headers=h).json()
    assert stats["trainers"] == 2 and stats["clients"] == 2 and stats["measurements_this_month"] == 1

    factors = client.get(f"{API}/admin/activity-factors", headers=h).json()
    moderate = next(f for f in factors if f["key"] == "moderate")
    r = client.patch(f"{API}/admin/activity-factors/{moderate['id']}", json={"factor": 1.55}, headers=h)
    assert r.json()["factor"] == 1.55

    defs = client.get(f"{API}/admin/measurement-definitions", headers=h).json()
    pulse = next(d for d in defs if d["key"] == "pulse")
    r = client.patch(f"{API}/admin/measurement-definitions/{pulse['id']}", json={"is_active": False}, headers=h)
    assert r.json()["is_active"] is False
    active = client.get(f"{API}/measurement-definitions", headers=auth("trainer_a")).json()
    assert "pulse" not in {d["key"] for d in active}


# ---------------- calculator ----------------
def test_calculator_endpoint(client, users, auth):
    r = client.post(
        f"{API}/calculate/bmr-tdee",
        json={"sex": "male", "age": 30, "weight": 80, "height": 180, "activity_key": "moderate"},
        headers=auth("client_a"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bmr"] == 1780 and body["tdee"] == 2670
    assert body["targets"] == {"maintenance": 2670, "fat_loss": 2170, "muscle_gain": 2970}
