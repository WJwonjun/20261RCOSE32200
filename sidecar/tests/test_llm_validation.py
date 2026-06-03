"""Tests for the real-LLM path's guard rails: legal-action validation and the
prompt exposing the legal action list."""

from __future__ import annotations

from pokemon_sidecar.client import _is_legal
from pokemon_sidecar.prompt import build_messages
from pokemon_sidecar.schemas import Action

LEGAL = [
    {"action": "move", "target": 0},
    {"action": "move", "target": 2},
    {"action": "switch", "target": 1},
]


def test_is_legal_accepts_matching_pair() -> None:
    assert _is_legal(Action(action="move", target=0), LEGAL)
    assert _is_legal(Action(action="switch", target=1), LEGAL)


def test_is_legal_rejects_unlisted_move_target() -> None:
    # move target 1 is not legal this turn (e.g. out of PP)
    assert not _is_legal(Action(action="move", target=1), LEGAL)


def test_is_legal_rejects_wrong_action_kind() -> None:
    # switching to target 0 is not offered (target 0 is a move, not a switch)
    assert not _is_legal(Action(action="switch", target=0), LEGAL)


def test_is_legal_rejects_none() -> None:
    assert not _is_legal(None, LEGAL)


def test_prompt_includes_legal_actions() -> None:
    turn_state = {
        "opponent_visible": {},
        "legal_actions": LEGAL,
        "turn_no": 1,
        "side": "A",
    }
    _system, user = build_messages("rules", "team", turn_state)
    content = user[0]["content"]
    assert "Legal actions" in content
    # The actual legal pairs must be present so the model can pick from them.
    assert '"action": "switch"' in content
    assert "idx_in_selection" in content
