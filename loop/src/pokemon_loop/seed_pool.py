"""Fixed seed teams used as an evaluation pool — they never mutate.

All species and moves are verified against the Pokemon Champions DB learnsets.
Species IDs and move IDs use normalized format (lowercase + underscores).
"""

from __future__ import annotations

from pathlib import Path

from .genome import Genome, Member, write_genome_json


def _make_ivs() -> dict[str, int]:
    return {"hp": 31, "atk": 31, "def": 31, "spa": 31, "spd": 31, "spe": 31}


# ---------------------------------------------------------------------------
# Seed team 1: Stall / Hazard-stack archetype
# Species all verified champions_legal=true in pokemon.json.
# Moves verified present in each species' learnset (learnsets.json).
# ---------------------------------------------------------------------------
_SEED_STALL = Genome(
    name="seed_stall",
    members=[
        Member(
            # Toxapex: defensive poison/water wall with hazards and recovery
            species="toxapex",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 252, "spa": 0, "spd": 4, "spe": 0},
            nature="bold",
            moves=["recover", "toxic", "toxic_spikes", "protect"],
            item="leftovers",
        ),
        Member(
            # Skarmory: physical wall with hazards, phazing, and recovery
            species="skarmory",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 252, "spa": 0, "spd": 4, "spe": 0},
            nature="impish",
            moves=["stealth_rock", "roost", "whirlwind", "spikes"],
            item="leftovers",
        ),
        Member(
            # Gliscor: defensive ground/flying that can spread toxic and recover
            species="gliscor",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 184, "spa": 0, "spd": 0, "spe": 72},
            nature="impish",
            moves=["earthquake", "roost", "toxic", "ice_fang"],
            item="toxic_orb",
        ),
        Member(
            # Arcanine: fast, bulky fire-type with reliable recovery
            species="arcanine",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0},
            nature="modest",
            moves=["flamethrower", "will_o_wisp", "morning_sun", "protect"],
            item="leftovers",
        ),
        Member(
            # Slowbro: bulky water/psychic wall with regenerator-style tanking
            species="slowbro",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 252, "spa": 0, "spd": 4, "spe": 0},
            nature="bold",
            moves=["scald", "slack_off", "thunder_wave", "psychic"],
            item="leftovers",
        ),
        Member(
            # Snorlax: specially bulky normal-type tank with reliable recovery
            species="snorlax",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 4, "spa": 0, "spd": 252, "spe": 0},
            nature="careful",
            moves=["body_slam", "toxic", "rest", "sleep_talk"],
            item="leftovers",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Seed team 2: Hyper Offense / fast sweepers
# Species all verified champions_legal=true. Moves from learnsets.
# ---------------------------------------------------------------------------
_SEED_HO = Genome(
    name="seed_hyper_offense",
    members=[
        Member(
            # Garchomp: fast physical dragon/ground sweeper
            species="garchomp",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252},
            nature="jolly",
            moves=["earthquake", "dragon_claw", "stone_edge", "fire_fang"],
            item="choice_band",
        ),
        Member(
            # Talonflame: priority brave bird user with flame charge setup
            species="talonflame",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252},
            nature="adamant",
            moves=["brave_bird", "flare_blitz", "swords_dance", "roost"],
            item="life_orb",
        ),
        Member(
            # Greninja: fast mixed attacker with wide coverage
            species="greninja",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 252},
            nature="timid",
            moves=["hydro_pump", "ice_beam", "dark_pulse", "grass_knot"],
            item="life_orb",
        ),
        Member(
            # Mega Charizard X: dragon/fire physical set-up sweeper
            species="mega_charizard_x",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252},
            nature="jolly",
            moves=["dragon_dance", "dragon_claw", "flare_blitz", "earthquake"],
            item="charizardite_x",
        ),
        Member(
            # Gyarados: physical dragon-dance sweeper with great coverage
            species="gyarados",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252},
            nature="adamant",
            moves=["waterfall", "earthquake", "ice_fang", "dragon_dance"],
            item="lum_berry",
        ),
        Member(
            # Lucario: fast fighting/steel with priority and wide coverage
            species="lucario",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252},
            nature="adamant",
            moves=["close_combat", "bullet_punch", "extreme_speed", "swords_dance"],
            item="life_orb",
        ),
    ],
)

# ---------------------------------------------------------------------------
# Seed team 3: Weather Balanced (rain theme)
# Politoed as rain setter (abilities are noop in MVP — archetype naming only).
# Species all verified champions_legal=true. Moves from learnsets.
# ---------------------------------------------------------------------------
_SEED_WEATHER = Genome(
    name="seed_weather_balanced",
    members=[
        Member(
            # Politoed: water-type rain setter with offensive moves
            species="politoed",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 0, "spa": 252, "spd": 4, "spe": 0},
            nature="modest",
            moves=["hydro_pump", "ice_beam", "rain_dance", "protect"],
            item="choice_specs",
        ),
        Member(
            # Starmie: fast water/psychic with rapid spin and recovery
            species="starmie",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252},
            nature="timid",
            moves=["surf", "ice_beam", "psychic", "rapid_spin"],
            item="life_orb",
        ),
        Member(
            # Greninja: fast mixed attacker that thrives in rain
            species="greninja",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 4, "atk": 0, "def": 0, "spa": 252, "spd": 0, "spe": 252},
            nature="timid",
            moves=["waterfall", "ice_beam", "dark_pulse", "u_turn"],
            item="life_orb",
        ),
        Member(
            # Gyarados: physical sweeper boosted by rain
            species="gyarados",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252},
            nature="adamant",
            moves=["waterfall", "dragon_dance", "crunch", "earthquake"],
            item="lum_berry",
        ),
        Member(
            # Tyranitar: sand setter / physical attacker (rain vs sand tension)
            species="tyranitar",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 4, "atk": 252, "def": 0, "spa": 0, "spd": 0, "spe": 252},
            nature="adamant",
            moves=["stone_edge", "crunch", "earthquake", "ice_punch"],
            item="choice_band",
        ),
        Member(
            # Skarmory: physical wall providing hazards and phazing
            species="skarmory",
            level=50,
            ivs=_make_ivs(),
            evs={"hp": 252, "atk": 0, "def": 252, "spa": 0, "spd": 4, "spe": 0},
            nature="impish",
            moves=["stealth_rock", "spikes", "roost", "brave_bird"],
            item="leftovers",
        ),
    ],
)

_SEEDS: list[Genome] = [_SEED_STALL, _SEED_HO, _SEED_WEATHER]


def seed_pool() -> list[Genome]:
    """Return the 3 fixed seed genomes (they never mutate)."""
    return list(_SEEDS)


def write_seed_jsons(out_dir: Path) -> list[Path]:
    """Dump the 3 seeds to disk; idempotent (only writes if missing)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for genome in _SEEDS:
        p = out_dir / f"{genome.name}.json"
        if not p.exists():
            write_genome_json(genome, p)
        paths.append(p)
    return paths
