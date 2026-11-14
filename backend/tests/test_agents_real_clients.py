"""DevAI agents on real client accounts: summary, drafts, approve/reject, access rules.

The DevAI host is never called (conftest keeps agents offline); agent replies are mocked
where a test needs one.
"""

from datetime import date, timedelta

import pytest

import app.routers.agents as agents_router
from app import llm
from app.models import MeasurementSession
from app.schemas.measurement import ValueIn
from app.services import measurements

API = "/api/v1"


def add_weights(db, client, weights, last_days_ago=0, waist=None):
    """Weekly sessions ending `last_days_ago` days ago."""
    last = date.today() - timedelta(days=last_days_ago)
    n = len(weights)
    for i, w in enumerate(weights):
        values = [ValueIn(key="weight", value_number=w)]
        if waist is not None:
            values.append(ValueIn(key="waist", value_number=waist))
        s = MeasurementSession(
            client_id=client.id,
            trainer_id=None,
            updated_by_id=None,
            session_date=last - timedelta(weeks=n - 1 - i),
        )
        s.values = measurements.build_values(db, values)
        db.add(s)
    db.commit()


@pytest.fixture()
def sent(monkeypatch):
    """Capture Telegram sends instead of calling the Bot API."""
    calls = []

    def fake_send(chat_id, text):
        calls.append((chat_id, text))
        return True

    monkeypatch.setattr(agents_router, "send_telegram_message", fake_send)
    return calls


def link_telegram(db, client, chat_id=555001):
    client.profile.telegram_chat_id = chat_id
    db.commit()


# ---------- summary ----------

def test_summary_uses_real_sessions_and_flags_stall(client, users, auth, db_session):
    db, _ = db_session
    add_weights(db, users["client_a"], [92.4, 92.3, 92.5, 92.3], waist=101)
    r = client.get(f"{API}/clients/{users['client_a'].id}/agent-summary", headers=auth("trainer_a"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["alerts"] == ["stalled"]
    assert body["facts"]["entries"] == 4
    assert body["facts"]["latest_weight_kg"] == 92.3
    assert body["facts"]["latest_waist_cm"] == 101.0
    assert body["source"] == "template"  # agents are offline in tests
    assert body["summary_ar"] and body["summary_en"]


def test_summary_flags_no_checkin(client, users, auth, db_session):
    db, _ = db_session
    add_weights(db, users["client_a"], [80.0, 79.0], last_days_ago=12)
    body = client.get(f"{API}/clients/{users['client_a'].id}/agent-summary", headers=auth("trainer_a")).json()
    assert "no_checkin" in body["alerts"]
    assert body["facts"]["days_since_last"] == 12


def test_summary_without_measurements(client, users, auth):
    body = client.get(f"{API}/clients/{users['client_a'].id}/agent-summary", headers=auth("trainer_a")).json()
    assert body["facts"]["entries"] == 0 and body["alerts"] == []


def test_summary_uses_devai_agent_reply(client, users, auth, db_session, monkeypatch):
    db, _ = db_session
    add_weights(db, users["client_a"], [80.0, 79.0])
    monkeypatch.setattr(llm, "run_agent", lambda *a, **k: '{"summary_ar": "ملخص الوكيل", "summary_en": "Agent summary"}')
    from app import config

    monkeypatch.setattr(config, "DEVAI_API_KEY", "test-key")
    body = client.get(f"{API}/clients/{users['client_a'].id}/agent-summary", headers=auth("trainer_a")).json()
    assert body["source"] == "agent"
    assert body["summary_en"] == "Agent summary"


# ---------- access rules ----------

def test_agent_endpoints_need_login(client, users):
    cid = users["client_a"].id
    assert client.get(f"{API}/clients/{cid}/agent-summary").status_code == 401
    assert client.post(f"{API}/clients/{cid}/agent-drafts").status_code == 401
    assert client.post(f"{API}/agent-drafts/1/approve").status_code == 401


def test_clients_cannot_use_coach_agents(client, users, auth):
    cid = users["client_a"].id
    assert client.get(f"{API}/clients/{cid}/agent-summary", headers=auth("client_a")).status_code == 403
    assert client.post(f"{API}/clients/{cid}/agent-drafts", headers=auth("client_a")).status_code == 403


def test_trainer_cannot_reach_another_trainers_client(client, users, auth):
    other = users["client_b"].id  # belongs to trainer_b
    assert client.get(f"{API}/clients/{other}/agent-summary", headers=auth("trainer_a")).status_code == 404
    assert client.post(f"{API}/clients/{other}/agent-drafts", headers=auth("trainer_a")).status_code == 404


def test_trainer_cannot_decide_another_trainers_draft(client, users, auth, sent):
    d = client.post(f"{API}/clients/{users['client_b'].id}/agent-drafts", headers=auth("trainer_b")).json()
    assert client.post(f"{API}/agent-drafts/{d['id']}/approve", headers=auth("trainer_a")).status_code == 404
    assert client.post(f"{API}/agent-drafts/{d['id']}/reject", headers=auth("trainer_a")).status_code == 404
    assert sent == []


def test_admin_can_use_agents_for_any_client(client, users, auth):
    r = client.post(f"{API}/clients/{users['client_b'].id}/agent-drafts", headers=auth("admin"))
    assert r.status_code == 201


# ---------- drafts ----------

def test_draft_is_pending_and_not_sent(client, users, auth, db_session, sent):
    db, _ = db_session
    add_weights(db, users["client_a"], [92.4, 92.3, 92.5, 92.3])
    r = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=auth("trainer_a"))
    assert r.status_code == 201
    d = r.json()
    assert d["status"] == "pending" and d["source"] == "template" and d["text"]
    assert d["telegram_sent"] is False
    assert sent == []


def test_approve_sends_edited_text_to_linked_client(client, users, auth, db_session, sent):
    db, _ = db_session
    link_telegram(db, users["client_a"], 555001)
    d = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=auth("trainer_a")).json()
    r = client.post(f"{API}/agent-drafts/{d['id']}/approve", json={"text": "  نص عدله المدرب  "}, headers=auth("trainer_a"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "approved" and body["text"] == "نص عدله المدرب"
    assert body["telegram_linked"] is True and body["telegram_sent"] is True
    assert sent == [(555001, "نص عدله المدرب")]


def test_approve_unlinked_client_is_not_sent(client, users, auth, sent):
    d = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=auth("trainer_a")).json()
    body = client.post(f"{API}/agent-drafts/{d['id']}/approve", headers=auth("trainer_a")).json()
    assert body["status"] == "approved"
    assert body["telegram_linked"] is False and body["telegram_sent"] is False
    assert sent == []


def test_failed_telegram_send_is_reported(client, users, auth, db_session, monkeypatch):
    db, _ = db_session
    link_telegram(db, users["client_a"])
    monkeypatch.setattr(agents_router, "send_telegram_message", lambda chat_id, text: False)
    d = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=auth("trainer_a")).json()
    body = client.post(f"{API}/agent-drafts/{d['id']}/approve", headers=auth("trainer_a")).json()
    assert body["telegram_linked"] is True and body["telegram_sent"] is False


def test_decided_drafts_cannot_be_decided_again(client, users, auth, db_session, sent):
    db, _ = db_session
    link_telegram(db, users["client_a"])
    h = auth("trainer_a")
    a = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=h).json()
    assert client.post(f"{API}/agent-drafts/{a['id']}/approve", headers=h).status_code == 200
    assert client.post(f"{API}/agent-drafts/{a['id']}/approve", headers=h).status_code == 409
    assert client.post(f"{API}/agent-drafts/{a['id']}/reject", headers=h).status_code == 409
    assert len(sent) == 1  # sent once only

    r = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=h).json()
    assert client.post(f"{API}/agent-drafts/{r['id']}/reject", headers=h).json()["status"] == "rejected"
    assert client.post(f"{API}/agent-drafts/{r['id']}/approve", headers=h).status_code == 409
    assert len(sent) == 1  # a rejected draft is never sent


def test_unknown_draft_is_404(client, users, auth):
    assert client.post(f"{API}/agent-drafts/99999/approve", headers=auth("trainer_a")).status_code == 404


def test_draft_uses_devai_agent_reply(client, users, auth, monkeypatch):
    from app import config

    monkeypatch.setattr(config, "DEVAI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "run_agent", lambda agent_id, msg, name="": "مرحبًا 👋\nرسالة من الوكيل")
    d = client.post(f"{API}/clients/{users['client_a'].id}/agent-drafts", headers=auth("trainer_a")).json()
    assert d["source"] == "agent" and "رسالة من الوكيل" in d["text"]
