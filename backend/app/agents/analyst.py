"""Agent 4 - Progress analyst. Facts and alerts in code, wording from the LLM (or templates)."""

from datetime import date

from app.agents import text as t
from app.db import get_db
from app.rules.progress import compute_facts


def get_client(client_id: str) -> dict | None:
    rows = get_db().table("clients").select("id,name,telegram_chat_id").eq("id", client_id).limit(1).execute().data
    return rows[0] if rows else None


def analyze(client: dict) -> dict:
    rows = (
        get_db().table("measurements").select("date,weight_kg,waist_cm,created_at")
        .eq("client_id", client["id"]).order("date").order("created_at").execute().data
    )
    facts, alerts = compute_facts(rows, date.today())
    summary_ar, summary_en = t.summary(client["name"], facts, alerts)
    return {
        "client_id": client["id"],
        "facts": facts,
        "alerts": alerts,
        "summary_ar": summary_ar,
        "summary_en": summary_en,
    }
