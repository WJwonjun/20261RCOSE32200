"""Tests for EloBoard."""

from __future__ import annotations

import pytest

from pokemon_loop.elo import EloBoard


def test_equal_rating_win_shifts_by_16():
    """Two teams at 1000: winner gains 16, loser loses 16 (K=32)."""
    board = EloBoard()
    board.update("alice", "bob", k=32)
    assert abs(board.get("alice") - 1016.0) < 0.01
    assert abs(board.get("bob") - 984.0) < 0.01


def test_underdog_win_shifts_more():
    """Underdog (lower rating) winning gains more than 16."""
    board = EloBoard()
    board._ratings["strong"] = 1200.0
    board._ratings["weak"] = 800.0
    board.update("weak", "strong", k=32)
    # Expected change for underdog: K * (1 - E_underdog)
    # E_underdog = 1 / (1 + 10^((1200-800)/400)) = 1/(1+10) ≈ 0.0909
    # gain ≈ 32 * (1 - 0.0909) ≈ 29.09
    assert board.get("weak") > 800.0 + 16.0
    assert board.get("strong") < 1200.0 - 16.0


def test_favourite_win_shifts_less():
    """Favourite (higher rating) winning gains less than 16."""
    board = EloBoard()
    board._ratings["strong"] = 1200.0
    board._ratings["weak"] = 800.0
    board.update("strong", "weak", k=32)
    # E_strong ≈ 0.909; gain ≈ 32*(1-0.909) ≈ 2.91
    assert board.get("strong") > 1200.0
    assert board.get("strong") < 1200.0 + 16.0


def test_new_team_defaults_to_1000():
    board = EloBoard()
    assert board.get("unknown_team") == 1000.0


def test_top_n_sorted_descending():
    board = EloBoard()
    board._ratings = {"a": 1100.0, "b": 900.0, "c": 1050.0, "d": 950.0}
    top2 = board.top(2)
    assert top2[0][0] == "a"
    assert top2[1][0] == "c"
    assert len(top2) == 2


def test_multiple_updates_accumulate():
    board = EloBoard()
    # Alice wins 5 times against Bob
    for _ in range(5):
        board.update("alice", "bob", k=32)
    assert board.get("alice") > 1050.0
    assert board.get("bob") < 950.0


def test_draw_between_equal_teams_is_noop():
    """Equal-rated teams that draw keep their ratings (score 0.5 == expected 0.5)."""
    board = EloBoard()
    board.update_draw("alice", "bob", k=32)
    assert abs(board.get("alice") - 1000.0) < 0.01
    assert abs(board.get("bob") - 1000.0) < 0.01


def test_draw_is_symmetric_and_not_a_win():
    """A draw must not credit either side a decisive win; it shifts toward parity."""
    board = EloBoard()
    board._ratings["strong"] = 1200.0
    board._ratings["weak"] = 800.0
    board.update_draw("strong", "weak", k=32)
    # Drawing as the favourite loses points; as the underdog gains points.
    assert board.get("strong") < 1200.0
    assert board.get("weak") > 800.0
    # Total rating is conserved (zero-sum), unlike the old "A always wins" path.
    assert abs((board.get("strong") + board.get("weak")) - 2000.0) < 0.01


def test_weight_scales_update():
    board1 = EloBoard()
    board2 = EloBoard()
    board1.update("a", "b", k=32, weight=1.0)
    board2.update("a", "b", k=32, weight=2.0)
    # weight=2 should produce double the shift
    delta1 = board1.get("a") - 1000.0
    delta2 = board2.get("a") - 1000.0
    assert abs(delta2 - 2 * delta1) < 0.01
