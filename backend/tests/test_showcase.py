"""The showcase seed (coach عيشه الزهراني + trainee هيا العمري) and, in Docker/CI, every PDF the coach can export for her."""
import os

import pytest

from app.db import seed_showcase
from app.models import User

API = "/api/v1"
PW = "Showcase-Test-1"


@pytest.fixture()
def seeded(db_session, monkeypatch):
    _, Session = db_session
    monkeypatch.setattr(seed_showcase, "get_sessionmaker", lambda: Session)
    monkeypatch.setenv("SHOWCASE_PASSWORD", PW)
    assert seed_showcase.main() == 0
    return Session


def _login(client, email):
    r = client.post(f"{API}/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_showcase_seed(client, seeded, monkeypatch):
    db = seeded()
    trainee = db.query(User).filter_by(email=seed_showcase.TRAINEE["email"]).one()
    coach = db.query(User).filter_by(email=seed_showcase.COACH["email"]).one()
    assert trainee.profile.trainer_id == coach.id

    t = _login(client, seed_showcase.TRAINEE["email"])
    assert client.get(f"{API}/onboarding", headers=t).json()["complete"] is True
    assert len(client.get(f"{API}/clients/{trainee.id}/sessions", headers=t).json()) == 7
    c = _login(client, seed_showcase.COACH["email"])
    assert [x["full_name"] for x in client.get(f"{API}/clients", headers=c).json()] == [seed_showcase.TRAINEE["full_name"]]

    assert seed_showcase.main() == 0  # second run changes nothing
    assert db.query(User).filter(User.email.in_([coach.email, trainee.email])).count() == 2
    monkeypatch.setenv("SHOWCASE_PASSWORD", "short")
    assert seed_showcase.main() == 1


def test_showcase_pdfs(client, seeded):
    """Real rendering of every PDF the coach can export for her trainee (Docker / CI only)."""
    pytest.importorskip("weasyprint", exc_type=OSError, reason="needs Pango (runs in Docker)")
    db = seeded()
    trainee = db.query(User).filter_by(email=seed_showcase.TRAINEE["email"]).one()
    cid, coach = trainee.id, _login(client, seed_showcase.COACH["email"])
    sessions = client.get(f"{API}/clients/{cid}/sessions", headers=coach).json()
    program = client.get(f"{API}/clients/{cid}/programs", headers=coach).json()
    program_id = (program[0] if isinstance(program, list) else program["items"][0])["id"]
    docs = client.get(f"{API}/clients/{cid}/documents", headers=coach).json()
    p = trainee.profile
    calc = {"sex": p.sex, "age": 30, "weight": 73.5, "height": p.height_cm, "activity_key": p.activity_key, "goal": "weight_loss", "client_id": cid}

    out = os.environ.get("PDF_SAMPLES_DIR")
    for lang in ("ar", "en"):
        responses = {
            "1_measurements": client.get(f"{API}/pdf/measurements/{cid}?lang={lang}&keys=weight,waist,body_fat,bmi", headers=coach),
            "2_session": client.get(f"{API}/pdf/session/{sessions[0]['id']}?lang={lang}", headers=coach),
            "3_program": client.get(f"{API}/pdf/program/{program_id}?lang={lang}", headers=coach),
            "4_calculator": client.post(f"{API}/pdf/calculator?lang={lang}", json=calc, headers=coach),
            **{f"5_{d['kind']}": client.get(f"{API}/pdf/documents/{d['id']}?lang={lang}", headers=coach) for d in docs},
        }
        for name, r in responses.items():
            assert r.status_code == 200, (name, lang, r.text[:300])
            assert r.content.startswith(b"%PDF"), (name, lang)
            if out:
                os.makedirs(os.path.join(out, "showcase"), exist_ok=True)
                with open(os.path.join(out, "showcase", f"{name}_{lang}.pdf"), "wb") as fh:
                    fh.write(r.content)
