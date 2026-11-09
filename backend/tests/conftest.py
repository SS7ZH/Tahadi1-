"""Test fixtures.

By default tests run against an in-memory SQLite database purely for speed and isolation.
Set TEST_DATABASE_URL to run the same suite against PostgreSQL, e.g.
    TEST_DATABASE_URL=postgresql://tahadi:tahadi@localhost:5432/tahadi_test pytest
"""

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, insert
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure test environment variables are set
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "var", "test-uploads"))

from app.core.security import hash_password  # noqa: E402
from app.db.reference_data import (  # noqa: E402
    DEFAULT_HOME,
    DOCUMENT_TEMPLATES,
    EXERCISES,
    NUTRITION_SETTINGS,
    SUBSCRIPTION_PLANS,
    activity_factors_v2,
    definitions_v2,
)  # noqa: E402
from app.db.session import get_db, normalize_db_url  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    ActivityFactor,
    Base,
    ClientProfile,
    DocumentTemplate,
    Exercise,
    HealthDeclaration,
    MeasurementDefinition,
    NutritionSetting,
    SignedDocument,
    SiteSetting,
    Subscription,
    SubscriptionPlan,
    User,
)  # noqa: E402
from app.routers.auth import login_limiter  # noqa: E402
from app import config  # noqa: E402

PASSWORD = "Passw0rd!"
PASSWORD_HASH = hash_password(PASSWORD)  # hash once; bcrypt is deliberately slow


def _make_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        return create_engine(normalize_db_url(url), connect_args={"prepare_threshold": None})
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@pytest.fixture()
def db_session():
    engine = _make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(ActivityFactor), activity_factors_v2())
        conn.execute(insert(MeasurementDefinition), definitions_v2())
        conn.execute(insert(NutritionSetting), NUTRITION_SETTINGS)
        conn.execute(insert(Exercise), EXERCISES)
        conn.execute(insert(SubscriptionPlan), SUBSCRIPTION_PLANS)
        conn.execute(insert(DocumentTemplate), DOCUMENT_TEMPLATES)
        conn.execute(insert(SiteSetting), [{"key": "home", "value": DEFAULT_HOME}])
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session, Session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    _, Session = db_session

    def _get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    login_limiter.reset()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def onboard(db, client, start=None):
    """Give a player a subscription, health declaration and signed disclaimer + contract."""
    start = start or date.today()
    sub = Subscription(
        client_id=client.id,
        plan_id=1,
        plan_name_ar="شهر واحد",
        plan_name_en="1 month",
        months=1,
        start_date=start,
        end_date=start + timedelta(days=29),
        kind="initial",
    )
    decl = HealthDeclaration(client_id=client.id, has_chronic=False, conditions=[])
    db.add_all([sub, decl])
    db.flush()
    for kind, sid in (("disclaimer", None), ("contract", sub.id)):
        db.add(
            SignedDocument(
                client_id=client.id,
                kind=kind,
                template_id=1 if kind == "contract" else 2,
                template_version=1,
                language="ar",
                rendered_text="test",
                typed_name=client.full_name,
                subscription_id=sid,
                health_declaration_id=decl.id if kind == "disclaimer" else None,
            )
        )
    db.commit()
    return sub


@pytest.fixture()
def users(db_session):
    """admin, trainer A with client A1, trainer B with client B1."""
    db, _ = db_session

    def mk(name, email, role, trainer=None, sex="male"):
        u = User(full_name=name, email=email, role=role, password_hash=PASSWORD_HASH)
        if role == "client":
            u.profile = ClientProfile(
                trainer_id=trainer.id if trainer else None,
                sex=sex,
                birth_date=date(1995, 1, 1),
                height_cm=180,
                goal="fat_loss",
                activity_key="moderate",
            )
        db.add(u)
        db.commit()
        return u

    admin = mk("المدير", "admin@test.app", "admin")
    trainer_a = mk("مدرب أ", "ta@test.app", "trainer")
    trainer_b = mk("مدرب ب", "tb@test.app", "trainer")
    client_a = mk("عميل أ", "ca@test.app", "client", trainer_a)
    client_b = mk("عميل ب", "cb@test.app", "client", trainer_b, sex="female")
    onboard(db, client_a)
    onboard(db, client_b)
    return {"admin": admin, "trainer_a": trainer_a, "trainer_b": trainer_b, "client_a": client_a, "client_b": client_b}


@pytest.fixture()
def auth(client, users):
    """auth("trainer_a") -> headers dict."""
    cache: dict[str, dict] = {}

    def _headers(who: str) -> dict:
        if who not in cache:
            r = client.post("/api/v1/auth/login", json={"email": users[who].email, "password": PASSWORD})
            assert r.status_code == 200, r.text
            cache[who] = {"Authorization": f"Bearer {r.json()['access_token']}"}
        return cache[who]

    return _headers


# Ensure agents are offline during tests to avoid external calls.
@pytest.fixture(autouse=True)
def offline_agents(monkeypatch):
    """Tests never call the real DevAI agents, even when backend/.env has a key.
    Live agent checks: python -m scripts.check_agents"""
    monkeypatch.setattr(config, "DEVAI_API_KEY", "")
