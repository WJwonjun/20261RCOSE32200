from __future__ import annotations

import os

import pytest

from pokemon_sidecar.client import LLMClient
from pokemon_sidecar.schemas import LLMCallResult, TurnState

SAMPLE_TURN_STATE = TurnState(
    rulebook_hash="abc123",
    acting_team={"pokemon": [{"name": "Pikachu", "hp": 100}]},
    opponent_visible={"pokemon": [{"name": "Charmander", "hp": 80}]},
    turn_no=1,
    side="player1",
    legal_actions=[{"action": "move", "target": 0}, {"action": "move", "target": 1}],
)


@pytest.fixture(autouse=True)
def force_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEMON_SIDECAR_STUB", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


async def test_stub_returns_first_legal_action() -> None:
    client = LLMClient()
    result = await client.choose_action(
        turn_state=SAMPLE_TURN_STATE,
        rulebook_path="/dev/null",
        team_spec="Pikachu @ Life Orb",
        idempotency_key="test-key-001",
    )

    assert isinstance(result, LLMCallResult)
    assert result.action is not None
    assert result.action.action in ("move", "switch")
    assert isinstance(result.action.target, int)
    assert result.action.target == 0
    assert result.action.reason == "stub"
    assert result.failure_reason is None
    assert result.idempotency_key == "test-key-001"
    assert result.latency_ms == 0
    assert result.cached_tokens == 0
    assert result.prompt_tokens == 0


async def test_stub_schema_valid() -> None:
    client = LLMClient()
    result = await client.choose_action(
        turn_state=SAMPLE_TURN_STATE,
        rulebook_path="/dev/null",
        team_spec="",
        idempotency_key="test-key-002",
    )
    # Round-trip through model_dump to confirm schema validity
    dumped = result.model_dump()
    restored = LLMCallResult(**dumped)
    assert restored.action is not None
    assert restored.action.action == result.action.action
