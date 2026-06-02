"""Palette: load valid species/moves/items/natures from the Pokemon Champions DB JSON files.

This module reads the source JSON directly (not via the C++ binary) so Python and C++
both read the same data and cannot drift. The C++ executor reads the same JSON files.

ID normalisation contract (must match C++ team_loader):
  - All IDs are lowercase with spaces and hyphens replaced by underscores.
  - Multiple consecutive underscores are collapsed.
  - Example: "Mega Charizard X" -> "mega_charizard_x"
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


def normalize_id(s: str) -> str:
    """Normalise a display name to a code ID: lowercase, whitespace/hyphens -> underscores."""
    s = s.strip().lower()
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s


def _repo_root() -> Path:
    """Return the repository root (two levels above the loop/ package)."""
    # loop/src/pokemon_loop/palette.py -> parents[3] = repo root
    return Path(__file__).resolve().parents[3]


def _default_db_root() -> Path:
    env_val = os.environ.get("POKEMON_CHAMPIONS_DB")
    if env_val:
        return Path(env_val)
    return _repo_root() / "pokemon-champions-db" / "data" / "json"


# Cache lives at loop/.cache/palette.json
# loop/src/pokemon_loop/palette.py -> parents[2] = loop/
_CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "palette.json"


@dataclass
class SpeciesEntry:
    id: str
    display_name: str          # e.g. "Mega Charizard X"
    dex: int
    types: tuple[str, ...]     # e.g. ("fire", "flying")
    base_stats: dict[str, int] # keys: hp, atk, def, spa, spd, spe
    learnset: tuple[str, ...]  # tuple of move IDs (normalised)


@dataclass
class MoveEntry:
    id: str
    display_name: str
    type: str | None           # None for rare status moves with no type
    category: str              # "physical" | "special" | "status"
    power: int                 # 0 for status moves
    accuracy: int              # 0-100; 0 means always-hit or no accuracy check
    pp_max: int
    priority: int


@dataclass
class Palette:
    species: dict[str, SpeciesEntry]   # keyed by id
    moves: dict[str, MoveEntry]         # keyed by id
    items: tuple[str, ...]             # ids
    natures: tuple[str, ...]           # ids


def _source_mtimes(db_root: Path) -> float:
    """Return the latest mtime among the 5 source JSON files."""
    files = ["pokemon.json", "moves.json", "items.json", "natures.json", "learnsets.json"]
    mtimes = []
    for f in files:
        p = db_root / f
        if p.exists():
            mtimes.append(p.stat().st_mtime)
    return max(mtimes) if mtimes else 0.0


def _load_from_json(db_root: Path) -> Palette:
    """Read and parse the 5 source JSONs into a Palette."""
    # --- moves ---
    with open(db_root / "moves.json", encoding="utf-8") as fh:
        raw_moves = json.load(fh)

    moves: dict[str, MoveEntry] = {}
    for m in raw_moves:
        name = m.get("name_en") or ""
        if not name:
            continue
        # Drop the garbage "-Champions Attackdex" sentinel and any name starting with "-"
        if name.startswith("-"):
            continue
        if not m.get("champions_legal"):
            continue
        cat = m.get("category")
        if cat not in ("Physical", "Special", "Status"):
            continue
        mid = normalize_id(name)
        type_raw = m.get("type_en")
        moves[mid] = MoveEntry(
            id=mid,
            display_name=name,
            type=normalize_id(type_raw) if type_raw else None,
            category=cat.lower(),
            power=int(m.get("power") or 0),
            accuracy=int(m.get("accuracy") or 0),
            pp_max=int(m.get("pp") or 0),
            priority=int(m.get("priority") or 0),
        )

    # --- learnsets ---
    with open(db_root / "learnsets.json", encoding="utf-8") as fh:
        raw_learnsets: dict[str, list[str]] = json.load(fh)

    # --- pokemon ---
    with open(db_root / "pokemon.json", encoding="utf-8") as fh:
        raw_pokemon = json.load(fh)

    species: dict[str, SpeciesEntry] = {}
    for p in raw_pokemon:
        if not p.get("champions_legal"):
            continue
        display = p.get("name_en") or ""
        if not display:
            continue
        sid = normalize_id(display)

        # Build learnset: filter to moves present in the legal moves table
        raw_ls = raw_learnsets.get(display, [])
        learnset_ids: list[str] = []
        for mv_name in raw_ls:
            if mv_name.startswith("-"):
                continue
            mid = normalize_id(mv_name)
            if mid in moves:
                learnset_ids.append(mid)

        # GA needs 4 distinct legal moves per member. Species with fewer learnable
        # moves in the DB (mostly regional/Mega forms the Serebii scraper missed)
        # are dropped from the palette so we never produce an illegal team.
        if len(learnset_ids) < 4:
            print(
                f"INFO: excluding '{display}' from palette — learnset size {len(learnset_ids)} < 4",
                file=sys.stderr,
            )
            continue

        types_raw = [p.get("type1"), p.get("type2")]
        types = tuple(
            normalize_id(t) for t in types_raw if t and t.lower() not in ("none", "")
        )

        species[sid] = SpeciesEntry(
            id=sid,
            display_name=display,
            dex=int(p.get("dex") or 0),
            types=types,
            base_stats={
                "hp":  int(p.get("hp")  or 0),
                "atk": int(p.get("atk") or 0),
                "def": int(p.get("def") or 0),
                "spa": int(p.get("spa") or 0),
                "spd": int(p.get("spd") or 0),
                "spe": int(p.get("spe") or 0),
            },
            learnset=tuple(learnset_ids),
        )

    # --- items ---
    with open(db_root / "items.json", encoding="utf-8") as fh:
        raw_items = json.load(fh)

    items: tuple[str, ...] = tuple(
        normalize_id(i["name_en"])
        for i in raw_items
        if i.get("champions_legal") and i.get("name_en")
    )

    # --- natures ---
    with open(db_root / "natures.json", encoding="utf-8") as fh:
        raw_natures = json.load(fh)

    natures: tuple[str, ...] = tuple(
        normalize_id(n["name_en"])
        for n in raw_natures
        if n.get("champions_legal") and n.get("name_en")
    )

    return Palette(species=species, moves=moves, items=items, natures=natures)


def load_palette(db_root: Path | None = None) -> Palette:
    """
    Load the Palette from the Pokemon Champions DB JSON files.

    Args:
        db_root: Path to the directory containing pokemon.json, moves.json, etc.
                 Defaults to $POKEMON_CHAMPIONS_DB env var, else
                 <repo-root>/pokemon-champions-db/data/json/.

    The result is cached at loop/.cache/palette.json and invalidated if any
    source JSON is newer than the cache.
    """
    root = Path(db_root) if db_root is not None else _default_db_root()
    cache = _CACHE_PATH

    # Check cache freshness
    if cache.exists():
        try:
            cache_mtime = cache.stat().st_mtime
            src_mtime = _source_mtimes(root)
            if cache_mtime >= src_mtime:
                data = json.loads(cache.read_text(encoding="utf-8"))
                # Reconstruct SpeciesEntry / MoveEntry from cached dicts
                species: dict[str, SpeciesEntry] = {}
                for sid, sv in data["species"].items():
                    species[sid] = SpeciesEntry(
                        id=sv["id"],
                        display_name=sv["display_name"],
                        dex=sv["dex"],
                        types=tuple(sv["types"]),
                        base_stats=sv["base_stats"],
                        learnset=tuple(sv["learnset"]),
                    )
                moves: dict[str, MoveEntry] = {}
                for mid, mv in data["moves"].items():
                    moves[mid] = MoveEntry(
                        id=mv["id"],
                        display_name=mv["display_name"],
                        type=mv["type"],
                        category=mv["category"],
                        power=mv["power"],
                        accuracy=mv["accuracy"],
                        pp_max=mv["pp_max"],
                        priority=mv["priority"],
                    )
                return Palette(
                    species=species,
                    moves=moves,
                    items=tuple(data["items"]),
                    natures=tuple(data["natures"]),
                )
        except (KeyError, json.JSONDecodeError, OSError):
            pass  # corrupt or stale cache — regenerate

    palette = _load_from_json(root)

    # Persist cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "species": {
            sid: {
                "id": se.id,
                "display_name": se.display_name,
                "dex": se.dex,
                "types": list(se.types),
                "base_stats": se.base_stats,
                "learnset": list(se.learnset),
            }
            for sid, se in palette.species.items()
        },
        "moves": {
            mid: {
                "id": me.id,
                "display_name": me.display_name,
                "type": me.type,
                "category": me.category,
                "power": me.power,
                "accuracy": me.accuracy,
                "pp_max": me.pp_max,
                "priority": me.priority,
            }
            for mid, me in palette.moves.items()
        },
        "items": list(palette.items),
        "natures": list(palette.natures),
    }
    cache.write_text(json.dumps(cache_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return palette
