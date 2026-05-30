"""Integration test: load the real palette from disk and verify counts/learnsets.

Skips automatically if the DB path does not exist (e.g. CI without the DB).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_DB_PATH = Path(os.environ.get(
    "POKEMON_CHAMPIONS_DB",
    # __file__ = loop/tests/test_palette_load.py
    # parents[0] = loop/tests/, parents[1] = loop/, parents[2] = repo-root
    Path(__file__).resolve().parents[2] / "pokemon-champions-db" / "data" / "json",
))


@pytest.fixture(scope="module")
def palette():
    if not _DB_PATH.exists():
        pytest.skip(f"DB path not found: {_DB_PATH} — set POKEMON_CHAMPIONS_DB to run this test")
    from pokemon_loop.palette import load_palette
    return load_palette(_DB_PATH)


def test_species_count(palette):
    assert len(palette.species) >= 250, f"Expected >=250 species, got {len(palette.species)}"


def test_moves_count(palette):
    assert len(palette.moves) >= 400, f"Expected >=400 moves, got {len(palette.moves)}"


def test_items_count(palette):
    assert len(palette.items) >= 50, f"Expected >=50 items, got {len(palette.items)}"


def test_natures_count(palette):
    assert len(palette.natures) >= 5, f"Expected >=5 natures, got {len(palette.natures)}"


def test_species_learnsets(palette):
    """All (or almost all) species must have non-empty learnsets.

    Regional forms (Alolan, Hisuian, Galarian, Paldean) lack learnset entries
    in the current DB — 13 such gaps are known. Allow up to 20 to accommodate
    any future additions while still catching regressions.
    """
    empty = [sid for sid, se in palette.species.items() if len(se.learnset) == 0]
    assert len(empty) <= 20, (
        f"Too many species with empty learnsets ({len(empty)}): {empty}"
    )


def test_learnset_moves_exist_in_moves_table(palette):
    """Every move ID in every learnset must exist in palette.moves."""
    violations: list[str] = []
    for sid, se in palette.species.items():
        for mid in se.learnset:
            if mid not in palette.moves:
                violations.append(f"{sid}: {mid}")
    assert not violations, (
        f"Learnset moves missing from moves table ({len(violations)}): {violations[:10]}"
    )


def test_ids_are_normalized(palette):
    """Spot-check that IDs are normalized (no uppercase, no spaces)."""
    import re
    bad_species = [sid for sid in palette.species if re.search(r"[A-Z\s]", sid)]
    bad_moves = [mid for mid in palette.moves if re.search(r"[A-Z\s]", mid)]
    bad_items = [iid for iid in palette.items if re.search(r"[A-Z\s]", iid)]
    bad_natures = [nid for nid in palette.natures if re.search(r"[A-Z\s]", nid)]
    assert not bad_species, f"Non-normalized species IDs: {bad_species[:5]}"
    assert not bad_moves, f"Non-normalized move IDs: {bad_moves[:5]}"
    assert not bad_items, f"Non-normalized item IDs: {bad_items[:5]}"
    assert not bad_natures, f"Non-normalized nature IDs: {bad_natures[:5]}"


def test_known_species_present(palette):
    """Known-good species must be present by their normalized ID."""
    expected = ["garchomp", "snorlax", "greninja", "tyranitar", "mega_charizard_x"]
    for sid in expected:
        assert sid in palette.species, f"Expected species {sid!r} not found in palette"


def test_known_moves_present(palette):
    """Known-good moves must be present."""
    expected = ["earthquake", "flamethrower", "surf", "close_combat", "dragon_claw"]
    for mid in expected:
        assert mid in palette.moves, f"Expected move {mid!r} not found in palette"
