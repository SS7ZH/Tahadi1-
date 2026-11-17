"""Private-chat bot via Telegram's webhook (ADR-0012). Telegram is faked: nothing leaves the test.

Players open a personal link and chat with the bot privately; everything they send is forwarded
to the coach's private chat; the coach answers with Telegram's Reply or the draft buttons.
"""

from datetime import date

import pytest
from sqlalchemy import select

import app.agents.intake as intake
import app.routers.agents as agents_router
import app.routers.questions as questions_router
import app.services.telegram_core as core
import app.services.telegram_updates as updates
from app import config
from app.models import AgentDraft, ClientPhoto, MeasurementSession, Question, SquatCheck, User
from app.rules.profile import next_step, parse_answer
from app.services import telegram_links, telegram_send

API = "/api/v1"
COACH, PLAYER, STRANGER = 5001, 6001, 7001


@pytest.fixture()
def tg(monkeypatch, db_session):
    _, Session = db_session
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", "secret-for-tests")
    for module in (intake, core, updates):
        monkeypatch.setattr(module, "get_sessionmaker", lambda: Session)
    out = {"sent": [], "copied": [], "answers": [], "force": [], "edits": [], "direct": []}

    def send_message(chat_id, text, buttons=None):
        out["sent"].append({"chat_id": chat_id, "text": text, "buttons": buttons})
        return 900 + len(out["sent"])

    def direct(chat_id, text):
        out["direct"].append((chat_id, text))
        return True

    monkeypatch.setattr(telegram_send, "send_message", send_message)
    monkeypatch.setattr(telegram_send, "send_telegram_message", direct)
    monkeypatch.setattr(agents_router, "send_telegram_message", direct)
    monkeypatch.setattr(questions_router, "send_telegram_message", direct)
    monkeypatch.setattr(telegram_send, "send_force_reply", lambda c, t: out["force"].append((c, t)) or 1)
    monkeypatch.setattr(telegram_send, "answer_callback", lambda i, t, alert=False: out["answers"].append((t, alert)) or True)
    monkeypatch.setattr(telegram_send, "edit_message", lambda c, m, t: out["edits"].append((c, m, t)) or True)
    monkeypatch.setattr(telegram_send, "copy_message", lambda to, frm, mid, cap=None: out["copied"].append((to, frm, mid, cap)) or 1)
    monkeypatch.setattr(telegram_send, "download_file", lambda f, m: b"FILE:" + f.encode())
    return out


def hook(client, update, secret=None):
    secret = core.webhook_secret() if secret is None else secret
    return client.post("/telegram/webhook", headers={"X-Telegram-Bot-Api-Secret-Token": secret}, json=update)


def private(user_id, text=None, **extra):
    m = {"message_id": 77, "chat": {"id": user_id, "type": "private"}, "from": {"id": user_id, "is_bot": False}, **extra}
    if text is not None:
        m["text"] = text
    return {"update_id": 1, "message": m}


def to(out, chat_id):
    return [s["text"] for s in out["sent"] if s["chat_id"] == chat_id]


def link_coach(client, auth, tg, who="trainer_a", tg_id=COACH):
    code = client.post(f"{API}/me/telegram/link", headers=auth(who)).json()["url"].split("start=")[1]
    hook(client, private(tg_id, f"/start {code}"))
    assert "تم ربط حسابك" in to(tg, tg_id)[-1]


def new_player(client, auth, name="ياسر الحربي", who="trainer_a"):
    r = client.post(f"{API}/clients/telegram", headers=auth(who), json={"full_name": name, "sex": "male"})
    assert r.status_code == 201, r.text
    return r.json()


def start_player(client, invite_url, tg_id=PLAYER):
    hook(client, private(tg_id, f"/start {invite_url.split('start=')[1]}"))


def ready_player(client, auth, tg):
    """Coach linked, player added, opened his link, skipped the profile questions."""
    link_coach(client, auth, tg)
    p = new_player(client, auth)
    start_player(client, p["invite_url"])
    for _ in range(3):
        hook(client, private(PLAYER, "تخطي"))
    return p


# ---------------------------------------------------------------- security & setup

def test_webhook_needs_telegrams_secret(client, tg, monkeypatch):
    assert hook(client, private(PLAYER, "hi"), secret="wrong").status_code == 401
    monkeypatch.setattr(config, "TELEGRAM_BOT_SECRET", "")
    assert hook(client, private(PLAYER, "hi")).status_code == 503


def test_old_group_and_bot_endpoints_are_gone(client):
    for path in ("/telegram/link/group", "/telegram/link/coach", "/telegram/message", "/telegram/video", "/telegram/draft-decision"):
        assert client.post(path).status_code in (404, 405), path


def test_strangers_and_groups_get_nothing_useful(client, users, tg):
    hook(client, private(STRANGER, "وزني 80"))
    assert "رابط" in to(tg, STRANGER)[-1]  # help text
    group = {"update_id": 2, "message": {"message_id": 1, "chat": {"id": -100, "type": "group"}, "from": {"id": PLAYER}, "text": "وزني 80"}}
    before = len(tg["sent"])
    hook(client, group)
    assert len(tg["sent"]) == before  # groups are ignored


# ---------------------------------------------------------------- players without login

def test_coach_adds_player_and_gets_a_personal_link(client, users, auth, db_session, tg):
    db, _ = db_session
    p = new_player(client, auth)
    assert p["client"]["email"] is None and p["invite_url"].startswith("https://t.me/tahadi_coach_bot?start=")
    assert db.get(User, p["client"]["id"]).password_hash is None
    again = client.post(f"{API}/clients/{p['client']['id']}/telegram/invite", headers=auth("trainer_a")).json()
    assert again["linked"] is False and again["invite_url"].startswith("https://t.me/")
    listed = client.get(f"{API}/telegram/clients", headers=auth("trainer_a")).json()
    assert {"id": p["client"]["id"], "name": "ياسر الحربي", "linked": False, "telegram_only": True} in listed


def test_telegram_player_cannot_log_in(client, users, auth, db_session, tg):
    db, _ = db_session
    user = db.get(User, new_player(client, auth)["client"]["id"])
    user.email = "ghost@test.app"
    db.commit()
    assert client.post(f"{API}/auth/login", json={"email": "ghost@test.app", "password": "anything123"}).status_code == 401


def test_other_trainers_players_are_hidden(client, users, auth, tg):
    p = new_player(client, auth, who="trainer_b")
    cid = p["client"]["id"]
    assert client.post(f"{API}/clients/{cid}/telegram/invite", headers=auth("trainer_a")).status_code == 404
    for path in (f"/clients/{cid}/photos", f"/clients/{cid}/squat-checks"):
        assert client.get(f"{API}{path}", headers=auth("trainer_a")).status_code == 404


# ---------------------------------------------------------------- linking

def test_player_opens_his_link(client, users, auth, db_session, tg):
    db, _ = db_session
    link_coach(client, auth, tg)
    p = new_player(client, auth)
    start_player(client, p["invite_url"])
    welcome = to(tg, PLAYER)[-1]
    assert "ياسر" in welcome and "عمرك" in welcome  # welcome + first profile question
    assert any("بدأ المحادثة" in t for t in to(tg, COACH))  # the coach is told the player started
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.telegram_chat_id == PLAYER and profile.telegram_step == "age"


def test_link_rules(client, users, auth, tg):
    link_coach(client, auth, tg)
    p, other = new_player(client, auth), new_player(client, auth, "فهد")
    start_player(client, p["invite_url"])
    start_player(client, other["invite_url"])  # same Telegram account, different player
    assert "مربوط بلاعب آخر" in to(tg, PLAYER)[-1]
    start_player(client, p["invite_url"], tg_id=STRANGER)  # someone else opens Yasser's link
    assert "مربوط بحساب تيليجرام آخر" in to(tg, STRANGER)[-1]


def test_unlink_then_relink(client, users, auth, db_session, tg):
    db, _ = db_session
    link_coach(client, auth, tg)
    p = new_player(client, auth)
    start_player(client, p["invite_url"])
    assert client.delete(f"{API}/clients/{p['client']['id']}/telegram", headers=auth("trainer_a")).status_code == 204
    new = client.post(f"{API}/clients/{p['client']['id']}/telegram/invite", headers=auth("trainer_a")).json()
    start_player(client, new["invite_url"], tg_id=STRANGER)
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.telegram_chat_id == STRANGER


# ---------------------------------------------------------------- messages

def test_measurement_saved_and_forwarded_to_coach(client, users, auth, db_session, tg):
    db, _ = db_session
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, "وزني ٩٢٫٥"))
    assert "92.5" in to(tg, PLAYER)[-1]
    fwd = to(tg, COACH)[-1]
    assert f"#c{p['client']['id']}" in fwd and "وزني" in fwd and "92.5" in fwd
    assert len(db.scalars(select(MeasurementSession).where(MeasurementSession.client_id == p["client"]["id"])).all()) == 1


def test_question_forwarded_and_drafted(client, users, auth, db_session, tg):
    db, _ = db_session
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, "هل أقدر آكل رز بالليل؟"))
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    draft = db.scalar(select(AgentDraft).where(AgentDraft.question_id == q.id))
    assert q.source == "telegram" and draft.status == "pending"
    coach_msgs = [s for s in tg["sent"] if s["chat_id"] == COACH]
    assert any("رز" in s["text"] and s["buttons"] is None for s in coach_msgs)  # the forwarded question
    dm = coach_msgs[-1]
    assert dm["buttons"][0][0]["callback_data"] == f"approve:{draft.id}" and f"#c{p['client']['id']}" in dm["text"]
    assert tg["direct"] == []  # nothing reached the player yet


def test_coach_answers_with_reply(client, users, auth, db_session, tg):
    db, _ = db_session
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, "كم بروتين أحتاج؟"))
    forwarded = next(t for t in to(tg, COACH) if "بروتين" in t)
    hook(client, private(COACH, "حوالي 150 جرام يوميًا", reply_to_message={"text": forwarded}))
    assert tg["direct"] == [(PLAYER, "حوالي 150 جرام يوميًا")]
    assert "أُرسل" in to(tg, COACH)[-1]
    q = db.scalar(select(Question).where(Question.client_id == p["client"]["id"]))
    db.refresh(q)
    assert q.status == "answered"


def test_coach_reply_to_a_photo_caption_works(client, users, auth, tg):
    p = ready_player(client, auth, tg)
    caption = core.client_tag(type("C", (), {"full_name": "ياسر", "id": p["client"]["id"]})())
    hook(client, private(COACH, "صورة ممتازة", reply_to_message={"caption": caption}))
    assert tg["direct"] == [(PLAYER, "صورة ممتازة")]


def test_coach_message_without_reply_gets_help(client, users, auth, tg):
    link_coach(client, auth, tg)
    hook(client, private(COACH, "مرحبا"))
    assert "Reply" in to(tg, COACH)[-1]


def test_other_coach_cannot_reply_to_my_player(client, users, auth, tg):
    p = ready_player(client, auth, tg)
    link_coach(client, auth, tg, who="trainer_b", tg_id=STRANGER)
    hook(client, private(STRANGER, "رسالة", reply_to_message={"text": f"👤 x · #c{p['client']['id']}"}))
    assert tg["direct"] == [] and "لا يمكنك" in to(tg, STRANGER)[-1]


# ---------------------------------------------------------------- draft buttons

def _draft(client, auth, db, tg):
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, "هل أتمرن اليوم؟"))
    return p, db.scalar(select(AgentDraft).where(AgentDraft.client_id == p["client"]["id"]))


def test_approve_button_sends_to_player_once(client, users, auth, db_session, tg):
    db, _ = db_session
    _, draft = _draft(client, auth, db, tg)
    press = {"update_id": 9, "callback_query": {"id": "cb", "from": {"id": COACH}, "data": f"approve:{draft.id}"}}
    hook(client, press)
    assert len(tg["direct"]) == 1 and tg["direct"][0][0] == PLAYER
    assert tg["answers"][-1][0].startswith("✅") and tg["edits"]
    hook(client, press)
    assert len(tg["direct"]) == 1


def test_edit_button_then_reply(client, users, auth, db_session, tg):
    db, _ = db_session
    _, draft = _draft(client, auth, db, tg)
    hook(client, {"update_id": 9, "callback_query": {"id": "cb", "from": {"id": COACH}, "data": f"edit:{draft.id}"}})
    prompt = tg["force"][-1][1]
    assert f"#{draft.id}" in prompt
    hook(client, private(COACH, "نعم، تمرين خفيف 💪", reply_to_message={"text": prompt}))
    assert tg["direct"] == [(PLAYER, "نعم، تمرين خفيف 💪")]


def test_reject_and_strangers_cannot_press(client, users, auth, db_session, tg):
    db, _ = db_session
    _, draft = _draft(client, auth, db, tg)
    hook(client, {"update_id": 9, "callback_query": {"id": "cb", "from": {"id": PLAYER}, "data": f"approve:{draft.id}"}})
    assert tg["direct"] == [] and tg["answers"][-1][1] is True
    hook(client, {"update_id": 10, "callback_query": {"id": "cb", "from": {"id": COACH}, "data": f"reject:{draft.id}"}})
    db.refresh(draft)
    assert draft.status == "rejected" and tg["direct"] == []


def test_web_approval_reaches_the_player(client, users, auth, db_session, tg):
    db, _ = db_session
    _, draft = _draft(client, auth, db, tg)
    r = client.post(f"{API}/agent-drafts/{draft.id}/approve", headers=auth("trainer_a"), json={"text": "رد من الموقع"})
    assert r.status_code == 200, r.text
    assert tg["direct"] == [(PLAYER, "رد من الموقع")]


# ---------------------------------------------------------------- media

def _path(url):
    return url.split("testserver", 1)[1]


def test_photo_recorded_forwarded_and_viewable(client, users, auth, db_session, tg):
    db, _ = db_session
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, photo=[{"file_id": "small"}, {"file_id": "big"}], caption="بعد 4 أسابيع"))
    photo = db.scalar(select(ClientPhoto).where(ClientPhoto.client_id == p["client"]["id"]))
    assert photo.telegram_file_id == "big" and photo.caption == "بعد 4 أسابيع"
    assert tg["copied"][-1][0] == COACH and f"#c{p['client']['id']}" in tg["copied"][-1][3]
    listed = client.get(f"{API}/clients/{p['client']['id']}/photos", headers=auth("trainer_a")).json()
    r = client.get(_path(listed[0]["url"]))
    assert r.status_code == 200 and r.content == b"FILE:big" and r.headers["content-type"] == "image/jpeg"
    assert client.get(_path(listed[0]["url"]).replace("token=", "token=x")).status_code == 404
    assert client.get(f"{API}/telegram-files/photo/{photo.id}?expires=1&token=abc").status_code == 404


def test_video_recorded_forwarded_reviewed_and_viewable(client, users, auth, db_session, tg):
    db, _ = db_session
    p = ready_player(client, auth, tg)
    hook(client, private(PLAYER, video={"file_id": "vid1", "file_size": 1000}))
    check = db.scalar(select(SquatCheck).where(SquatCheck.client_id == p["client"]["id"]))
    assert check.status == "awaiting_review" and check.telegram_file_id == "vid1"
    assert "استلمنا" in to(tg, PLAYER)[-1] and tg["copied"][-1][0] == COACH
    url = client.get(f"{API}/squat-checks/{check.id}/video", headers=auth("trainer_a")).json()["url"]
    assert client.get(_path(url)).content == b"FILE:vid1"
    r = client.patch(f"{API}/squat-checks/{check.id}", headers=auth("trainer_a"),
                     json={"reps": 8, "errors": [{"type": "knees_caving"}, {"type": "bogus"}], "confidence": 0.9})
    assert r.json()["status"] == "analysed" and r.json()["errors"] == [{"rep": None, "type": "knees_caving"}]


# ---------------------------------------------------------------- profile questions

def test_profile_questions_fill_the_profile(client, users, auth, db_session, tg):
    db, _ = db_session
    link_coach(client, auth, tg)
    p = new_player(client, auth)
    start_player(client, p["invite_url"])
    hook(client, private(PLAYER, "ما أدري"))
    assert "لم أفهم" in to(tg, PLAYER)[-1]
    for answer, expect in (("٢٨", "طولك"), ("1.78", "هدفك"), ("1", "اكتمل")):
        hook(client, private(PLAYER, answer))
        assert expect in to(tg, PLAYER)[-1]
    profile = db.get(User, p["client"]["id"]).profile
    db.refresh(profile)
    assert profile.birth_date.year == date.today().year - 28 and profile.height_cm == 178 and profile.goal == "fat_loss"


@pytest.mark.parametrize("step,text,expected", [
    ("age", "30", (True, date(1996, 1, 1))), ("height", "175", (True, 175)), ("height", "50", (False, None)),
    ("goal", "2", (True, "muscle_gain")), ("goal", "تخطي", (True, None)),
])
def test_profile_answer_parsing(step, text, expected):
    assert parse_answer(step, text, today=date(2026, 11, 15)) == expected


def test_next_step_skips_known_fields():
    class P:
        birth_date, height_cm, goal = date(1990, 1, 1), None, "fitness"
    assert next_step(P()) == "height" and next_step(P(), after="height") == "goal" and next_step(P(), after="goal") is None


def test_broken_updates_are_ignored(client, tg):
    assert hook(client, {"update_id": 1, "message": {"chat": {"id": 1}}}).status_code == 200
    assert hook(client, {"update_id": 2, "callback_query": {"id": "x", "data": "approve:nope"}}).status_code == 200


def test_link_code_kinds():
    code, _ = telegram_links.make_code(telegram_links.KIND_CLIENT, 7)
    assert telegram_links.kind_of(code) == telegram_links.KIND_CLIENT and telegram_links.kind_of("garbage") is None


def test_telegram_calls_never_crash_on_a_malformed_token(monkeypatch):
    """A token pasted with a newline made httpx raise InvalidURL, which escaped and silenced the bot."""
    import importlib
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456789:AAH" + "x" * 32 + "\n")
    assert not importlib.reload(config).TELEGRAM_BOT_TOKEN.endswith("\n")
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "bad\ntoken")
    import app.services.telegram_send as ts
    importlib.reload(ts)
    assert ts.send_message(1, "hi") is None
    importlib.reload(config)
    importlib.reload(ts)
