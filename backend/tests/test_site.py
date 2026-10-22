import copy

from app.db.reference_data import DEFAULT_HOME

API = "/api/v1"


def test_public_endpoints_need_no_login(client, users):
    site = client.get(f"{API}/public/site")
    assert site.status_code == 200
    home = site.json()["home"]
    assert home["hero_title_ar"] and home["hero_title_en"] and len(home["features"]) == 5
    factors = client.get(f"{API}/public/activity-factors").json()
    assert [f["key"] for f in factors][:2] == ["sedentary", "light"] and factors[0]["name_en"] == "Sedentary"
    settings = {s["goal"]: s for s in client.get(f"{API}/public/nutrition-settings").json()}
    assert settings["weight_gain"]["calorie_adjustment"] == 500
    assert len(client.get(f"{API}/public/plans").json()) == 4
    # player-only data still needs login
    assert client.get(f"{API}/activity-factors").status_code == 401


def test_admin_edits_home_content(client, users, auth):
    body = copy.deepcopy(DEFAULT_HOME)
    body["hero_title_en"] = "Train smarter"
    body["contact"] = {"phone": "+966 50 000 0000", "whatsapp": "+966500000000", "email": "hello@tahadi.app"}
    r = client.put(f"{API}/admin/site/home", json=body, headers=auth("admin"))
    assert r.status_code == 200
    home = client.get(f"{API}/public/site").json()["home"]
    assert home["hero_title_en"] == "Train smarter" and home["contact"]["email"] == "hello@tahadi.app"


def test_home_content_permissions_and_validation(client, users, auth):
    body = copy.deepcopy(DEFAULT_HOME)
    assert client.put(f"{API}/admin/site/home", json=body, headers=auth("trainer_a")).status_code == 403
    assert client.put(f"{API}/admin/site/home", json=body).status_code == 401
    bad = copy.deepcopy(DEFAULT_HOME)
    bad["contact"]["email"] = "not-an-email"
    assert client.put(f"{API}/admin/site/home", json=bad, headers=auth("admin")).status_code == 422
    missing = copy.deepcopy(DEFAULT_HOME)
    missing["features"] = missing["features"][:3]
    assert client.put(f"{API}/admin/site/home", json=missing, headers=auth("admin")).status_code == 422
    xss = copy.deepcopy(DEFAULT_HOME)
    xss["contact"]["phone"] = "<script>"
    assert client.put(f"{API}/admin/site/home", json=xss, headers=auth("admin")).status_code == 422
