"""Tests for provider selection / OpenAI-compatible wiring (no network)."""

from __future__ import annotations

import pytest

from pokemon_sidecar.client import (
    CHOOSE_ACTION_TOOL,
    _flatten_messages,
    _openai_config,
    _openai_tool,
    _provider,
)

_KEYS = ["POKEMON_SIDECAR_STUB", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
         "GROQ_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL", "POKEMON_SIDECAR_MODEL"]


@pytest.fixture(autouse=True)
def clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k in _KEYS:
        monkeypatch.delenv(k, raising=False)


def test_provider_defaults_to_stub_with_no_keys() -> None:
    assert _provider() == "stub"
    assert _openai_config() is None


def test_stub_env_forces_stub_even_with_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEMON_SIDECAR_STUB", "1")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    assert _provider() == "stub"


def test_gemini_key_selects_openai_with_default_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "free-key")
    assert _provider() == "openai"
    base_url, api_key, model = _openai_config()
    assert "generativelanguage.googleapis.com" in base_url
    assert api_key == "free-key"
    assert model == "gemini-2.0-flash"


def test_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("POKEMON_SIDECAR_MODEL", "gemini-2.5-flash")
    assert _openai_config()[2] == "gemini-2.5-flash"


def test_openai_key_takes_precedence_over_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic")
    assert _provider() == "anthropic"
    monkeypatch.setenv("GEMINI_API_KEY", "gemini")
    assert _provider() == "openai"  # free key wins


def test_ollama_via_openai_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "ollama")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    base_url, api_key, _ = _openai_config()
    assert base_url == "http://localhost:11434/v1"
    assert api_key == "ollama"


def test_openai_tool_conversion() -> None:
    t = _openai_tool(CHOOSE_ACTION_TOOL)
    assert t["type"] == "function"
    assert t["function"]["name"] == "choose_action"
    assert t["function"]["parameters"] == CHOOSE_ACTION_TOOL["input_schema"]


def test_flatten_messages_merges_system_blocks() -> None:
    system_blocks = [{"type": "text", "text": "RULES"}, {"type": "text", "text": "TEAM"}]
    user_messages = [{"role": "user", "content": "go"}]
    msgs = _flatten_messages(system_blocks, user_messages)
    assert msgs[0]["role"] == "system"
    assert "RULES" in msgs[0]["content"] and "TEAM" in msgs[0]["content"]
    assert msgs[1] == {"role": "user", "content": "go"}
