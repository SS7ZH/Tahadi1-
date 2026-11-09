"""Agent 1 - Intake. Turns a Telegram message into a saved measurement."""

from datetime import date

from app.agents import text as t
from app.db import get_db
from app.rules.parsing import is_arabic, normalize, parse_measurement, validate_measurement


def find_client_by_chat(chat_id: int) -> dict | None:
    rows = get_db().table("clients").select("id,name").eq("telegram_chat_id", chat_id).limit(1).execute().data
    return rows[0] if rows else None


def save_measurement(client_id: str, values: dict) -> None:
    get_db().table("measurements").insert(
        {
            "client_id": client_id,
            "date": date.today().isoformat(),
            "weight_kg": values.get("weight_kg"),
            "waist_cm": values.get("waist_cm"),
            "source": "telegram",
        }
    ).execute()


def handle_message(chat_id: int, text: str) -> str:
    client = find_client_by_chat(chat_id)
    if client is None:
        return t.NOT_LINKED

    arabic = is_arabic(text)
    values = parse_measurement(text)
    if values is None:
        values = validate_measurement(t.extract_measurement(normalize(text)))
    if values is None:
        return t.not_a_measurement(arabic)

    save_measurement(client["id"], values)
    return t.confirmation(values, arabic)
