"""
palette.py — loads the pokemon-champions-db JSON and produces the /api/palette
response shape.  Parsed once at first request, then served from module-level cache.

NOTE: For Mega/Alolan/Galarian/Hisuian forms we use the BASE dex number because
PokéAPI sprite URLs are keyed only on the base dex (e.g. both Charizard and
Mega Charizard X resolve to dex 6).  The correct sprite for the form variant is
not trivially derivable from the URL scheme; base-dex is the documented fallback.
"""

import json
import os
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # dashboard/../../.. = repo root

_palette_cache: Optional[dict] = None


def _db_root() -> Path:
    # POKEMON_CHAMPIONS_DB points at the directory that *directly* contains the
    # JSON files (pokemon.json, moves.json, ...), matching the Core<->DB contract
    # in AGENTS.md and the loop/core loaders. Falls back to the in-repo location.
    env = os.environ.get("POKEMON_CHAMPIONS_DB")
    if env:
        return Path(env)
    return _REPO_ROOT / "pokemon-champions-db" / "data" / "json"


def _normalize_id(name_en: str) -> str:
    """Normalize a Pokemon name_en to the ID used by the C++/Python contract."""
    return name_en.lower().replace(" ", "_").replace("-", "_")


def load_palette() -> dict:
    """Return the cached palette dict, loading from disk on first call."""
    global _palette_cache
    if _palette_cache is not None:
        return _palette_cache
    _palette_cache = _build_palette()
    return _palette_cache


def clear_palette_cache() -> None:
    """Clear the in-memory cache (used by tests to reset state between runs)."""
    global _palette_cache
    _palette_cache = None


def _build_palette() -> dict:
    json_path = _db_root() / "pokemon.json"
    if not json_path.exists():
        raise FileNotFoundError(f"pokemon.json not found at {json_path}")

    raw: list[dict] = json.loads(json_path.read_text(encoding="utf-8"))

    species: dict[str, dict] = {}
    for entry in raw:
        name_en: str = entry.get("name_en", "")
        if not name_en:
            continue

        normalized_id = _normalize_id(name_en)

        # Use the base dex from the JSON record.  For forms (Mega, Alolan, etc.)
        # the dex field already carries the base species number (e.g. Mega Charizard X → 6).
        dex: int = entry.get("dex", 0)

        types: list[str] = []
        t1 = entry.get("type1", "")
        t2 = entry.get("type2", "")
        if t1:
            types.append(t1.lower())
        if t2 and t2.lower() != t1.lower():
            types.append(t2.lower())

        species[normalized_id] = {
            "dex": dex,
            "types": types,
            "display": name_en,
        }

    return {"species": species}
