"""Tests for genome.py: random_genome, mutate, crossover.

Uses a tiny mock Palette (3 species with explicit learnsets) — never loads the real DB.
This keeps tests offline and fast.
"""

from __future__ import annotations

import random

import pytest

from pokemon_loop.genome import Genome, Member, crossover, mutate, random_genome
from pokemon_loop.palette import MoveEntry, Palette, SpeciesEntry


# ---------------------------------------------------------------------------
# Minimal mock Palette: 3 species (each 6+ moves), 10 items, 5 natures
# ---------------------------------------------------------------------------

def _make_move(mid: str) -> MoveEntry:
    return MoveEntry(
        id=mid,
        display_name=mid.replace("_", " ").title(),
        type="normal",
        category="physical",
        power=50,
        accuracy=100,
        pp_max=20,
        priority=0,
    )


def _make_species(sid: str, move_ids: list[str]) -> SpeciesEntry:
    return SpeciesEntry(
        id=sid,
        display_name=sid.replace("_", " ").title(),
        dex=1,
        types=("normal",),
        base_stats={"hp": 80, "atk": 80, "def": 80, "spa": 80, "spd": 80, "spe": 80},
        learnset=tuple(move_ids),
    )


# Species A: 8 moves
_SPECIES_A_MOVES = [f"move_a{i}" for i in range(8)]
# Species B: 6 moves
_SPECIES_B_MOVES = [f"move_b{i}" for i in range(6)]
# Species C: 5 moves (enough for 4 + 1 spare, no padding needed)
_SPECIES_C_MOVES = [f"move_c{i}" for i in range(5)]

_ALL_MOVE_IDS = _SPECIES_A_MOVES + _SPECIES_B_MOVES + _SPECIES_C_MOVES
_ALL_MOVES = {mid: _make_move(mid) for mid in _ALL_MOVE_IDS}

_SPECIES_A = _make_species("species_a", _SPECIES_A_MOVES)
_SPECIES_B = _make_species("species_b", _SPECIES_B_MOVES)
_SPECIES_C = _make_species("species_c", _SPECIES_C_MOVES)

# Need 6 species for random_genome; add 3 more minimal ones
_EXTRA_SPECIES = {
    f"species_{i}": _make_species(f"species_{i}", [f"move_x{i}_{j}" for j in range(6)])
    for i in range(3)
}
_EXTRA_MOVES = {
    mid: _make_move(mid)
    for sp in _EXTRA_SPECIES.values()
    for mid in sp.learnset
}

_ALL_SPECIES = {
    "species_a": _SPECIES_A,
    "species_b": _SPECIES_B,
    "species_c": _SPECIES_C,
    **_EXTRA_SPECIES,
}
_ALL_MOVES_FULL = {**_ALL_MOVES, **_EXTRA_MOVES}

MOCK_PALETTE = Palette(
    species=_ALL_SPECIES,
    moves=_ALL_MOVES_FULL,
    items=tuple(f"item_{i}" for i in range(10)),
    natures=("adamant", "bold", "timid", "modest", "jolly"),
)


def _rng(seed: int = 0) -> random.Random:
    return random.Random(seed)


# ---------------------------------------------------------------------------
# random_genome tests
# ---------------------------------------------------------------------------

def test_random_genome_six_distinct_species():
    g = random_genome(MOCK_PALETTE, "test_team", _rng(1))
    assert len(g.members) == 6
    species_list = [m.species for m in g.members]
    assert len(set(species_list)) == 6, f"Duplicate species: {species_list}"


def test_random_genome_moves_from_species_learnset():
    """Each member's moves must all come from that species' learnset."""
    for seed in range(20):
        g = random_genome(MOCK_PALETTE, "test", _rng(seed))
        for m in g.members:
            entry = MOCK_PALETTE.species[m.species]
            for mv in m.moves:
                assert mv in entry.learnset, (
                    f"Move {mv!r} not in learnset of {m.species!r}: {entry.learnset}"
                )


def test_random_genome_four_distinct_moves_per_member():
    for seed in range(20):
        g = random_genome(MOCK_PALETTE, "test", _rng(seed))
        for m in g.members:
            assert len(m.moves) == 4
            assert len(set(m.moves)) == 4, f"Duplicate moves in {m.species}: {m.moves}"


def test_random_genome_ev_constraints():
    for seed in range(20):
        g = random_genome(MOCK_PALETTE, "test", _rng(seed))
        for m in g.members:
            total = sum(m.evs.values())
            assert total <= 508, f"Total EVs {total} > 508"
            for stat, val in m.evs.items():
                assert val <= 252, f"EV {stat}={val} > 252"


def test_random_genome_item_and_nature_from_palette():
    g = random_genome(MOCK_PALETTE, "test", _rng(4))
    for m in g.members:
        assert m.nature in MOCK_PALETTE.natures
        assert m.item in MOCK_PALETTE.items


# ---------------------------------------------------------------------------
# mutate tests
# ---------------------------------------------------------------------------

def test_mutate_swap_move_stays_in_learnset():
    """After mutate, all moves for each member must still be in that species' learnset."""
    for seed in range(50):
        g = random_genome(MOCK_PALETTE, "orig", _rng(seed))
        g2 = mutate(g, MOCK_PALETTE, _rng(seed + 1000), rate=0.5)
        for m in g2.members:
            entry = MOCK_PALETTE.species[m.species]
            for mv in m.moves:
                assert mv in entry.learnset, (
                    f"After mutate: move {mv!r} not in learnset of {m.species!r}"
                )


def test_mutate_always_different():
    """Over 100 random seeds, mutate should always produce a changed genome."""
    for seed in range(100):
        g = random_genome(MOCK_PALETTE, "orig", _rng(seed))
        g2 = mutate(g, MOCK_PALETTE, _rng(seed + 1000))
        assert g.model_dump() != g2.model_dump(), (
            f"mutate produced identical genome at seed={seed}"
        )


def test_mutate_output_item_nature_from_palette():
    g = random_genome(MOCK_PALETTE, "orig", _rng(7))
    for seed in range(20):
        g2 = mutate(g, MOCK_PALETTE, _rng(seed + 500))
        for m in g2.members:
            assert m.nature in MOCK_PALETTE.natures
            assert m.item in MOCK_PALETTE.items


def test_mutate_does_not_modify_input():
    g = random_genome(MOCK_PALETTE, "orig", _rng(9))
    original_dump = g.model_dump()
    mutate(g, MOCK_PALETTE, _rng(99))
    assert g.model_dump() == original_dump, "mutate modified the input genome"


# ---------------------------------------------------------------------------
# crossover tests
# ---------------------------------------------------------------------------

def test_crossover_each_slot_from_parents():
    a = random_genome(MOCK_PALETTE, "parent_a", _rng(10))
    b = random_genome(MOCK_PALETTE, "parent_b", _rng(20))
    parent_species = {m.species for m in a.members} | {m.species for m in b.members}

    for seed in range(30):
        child = crossover(a, b, _rng(seed + 300))
        assert len(child.members) == 6
        for cm in child.members:
            assert cm.species in parent_species, (
                f"Child species {cm.species!r} not in either parent"
            )


def test_crossover_output_valid_genome():
    a = random_genome(MOCK_PALETTE, "pa", _rng(11))
    b = random_genome(MOCK_PALETTE, "pb", _rng(22))
    child = crossover(a, b, _rng(33))
    assert isinstance(child, Genome)
    assert len(child.members) == 6
    for m in child.members:
        assert len(m.moves) == 4
