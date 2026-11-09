"""Telegram webhook router & demo API endpoints.
Implements Muhanad's responsibilities:
- POST /telegram: incoming webhook, forwards text to Saeed's intake agent
- Send approved reply to client via Telegram (bot token in .env)
- GET /summary/{client}: progress analyst summary
- POST /draft/{client}: coach assistant draft
- POST /draft/{client}/approve: mark draft approved and send to client's Telegram
- POST /draft/{client}/reject: mark draft rejected
- POST /form_checks: save squat set to form_checks table
"""

import json
import logging
import os
import urllib.request
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.demo import DemoDraft, DemoFormCheck, DemoMeasurement
from app.services.agents import (
    CHAT_ID_BY_CLIENT,
    CLIENT_CHAT_IDS,
    coach_assistant,
    intake_agent,
    progress_analyst,
)

logger = logging.getLogger("tahadi.telegram")
router = APIRouter(tags=["demo"])


class WebhookPayload(BaseModel):
    message: str | None = None
    chat_id: int | None = None
    client: str | None = None


class FormCheckPayload(BaseModel):
    client: str
    reps: int
    errors: str | None = None


class ApprovePayload(BaseModel):
    text: str | None = None


def send_telegram_message(chat_id: int | str, text: str) -> bool:
    """Send message to client via Telegram bot API using TELEGRAM_BOT_TOKEN from env."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if not bot_token:
        logger.info("[Telegram] TELEGRAM_BOT_TOKEN not set. Simulating message to %s: %s", chat_id, text)
        return True

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.exception("[Telegram] Failed to send message to %s: %s", chat_id, e)
        return False


# ---- Telegram webhook endpoint ----
@router.post("/telegram")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Receives Telegram webhook updates (or direct JSON test payloads)

    and forwards incoming message to Saeed's intake agent.
    """
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    # Extract text and chat_id from standard Telegram update structure
    text = ""
    chat_id = None
    client_name = None

    if "message" in body and isinstance(body["message"], dict):
        # Official Telegram webhook shape: {"message": {"text": "weight 82", "chat": {"id": 12345}}}
        text = body["message"].get("text", "")
        chat_id = body["message"].get("chat", {}).get("id")
    elif "message" in body and isinstance(body["message"], str):
        # Direct payload shape: {"message": "weight 82", "chat_id": 111001, "client": "..."}
        text = body.get("message", "")
        chat_id = body.get("chat_id")
        client_name = body.get("client")
    elif "text" in body:
        text = body.get("text", "")
        chat_id = body.get("chat_id")
        client_name = body.get("client")

    logger.info("[Telegram] Webhook received message='%s' chat_id=%s client=%s", text, chat_id, client_name)

    # Pass to Saeed's intake agent
    result = intake_agent(text=text, client=client_name, chat_id=chat_id, db=db)

    # If message was from a live Telegram chat, send confirmation back to client
    if chat_id and result.get("status") == "success":
        send_telegram_message(chat_id, f"✅ {result.get('message')}")

    return result


# ---- Seed 3 fake clients with 4 weeks of measurements if empty ----
def ensure_seed_data(db: Session):
    try:
        DemoMeasurement.metadata.create_all(bind=db.get_bind(), checkfirst=True)
    except Exception:
        pass
    try:
        existing = db.scalar(select(DemoMeasurement).limit(1))
        if existing:
            return
    except Exception:
        return

    seed_records = [
        # Ahmed Al-Rashidi: 4 weeks
        ("Ahmed Al-Rashidi", "2026-10-12", 89.5),
        ("Ahmed Al-Rashidi", "2026-10-19", 88.2),
        ("Ahmed Al-Rashidi", "2026-10-26", 87.0),
        ("Ahmed Al-Rashidi", "2026-11-02", 86.0),
        # Sara Al-Zahrani: 4 weeks
        ("Sara Al-Zahrani", "2026-10-12", 70.5),
        ("Sara Al-Zahrani", "2026-10-19", 69.8),
        ("Sara Al-Zahrani", "2026-10-26", 68.9),
        ("Sara Al-Zahrani", "2026-11-02", 67.8),
        # Mohammed Al-Otaibi: 4 weeks
        ("Mohammed Al-Otaibi", "2026-10-12", 83.0),
        ("Mohammed Al-Otaibi", "2026-10-19", 84.1),
        ("Mohammed Al-Otaibi", "2026-10-26", 85.0),
        ("Mohammed Al-Otaibi", "2026-11-02", 86.0),
    ]
    for client, dt, wt in seed_records:
        db.add(DemoMeasurement(client=client, date=dt, weight_kg=wt))
    db.commit()


# ---- Progress Analyst summary ----
@router.get("/summary/{client}")
def get_summary(client: str, db: Session = Depends(get_db)):
    """GET /summary/{client} — Progress analyst endpoint."""
    ensure_seed_data(db)

    # Get measurements for this client
    q = select(DemoMeasurement).where(DemoMeasurement.client == client).order_by(DemoMeasurement.date.asc())
    rows = db.scalars(q).all()
    measurements = [{"date": r.date, "weight_kg": r.weight_kg} for r in rows]

    summary_text = progress_analyst(client, db=db)

    return {
        "client": client,
        "summary": summary_text,
        "measurements": measurements,
    }


# ---- Coach Assistant draft ----
@router.post("/draft/{client}")
def post_draft(client: str, db: Session = Depends(get_db)):
    """POST /draft/{client} — Coach assistant endpoint."""
    draft_text = coach_assistant(client, db=db)

    # Save to drafts table
    d = DemoDraft(client=client, text=draft_text, status="pending")
    db.add(d)
    db.commit()
    db.refresh(d)

    return {
        "id": d.id,
        "client": client,
        "text": draft_text,
        "status": "pending",
    }


# ---- Approve draft & send via Telegram ----
@router.post("/draft/{client}/approve")
def approve_draft(client: str, payload: ApprovePayload | None = None, db: Session = Depends(get_db)):
    """POST /draft/{client}/approve — Approve draft and send to client's Telegram."""
    # Find pending draft or use supplied text
    q = select(DemoDraft).where(DemoDraft.client == client).order_by(DemoDraft.id.desc()).limit(1)
    d = db.scalar(q)

    text_to_send = ""
    if payload and payload.text:
        text_to_send = payload.text
    elif d:
        text_to_send = d.text
    else:
        text_to_send = coach_assistant(client, db=db)

    if d:
        d.status = "approved"
        d.text = text_to_send
        db.commit()

    # Send to client's Telegram
    chat_id = CHAT_ID_BY_CLIENT.get(client, 111001)
    telegram_sent = send_telegram_message(chat_id, text_to_send)

    return {
        "status": "approved",
        "client": client,
        "telegram_sent": telegram_sent,
        "chat_id": chat_id,
        "text": text_to_send,
    }


# ---- Reject draft ----
@router.post("/draft/{client}/reject")
def reject_draft(client: str, db: Session = Depends(get_db)):
    """POST /draft/{client}/reject — Mark draft as rejected."""
    q = select(DemoDraft).where(DemoDraft.client == client).order_by(DemoDraft.id.desc()).limit(1)
    d = db.scalar(q)
    if d:
        d.status = "rejected"
        db.commit()
    return {"status": "rejected", "client": client}


# ---- Form checks saving ----
@router.post("/form_checks")
@router.post("/demo/form-checks")
def save_form_check(payload: FormCheckPayload, db: Session = Depends(get_db)):
    """POST /form_checks — Save squat set to form_checks table."""
    fc = DemoFormCheck(client=payload.client, reps=payload.reps, errors=payload.errors)
    db.add(fc)
    db.commit()
    db.refresh(fc)
    return {"status": "success", "id": fc.id, "client": fc.client, "reps": fc.reps}


# ---- Get form checks list ----
@router.get("/form_checks")
@router.get("/demo/form-checks")
def get_form_checks(client: str | None = None, db: Session = Depends(get_db)):
    q = select(DemoFormCheck)
    if client:
        q = q.where(DemoFormCheck.client == client)
    q = q.order_by(DemoFormCheck.id.desc())
    rows = db.scalars(q).all()
    return [{"id": r.id, "client": r.client, "reps": r.reps, "errors": r.errors} for r in rows]
