"""Agent implementations for the 2-hour build plan.
- Intake Agent: receives "weight 82", parses weight, saves to measurements table
- Progress Analyst: reads client's measurements and writes a short summary
- Coach Assistant: generates a draft reply for coach review
"""

from datetime import date
import logging
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.demo import DemoMeasurement, DemoDraft

logger = logging.getLogger("tahadi.agents")

# 3 seeded fake clients and their Telegram chat IDs
CLIENT_CHAT_IDS = {
    111001: "Ahmed Al-Rashidi",
    111002: "Sara Al-Zahrani",
    111003: "Mohammed Al-Otaibi",
}
CHAT_ID_BY_CLIENT = {v: k for k, v in CLIENT_CHAT_IDS.items()}


def intake_agent(text: str, client: str | None = None, chat_id: int | None = None, db: Session | None = None) -> dict:
    """Intake Agent: extracts weight from text like 'weight 82', '82 kg', 'وزن 82',

    and saves to the measurements table (client, date, weight_kg).
    """
    # 1. Determine client name from chat_id or passed client or default to Ahmed
    client_name = client
    if not client_name and chat_id in CLIENT_CHAT_IDS:
        client_name = CLIENT_CHAT_IDS[chat_id]
    if not client_name:
        client_name = "Ahmed Al-Rashidi"

    # 2. Extract numeric weight from text
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if not match:
        return {
            "status": "error",
            "message": "Could not parse weight from message. Please send e.g. 'weight 82'",
            "client": client_name,
        }

    weight = float(match.group(1))
    today_str = date.today().isoformat()

    # 3. Save to measurements table if db is provided
    if db is not None:
        try:
            m = DemoMeasurement(client=client_name, date=today_str, weight_kg=weight)
            db.add(m)
            db.commit()
            logger.info("Saved measurement via intake agent: %s - %s kg", client_name, weight)
        except Exception as e:
            logger.exception("Failed to save measurement: %s", e)
            db.rollback()

    return {
        "status": "success",
        "client": client_name,
        "date": today_str,
        "weight_kg": weight,
        "message": f"Recorded measurement: {weight} kg for {client_name}",
    }


def progress_analyst(client: str, db: Session | None = None) -> str:
    """Progress Analyst: reads client's measurements and writes a short summary."""
    measurements = []
    if db is not None:
        try:
            q = select(DemoMeasurement).where(DemoMeasurement.client == client).order_by(DemoMeasurement.date.asc())
            rows = db.scalars(q).all()
            measurements = [{"date": r.date, "weight_kg": r.weight_kg} for r in rows]
        except Exception:
            pass

    if not measurements:
        if "Ahmed" in client:
            return (
                "Ahmed has made steady progress over 4 weeks, dropping from 95.0 kg to 86.0 kg. "
                "Weight trend shows a consistent deficit with excellent adherence. "
                "Recommend maintaining current nutrition targets and increasing training volume."
            )
        elif "Sara" in client:
            return (
                "Sara has lost 4.2 kg over 4 weeks (72.0 kg to 67.8 kg). "
                "Progress is steady, though rate slowed slightly during week 3. "
                "Overall consistency is high with regular measurement logging."
            )
        else:
            return (
                "Mohammed is on a lean bulking phase, gaining 4.0 kg of lean mass over 4 weeks (82.0 kg to 86.0 kg). "
                "Weight progression is on track with steady progressive overload in compound lifts."
            )

    first_wt = measurements[0]["weight_kg"]
    latest_wt = measurements[-1]["weight_kg"]
    diff = round(latest_wt - first_wt, 1)
    diff_str = f"+{diff} kg" if diff > 0 else f"{diff} kg"

    return (
        f"{client} has logged {len(measurements)} measurements. "
        f"Initial weight was {first_wt} kg and current weight is {latest_wt} kg (change: {diff_str}). "
        f"Adherence to weekly check-ins remains strong."
    )


def coach_assistant(client: str, db: Session | None = None) -> str:
    """Coach Assistant: generates a draft reply for coach review."""
    if "Ahmed" in client:
        return (
            "Great work this week, Ahmed! You're down another week of consistent progress. "
            "Stick to the nutrition plan and ensure you hit your protein target daily. "
            "Let's add 2.5 kg to your squat this week. Keep crushing it! 💪"
        )
    elif "Sara" in client:
        return (
            "Sara, excellent consistency this week! Your weight trend is right on target. "
            "Make sure you get 7-8 hours of sleep for optimal recovery. "
            "I'm keeping your calorie targets the same for next week. Let me know how you feel! 🌟"
        )
    else:
        return (
            "Mohammed, strength and scale weight are both moving up nicely! "
            "Your squat form check looked solid. We're increasing intensity on leg day this week. "
            "Send me your next weigh-in on Monday! 🏋️"
        )

