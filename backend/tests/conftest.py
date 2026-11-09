import pytest

from app import config


@pytest.fixture(autouse=True)
def offline_agents(monkeypatch):
    """Tests never call the real DevAI agents, even when backend/.env has a key.
    Live agent checks: python -m scripts.check_agents"""
    monkeypatch.setattr(config, "DEVAI_API_KEY", "")
