"""DevAI connection: stream parsing and template fallback (no DevAI host needed)."""

import pytest

from app import config, llm
from app.agents import text


def test_reads_content_and_text_delta_events():
    lines = [
        ": comment",
        'data: {"type": "content", "chunk": "{\\"weight_kg\\": "}',
        'data: {"type": "text-delta", "delta": "82}"}',
        "data: [DONE]",
    ]
    assert llm._read_stream(lines) == '{"weight_kg": 82}'


def test_stream_error_without_text_raises():
    with pytest.raises(llm.LLMError):
        llm._read_stream(['data: {"type": "error", "errorText": "bad key"}'])


def test_not_configured_uses_templates(monkeypatch):
    monkeypatch.setattr(config, "DEVAI_API_KEY", "")
    assert text.ask_agent("coach", "{}") is None
    ar, en = text.summary("Omar Haddad", {"entries": 0}, [])
    assert "Omar Haddad" in en


def test_agent_reply_is_used_when_valid(monkeypatch):
    monkeypatch.setattr(
        llm, "run_agent", lambda agent_id, msg, name="": '```json\n{"summary_ar": "ملخص", "summary_en": "Summary"}\n```'
    )
    assert text.summary("Omar", {"entries": 1}, []) == ("ملخص", "Summary")


def test_bad_agent_reply_falls_back(monkeypatch):
    monkeypatch.setattr(llm, "run_agent", lambda agent_id, msg, name="": "not json")
    ar, en = text.summary("Omar", {"entries": 0}, [])
    assert en == "No measurements yet for Omar."


def test_agent_failure_falls_back(monkeypatch):
    def boom(*a, **k):
        raise llm.LLMError("host down")

    monkeypatch.setattr(llm, "run_agent", boom)
    body = text.draft("Omar Haddad", {"entries": 3}, ["stalled"], None)
    assert body.startswith("مرحبًا Omar")


def test_model_failure_finish_event_raises():
    """DevAI reports a failed model call as a 'finish' event with no text."""
    lines = [
        'data: {"type":"start","messageId":"m1"}',
        'data: {"type":"finish","finishReason":"error","messageMetadata":{"outcome":{"status":"incomplete",'
        '"reason":"failed","error":{"code":"model-failed","retryable":true,"phase":"before-content"}}}}',
        "data: [DONE]",
    ]
    with pytest.raises(llm.LLMError, match="model-failed"):
        llm._read_stream(lines)
