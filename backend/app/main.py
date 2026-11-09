"""Tahadi agent backend - 9 endpoints (cap 10, ADR-0007)."""

from typing import Literal
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app import config
from app.agents import coach
from app.agents.analyst import analyze, get_client
from app.agents.intake import handle_message
from app.db import get_db

app = FastAPI(title="Tahadi agent backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- models ----------

class TelegramMessage(BaseModel):
    chat_id: int
    text: str = Field(min_length=1, max_length=2000)


class FormCheckIn(BaseModel):
    client_id: UUID
    exercise: str = "squat"
    reps: int = Field(ge=0, le=500)
    errors: list[dict] = []
    confidence: float = Field(ge=0, le=1)


def _client_or_404(client_id: UUID) -> dict:
    client = get_client(str(client_id))
    if client is None:
        raise HTTPException(404, "Client not found")
    return client


def _draft_or_404(draft_id: UUID) -> dict:
    draft = coach.get_draft(str(draft_id))
    if draft is None:
        raise HTTPException(404, "Draft not found")
    return draft


# ---------- endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/clients")
def list_clients():
    return get_db().table("clients").select("id,name,telegram_chat_id").order("name").execute().data


@app.post("/telegram/message")
def telegram_message(body: TelegramMessage):
    return {"reply": handle_message(body.chat_id, body.text)}


@app.get("/summary/{client_id}")
def summary(client_id: UUID):
    return analyze(_client_or_404(client_id))


@app.post("/draft/{client_id}", status_code=201)
def create_draft(client_id: UUID):
    return coach.create_draft(_client_or_404(client_id))


@app.get("/drafts")
def drafts(status: Literal["pending", "approved", "rejected"] | None = None):
    return coach.list_drafts(status)


def _set_status(draft_id: UUID, status: str) -> dict:
    try:
        return coach.set_status(_draft_or_404(draft_id), status)
    except coach.DraftNotPending:
        raise HTTPException(409, "Draft is no longer pending")


@app.post("/drafts/{draft_id}/approve")
def approve(draft_id: UUID):
    draft = _set_status(draft_id, "approved")
    client = get_client(draft["client_id"]) or {}
    return {"draft": draft, "telegram_chat_id": client.get("telegram_chat_id")}


@app.post("/drafts/{draft_id}/reject")
def reject(draft_id: UUID):
    return _set_status(draft_id, "rejected")


@app.post("/form-checks", status_code=201)
def form_check(body: FormCheckIn):
    _client_or_404(body.client_id)
    row = body.model_dump(mode="json")
    return get_db().table("form_checks").insert(row).execute().data[0]
