"""Direct, self-contained test for demo endpoints:
- GET /summary/{client}
- POST /telegram
- POST /draft/{client}
- POST /draft/{client}/approve
- POST /draft/{client}/reject
- POST /form_checks
"""

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.db.session import get_db
from app.models.base import Base
from app.models.demo import DemoMeasurement, DemoFormCheck, DemoDraft
from app.routers import telegram


@pytest.fixture()
def demo_client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    app = FastAPI()
    app.include_router(telegram.router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client


def test_summary_and_seed(demo_client):
    r = demo_client.get("/summary/Ahmed%20Al-Rashidi")
    assert r.status_code == 200
    data = r.json()
    assert data["client"] == "Ahmed Al-Rashidi"
    assert "summary" in data
    assert "measurements" in data
    assert len(data["measurements"]) == 4


def test_telegram_webhook(demo_client):
    payload = {"message": "weight 82", "client": "Ahmed Al-Rashidi", "chat_id": 111001}
    r = demo_client.post("/telegram", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["weight_kg"] == 82.0

    # Verify measurement appeared
    r_sum = demo_client.get("/summary/Ahmed%20Al-Rashidi")
    assert any(m["weight_kg"] == 82.0 for m in r_sum.json()["measurements"])


def test_draft_workflow(demo_client):
    r_draft = demo_client.post("/draft/Ahmed%20Al-Rashidi")
    assert r_draft.status_code == 200
    assert r_draft.json()["status"] == "pending"

    r_app = demo_client.post("/draft/Ahmed%20Al-Rashidi/approve", json={"text": "Approved custom text"})
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "approved"

    r_rej = demo_client.post("/draft/Ahmed%20Al-Rashidi/reject")
    assert r_rej.status_code == 200
    assert r_rej.json()["status"] == "rejected"


def test_form_checks(demo_client):
    r = demo_client.post("/form_checks", json={"client": "Ahmed Al-Rashidi", "reps": 7, "errors": "Go lower"})
    assert r.status_code == 200
    assert r.json()["reps"] == 7

    r2 = demo_client.get("/form_checks?client=Ahmed%20Al-Rashidi")
    assert r2.status_code == 200
    assert len(r2.json()) == 1
