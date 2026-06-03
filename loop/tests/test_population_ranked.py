"""Tests for population_ranked: champion / HoF selection must be scoped to the
current population, not the globally-accumulated Elo board."""

from __future__ import annotations

from pokemon_loop.elo import EloBoard
from pokemon_loop.evolution import population_ranked
from pokemon_loop.genome import Genome, Member


def _genome(name: str) -> Genome:
    """Minimal valid 6-member genome — population_ranked only reads .name."""
    m = Member(species="x", ivs={}, evs={}, nature="hardy", moves=[], item="none")
    return Genome(name=name, members=[m for _ in range(6)])


def test_population_ranked_excludes_stale_prior_gen_names():
    """A high-rated name from an earlier generation that is no longer in the
    population must not appear — that is exactly the case the global elo.top()
    used to surface and then silently drop (genome object gone -> skipped)."""
    elo = EloBoard()
    elo._ratings["gen0_old_champ"] = 1200.0  # highest globally, but retired
    elo._ratings["gen1_a"] = 1050.0
    elo._ratings["gen1_b"] = 1010.0

    population = [_genome("gen1_a"), _genome("gen1_b")]

    # The old approach (global top) would have picked the retired name first…
    assert elo.top(2)[0][0] == "gen0_old_champ"

    # …population_ranked correctly restricts to the living population.
    ranked = population_ranked(population, elo)
    names = [n for n, _ in ranked]
    assert names == ["gen1_a", "gen1_b"]
    assert "gen0_old_champ" not in names


def test_population_ranked_sorted_best_first():
    elo = EloBoard()
    elo._ratings = {"a": 1010.0, "b": 1080.0, "c": 1040.0}
    population = [_genome("a"), _genome("b"), _genome("c")]
    assert [n for n, _ in population_ranked(population, elo)] == ["b", "c", "a"]
