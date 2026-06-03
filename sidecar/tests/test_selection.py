"""Tests for the team-preview (6 -> 3) selection path: stub heuristic,
validation, and the LLMClient.choose_selection entry point in stub mode."""

from __future__ import annotations

import pytest

from pokemon_sidecar.client import LLMClient, _stub_selection, _valid_selection


def _party(totals: list[int]) -> list[dict]:
    return [
        {"slot": i, "name": f"p{i}", "stats": {"hp": t}}
        for i, t in enumerate(totals)
    ]


@pytest.fixture(autouse=True)
def force_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEMON_SIDECAR_STUB", "1")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_valid_selection_rules() -> None:
    assert _valid_selection([0, 1, 2], 6)
    assert _valid_selection([5, 0, 3], 6)
    assert not _valid_selection([0, 1, 1], 6)   # duplicate
    assert not _valid_selection([0, 1, 6], 6)   # out of range
    assert not _valid_selection([0, 1], 6)      # wrong length
    assert not _valid_selection(None, 6)


def test_stub_selection_picks_strongest_three() -> None:
    state = {"side": "A", "party": _party([300, 700, 400, 800, 100, 500]), "select_count": 3}
    r = _stub_selection(state, "k")
    # totals: slot3=800, slot1=700, slot5=500
    assert r.selection == [3, 1, 5]
    assert r.lead_idx_in_party == 3
    assert r.failure_reason is None


def test_stub_selection_tiebreak_by_index() -> None:
    state = {"side": "A", "party": _party([100, 100, 100, 100, 100, 100]), "select_count": 3}
    r = _stub_selection(state, "k")
    assert r.selection == [0, 1, 2]


def test_stub_selection_too_few_is_schema_violation() -> None:
    state = {"side": "A", "party": _party([100, 200]), "select_count": 3}
    r = _stub_selection(state, "k")
    assert r.selection is None
    assert r.failure_reason == "schema_violation"


async def test_choose_selection_stub_roundtrip() -> None:
    client = LLMClient()
    state = {"side": "B", "party": _party([100, 900, 200, 50, 600, 300]), "select_count": 3}
    r = await client.choose_selection(
        selection_state=state,
        rulebook_path="/dev/null",
        team_spec="",
        idempotency_key="sel-key",
    )
    assert r.selection == [1, 4, 5]  # 900, 600, 300
    assert r.lead_idx_in_party == 1
    assert r.idempotency_key == "sel-key"
    # distinct, valid party slots
    assert len(set(r.selection)) == 3
    assert all(0 <= i < 6 for i in r.selection)
