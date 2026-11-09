"""Agent 5 - Coach assistant. Drafts replies; nothing is sent without coach approval."""

from datetime import datetime, timezone

from app.agents import text as t
from app.agents.analyst import analyze
from app.db import get_db


class DraftNotPending(Exception):
    pass


def latest_form_check(client_id: str) -> dict | None:
    rows = (
        get_db().table("form_checks").select("exercise,reps,errors,confidence,created_at")
        .eq("client_id", client_id).order("created_at", desc=True).limit(1).execute().data
    )
    return rows[0] if rows else None


def create_draft(client: dict) -> dict:
    analysis = analyze(client)
    body = t.draft(client["name"], analysis["facts"], analysis["alerts"], latest_form_check(client["id"]))
    return get_db().table("drafts").insert({"client_id": client["id"], "text": body}).execute().data[0]


def list_drafts(status: str | None) -> list[dict]:
    q = get_db().table("drafts").select("*, clients(name)").order("created_at", desc=True)
    if status:
        q = q.eq("status", status)
    rows = q.execute().data
    for r in rows:
        r["client_name"] = (r.pop("clients", None) or {}).get("name")
    return rows


def get_draft(draft_id: str) -> dict | None:
    rows = get_db().table("drafts").select("*").eq("id", draft_id).limit(1).execute().data
    return rows[0] if rows else None


def set_status(draft: dict, status: str) -> dict:
    if draft["status"] != "pending":
        raise DraftNotPending(draft["status"])
    changes = {"status": status}
    if status == "approved":
        changes["sent_at"] = datetime.now(timezone.utc).isoformat()
    # Only update while still pending, so two clicks can't approve twice.
    rows = (
        get_db().table("drafts").update(changes)
        .eq("id", draft["id"]).eq("status", "pending").execute().data
    )
    if not rows:
        raise DraftNotPending("changed")
    return rows[0]
