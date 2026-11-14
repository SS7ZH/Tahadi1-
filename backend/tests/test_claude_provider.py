"""Claude API provider: selection, request shape, and fallbacks. No network: the client is faked."""

from types import SimpleNamespace

import pytest

from app import config, llm
from app.agents import text


class FakeClaude:
    """Records the request and returns a canned reply."""

    def __init__(self, reply="", stop_reason="end_turn"):
        self.calls = []
        self.reply, self.stop_reason = reply, stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            stop_reason=self.stop_reason,
            content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=self.reply)],
        )


@pytest.fixture()
def claude(monkeypatch):
    def make(reply="", stop_reason="end_turn"):
        fake = FakeClaude(reply, stop_reason)
        monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setattr(config, "LLM_PROVIDER", "claude")
        monkeypatch.setattr(llm, "_claude_client", lambda key: fake)
        return fake

    return make


def test_provider_selection(monkeypatch):
    assert llm.provider() == "devai"  # conftest: no keys, nothing chosen
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "k")
    assert llm.provider() == "claude"  # a Claude key alone selects Claude
    monkeypatch.setattr(config, "LLM_PROVIDER", "devai")
    assert llm.provider() == "devai"  # an explicit choice wins


@pytest.mark.parametrize("agent", ["intake", "analyst", "coach"])
def test_every_agent_has_its_exported_prompt(agent):
    prompt = llm.system_prompt(agent)
    for section in ("## Identity", "## Scope", "## Examples"):
        assert section in prompt


def test_request_uses_the_agent_prompt_model_and_fallbacks(claude):
    fake = claude('{"weight_kg": 82.5, "waist_cm": null}')
    assert llm.ask("intake", "وزني اثنين وثمانين ونص") == '{"weight_kg": 82.5, "waist_cm": null}'
    call = fake.calls[0]
    assert call["system"] == llm.system_prompt("intake")
    assert call["model"] == config.CLAUDE_MODEL
    assert call["messages"] == [{"role": "user", "content": "وزني اثنين وثمانين ونص"}]
    assert call["output_config"] == {"effort": config.CLAUDE_EFFORT}
    assert call["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in call["betas"]


def test_intake_fallback_parser_on_claude(claude):
    claude('{"weight_kg": 82.5, "waist_cm": null}')
    assert text.extract_measurement("وزني اثنين وثمانين ونص") == {"weight_kg": 82.5, "waist_cm": None}


def test_summary_and_draft_marked_as_agent(claude):
    claude('{"summary_ar": "ملخص", "summary_en": "Summary"}')
    assert text.summary_result("Omar", {"entries": 1}, [])["source"] == "agent"
    claude("مرحبًا عمر 👋\nاستمر.")
    body, source = text.draft_result("Omar Haddad", {"entries": 1}, [], None)
    assert source == "agent" and body.startswith("مرحبًا عمر")


def test_refusal_falls_back_to_template(claude):
    claude("", stop_reason="refusal")
    with pytest.raises(llm.LLMError):
        llm.ask("coach", "{}")
    body, source = text.draft_result("Omar Haddad", {"entries": 0}, [], None)
    assert source == "template" and body.startswith("مرحبًا Omar")


def test_missing_key_uses_template(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "claude")
    with pytest.raises(llm.LLMNotConfigured):
        llm.ask("analyst", "{}")
    assert text.summary_result("Omar", {"entries": 0}, [])["source"] == "template"


def test_agent_summary_endpoint_runs_on_claude(client, users, auth, claude):
    fake = claude('{"summary_ar": "ملخص كلود", "summary_en": "Claude summary"}')
    r = client.get(f"/api/v1/clients/{users['client_a'].id}/agent-summary", headers=auth("trainer_a"))
    assert r.status_code == 200
    assert r.json()["source"] == "agent" and r.json()["summary_en"] == "Claude summary"
    assert fake.calls[0]["system"] == llm.system_prompt("analyst")
