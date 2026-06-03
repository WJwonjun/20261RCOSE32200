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


REALISTIC_TURN_STATE = TurnState(
    rulebook_hash="x",
    acting_team={
        "active_slot": 0,
        "party": [
            {
                "slot": 0,
                "is_active": True,
                "type1": "Fire",
                "type2": "Flying",
                "moves": [
                    {"name": "Ember", "type": "Fire", "power": 40},        # STAB -> 60
                    {"name": "Earthquake", "type": "Ground", "power": 100},  # 100
                    {"name": "Hurricane", "type": "Flying", "power": 110},   # STAB -> 165 (best)
                    {"name": "Growl", "type": "Normal", "power": 0},         # status
                ],
            }
        ],
    },
    opponent_visible={"active_slot": 0, "party": []},
    turn_no=1,
    side="A",
    legal_actions=[
        {"action": "move", "target": 0},
        {"action": "move", "target": 1},
        {"action": "move", "target": 2},
        {"action": "move", "target": 3},
        {"action": "switch", "target": 1},
    ],
)


async def test_stub_picks_highest_power_stab_move() -> None:
    """Stub must choose the strongest STAB-weighted move, not always slot 0."""
    client = LLMClient()
    result = await client.choose_action(
        turn_state=REALISTIC_TURN_STATE,
        rulebook_path="/dev/null",
        team_spec="",
        idempotency_key="k",
    )
    assert result.action is not None
    assert result.action.action == "move"
    # Hurricane (110 * 1.5 STAB = 165) beats Earthquake (100) and Ember (60).
    assert result.action.target == 2


async def test_stub_falls_back_to_switch_when_no_damaging_move() -> None:
    """With only a status move + a switch legal, the stub takes the switch."""
    ts = TurnState(
        rulebook_hash="x",
        acting_team={
            "party": [
                {
                    "is_active": True,
                    "type1": "Normal",
                    "type2": None,
                    "moves": [{"name": "Growl", "type": "Normal", "power": 0}],
                }
            ]
        },
        opponent_visible={"party": []},
        turn_no=1,
        side="A",
        legal_actions=[{"action": "switch", "target": 1}],
    )
    client = LLMClient()
    result = await client.choose_action(ts, "/dev/null", "", "k")
    assert result.action is not None
    assert result.action.action == "switch"
    assert result.action.target == 1


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
