"""
Hard-coded team definitions for the MVP tournament.

Each team is a dict with:
  name: str
  members: list of 6 dicts, each with species, moves (list of 4), held_item

Note: The current battle_demo binary uses hard-coded teams internally.
If --team-a / --team-b flags are not supported by the binary, the orchestrator
falls back to running battle_demo with varying RNG seeds, which uses the
built-in teams A and B for every battle.  The team data here is written to
loop/teams/{name}.json for future use once the C++ flag is implemented.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict


class PokemonSpec(TypedDict):
    species: str
    moves: list[str]
    held_item: str


class Team(TypedDict):
    name: str
    members: list[PokemonSpec]


TEAMS: list[Team] = [
    {
        "name": "Rain_Sweepers",
        "members": [
            {"species": "Politoed", "moves": ["Surf", "Ice Beam", "Thunderbolt", "Protect"], "held_item": "Choice Specs"},
            {"species": "Ludicolo", "moves": ["Surf", "Giga Drain", "Ice Beam", "Rain Dance"], "held_item": "Life Orb"},
            {"species": "Kingdra", "moves": ["Surf", "Dragon Pulse", "Ice Beam", "Protect"], "held_item": "Lum Berry"},
            {"species": "Jolteon", "moves": ["Thunderbolt", "Shadow Ball", "Quick Attack", "Protect"], "held_item": "Choice Specs"},
            {"species": "Kabutops", "moves": ["Waterfall", "Stone Edge", "X-Scissor", "Aqua Jet"], "held_item": "Life Orb"},
            {"species": "Toxicroak", "moves": ["Surf", "Cross Chop", "Sucker Punch", "Bulk Up"], "held_item": "Black Sludge"},
        ],
    },
    {
        "name": "Sun_Sweepers",
        "members": [
            {"species": "Ninetales", "moves": ["Flamethrower", "SolarBeam", "Energy Ball", "Sunny Day"], "held_item": "Heat Rock"},
            {"species": "Venusaur", "moves": ["SolarBeam", "Sludge Bomb", "Sleep Powder", "Growth"], "held_item": "Life Orb"},
            {"species": "Charizard", "moves": ["Fire Blast", "SolarBeam", "Air Slash", "Roost"], "held_item": "Choice Specs"},
            {"species": "Arcanine", "moves": ["Flare Blitz", "Extreme Speed", "Close Combat", "Wild Charge"], "held_item": "Choice Band"},
            {"species": "Tangrowth", "moves": ["SolarBeam", "Earthquake", "Rock Slide", "Synthesis"], "held_item": "Assault Vest"},
            {"species": "Houndoom", "moves": ["Fire Blast", "Dark Pulse", "Nasty Plot", "Sucker Punch"], "held_item": "Life Orb"},
        ],
    },
    {
        "name": "Stall",
        "members": [
            {"species": "Blissey", "moves": ["Soft-Boiled", "Toxic", "Seismic Toss", "Protect"], "held_item": "Leftovers"},
            {"species": "Skarmory", "moves": ["Stealth Rock", "Roost", "Whirlwind", "Spikes"], "held_item": "Leftovers"},
            {"species": "Gastrodon", "moves": ["Scald", "Toxic", "Recover", "Protect"], "held_item": "Leftovers"},
            {"species": "Gliscor", "moves": ["Earthquake", "Roost", "Toxic", "Ice Fang"], "held_item": "Toxic Orb"},
            {"species": "Ferrothorn", "moves": ["Power Whip", "Leech Seed", "Protect", "Gyro Ball"], "held_item": "Leftovers"},
            {"species": "Tentacruel", "moves": ["Scald", "Toxic Spikes", "Rapid Spin", "Protect"], "held_item": "Leftovers"},
        ],
    },
    {
        "name": "Hyper_Offense",
        "members": [
            {"species": "Garchomp", "moves": ["Earthquake", "Dragon Claw", "Stone Edge", "Fire Fang"], "held_item": "Choice Band"},
            {"species": "Lucario", "moves": ["Close Combat", "Iron Tail", "Extreme Speed", "Crunch"], "held_item": "Life Orb"},
            {"species": "Gyarados", "moves": ["Waterfall", "Earthquake", "Ice Fang", "Dragon Dance"], "held_item": "Lum Berry"},
            {"species": "Weavile", "moves": ["Ice Punch", "Night Slash", "Low Kick", "Pursuit"], "held_item": "Choice Band"},
            {"species": "Salamence", "moves": ["Outrage", "Earthquake", "Fire Blast", "Dragon Dance"], "held_item": "Life Orb"},
            {"species": "Machamp", "moves": ["Dynamic Punch", "Payback", "Stone Edge", "Ice Punch"], "held_item": "Choice Band"},
        ],
    },
    {
        "name": "Balanced_A",
        "members": [
            {"species": "Metagross", "moves": ["Meteor Mash", "Earthquake", "Ice Punch", "Bullet Punch"], "held_item": "Leftovers"},
            {"species": "Starmie", "moves": ["Surf", "Ice Beam", "Thunderbolt", "Rapid Spin"], "held_item": "Life Orb"},
            {"species": "Tyranitar", "moves": ["Stone Edge", "Crunch", "Earthquake", "Ice Punch"], "held_item": "Choice Band"},
            {"species": "Rotom-W", "moves": ["Thunderbolt", "Hydro Pump", "Will-O-Wisp", "Volt Switch"], "held_item": "Leftovers"},
            {"species": "Conkeldurr", "moves": ["Drain Punch", "Mach Punch", "Thunder Punch", "Bulk Up"], "held_item": "Assault Vest"},
            {"species": "Togekiss", "moves": ["Air Slash", "Dazzling Gleam", "Roost", "Nasty Plot"], "held_item": "Leftovers"},
        ],
    },
    {
        "name": "Balanced_B",
        "members": [
            {"species": "Gengar", "moves": ["Shadow Ball", "Sludge Bomb", "Focus Blast", "Thunderbolt"], "held_item": "Life Orb"},
            {"species": "Dragonite", "moves": ["Dragon Claw", "Extreme Speed", "Fire Punch", "Earthquake"], "held_item": "Lum Berry"},
            {"species": "Vaporeon", "moves": ["Surf", "Ice Beam", "Wish", "Protect"], "held_item": "Leftovers"},
            {"species": "Heracross", "moves": ["Close Combat", "Megahorn", "Stone Edge", "Knock Off"], "held_item": "Choice Scarf"},
            {"species": "Magnezone", "moves": ["Thunderbolt", "Flash Cannon", "Volt Switch", "Hidden Power Fire"], "held_item": "Choice Specs"},
            {"species": "Mamoswine", "moves": ["Earthquake", "Icicle Crash", "Stone Edge", "Ice Shard"], "held_item": "Life Orb"},
        ],
    },
    {
        "name": "Trick_Room_Slow",
        "members": [
            {"species": "Reuniclus", "moves": ["Psychic", "Shadow Ball", "Focus Blast", "Recover"], "held_item": "Life Orb"},
            {"species": "Snorlax", "moves": ["Body Slam", "Earthquake", "Crunch", "Self-Destruct"], "held_item": "Leftovers"},
            {"species": "Rhyperior", "moves": ["Earthquake", "Stone Edge", "Rock Blast", "Megahorn"], "held_item": "Assault Vest"},
            {"species": "Conkeldurr", "moves": ["Drain Punch", "Mach Punch", "Ice Punch", "Stone Edge"], "held_item": "Life Orb"},
            {"species": "Escavalier", "moves": ["Megahorn", "Iron Head", "Return", "Knock Off"], "held_item": "Choice Band"},
            {"species": "Slowbro", "moves": ["Scald", "Psychic", "Fire Blast", "Slack Off"], "held_item": "Leftovers"},
        ],
    },
    {
        "name": "Quick_Attack_Spam",
        "members": [
            {"species": "Ambipom", "moves": ["Fake Out", "Quick Attack", "Return", "Low Kick"], "held_item": "Choice Band"},
            {"species": "Weavile", "moves": ["Ice Shard", "Quick Attack", "Night Slash", "Ice Punch"], "held_item": "Life Orb"},
            {"species": "Talonflame", "moves": ["Brave Bird", "Flare Blitz", "Quick Attack", "U-turn"], "held_item": "Choice Band"},
            {"species": "Arcanine", "moves": ["Extreme Speed", "Flare Blitz", "Wild Charge", "Close Combat"], "held_item": "Life Orb"},
            {"species": "Togekiss", "moves": ["Extreme Speed", "Air Slash", "Dazzling Gleam", "Roost"], "held_item": "Leftovers"},
            {"species": "Lucario", "moves": ["Extreme Speed", "Bullet Punch", "Close Combat", "Iron Tail"], "held_item": "Choice Band"},
        ],
    },
]


def dump_teams(output_dir: Path) -> None:
    """Write each team to output_dir/{name}.json for future use with --team-a/--team-b."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for team in TEAMS:
        path = output_dir / f"{team['name']}.json"
        path.write_text(json.dumps(team, indent=2))
