"""PDF exports.

The HTML/permission tests run everywhere (html_to_pdf is replaced by a stub that records the HTML).
test_real_pdf_render needs WeasyPrint + Pango and runs inside the Docker image.
"""
from datetime import date
from urllib.parse import unquote

import pytest

from app.models import AuditLog
from app.routers import pdf as pdf_router

API = "/api/v1"
TODAY = date.today().isoformat()


@pytest.fixture()
def captured(monkeypatch):
    seen = []

    def fake(html: str) -> bytes:
        seen.append(html)
        return b"%PDF-1.7 fake"

    monkeypatch.setattr(pdf_router, "html_to_pdf", fake)
    return seen


def _session(client, h, cid, weight, day):
    body = {"session_date": day, "values": [{"key": "weight", "value_number": weight}, {"key": "waist", "value_number": 90}]}
    assert client.post(f"{API}/clients/{cid}/sessions", json=body, headers=h).status_code == 201


def _filename(resp) -> str:
    cd = resp.headers["content-disposition"]
    assert cd.startswith("attachment;")
    return unquote(cd.split("filename*=UTF-8''", 1)[1])


def test_measurements_pdf_arabic_and_english(client, users, auth, captured, db_session):
    cid, coach = users["client_a"].id, auth("trainer_a")
    _session(client, coach, cid, 92, "2026-08-01")
    _session(client, coach, cid, 88, "2026-09-01")
    client.post(f"{API}/clients/{cid}/comments", json={"body": "استمر يا بطل"}, headers=coach)

    r = client.get(f"{API}/pdf/measurements/{cid}?keys=weight,bmi", headers=auth("client_a"))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert _filename(r) == f"tahadi_measurements_عميل-أ_{TODAY}.pdf"
    html = captured[-1]
    assert 'dir="rtl"' in html and "تقرير القياسات" in html
    assert "المدرب: <b>مدرب أ</b>" in html and "العميل: <b>عميل أ</b>" in html
    assert "صفحة" in html and "صادر من منصة تحدي" in html  # footer page counter
    assert "<svg" in html and "استمر يا بطل" in html and "2026-08-01" in html

    en = client.get(f"{API}/pdf/measurements/{cid}?lang=en&comments=false", headers=coach)
    html = captured[-1]
    assert 'dir="ltr"' in html and "Measurements report" in html and "Page" in html and "Issued by Tahadi" in html
    assert "استمر يا بطل" not in html  # comments optional
    assert en.status_code == 200

    db, Session = db_session
    actions = [(a.action, a.entity) for a in Session().query(AuditLog).filter(AuditLog.action == "export")]
    assert actions == [("export", "measurements_pdf"), ("export", "measurements_pdf")]


def test_measurements_pdf_permissions(client, users, auth, captured):
    cid = users["client_a"].id
    assert client.get(f"{API}/pdf/measurements/{cid}", headers=auth("trainer_b")).status_code == 404
    assert client.get(f"{API}/pdf/measurements/{cid}", headers=auth("client_b")).status_code == 404
    assert client.get(f"{API}/pdf/measurements/{cid}").status_code == 401


def test_program_pdf(client, users, auth, captured):
    cid, coach = users["client_a"].id, auth("trainer_a")
    body = {
        "title": "خطة القوة",
        "start_date": TODAY,
        "days": [
            {"day_number": 1, "title": "اليوم 1: صدر", "items": [
                {"kind": "resistance", "exercise_id": 1, "sets": 4, "reps": "8-12", "load_value": 60, "load_unit": "kg", "rest_seconds": 90, "video_url": "https://example.com/v"},
                {"kind": "cardio", "cardio_type": "treadmill", "duration_min": 20, "hr_zone": 2},
            ]},
        ],
    }
    p = client.post(f"{API}/clients/{cid}/programs", json=body, headers=coach).json()
    r = client.get(f"{API}/pdf/program/{p['id']}?lang=en", headers=coach)
    assert r.status_code == 200 and _filename(r).startswith("tahadi_program_")
    html = captured[-1]
    assert "Barbell bench press" in html and "8-12" in html and "Treadmill" in html and "https://example.com/v" in html
    # players can't export drafts (they can't see them)
    assert client.get(f"{API}/pdf/program/{p['id']}", headers=auth("client_a")).status_code == 404
    client.post(f"{API}/programs/{p['id']}/activate", headers=coach)
    ar = client.get(f"{API}/pdf/program/{p['id']}", headers=auth("client_a"))
    assert ar.status_code == 200 and "ضغط البنش بالبار" in captured[-1] and "البرنامج التدريبي" in captured[-1]


def test_signed_documents_pdf(client, users, auth, captured):
    # fixture players have a signed contract + disclaimer
    docs = client.get(f"{API}/clients/{users['client_a'].id}/documents", headers=auth("client_a")).json()
    html_by_kind = {}
    for d in docs:
        r = client.get(f"{API}/pdf/documents/{d['id']}", headers=auth("trainer_a"))
        assert r.status_code == 200 and _filename(r).startswith(f"tahadi_{d['kind']}_")
        html_by_kind[d["kind"]] = captured[-1]
        assert "عميل أ" in captured[-1] and "التوقيع" in captured[-1]
    disclaimer = next(d for d in docs if d["kind"] == "disclaimer")
    assert "إجابات الإقرار الصحي" in html_by_kind["disclaimer"]
    assert "إجابات الإقرار الصحي" not in html_by_kind["contract"]
    assert client.get(f"{API}/pdf/documents/{disclaimer['id']}", headers=auth("trainer_b")).status_code == 404


def test_calculator_pdf_names(client, users, auth, captured):
    body = {"sex": "male", "age": 30, "weight": 80, "height": 180, "activity_key": "moderate", "goal": "weight_loss"}
    # coach: own name + picked client
    r = client.post(f"{API}/pdf/calculator", json={**body, "client_id": users["client_a"].id}, headers=auth("trainer_a"))
    assert r.status_code == 200
    html = captured[-1]
    assert "مدرب أ" in html and "عميل أ" in html
    assert ">2170<" in html  # 2670 − 500 for weight loss
    # coach: picking someone else's client → 404; nothing chosen → 422
    assert client.post(f"{API}/pdf/calculator", json={**body, "client_id": users["client_b"].id}, headers=auth("trainer_a")).status_code == 404
    assert client.post(f"{API}/pdf/calculator", json=body, headers=auth("trainer_a")).json()["code"] == "NAMES_REQUIRED"
    # player: both names automatic
    assert client.post(f"{API}/pdf/calculator", json=body, headers=auth("client_a")).status_code == 200
    assert "مدرب أ" in captured[-1] and "عميل أ" in captured[-1]
    # admin: must type both
    assert client.post(f"{API}/pdf/calculator", json={**body, "client_name": "Sara"}, headers=auth("admin")).status_code == 422
    ok = client.post(f"{API}/pdf/calculator?lang=en", json={**body, "client_name": "Sara", "coach_name": "Khalid"}, headers=auth("admin"))
    assert ok.status_code == 200 and "Khalid" in captured[-1] and "Calorie calculator" in captured[-1]
    # not logged in → 401
    assert client.post(f"{API}/pdf/calculator", json=body).status_code == 401


def test_real_pdf_render():
    weasyprint = pytest.importorskip("weasyprint", exc_type=OSError, reason="needs Pango (runs in Docker)")
    from app.core.i18n import set_language
    from app.pdf.render import html_to_pdf, render_html

    set_language("ar")
    html = render_html("calculator.html", title_key="calculator", coach_name="خالد", client_name="سارة",
                       inputs={"sex": "female", "age": 25, "weight": 60, "height": 165}, goal="maintenance",
                       activity_name="نشاط متوسط", activity_factor=1.5, bmr=1345.25, tdee=2017.9,
                       plan={"calories": 2018, "meals_per_day": 4, "macros": {m: {"g": 1, "kcal": 1, "pct": 1} for m in ("protein", "carbs", "fat")},
                             "per_meal": {"calories": 504, "protein": 25, "carbs": 69, "fat": 14}})
    pdf = html_to_pdf(html)
    assert pdf.startswith(b"%PDF") and len(pdf) > 10_000 and weasyprint


def test_render_sample_pdfs(client, users, auth):
    """Real rendering of all five documents in Arabic and English (Docker / CI only).

    With PDF_SAMPLES_DIR set, the files are written there so they can be inspected visually.
    """
    pytest.importorskip("weasyprint", exc_type=OSError, reason="needs Pango (runs in Docker)")
    import os

    out = os.environ.get("PDF_SAMPLES_DIR")
    cid, coach, player = users["client_a"].id, auth("trainer_a"), auth("client_a")
    for day, w in (("2026-07-01", 95), ("2026-08-01", 92), ("2026-09-01", 89)):
        _session(client, coach, cid, w, day)
    client.post(f"{API}/clients/{cid}/comments", json={"body": "تقدم ممتاز، استمر على نفس البرنامج"}, headers=coach)
    client.post(f"{API}/clients/{cid}/nutrition", json={}, headers=coach)
    program = client.post(
        f"{API}/clients/{cid}/programs",
        json={
            "title": "برنامج خسارة الدهون – المرحلة 1",
            "goal": "خسارة الدهون",
            "start_date": TODAY,
            "days": [
                {"day_number": 1, "title": "اليوم 1: صدر وترايسبس", "warmup": "5 دقائق دراجة", "items": [
                    {"kind": "resistance", "exercise_id": 1, "sets": 4, "reps": "8-12", "load_value": 70, "load_unit": "pct_1rm", "rest_seconds": 90},
                    {"kind": "resistance", "custom_name": "تمرين مخصص", "sets": 3, "reps": "15"},
                    {"kind": "cardio", "cardio_type": "hiit", "duration_min": 12, "hr_zone": 4, "work_seconds": 30, "interval_rest_seconds": 30, "rounds": 10},
                ]},
                {"day_number": 2, "title": "راحة", "is_rest": True},
            ],
        },
        headers=coach,
    ).json()
    docs = client.get(f"{API}/clients/{cid}/documents", headers=player).json()
    calc = {"sex": "male", "age": 30, "weight": 80, "height": 180, "activity_key": "moderate", "goal": "weight_loss"}

    for lang in ("ar", "en"):
        responses = {
            "measurements": client.get(f"{API}/pdf/measurements/{cid}?lang={lang}&keys=weight,waist,bmi", headers=coach),
            "program": client.get(f"{API}/pdf/program/{program['id']}?lang={lang}", headers=coach),
            "calculator": client.post(f"{API}/pdf/calculator?lang={lang}", json={**calc, "client_id": cid}, headers=coach),
            **{d["kind"]: client.get(f"{API}/pdf/documents/{d['id']}?lang={lang}", headers=coach) for d in docs},
        }
        for name, r in responses.items():
            assert r.status_code == 200, (name, lang, r.text[:300])
            assert r.content.startswith(b"%PDF") and len(r.content) > 5_000, (name, lang)
            if out:
                os.makedirs(out, exist_ok=True)
                with open(os.path.join(out, f"{name}_{lang}.pdf"), "wb") as fh:
                    fh.write(r.content)
