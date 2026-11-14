"""Runs the three agents (intake, analyst, coach) on one of two providers.

* claude - the Claude API, with each agent's instructions from app/agents/prompts/<agent>.md
           (exported from DevAI Desktop by scripts/export_devai_prompts.py). Works anywhere,
           including Render. Needs ANTHROPIC_API_KEY.
* devai  - the agents inside DevAI Desktop, through its local host API (only on the machine
           where DevAI Desktop is open). Same calls DevAI's own flow scheduler makes:
             1. POST {DEVAI_HOST_URL}/api/sessions              -> new session for the agent
             2. POST {DEVAI_HOST_URL}/api/sessions/{id}/chat    -> send the message, read the stream

LLM_PROVIDER picks one; when unset, Claude is used if ANTHROPIC_API_KEY is set, else DevAI.
When the chosen provider is not configured or fails, callers fall back to fixed templates.
"""

import json
import time
from functools import lru_cache
from pathlib import Path

import anthropic
import httpx

from app import config

PROMPTS = Path(__file__).resolve().parent / "agents" / "prompts"

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
        elif kind == "finish" and event.get("finishReason") == "error":
            # e.g. {"outcome": {"status": "incomplete", "error": {"code": "model-failed", ...}}}
            outcome = (event.get("messageMetadata") or {}).get("outcome") or {}
            code = (outcome.get("error") or {}).get("code") or outcome.get("reason") or "unknown"
            error = f"DevAI model call failed ({code}); check DevAI Desktop's connection (VPN / API key)"
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


# ---------------------------------------------------------------- provider selection

def provider() -> str:
    """'claude' or 'devai'."""
    chosen = (config.LLM_PROVIDER or "").strip().lower()
    if chosen in ("claude", "devai"):
        return chosen
    return "claude" if config.ANTHROPIC_API_KEY else "devai"


def ask(agent: str, message: str) -> str:
    """Run one agent ('intake' | 'analyst' | 'coach') on the configured provider."""
    if provider() == "claude":
        return run_claude(agent, message)
    return run_agent(config.AGENT_IDS[agent], message, name=f"Tahadi {agent}")


# ---------------------------------------------------------------- Claude API

@lru_cache
def system_prompt(agent: str) -> str:
    path = PROMPTS / f"{agent}.md"
    if not path.is_file():
        raise LLMNotConfigured(f"missing agent prompt {path.name}; run python -m scripts.export_devai_prompts")
    return path.read_text(encoding="utf-8")


@lru_cache
def _claude_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)


def run_claude(agent: str, message: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise LLMNotConfigured("ANTHROPIC_API_KEY is not set")
    try:
        response = _claude_client(config.ANTHROPIC_API_KEY).beta.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=16000,
            system=system_prompt(agent),
            messages=[{"role": "user", "content": message}],
            # Short, rule-bound tasks: low effort keeps replies fast and cheap.
            output_config={"effort": config.CLAUDE_EFFORT},
            # If a request is declined by a safety classifier, the API retries it on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as exc:
        raise LLMError("Claude API rejected the key (401); check ANTHROPIC_API_KEY") from exc
    except anthropic.RateLimitError as exc:
        raise LLMError("Claude API rate limit (429)") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Claude API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError(f"Claude API not reachable: {exc}") from exc
    if response.stop_reason == "refusal":
        raise LLMError("Claude declined the request")
    return "".join(block.text for block in response.content if block.type == "text")
