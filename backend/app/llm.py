"""Runs the agents you built in DevAI Desktop, through its local host API.

Same calls DevAI's own flow scheduler makes:
  1. POST {DEVAI_HOST_URL}/api/sessions              -> new session for the agent
  2. POST {DEVAI_HOST_URL}/api/sessions/{id}/chat    -> send the message, read the streamed reply

Needs DevAI Desktop open on the same machine, DEVAI_API_KEY, and the agent ids
(DEVAI_INTAKE_AGENT_ID, DEVAI_ANALYST_AGENT_ID, DEVAI_COACH_AGENT_ID). When something is
missing, callers fall back to fixed templates so the demo keeps working.
"""

import json
import time

import httpx

from app import config

TIMEOUT = httpx.Timeout(120.0, connect=5.0)


class LLMNotConfigured(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


def _headers() -> dict:
    return {"x-api-key": config.DEVAI_API_KEY, "content-type": "application/json"}


def _create_session(client: httpx.Client, agent_id: str, name: str) -> str:
    r = client.post(
        f"{config.DEVAI_HOST_URL}/api/sessions",
        headers=_headers(),
        json={"agentId": agent_id, "name": name, "workspaceMode": "none", "model": config.DEVAI_MODEL},
    )
    if r.status_code not in (200, 201):
        raise LLMError(f"DevAI session failed ({r.status_code}): {r.text[:200]}")
    body = r.json()
    session_id = body.get("sessionId") or body.get("id")
    if not session_id:
        raise LLMError(f"DevAI returned no session id: {r.text[:200]}")
    return session_id


def _read_stream(lines) -> str:
    text, error = "", None
    for line in lines:
        line = line.strip()
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            continue
        try:
            event = json.loads(data)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "content":
            text += event.get("chunk") or event.get("content") or ""
        elif kind == "text-delta":
            text += event.get("delta") or event.get("text") or ""
        elif kind == "error":
            error = event.get("errorText") or event.get("message") or str(event.get("error"))
        elif kind == "tool-approval-request":
            error = "agent asked to approve a tool; give the agent no tools that need approval"
    if error and not text:
        raise LLMError(f"DevAI agent error: {error}")
    return text


def run_agent(agent_id: str, message: str, name: str = "Tahadi") -> str:
    if not config.DEVAI_API_KEY or not agent_id:
        raise LLMNotConfigured("DEVAI_API_KEY or the agent id is not set")
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            session_id = _create_session(client, agent_id, name)
            body = {
                "messages": [
                    {
                        "id": f"tahadi_{int(time.time() * 1000)}",
                        "role": "user",
                        "parts": [{"type": "text", "text": message}],
                    }
                ],
                "agentId": agent_id,
                "modelId": config.DEVAI_MODEL,
                "message": {"role": "user", "content": message},
                "streaming": True,
            }
            headers = {**_headers(), "accept": "text/event-stream"}
            with client.stream(
                "POST", f"{config.DEVAI_HOST_URL}/api/sessions/{session_id}/chat", headers=headers, json=body
            ) as r:
                if r.status_code != 200:
                    raise LLMError(f"DevAI chat failed ({r.status_code}): {r.read()[:200]!r}")
                return _read_stream(r.iter_lines())
    except httpx.HTTPError as exc:
        raise LLMError(f"DevAI host not reachable at {config.DEVAI_HOST_URL}: {exc}") from exc
