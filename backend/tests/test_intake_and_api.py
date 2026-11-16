"""Intake flow and API shape tests with the database and LLM replaced by fakes."""

from fastapi.testclient import TestClient

from app.agents import intake, text
from app.main import app

client = TestClient(app)


def test_health(client):  # the conftest fixture (test database), not the module-level client
    assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}


def test_unlinked_chat_gets_link_message(monkeypatch):
    saved = []
    monkeypatch.setattr(intake, "find_client_by_chat", lambda chat_id: None)
    monkeypatch.setattr(intake, "save_measurement", lambda cid, v: saved.append(v))
    assert intake.handle_message(1, "weight 82") == text.NOT_LINKED
    assert saved == []


def test_arabic_measurement_saved_and_confirmed_in_arabic(monkeypatch):
    saved = []
    monkeypatch.setattr(intake, "find_client_by_chat", lambda chat_id: {"id": "c1", "name": "x"})
    monkeypatch.setattr(intake, "save_measurement", lambda cid, v: saved.append((cid, v)))
    reply = intake.handle_message(111, "وزني ٨٢٫٥")
    assert saved == [("c1", {"weight_kg": 82.5, "waist_cm": None})]
    assert "82.5" in reply and "تم" in reply


def test_non_measurement_is_saved_as_a_question(monkeypatch):
    saved, questions = [], []
    monkeypatch.setattr(intake, "find_client_by_chat", lambda chat_id: {"id": "c1", "name": "x"})
    monkeypatch.setattr(intake, "save_measurement", lambda cid, v: saved.append(v))
    monkeypatch.setattr(intake, "save_question", lambda cid, t: questions.append((cid, t)) or 7)
    result = intake.process_message(111, "when is my next session?")
    assert saved == []
    assert questions == [("c1", "when is my next session?")]
    assert result.reply == text.not_a_measurement(False) and result.question_id == 7


def test_llm_fallback_values_are_range_checked(monkeypatch):
    saved = []
    monkeypatch.setattr(intake, "find_client_by_chat", lambda chat_id: {"id": "c1", "name": "x"})
    monkeypatch.setattr(intake, "save_measurement", lambda cid, v: saved.append(v))
    monkeypatch.setattr(intake, "save_question", lambda cid, t: 1)
    monkeypatch.setattr(text, "extract_measurement", lambda t: {"weight_kg": 999, "waist_cm": None})
    intake.handle_message(111, "I'm about eighty two")
    assert saved == []


def test_bad_ids_and_bodies_are_422(client, auth):
    h = auth("trainer_a")
    assert client.get("/api/v1/clients/not-a-number/agent-summary", headers=h).status_code == 422
    assert client.post("/api/v1/agent-drafts/not-a-number/approve", headers=h).status_code == 422
    assert client.get("/api/v1/clients/not-a-number/squat-checks", headers=h).status_code == 422


def test_template_draft_without_llm():
    body = text.draft(
        "Omar",
        {"entries": 4, "weight_change_2w_kg": 0.0},
        ["stalled"],
        {"errors": [{"rep": 3, "type": "knees_caving"}], "confidence": 0.82},
    )
    assert body.startswith("مرحبًا Omar")
    assert "ثابت" in body and "ركبتيك" in body


def test_low_confidence_form_check_asks_to_refilm():
    body = text.draft("Omar", {"entries": 4}, [], {"errors": [{"type": "knees_caving"}], "confidence": 0.4})
    assert "أعد تصويره" in body and "ركبتيك" not in body


def test_endpoint_count_within_cap():
    routes = {(m, r.path) for r in app.routes if hasattr(r, "methods") for m in r.methods}
    api = {x for x in routes if x[0] in {"GET", "POST", "PUT", "PATCH", "DELETE"}}
    api -= {(m, p) for m, p in api if p.startswith(("/docs", "/openapi", "/redoc"))}
    assert len(api) <= 10
