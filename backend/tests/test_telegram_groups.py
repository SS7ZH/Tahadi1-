"""Telegram groups, no player login (ADR-0011): players, linking, messages, drafts, profile, videos.

Telegram itself is faked: nothing leaves the test. The bot endpoints are called the way the bot
worker calls them (with X-Bot-Secret).
"""

from datetime import date

import pytest
from sqlalchemy import select

import app.agents.intake as intake
import app.routers.agents as agents_router
import app.routers.questions as questions_router
import app.routers.telegram as tg_router
from app import config
from app.models import AgentDraft, MeasurementSession, Question, SquatCheck, User
from app.rules.profile import next_step, parse_answer
from app.services import telegram_links, telegram_send

API = "/api/v1"
SECRET = "test-bot-secret"
BOT = {"X-Bot-Secret": SECRET}
COACH_TG, PLAYER_TG, STRANGER_TG = 5001, 6001, 7001
GROUP = -100123


@pytest.fixture()
def tg(monkeypatch, db_session):
    """Bot secret set, agents/routers use the test database, Telegram calls recorded."""
    _, Session = db_session
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", SECRET)
    monkeypatch.setattr(intake, "get_sessionmaker", lambda: Session)
    monkeypatch.setattr(tg_router, "get_sessionmaker", lambda: Session)
    sent = {"messages": [], "edits": [], "group": []}

    def fake_send_message(chat_id, text, buttons=None):
        sent["messages"].append({"chat_id": chat_id, "text": text, "buttons": buttons})
        return 900 + len(sent["messages"])

    def fake_group_send(chat_id, text):
        sent["group"].append((chat_id, text))
        return True

    monkeypatch.setattr(telegram_send, "send_message", fake_send_message)
    monkeypatch.setattr(telegram_send, "send_telegram_message", fake_group_send)
    monkeypatch.setattr(telegram_send, "edit_message", lambda c, m, t: sent["edits"].append((c, m, t)) or True)
    monkeypatch.setattr(agents_router, "send_telegram_message", fake_group_send)
    monkeypatch.setattr(questions_router, "send_telegram_message", fake_group_send)
    return sent


def new_player(client, auth, name="ياسر الحربي", who="trainer_a"):
    r = client.post(f"{API}/clients/telegram", headers=auth(who), json={"full_name": name, "sex": "male"})
    assert r.status_code == 201, r.text
    return r.json()


def link_coach(client, auth, who="trainer_a", tg_id=COACH_TG):
    url = client.post(f"{API}/me/telegram/link", headers=auth(who)).json()["url"]
    code = url.split("start=")[1]
    r = client.post("/telegram/link/coach", headers=BOT, json={"code": code, "telegram_user_id": tg_id})
    assert r.status_code == 200, r.text


def linked_player(client, auth, chat_id=GROUP):
    link_coach(client, auth)
    p = new_player(client, auth)
    r = client.post("/telegram/link/group", headers=BOT,
                    json={"code": p["group_code"], "chat_id": chat_id, "from_user_id": COACH_TG, "invite_url": "https://t.me/+abc"})
    assert r.status_code == 200, r.text
    return p, r.json()


def say(client, text, from_user=PLAYER_TG, chat_id=GROUP):
    r = client.post("/telegram/message", headers=BOT, json={"chat_id": chat_id, "text": text, "from_user_id": from_user})
    assert r.status_code == 200, r.text
    return r.json()["reply"]


# ---------------------------------------------------------------- players without login

def test_coach_adds_telegram_player_without_email_or_password(client, users, auth, db_session, tg):
    db, _ = db_session
    p = new_player(client, auth)
    assert p["client"]["email"] is None
    assert p["link_command"] == f"/link {p['group_code']}"
    user = db.get(User, p["client"]["id"])
    assert user.password_hash is None and user.profile.trainer_id == users["trainer_a"].id
    listed = client.get(f"{API}/telegram/clients", headers=auth("trainer_a")).json()
    assert {"id": user.id, "linked": False, "telegram_only": True}.items() <= next(x for x in listed if x["id"] == user.id).items()


def test_telegram_player_cannot_log_in(client, users, auth, db_session, tg):
    db, _ = db_session
    p = new_player(client, auth)
    user = db.get(User, p["client"]["id"])
    user.email = "ghost@test.app"  # even if an email existed, there is no password
    db.commit()
    r = client.post(f"{API}/auth/login", json={"email": "ghost@test.app", "password": "anything123"})
    assert r.status_code == 401


def test_normal_accounts_still_need_email_and_password(client, auth):
    r = client.post(f"{API}/clients", headers=auth("trainer_a"), json={"full_name": "بلا بريد", "sex": "male", "birth_date": "1995-01-01", "height_cm": 175})
    assert r.status_code == 422


# ---------------------------------------------------------------- bot secret & old endpoints

def test_bot_endpoints_need_the_secret(client, users, tg, monkeypatch):
    body = {"chat_id": GROUP, "text": "وزني 80"}
    assert client.post("/telegram/message", json=body).status_code == 401
    assert client.post("/telegram/message", headers={"X-Bot-Secret": "wrong"}, json=body).status_code == 401
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", "")
    assert client.post("/telegram/message", headers=BOT, json=body).status_code == 503


def test_old_demo_endpoints_are_gone(client):
    for method, path in [("post", "/draft/Ahmed/approve"), ("get", "/summary/Ahmed"), ("post", "/telegram"), ("post", "/form_checks"),
                         ("post", "/telegram/link/claim")]:
        assert getattr(client, method)(path).status_code in (404, 405), path


# ---------------------------------------------------------------- linking

def test_group_linking_rules(client, users, auth, db_session, tg):
    db, _ = db_session
    p = new_player(client, auth)
    code = p["group_code"]
    body = {"code": code, "chat_id": GROUP, "from_user_id": COACH_TG}
    # the coach has not linked his own Telegram yet
    assert client.post("/telegram/link/group", headers=BOT, json=body).status_code == 403
    link_coach(client, auth)
    # someone else in the group cannot link it
    assert client.post("/telegram/link/group", headers=BOT, json={**body, "from_user_id": STRANGER_TG}).status_code == 403
    r = client.post("/telegram/link/group", headers=BOT, json={**body, "invite_url": "https://t.me/+abc"})
    assert r.status_code == 200 and "ياسر" in r.json()["reply"]
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.telegram_chat_id == GROUP and profile.telegram_invite_url == "https://t.me/+abc"
    # same code, another group -> refused; another player, same group -> refused
    assert client.post("/telegram/link/group", headers=BOT, json={**body, "chat_id": -999}).status_code == 409
    other = new_player(client, auth, "فهد")
    assert client.post("/telegram/link/group", headers=BOT, json={**body, "code": other["group_code"]}).status_code == 409


def test_codes_expire_and_are_kind_specific(client, users, auth, tg):
    p = new_player(client, auth)
    old, _ = telegram_links.make_code(telegram_links.KIND_GROUP, p["client"]["id"], now=1_000_000)
    link_coach(client, auth)
    r = client.post("/telegram/link/group", headers=BOT, json={"code": old, "chat_id": GROUP, "from_user_id": COACH_TG})
    assert r.status_code == 410
    # a group code is not a coach code
    r = client.post("/telegram/link/coach", headers=BOT, json={"code": p["group_code"], "telegram_user_id": 1})
    assert r.status_code == 400


def test_trainer_cannot_get_codes_for_other_trainers_players(client, users, auth, tg):
    p = new_player(client, auth, who="trainer_b")
    assert client.post(f"{API}/clients/{p['client']['id']}/telegram/group-code", headers=auth("trainer_a")).status_code == 404


# ---------------------------------------------------------------- messages

def test_player_measurement_is_saved(client, users, auth, db_session, tg):
    db, _ = db_session
    p, _ = linked_player(client, auth)
    say(client, "تخطي")  # skip age
    say(client, "تخطي")  # skip height
    say(client, "تخطي")  # skip goal
    reply = say(client, "وزني ٩٢٫٥")
    assert "92.5" in reply
    sessions = db.scalars(select(MeasurementSession).where(MeasurementSession.client_id == p["client"]["id"])).all()
    assert len(sessions) == 1 and sessions[0].source == "telegram"


def test_question_is_logged_and_drafted_privately_to_the_coach(client, users, auth, db_session, tg):
    db, _ = db_session
    p, _ = linked_player(client, auth)
    for _ in range(3):
        say(client, "تخطي")
    reply = say(client, "هل أقدر آكل رز بالليل؟")
    assert "مدربك" in reply
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    assert q.source == "telegram" and q.status == "open"
    draft = db.scalar(select(AgentDraft).where(AgentDraft.question_id == q.id))
    assert draft is not None and draft.status == "pending"
    dm = tg["messages"][-1]
    assert dm["chat_id"] == COACH_TG and "رز" in dm["text"]
    assert [b["callback_data"] for b in dm["buttons"][0]] == [f"approve:{draft.id}", f"edit:{draft.id}", f"reject:{draft.id}"]
    assert tg["group"] == []  # nothing reached the player yet


def test_coach_message_in_group_answers_questions_and_is_not_data(client, users, auth, db_session, tg):
    db, _ = db_session
    p, _ = linked_player(client, auth)
    for _ in range(3):
        say(client, "تخطي")
    say(client, "كم بروتين أحتاج؟")
    assert say(client, "وزني 200", from_user=COACH_TG) is None  # coach's text is never saved as the player's weight
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    db.refresh(q)
    assert q.status == "answered" and q.replies[-1].body == "وزني 200"
    assert db.scalars(select(MeasurementSession).where(MeasurementSession.client_id == p["client"]["id"])).all() == []


def test_unlinked_group_gets_instructions(client, tg):
    assert "/link" in say(client, "وزني 80", chat_id=-555)


# ---------------------------------------------------------------- approvals

def _pending_question_draft(client, auth, db):
    p, _ = linked_player(client, auth)
    for _ in range(3):
        say(client, "تخطي")
    say(client, "هل أتمرن اليوم؟")
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    return p, q, db.scalar(select(AgentDraft).where(AgentDraft.question_id == q.id))


def test_coach_approves_from_telegram_button(client, users, auth, db_session, tg):
    db, _ = db_session
    _, q, draft = _pending_question_draft(client, auth, db)
    r = client.post("/telegram/draft-decision", headers=BOT, json={"draft_id": draft.id, "action": "approve", "from_user_id": COACH_TG, "text": "نعم، تمرين خفيف اليوم 💪"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert tg["group"] == [(GROUP, "نعم، تمرين خفيف اليوم 💪")]
    db.refresh(q)
    assert q.status == "answered" and q.replies[-1].body == "نعم، تمرين خفيف اليوم 💪"
    assert tg["edits"] and tg["edits"][-1][0] == COACH_TG  # the coach's message loses its buttons
    again = client.post("/telegram/draft-decision", headers=BOT, json={"draft_id": draft.id, "action": "approve", "from_user_id": COACH_TG})
    assert again.json()["status"] == "approved" and len(tg["group"]) == 1  # sent once only


def test_only_the_coach_can_press_the_buttons(client, users, auth, db_session, tg):
    db, _ = db_session
    _, _, draft = _pending_question_draft(client, auth, db)
    r = client.post("/telegram/draft-decision", headers=BOT, json={"draft_id": draft.id, "action": "approve", "from_user_id": PLAYER_TG})
    assert r.status_code == 403 and tg["group"] == []


def test_reject_from_telegram_sends_nothing(client, users, auth, db_session, tg):
    db, _ = db_session
    _, q, draft = _pending_question_draft(client, auth, db)
    r = client.post("/telegram/draft-decision", headers=BOT, json={"draft_id": draft.id, "action": "reject", "from_user_id": COACH_TG})
    assert r.json()["status"] == "rejected" and tg["group"] == []
    db.refresh(q)
    assert q.status == "open"


def test_web_approval_does_the_same(client, users, auth, db_session, tg):
    db, _ = db_session
    _, q, draft = _pending_question_draft(client, auth, db)
    r = client.post(f"{API}/agent-drafts/{draft.id}/approve", headers=auth("trainer_a"), json={"text": "رد من الموقع"})
    assert r.status_code == 200 and r.json()["telegram_sent"] is True
    assert tg["group"] == [(GROUP, "رد من الموقع")]
    db.refresh(q)
    assert q.status == "answered" and tg["edits"]


def test_manual_web_reply_to_telegram_question_reaches_the_group(client, users, auth, db_session, tg):
    db, _ = db_session
    _, q, _ = _pending_question_draft(client, auth, db)
    r = client.post(f"{API}/questions/{q.id}/replies", headers=auth("trainer_a"), json={"body": "أهلًا، نعم"})
    assert r.status_code == 201 and r.json()["source"] == "telegram"
    assert tg["group"] == [(GROUP, "أهلًا، نعم")]


# ---------------------------------------------------------------- profile questions

def test_profile_questions_fill_the_profile(client, users, auth, db_session, tg):
    db, _ = db_session
    p, linked = linked_player(client, auth)
    assert "عمرك" in linked["reply"]
    assert "لم أفهم" in say(client, "ما أدري")
    assert "طولك" in say(client, "٢٨")
    assert "هدفك" in say(client, "1.78")
    assert "اكتمل" in say(client, "1")
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.birth_date.year == date.today().year - 28
    assert profile.height_cm == 178 and profile.goal == "fat_loss" and profile.telegram_step is None


@pytest.mark.parametrize("step,text,expected", [
    ("age", "30", (True, date(2026, 1, 1).replace(year=2026 - 30))),
    ("age", "1996", (True, date(1996, 1, 1))),
    ("age", "300", (False, None)),
    ("height", "175", (True, 175)),
    ("height", "1.70", (True, 170)),
    ("height", "50", (False, None)),
    ("goal", "2", (True, "muscle_gain")),
    ("goal", "أبي أخسر دهون", (True, "fat_loss")),
    ("goal", "تخطي", (True, None)),
])
def test_profile_answer_parsing(step, text, expected):
    assert parse_answer(step, text, today=date(2026, 11, 15)) == expected


def test_next_step_skips_known_fields():
    class P:
        birth_date, height_cm, goal = date(1990, 1, 1), None, "fitness"
    assert next_step(P()) == "height"
    assert next_step(P(), after="height") == "goal"
    assert next_step(P(), after="goal") is None


# ---------------------------------------------------------------- videos

MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200


def test_player_video_is_stored_for_review_and_feeds_the_draft(client, users, auth, db_session, tg):
    db, _ = db_session
    p, _ = linked_player(client, auth)
    r = client.post("/telegram/video", headers=BOT, data={"chat_id": str(GROUP), "from_user_id": str(PLAYER_TG)},
                    files={"file": ("squat.mp4", MP4, "video/mp4")})
    assert r.status_code == 200 and "استلمنا" in r.json()["reply"]
    check = db.scalar(select(SquatCheck).where(SquatCheck.client_id == p["client"]["id"]))
    assert check.status == "awaiting_review" and check.video_path
    assert any("فيديو" in m["text"] and m["chat_id"] == COACH_TG for m in tg["messages"])
    # the coach analyses it in the browser and saves the result to the player
    r = client.patch(f"{API}/squat-checks/{check.id}", headers=auth("trainer_a"),
                     json={"reps": 8, "errors": [{"rep": 3, "type": "knees_caving"}, {"type": "bogus"}], "confidence": 0.9})
    assert r.status_code == 200 and r.json()["status"] == "analysed" and r.json()["errors"] == [{"rep": 3, "type": "knees_caving"}]
    listed = client.get(f"{API}/clients/{p['client']['id']}/squat-checks", headers=auth("trainer_a")).json()
    assert listed[0]["has_video"] is True
    from app.agents.coach import latest_squat_check
    db.expire_all()  # the PATCH ran in another session; drop this session's cached copy
    assert latest_squat_check(db, p["client"]["id"])["reps"] == 8


def test_non_video_upload_is_refused_politely(client, users, auth, tg):
    linked_player(client, auth)
    r = client.post("/telegram/video", headers=BOT, data={"chat_id": str(GROUP)}, files={"file": ("x.mp4", b"not a video at all", "video/mp4")})
    assert "MP4" in r.json()["reply"]


def test_other_trainers_squat_checks_are_hidden(client, users, auth, tg):
    p = new_player(client, auth, who="trainer_b")
    assert client.get(f"{API}/clients/{p['client']['id']}/squat-checks", headers=auth("trainer_a")).status_code == 404
