"""Agent 1 - Intake. Turns messages in a player's Telegram group into data (ADR-0011).

Each player has a group (bot + player + coach). For every text message:
* from the coach        -> not processed as data; answers the player's open Telegram questions
* profile step active   -> the answer is saved to the profile (age, height, goal), next question asked
* a measurement         -> saved as a measurement session (regex first, agent fallback)
* anything else         -> saved as a question for the coach; the caller drafts an AI reply for approval
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from app.agents import text as t
from app.db.session import get_sessionmaker
from app.models import ClientProfile, MeasurementSession, Question, QuestionReply, User
from app.rules.parsing import is_arabic, normalize, parse_measurement, validate_measurement
from app.rules.profile import PROFILE_STEPS, next_step, parse_answer, question_for
from app.schemas.measurement import ValueIn
from app.services import audit, measurements

NOT_LINKED_GROUP = "هذه المجموعة غير مرتبطة بلاعب بعد. على المدرب إرسال: /link <الرمز> من صفحة اللاعب."


@dataclass
class IntakeResult:
    reply: str | None  # what the bot says in the group (None = stay silent)
    question_id: int | None = None  # set when the message was saved as a question


def find_client_by_chat(chat_id: int) -> dict | None:
    with get_sessionmaker()() as db:
        row = db.execute(
            select(User.id, User.full_name, ClientProfile.trainer_id, ClientProfile.telegram_step)
            .join(ClientProfile, ClientProfile.user_id == User.id)
            .where(
                ClientProfile.telegram_chat_id == chat_id,
                User.role == "client",
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
            .limit(1)
        ).first()
        if row is None:
            return None
        coach_tg = db.scalar(select(User.telegram_user_id).where(User.id == row.trainer_id)) if row.trainer_id else None
    return {"id": row.id, "name": row.full_name, "trainer_id": row.trainer_id, "coach_telegram_user_id": coach_tg, "step": row.telegram_step}


def save_measurement(client_id: int, values: dict) -> None:
    inputs = [
        ValueIn(key=key, value_number=values[value_key])
        for key, value_key in (("weight", "weight_kg"), ("waist", "waist_cm"))
        if values.get(value_key) is not None
    ]
    with get_sessionmaker()() as db:
        client = db.get(User, client_id)
        if client is None or client.profile is None:
            return
        session = MeasurementSession(
            client_id=client.id,
            trainer_id=None,
            updated_by_id=client.id,
            session_date=date.today(),
            source="telegram",
        )
        session.values = measurements.build_values(db, inputs)
        db.add(session)
        db.flush()
        audit.record(
            db,
            client,
            "create",
            "measurement_session",
            session.id,
            {"client_id": client.id, "source": "telegram", "after": audit.session_snapshot(session)},
        )
        db.commit()


def save_question(client_id: int, text: str) -> int:
    with get_sessionmaker()() as db:
        question = Question(client_id=client_id, body=text.strip()[:4000], status="open", source="telegram")
        db.add(question)
        db.commit()
        return question.id


def record_coach_reply(client_id: int, trainer_id: int | None, text: str) -> None:
    """The coach wrote in the group: that answers the player's open Telegram questions."""
    with get_sessionmaker()() as db:
        open_questions = db.scalars(
            select(Question).where(Question.client_id == client_id, Question.source == "telegram", Question.status == "open")
        ).all()
        for q in open_questions:
            q.replies.append(QuestionReply(author_id=trainer_id, body=text.strip()[:4000]))
            q.status = "answered"
        db.commit()


def save_profile_answer(client_id: int, step: str, value) -> str | None:
    """Store one profile answer and return the next step (None when done)."""
    with get_sessionmaker()() as db:
        profile = db.get(ClientProfile, client_id)
        if profile is None:
            return None
        if value is not None:
            setattr(profile, PROFILE_STEPS[step], value)
        profile.telegram_step = next_step(profile, after=step)
        db.commit()
        return profile.telegram_step


def process_message(chat_id: int, text: str, from_user_id: int | None = None) -> IntakeResult:
    client = find_client_by_chat(chat_id)
    if client is None:
        return IntakeResult(NOT_LINKED_GROUP if chat_id < 0 else t.NOT_LINKED)

    if from_user_id is not None and from_user_id == client["coach_telegram_user_id"]:
        record_coach_reply(client["id"], client["trainer_id"], text)
        return IntakeResult(None)

    arabic = is_arabic(text)
    step = client.get("step")
    if step in PROFILE_STEPS:
        ok, value = parse_answer(step, text)
        if ok:
            following = save_profile_answer(client["id"], step, value)
            done = "شكرًا! اكتمل ملفك ✅ أرسل وزنك متى ما أردت، مثل: وزني 82"
            return IntakeResult(question_for(following) if following else done)
        if parse_measurement(text) is None:
            return IntakeResult("لم أفهم الإجابة 🙏\n" + question_for(step))

    values = parse_measurement(text)
    if values is None:
        values = validate_measurement(t.extract_measurement(normalize(text)))
    if values is not None:
        save_measurement(client["id"], values)
        return IntakeResult(t.confirmation(values, arabic))

    question_id = save_question(client["id"], text)
    return IntakeResult(t.not_a_measurement(arabic), question_id)


def handle_message(chat_id: int, text: str, from_user_id: int | None = None) -> str:
    """Reply text only (kept for callers and tests that only need the reply)."""
    return process_message(chat_id, text, from_user_id).reply or ""
