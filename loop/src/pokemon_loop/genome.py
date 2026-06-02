"""Genome: pydantic model + GA operators (random_genome, mutate, crossover).

Wire format contract (C++ team_loader):
  All IDs are lowercase + underscores (normalized). Fields:
  {
    "name": str,
    "members": [
      {
        "species": "<species_id>",      # e.g. "snorlax", "mega_charizard_x"
        "level": 50,
        "ivs": {"hp":31, "atk":31, ...},
        "evs": {"hp":0, "atk":252, ...},
        "nature": "<nature_id>",        # e.g. "adamant"
        "moves": ["<move_id>", ...],    # 4 entries, e.g. "body_slam"
        "item": "<item_id>"             # e.g. "leftovers"
      },
      ...
    ]
  }
  IDs are normalized (lowercase, spaces/hyphens -> underscores).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator

from .palette import Palette, SpeciesEntry


_STAT_KEYS = ["hp", "atk", "def", "spa", "spd", "spe"]
_MAX_TOTAL_EVS = 508
_MAX_PER_EV = 252

# Note: species are filtered to learnset >= 4 in palette.py, so _moves_for_species
# can sample 4 distinct moves without padding.


class Member(BaseModel):
    species: str
    level: int = 50
    ivs: dict[str, int]
    evs: dict[str, int]
    nature: str
    moves: list[str]
    item: str

    @field_validator("moves")
    @classmethod
    def four_moves(cls, v: list[str]) -> list[str]:
        if len(v) > 4:
            raise ValueError(f"moves must have at most 4 entries, got {len(v)}")
        return v

    @field_validator("evs")
    @classmethod
    def ev_constraints(cls, v: dict[str, int]) -> dict[str, int]:
        total = sum(v.values())
        if total > _MAX_TOTAL_EVS:
            raise ValueError(f"Total EVs {total} exceeds {_MAX_TOTAL_EVS}")
        if any(val > _MAX_PER_EV for val in v.values()):
            raise ValueError(f"Single-stat EV exceeds {_MAX_PER_EV}")
        return v


class Genome(BaseModel):
    name: str
    members: list[Member]

    @field_validator("members")
    @classmethod
    def six_members(cls, v: list[Member]) -> list[Member]:
        if len(v) != 6:
            raise ValueError(f"members must have exactly 6 entries, got {len(v)}")
        return v


def _random_evs(rng: random.Random) -> dict[str, int]:
    """Distribute up to 508 EVs across 6 stats, each capped at 252."""
    evs = {k: 0 for k in _STAT_KEYS}
    remaining = _MAX_TOTAL_EVS
    keys = list(_STAT_KEYS)
    rng.shuffle(keys)
    for k in keys[:-1]:
        max_this = min(_MAX_PER_EV, remaining)
        if max_this <= 0:
            break
        val = rng.randint(0, max_this)
        evs[k] = val
        remaining -= val
    return evs


def _moves_for_species(entry: SpeciesEntry, palette: Palette, rng: random.Random, n: int = 4) -> list[str]:
    """Sample n distinct moves from a species' learnset.

    Palette guarantees learnset >= 4, so n=4 sampling always succeeds.
    """
    return rng.sample(list(entry.learnset), n)


def _random_member(entry: SpeciesEntry, palette: Palette, rng: random.Random) -> Member:
    moves = _moves_for_species(entry, palette, rng, n=4)
    nature = rng.choice(palette.natures)
    item = rng.choice(palette.items)
    ivs = {k: 31 for k in _STAT_KEYS}
    evs = _random_evs(rng)
    return Member(
        species=entry.id,
        level=50,
        ivs=ivs,
        evs=evs,
        nature=nature,
        moves=moves,
        item=item,
    )


def random_genome(palette: Palette, name: str, rng: random.Random) -> Genome:
    """Generate a Genome with 6 distinct species sampled uniformly from the legal pool."""
    all_species = list(palette.species.values())
    chosen_entries = rng.sample(all_species, 6)
    members = [_random_member(e, palette, rng) for e in chosen_entries]
    return Genome(name=name, members=members)


def mutate(g: Genome, palette: Palette, rng: random.Random, rate: float = 0.15) -> Genome:
    """
    Mutate a genome.

    For each member, the following sites are independently tested at probability `rate`:
      - swap_move: replace one move with a random legal move from THE SPECIES' learnset.
      - change_item: pick a different item.
      - change_nature: pick a different nature.
      - replace_member: replace this mon entirely with a fresh random member.

    At least 1 mutation is guaranteed per call.
    Returns a NEW genome (input is unmodified).
    """
    new_members: list[Member] = []
    mutations_applied = 0

    for m in g.members:
        entry = palette.species.get(m.species)
        # Fallback: if species somehow not found, use global move pool (should not happen)
        learnset = list(entry.learnset) if entry else list(palette.moves.keys())

        new_moves = list(m.moves)
        new_item = m.item
        new_nature = m.nature
        replace_mon = False

        # swap_move: per move slot — exclude current move and other occupied slots
        for i in range(len(new_moves)):
            if rng.random() < rate:
                current_move = new_moves[i]
                others = [mv for j, mv in enumerate(new_moves) if j != i]
                candidates = [mv for mv in learnset if mv != current_move and mv not in others]
                if candidates:
                    new_moves[i] = rng.choice(candidates)
                    mutations_applied += 1

        if rng.random() < rate:
            new_item = rng.choice(palette.items)
            mutations_applied += 1

        if rng.random() < rate:
            new_nature = rng.choice(palette.natures)
            mutations_applied += 1

        if rng.random() < rate:
            replace_mon = True

        if replace_mon:
            existing = {mem.species for mem in new_members}
            candidates_species = [
                e for sid, e in palette.species.items()
                if sid not in existing and sid != m.species
            ]
            if candidates_species:
                new_entry = rng.choice(candidates_species)
                new_member = _random_member(new_entry, palette, rng)
                new_members.append(new_member)
                mutations_applied += 1
                continue

        new_members.append(Member(
            species=m.species,
            level=m.level,
            ivs=dict(m.ivs),
            evs=dict(m.evs),
            nature=new_nature,
            moves=new_moves,
            item=new_item,
        ))

    # Guarantee at least 1 mutation
    if mutations_applied == 0:
        idx = rng.randrange(len(new_members))
        m = new_members[idx]
        entry = palette.species.get(m.species)
        learnset = list(entry.learnset) if entry else list(palette.moves.keys())
        current_moves = list(m.moves)
        move_idx = rng.randrange(len(current_moves))
        current_move = current_moves[move_idx]
        others = [mv for j, mv in enumerate(current_moves) if j != move_idx]
        # Exclude both the current move AND moves already in the other slots
        candidates = [mv for mv in learnset if mv != current_move and mv not in others]
        if candidates:
            current_moves[move_idx] = rng.choice(candidates)
        new_members[idx] = Member(
            species=m.species,
            level=m.level,
            ivs=dict(m.ivs),
            evs=dict(m.evs),
            nature=m.nature,
            moves=current_moves,
            item=m.item,
        )

    return Genome(name=g.name, members=new_members)


def crossover(a: Genome, b: Genome, rng: random.Random) -> Genome:
    """
    Uniform slot crossover: for each of 6 slots pick the mon from parent a or b.

    After crossover each member's moves are guaranteed to be learnset-valid for
    their species because the species and moves came from the same parent member
    (moves were already learnset-valid in the parent).

    Returns a new genome named after both parents.
    """
    chosen_members: list[Member] = []
    used_species: set[str] = set()

    for slot in range(6):
        parents = [a.members[slot], b.members[slot]]
        if rng.random() < 0.5:
            parents = list(reversed(parents))

        for candidate in parents:
            if candidate.species not in used_species:
                chosen_members.append(Member(
                    species=candidate.species,
                    level=candidate.level,
                    ivs=dict(candidate.ivs),
                    evs=dict(candidate.evs),
                    nature=candidate.nature,
                    moves=list(candidate.moves),
                    item=candidate.item,
                ))
                used_species.add(candidate.species)
                break
        else:
            # Both slots share species already chosen — use parent a's slot
            chosen_members.append(Member(
                species=a.members[slot].species,
                level=a.members[slot].level,
                ivs=dict(a.members[slot].ivs),
                evs=dict(a.members[slot].evs),
                nature=a.members[slot].nature,
                moves=list(a.members[slot].moves),
                item=a.members[slot].item,
            ))
            used_species.add(a.members[slot].species)

    child_name = f"child_{a.name}_{b.name}"
    return Genome(name=child_name, members=chosen_members)


def write_genome_json(g: Genome, path: Path) -> None:
    """Serialize a Genome to the contract JSON shape expected by the C++ team_loader.

    All IDs (species, moves, item, nature) are already normalized (lowercase + underscores)
    by the time they are stored in the Genome/Member objects. The C++ team_loader is
    updated to accept these normalized IDs.
    """
    data: dict[str, Any] = {
        "name": g.name,
        "members": [
            {
                "species": m.species,
                "level": m.level,
                "ivs": m.ivs,
                "evs": m.evs,
                "nature": m.nature,
                "moves": m.moves,
                "item": m.item,
            }
            for m in g.members
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))
