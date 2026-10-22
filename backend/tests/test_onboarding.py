from datetime import date, timedelta

from app.services import onboarding as svc

API = "/api/v1"
PDF = b"%PDF-1.4\n% test report\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


# ---------------- pure helpers ----------------
def test_end_date_months():
    assert svc.end_date_for(date(2026, 10, 22), 1) == date(2026, 11, 21)
    assert svc.end_date_for(date(2026, 1, 31), 1) == date(2026, 2, 27)  # Feb has 28 days in 2026
    assert svc.end_date_for(date(2026, 10, 22), 12) == date(2027, 10, 21)


def test_name_normalization_for_signatures():
    assert svc.normalize_name("  أحمد   المحمد ") == svc.normalize_name("احمد المحمد")
    assert svc.normalize_name("فاطِمة") == svc.normalize_name("فاطمه")
    assert svc.normalize_name("Sara  Ali") == svc.normalize_name("sara ali")
    assert svc.normalize_name("Sara Ali") != svc.normalize_name("Sara")


# ---------------- helpers ----------------
def _new_player(client, auth_headers, name="لاعب جديد", email="new@test.app"):
    body = {"full_name": name, "email": email, "password": "Passw0rd!", "sex": "male", "birth_date": "1992-05-01", "height_cm": 176}
    r = client.post(f"{API}/clients", json=body, headers=auth_headers)
    assert r.status_code == 201, r.text
    login = client.post(f"{API}/auth/login", json={"email": email, "password": "Passw0rd!"}).json()
    return r.json()["id"], {"Authorization": f"Bearer {login['access_token']}"}


def _step1(client, h, plan_id=1, start=None):
    return client.post(f"{API}/onboarding/subscription", json={"plan_id": plan_id, "start_date": (start or date.today()).isoformat()}, headers=h)


def _step2(client, h, name="لاعب جديد", **extra):
    tid = client.get(f"{API}/onboarding/disclaimer", headers=h).json()["template_id"]
    body = {"has_chronic": False, "template_id": tid, "typed_name": name, "agreed": True, **extra}
    return client.post(f"{API}/onboarding/health", json=body, headers=h)


def _step3(client, h, name="لاعب جديد"):
    tid = client.get(f"{API}/onboarding/contract", headers=h).json()["template_id"]
    return client.post(f"{API}/onboarding/contract", json={"template_id": tid, "typed_name": name, "agreed": True}, headers=h)


# ---------------- the wizard ----------------
def test_new_player_is_gated_until_all_steps_done(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"))
    blocked = client.get(f"{API}/clients/{cid}/summary", headers=h)
    assert blocked.status_code == 403 and blocked.json()["code"] == "ONBOARDING_REQUIRED"
    assert client.get(f"{API}/auth/me", headers=h).status_code == 200  # login/profile still work
    st = client.get(f"{API}/onboarding", headers=h).json()
    assert st["step"] == 1 and len(st["plans"]) == 4 and st["coach_name"] == "مدرب أ"

    # step order is enforced
    assert client.get(f"{API}/onboarding/contract", headers=h).status_code == 409

    # start date can't be in the past
    assert _step1(client, h, start=date.today() - timedelta(days=1)).status_code == 422
    sub = _step1(client, h, plan_id=2).json()
    assert sub["months"] == 3 and sub["end_date"] == svc.end_date_for(date.today(), 3).isoformat()
    assert _step1(client, h).status_code == 409  # only the coach can change it afterwards

    # step 2: name must match the account name; no file needed
    dis = client.get(f"{API}/onboarding/disclaimer", headers=h).json()
    assert "لاعب جديد" in dis["text"] and "مدرب أ" in dis["text"]
    bad = _step2(client, h, name="someone else")
    assert bad.status_code == 422 and bad.json()["code"] == "NAME_MISMATCH"
    assert _step2(client, h, name="  لاعب   جديد ").json()["step"] == 3

    # step 3: contract text has the plan and dates filled in
    c = client.get(f"{API}/onboarding/contract", headers=h).json()
    assert "3 أشهر" in c["text"] and sub["end_date"] in c["text"] and "{" not in c["text"]
    assert _step3(client, h).json()["complete"] is True
    assert client.get(f"{API}/clients/{cid}/summary", headers=h).status_code == 200

    docs = client.get(f"{API}/clients/{cid}/documents", headers=auth("trainer_a")).json()
    assert {d["kind"] for d in docs} == {"contract", "disclaimer"}
    contract = next(d for d in docs if d["kind"] == "contract")
    assert contract["typed_name"] == "لاعب جديد" and contract["template_version"] == 1 and contract["ip_address"]


def test_english_contract_and_signature(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"), name="Sara Ali", email="sara@test.app")
    en = {**h, "Accept-Language": "en"}
    _step1(client, en)
    _step2(client, en, name="sara ali")
    c = client.get(f"{API}/onboarding/contract", headers=en).json()
    assert c["language"] == "en" and "1 month" in c["text"] and "Party two (Client): Sara Ali" in c["text"]
    assert _step3(client, en, name="Sara Ali").status_code == 201
    doc = next(d for d in client.get(f"{API}/clients/{cid}/documents", headers=en).json() if d["kind"] == "contract")
    assert doc["language"] == "en"


def test_template_edit_does_not_change_signed_documents(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"))
    _step1(client, h)
    _step2(client, h)
    stale = client.get(f"{API}/onboarding/contract", headers=h).json()["template_id"]
    # admin publishes version 2 while the player has the page open
    new = {"kind": "contract", "body_ar": "عقد جديد {client_name} – النسخة الثانية", "body_en": "New contract {client_name} – version 2"}
    v2 = client.post(f"{API}/admin/templates", json=new, headers=auth("admin")).json()
    assert v2["version"] == 2
    r = client.post(f"{API}/onboarding/contract", json={"template_id": stale, "typed_name": "لاعب جديد", "agreed": True}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "TEMPLATE_CHANGED"
    assert _step3(client, h).status_code == 201
    signed = next(d for d in client.get(f"{API}/clients/{cid}/documents", headers=h).json() if d["kind"] == "contract")
    assert signed["template_version"] == 2 and "النسخة الثانية" in signed["rendered_text"]

    # version 3 later: the signed text stays exactly as it was
    client.post(f"{API}/admin/templates", json={**new, "body_ar": "نسخة ثالثة {client_name}"}, headers=auth("admin"))
    again = client.get(f"{API}/documents/{signed['id']}", headers=h).json()
    assert again["rendered_text"] == signed["rendered_text"]
    versions = client.get(f"{API}/admin/templates?kind=contract", headers=auth("admin")).json()["versions"]
    assert [v["version"] for v in versions] == [3, 2, 1] and [v["is_active"] for v in versions] == [True, False, False]


def test_renewal_requires_new_contract_but_extension_does_not(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"))
    _step1(client, h), _step2(client, h), _step3(client, h)
    coach = auth("trainer_a")
    sub = client.get(f"{API}/clients/{cid}/subscriptions", headers=coach).json()["current"]
    ext = client.patch(f"{API}/subscriptions/{sub['id']}", json={"end_date": (date.today() + timedelta(days=60)).isoformat()}, headers=coach)
    assert ext.status_code == 200
    assert client.get(f"{API}/clients/{cid}/summary", headers=h).status_code == 200  # still fine

    r = client.post(f"{API}/clients/{cid}/subscriptions", json={"plan_id": 3, "start_date": date.today().isoformat(), "kind": "renewal"}, headers=coach)
    assert r.status_code == 201
    assert client.get(f"{API}/clients/{cid}/summary", headers=h).json()["code"] == "ONBOARDING_REQUIRED"
    assert client.get(f"{API}/onboarding", headers=h).json()["step"] == 3
    assert _step3(client, h).status_code == 201
    subs = client.get(f"{API}/clients/{cid}/subscriptions", headers=coach).json()
    assert len(subs["history"]) == 2 and all(s["contract_signed"] for s in subs["history"])
    # players can't manage subscriptions
    assert client.post(f"{API}/clients/{cid}/subscriptions", json={"plan_id": 1, "start_date": date.today().isoformat()}, headers=h).status_code == 403
    assert client.patch(f"{API}/subscriptions/{sub['id']}", json={"end_date": date.today().isoformat()}, headers=h).status_code == 403


# ---------------- health & files ----------------
def test_chronic_condition_with_file_privacy(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"))
    _step1(client, h)
    # file checks: content, not extension
    fake = client.post(f"{API}/onboarding/files", files={"file": ("report.pdf", b"MZ\x90\x00not a pdf", "application/pdf")}, headers=h)
    assert fake.status_code == 422 and fake.json()["code"] == "FILE_TYPE"
    big = client.post(f"{API}/onboarding/files", files={"file": ("big.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024), "application/pdf")}, headers=h)
    assert big.status_code == 413
    f1 = client.post(f"{API}/onboarding/files", files={"file": ("تقرير.pdf", PDF, "application/pdf")}, headers=h).json()
    f2 = client.post(f"{API}/onboarding/files", files={"file": ("scan.png", PNG, "image/png")}, headers=h).json()
    assert f1["content_type"] == "application/pdf" and f2["content_type"] == "image/png"
    client.post(f"{API}/onboarding/files", files={"file": ("c.pdf", PDF, "application/pdf")}, headers=h)
    fourth = client.post(f"{API}/onboarding/files", files={"file": ("d.pdf", PDF, "application/pdf")}, headers=h)
    assert fourth.status_code == 422 and fourth.json()["code"] == "TOO_MANY_FILES"

    # "yes" requires the condition and details
    assert _step2(client, h, has_chronic=True).status_code == 422
    ok = _step2(client, h, has_chronic=True, conditions=["diabetes", "joint_back"], details="Type 2, controlled", file_ids=[f1["id"], f2["id"]])
    assert ok.status_code == 201

    coach = auth("trainer_a")
    health = client.get(f"{API}/clients/{cid}/health", headers=coach).json()
    assert health["current"]["has_chronic"] and len(health["current"]["files"]) == 2
    card = next(c for c in client.get(f"{API}/clients", headers=coach).json() if c["id"] == cid)
    assert card["has_chronic"] is True

    url = client.get(f"{API}/files/{f1['id']}/url", headers=coach).json()
    assert url["expires_in"] == 300
    got = client.get(url["url"].replace("http://testserver", ""))  # local dev storage: signed backend link
    assert got.status_code == 200 and got.content == PDF
    tampered = client.get(url["url"].replace("http://testserver", "").replace("token=", "token=0"))
    assert tampered.status_code == 403

    # another coach / another player can't see it
    assert client.get(f"{API}/files/{f1['id']}/url", headers=auth("trainer_b")).status_code == 404
    assert client.get(f"{API}/clients/{cid}/health", headers=auth("trainer_b")).status_code == 404
    assert client.get(f"{API}/files/{f1['id']}/url", headers=auth("client_a")).status_code == 404


def test_health_update_badge_and_review(client, users, auth):
    cid, h = _new_player(client, auth("trainer_a"))
    _step1(client, h), _step2(client, h), _step3(client, h)
    coach = auth("trainer_a")
    card = lambda: next(c for c in client.get(f"{API}/clients", headers=coach).json() if c["id"] == cid)  # noqa: E731
    assert card()["health_update_pending"] is False
    r = client.post(f"{API}/me/health-declaration", json={"has_chronic": True, "conditions": ["asthma"], "details": "Seasonal"}, headers=h)
    assert r.status_code == 201
    assert card()["health_update_pending"] is True and card()["has_chronic"] is True
    hist = client.get(f"{API}/clients/{cid}/health", headers=coach).json()
    assert len(hist["history"]) == 2 and hist["needs_review"] is True  # previous version kept
    client.post(f"{API}/clients/{cid}/health/review", headers=coach)
    assert card()["health_update_pending"] is False


def test_plans_admin_and_public(client, users, auth):
    assert len(client.get(f"{API}/public/plans").json()) == 4  # no login needed
    r = client.patch(f"{API}/admin/plans/1", json={"price": 299}, headers=auth("admin"))
    assert r.status_code == 200 and r.json()["price"] == 299
    assert client.patch(f"{API}/admin/plans/1", json={"price": 1}, headers=auth("trainer_a")).status_code == 403
    client.patch(f"{API}/admin/plans/4", json={"is_active": False}, headers=auth("admin"))
    assert len(client.get(f"{API}/public/plans").json()) == 3


def test_supabase_storage_requests(monkeypatch):
    """Shape of the Supabase Storage calls (no network): private bucket, secret key, 5-minute signed URL."""
    from app.core.config import settings
    from app.services import storage

    calls = []

    class Resp:
        def __init__(self, payload=None, code=200):
            self.status_code, self._p = code, payload or {}

        def json(self):
            return self._p

    def fake_post(url, **kw):
        calls.append((url, kw))
        if "/object/sign/" in url:
            return Resp({"signedURL": "/object/sign/medical-files/clients/7/x.pdf?token=abc"})
        return Resp({"Key": "medical-files/clients/7/x.pdf"})

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setattr(storage.httpx, "post", fake_post)

    storage.save("clients/7/x.pdf", PDF, "application/pdf")
    url = storage.signed_url("clients/7/x.pdf", "http://api")
    upload, sign = calls
    assert upload[0] == "https://proj.supabase.co/storage/v1/object/medical-files/clients/7/x.pdf"
    assert upload[1]["headers"]["apikey"] == "sb_secret_test" and upload[1]["headers"]["x-upsert"] == "false"
    assert sign[0] == "https://proj.supabase.co/storage/v1/object/sign/medical-files/clients/7/x.pdf"
    assert sign[1]["json"] == {"expiresIn": 300}
    assert url == "https://proj.supabase.co/storage/v1/object/sign/medical-files/clients/7/x.pdf?token=abc"
