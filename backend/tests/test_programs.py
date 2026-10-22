from datetime import date, timedelta
from types import SimpleNamespace

from app.services import programs as svc

API = "/api/v1"
TODAY = date.today()


# ---------------- pure logic ----------------
def _prog(start, weeks=4, days=()):
    return SimpleNamespace(
        start_date=start,
        weeks=weeks,
        days=[SimpleNamespace(id=i + 1, day_number=dn, week_number=wk) for i, (dn, wk) in enumerate(days)],
    )


def test_today_position_repeating_and_specific_week():
    start = date(2026, 1, 5)
    p = _prog(start, weeks=4, days=[(1, None), (3, None), (3, 2)])  # ids 1, 2, 3
    assert svc.today_position(p, start)["day_id"] == 1  # week 1 day 1
    assert svc.today_position(p, start + timedelta(days=2))["day_id"] == 2  # week 1 day 3 (repeating)
    pos = svc.today_position(p, start + timedelta(days=9))  # week 2 day 3 → week-specific wins
    assert (pos["week"], pos["day_number"], pos["day_id"]) == (2, 3, 3)
    assert svc.today_position(p, start + timedelta(days=1))["day_id"] is None  # rest (no day 2)


def test_today_position_before_and_after():
    start = date(2026, 1, 5)
    p = _prog(start, weeks=2, days=[(1, None)])
    before = svc.today_position(p, start - timedelta(days=3))
    assert before["state"] == "not_started" and before["starts_in_days"] == 3
    assert svc.today_position(p, start + timedelta(days=14))["state"] == "finished"


def test_hr_zones_from_age():
    assert svc.max_heart_rate(30) == 190
    assert svc.hr_target(30, 3) == {"zone": 3, "min_bpm": 133, "max_bpm": 152, "pct": [70, 80]}
    assert svc.hr_target(None, 3) is None


# ---------------- API ----------------
def _program_body(start=None, **extra):
    return {
        "title": "Strength block",
        "goal": "Fat loss",
        "start_date": (start or TODAY).isoformat(),
        "weeks": 4,
        "days_per_week": 3,
        "days": [
            {
                "day_number": 1,
                "title": "Day 1: Chest & Triceps",
                "warmup": "5 min bike",
                "items": [
                    {"kind": "resistance", "exercise_id": 1, "sets": 4, "reps": "8–12", "load_value": 70, "load_unit": "pct_1rm", "rest_seconds": 90},
                    {"kind": "resistance", "custom_name": "Band pull-apart", "sets": 3, "reps": "15"},
                    {"kind": "cardio", "cardio_type": "hiit", "duration_min": 12, "hr_zone": 4, "work_seconds": 30, "interval_rest_seconds": 30, "rounds": 10},
                ],
            },
            {"day_number": 2, "title": "Rest", "is_rest": True},
            {"day_number": 3, "title": "Day 2: Legs", "items": [{"kind": "resistance", "exercise_id": 25, "sets": 5, "reps": "5"}]},
        ],
        **extra,
    }


def _create(client, headers, client_id, **kw):
    r = client.post(f"{API}/clients/{client_id}/programs", json=_program_body(**kw), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_builder_flow_and_client_view(client, users, auth):
    cid = users["client_a"].id
    coach = auth("trainer_a")
    p = _create(client, coach, cid)
    assert p["status"] == "draft" and len(p["days"]) == 3
    first = p["days"][0]["items"]
    assert first[0]["reps"] == "8-12" and first[0]["exercise_name_en"] == "Barbell bench press"
    assert first[2]["hr_target"]["zone"] == 4  # client A born 1995 → HR targets shown

    player = auth("client_a")
    # drafts are invisible to the player
    assert client.get(f"{API}/programs/{p['id']}", headers=player).status_code == 404
    assert client.get(f"{API}/clients/{cid}/programs", headers=player).json() == []
    assert client.get(f"{API}/clients/{cid}/program/current", headers=player).json() is None

    act = client.post(f"{API}/programs/{p['id']}/activate", headers=coach)
    assert act.status_code == 200 and act.json()["status"] == "active"
    cur = client.get(f"{API}/clients/{cid}/program/current", headers=player).json()
    assert cur["id"] == p["id"] and cur["today"]["state"] == "running"
    assert cur["today"]["day_id"] == cur["days"][0]["id"]  # started today → day 1

    # a second program replaces it; the first is archived and stays viewable
    p2 = _create(client, coach, cid, title="Block 2")
    client.post(f"{API}/programs/{p2['id']}/activate", headers=coach)
    assert client.get(f"{API}/programs/{p['id']}", headers=player).json()["status"] == "archived"
    statuses = {x["id"]: x["status"] for x in client.get(f"{API}/clients/{cid}/programs", headers=coach).json()}
    assert statuses == {p["id"]: "archived", p2["id"]: "active"}


def test_player_cannot_write_programs(client, users, auth):
    cid = users["client_a"].id
    p = _create(client, auth("trainer_a"), cid)
    client.post(f"{API}/programs/{p['id']}/activate", headers=auth("trainer_a"))
    player = auth("client_a")
    body = _program_body()
    assert client.post(f"{API}/clients/{cid}/programs", json=body, headers=player).status_code == 403
    assert client.put(f"{API}/programs/{p['id']}", json=body, headers=player).status_code == 403
    assert client.delete(f"{API}/programs/{p['id']}", headers=player).status_code == 403
    assert client.post(f"{API}/programs/{p['id']}/activate", headers=player).status_code == 403
    assert client.post(f"{API}/programs/{p['id']}/archive", headers=player).status_code == 403
    assert client.post(f"{API}/programs/{p['id']}/duplicate", json={"as_template": True}, headers=player).status_code == 403
    assert client.get(f"{API}/exercises", headers=player).status_code == 403
    assert client.get(f"{API}/program-templates", headers=player).status_code == 403


def test_other_trainer_gets_404(client, users, auth):
    p = _create(client, auth("trainer_a"), users["client_a"].id)
    other = auth("trainer_b")
    assert client.get(f"{API}/programs/{p['id']}", headers=other).status_code == 404
    assert client.put(f"{API}/programs/{p['id']}", json=_program_body(), headers=other).status_code == 404
    assert client.get(f"{API}/clients/{users['client_a'].id}/programs", headers=other).status_code == 404
    # cannot duplicate into a client that is not theirs either
    own = _create(client, other, users["client_b"].id)
    r = client.post(f"{API}/programs/{own['id']}/duplicate", json={"client_id": users["client_a"].id}, headers=other)
    assert r.status_code == 404


def test_validation_messages(client, users, auth):
    cid, coach = users["client_a"].id, auth("trainer_a")
    bad_reps = _program_body()
    bad_reps["days"][0]["items"][0]["reps"] = "lots"
    assert client.post(f"{API}/clients/{cid}/programs", json=bad_reps, headers=coach).status_code == 422
    bad_url = _program_body()
    bad_url["days"][0]["items"][0]["video_url"] = "javascript:alert(1)"
    r = client.post(f"{API}/clients/{cid}/programs", json=bad_url, headers=coach)
    assert r.status_code == 422 and "http" in r.json()["detail"]
    dup_day = _program_body()
    dup_day["days"][1]["day_number"] = 1
    assert client.post(f"{API}/clients/{cid}/programs", json=dup_day, headers=coach).status_code == 422
    no_name = _program_body()
    no_name["days"][0]["items"] = [{"kind": "resistance", "sets": 3}]
    assert client.post(f"{API}/clients/{cid}/programs", json=no_name, headers=coach).status_code == 422
    empty = client.post(f"{API}/clients/{cid}/programs", json={"title": "Empty", "start_date": TODAY.isoformat()}, headers=coach).json()
    r = client.post(f"{API}/programs/{empty['id']}/activate", headers=coach)
    assert r.status_code == 422 and r.json()["code"] == "EMPTY_PROGRAM"


def test_templates_duplicate_and_delete_rules(client, users, auth):
    coach_a, coach_b = auth("trainer_a"), auth("trainer_b")
    p = _create(client, coach_a, users["client_a"].id)
    tpl = client.post(f"{API}/programs/{p['id']}/duplicate", json={"as_template": True, "title": "Beginner 3-day"}, headers=coach_a).json()
    assert tpl["is_template"] and tpl["client_id"] is None and tpl["start_date"] is None and len(tpl["days"]) == 3
    # templates are shared for reading, but only the author/admin may change them
    assert [t["title"] for t in client.get(f"{API}/program-templates", headers=coach_b).json()] == ["Beginner 3-day"]
    assert client.put(f"{API}/programs/{tpl['id']}", json=_program_body(), headers=coach_b).status_code == 403
    copy = client.post(f"{API}/programs/{tpl['id']}/duplicate", json={"client_id": users["client_b"].id}, headers=coach_b)
    assert copy.status_code == 201 and copy.json()["client_id"] == users["client_b"].id and copy.json()["status"] == "draft"
    # active programs cannot be deleted, drafts can
    client.post(f"{API}/programs/{p['id']}/activate", headers=coach_a)
    assert client.delete(f"{API}/programs/{p['id']}", headers=coach_a).status_code == 409
    assert client.delete(f"{API}/programs/{copy.json()['id']}", headers=coach_b).status_code == 204


def test_question_about_a_program_day(client, users, auth):
    cid = users["client_a"].id
    p = _create(client, auth("trainer_a"), cid)
    day_id = p["days"][0]["id"]
    player = auth("client_a")
    # draft program day → not allowed
    assert client.post(f"{API}/clients/{cid}/questions", json={"body": "?", "program_day_id": day_id}, headers=player).status_code == 404
    client.post(f"{API}/programs/{p['id']}/activate", headers=auth("trainer_a"))
    r = client.post(f"{API}/clients/{cid}/questions", json={"body": "Can I swap bench for dumbbells?", "program_day_id": day_id}, headers=player)
    assert r.status_code == 201
    assert r.json()["program_day_title"] == "Day 1: Chest & Triceps" and r.json()["program_id"] == p["id"]
    inbox = client.get(f"{API}/trainer/questions", headers=auth("trainer_a")).json()
    assert inbox[0]["program_day_id"] == day_id


def test_exercise_library_admin_only_writes(client, users, auth):
    lib = client.get(f"{API}/exercises?muscle_group=chest", headers=auth("trainer_a")).json()
    assert len(lib) == 6 and all(e["muscle_group"] == "chest" for e in lib)
    body = {"name_ar": "ضغط أرضي", "name_en": "Floor press", "muscle_group": "chest", "equipment": "barbell"}
    assert client.post(f"{API}/admin/exercises", json=body, headers=auth("trainer_a")).status_code == 403
    r = client.post(f"{API}/admin/exercises", json=body, headers=auth("admin"))
    assert r.status_code == 201
    off = client.patch(f"{API}/admin/exercises/{r.json()['id']}", json={"is_active": False}, headers=auth("admin")).json()
    assert off["is_active"] is False
    assert len(client.get(f"{API}/exercises?muscle_group=chest", headers=auth("trainer_a")).json()) == 6
