"""The bot running inside the backend via Telegram's webhook (ADR-0011). Telegram is faked."""

import pytest
from sqlalchemy import select

import app.agents.intake as intake
import app.services.telegram_core as core
import app.services.telegram_updates as updates
from app import config
from app.models import AgentDraft, MeasurementSession, Question, SquatCheck, User
from app.services import telegram_send

API = "/api/v1"
COACH, PLAYER = 5001, 6001
GROUP = -100777
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200


@pytest.fixture()
def tg(monkeypatch, db_session):
    _, Session = db_session
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", "secret-for-tests")
    for module in (intake, core, updates):
        monkeypatch.setattr(module, "get_sessionmaker", lambda: Session)
    out = {"sent": [], "group": [], "answers": [], "force": [], "edits": []}

    def send_message(chat_id, text, buttons=None):
        out["sent"].append({"chat_id": chat_id, "text": text, "buttons": buttons})
        return 900 + len(out["sent"])

    monkeypatch.setattr(telegram_send, "send_message", send_message)
    monkeypatch.setattr(telegram_send, "send_telegram_message", lambda c, t: out["group"].append((c, t)) or True)
    monkeypatch.setattr(telegram_send, "send_force_reply", lambda c, t: out["force"].append((c, t)) or 1)
    monkeypatch.setattr(telegram_send, "answer_callback", lambda i, t, alert=False: out["answers"].append((t, alert)) or True)
    monkeypatch.setattr(telegram_send, "create_invite_link", lambda c: "https://t.me/+invite")
    monkeypatch.setattr(telegram_send, "download_file", lambda f, m: MP4)
    monkeypatch.setattr(telegram_send, "edit_message", lambda c, m, t: out["edits"].append((c, m, t)) or True)
    return out


def hook(client, update, secret=None):
    secret = secret if secret is not None else core.webhook_secret()
    r = client.post("/telegram/webhook", headers={"X-Telegram-Bot-Api-Secret-Token": secret}, json=update)
    return r


def msg(chat_id, user_id, text=None, chat_type="group", **extra):
    m = {"message_id": 1, "chat": {"id": chat_id, "type": chat_type}, "from": {"id": user_id, "is_bot": False}, **extra}
    if text is not None:
        m["text"] = text
    return {"update_id": 1, "message": m}


def to_chat(out, chat_id):
    return [s["text"] for s in out["sent"] if s["chat_id"] == chat_id]


def setup_group(client, auth, tg):
    code = client.post(f"{API}/me/telegram/link", headers=auth("trainer_a")).json()["url"].split("start=")[1]
    hook(client, msg(COACH, COACH, f"/start {code}", chat_type="private"))
    assert "تم ربط حسابك" in to_chat(tg, COACH)[-1]
    p = client.post(f"{API}/clients/telegram", headers=auth("trainer_a"), json={"full_name": "ياسر", "sex": "male"}).json()
    hook(client, msg(GROUP, COACH, f"/link@tahadi_coach_bot {p['group_code']}"))
    return p


def test_webhook_needs_telegrams_secret(client, tg, monkeypatch):
    assert hook(client, msg(GROUP, PLAYER, "hi"), secret="wrong").status_code == 401
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", "")
    assert hook(client, msg(GROUP, PLAYER, "hi")).status_code == 503


def test_link_coach_and_group(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    assert "ياسر" in to_chat(tg, GROUP)[-1]  # welcome in the group
    assert any("https://t.me/+invite" in t for t in to_chat(tg, COACH))  # invite link sent privately to the coach
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.telegram_chat_id == GROUP and profile.telegram_invite_url == "https://t.me/+invite"


def test_stranger_cannot_link_a_group(client, users, auth, tg):
    p = client.post(f"{API}/clients/telegram", headers=auth("trainer_a"), json={"full_name": "فهد", "sex": "male"}).json()
    hook(client, msg(GROUP, 999, f"/link {p['group_code']}"))
    assert "مدرب اللاعب" in to_chat(tg, GROUP)[-1]


def test_full_happy_flow_with_buttons(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    for answer in ("28", "175", "1"):
        hook(client, msg(GROUP, PLAYER, answer))
    assert "اكتمل" in to_chat(tg, GROUP)[-1]
    hook(client, msg(GROUP, PLAYER, "وزني ٩٢"))
    assert "92" in to_chat(tg, GROUP)[-1]
    assert len(db.scalars(select(MeasurementSession).where(MeasurementSession.client_id == p["client"]["id"])).all()) == 1

    hook(client, msg(GROUP, PLAYER, "هل أقدر آكل رز بالليل؟"))
    draft = db.scalar(select(AgentDraft).where(AgentDraft.client_id == p["client"]["id"]))
    dm = tg["sent"][-1]
    assert dm["chat_id"] == COACH and dm["buttons"][0][0]["callback_data"] == f"approve:{draft.id}"
    assert tg["group"] == []

    hook(client, {"update_id": 9, "callback_query": {"id": "cb1", "from": {"id": COACH}, "data": f"approve:{draft.id}"}})
    assert len(tg["group"]) == 1 and tg["group"][0][0] == GROUP
    assert tg["answers"][-1][0].startswith("✅")
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    db.refresh(q)
    assert q.status == "answered"


def test_edit_button_then_reply_sends_edited_text(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    for _ in range(3):
        hook(client, msg(GROUP, PLAYER, "تخطي"))
    hook(client, msg(GROUP, PLAYER, "كم مرة أتمرن بالأسبوع؟"))
    draft = db.scalar(select(AgentDraft).where(AgentDraft.client_id == p["client"]["id"]))
    hook(client, {"update_id": 9, "callback_query": {"id": "cb1", "from": {"id": COACH}, "data": f"edit:{draft.id}"}})
    prompt = tg["force"][-1][1]
    assert f"#{draft.id}" in prompt
    hook(client, msg(COACH, COACH, "٣ مرات في الأسبوع تكفي 💪", chat_type="private", reply_to_message={"text": prompt}))
    assert tg["group"] == [(GROUP, "٣ مرات في الأسبوع تكفي 💪")]


def test_only_the_coach_can_press_buttons(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    for _ in range(3):
        hook(client, msg(GROUP, PLAYER, "تخطي"))
    hook(client, msg(GROUP, PLAYER, "سؤال؟"))
    draft = db.scalar(select(AgentDraft).where(AgentDraft.client_id == p["client"]["id"]))
    hook(client, {"update_id": 9, "callback_query": {"id": "cb1", "from": {"id": PLAYER}, "data": f"approve:{draft.id}"}})
    assert tg["group"] == [] and tg["answers"][-1][1] is True  # shown as an alert


def test_coach_text_and_bot_messages_are_not_data(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    before = len(tg["sent"])
    hook(client, msg(GROUP, COACH, "وزني 200"))
    bot_update = msg(GROUP, 42, "وزني 70")
    bot_update["message"]["from"]["is_bot"] = True
    hook(client, bot_update)
    assert len(tg["sent"]) == before
    assert db.scalars(select(MeasurementSession).where(MeasurementSession.client_id == p["client"]["id"])).all() == []


def test_video_is_downloaded_and_stored(client, users, auth, db_session, tg):
    db, _ = db_session
    p = setup_group(client, auth, tg)
    hook(client, msg(GROUP, PLAYER, video={"file_id": "abc", "file_size": 1000}))
    check = db.scalar(select(SquatCheck).where(SquatCheck.client_id == p["client"]["id"]))
    assert check.status == "awaiting_review" and check.video_path
    assert "استلمنا" in to_chat(tg, GROUP)[-1]


def test_broken_update_is_ignored(client, tg):
    assert hook(client, {"update_id": 1, "message": {"chat": {"id": 1}}}).status_code == 200
    assert hook(client, {"update_id": 2, "callback_query": {"id": "x", "data": "approve:notanumber"}}).status_code == 200
