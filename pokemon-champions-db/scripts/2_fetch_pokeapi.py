#!/usr/bin/env python3
"""Step 2 — Fetch PokeAPI bulk CSV name tables and build lookup maps.

Source: https://github.com/PokeAPI/pokeapi  (data/v2/csv) — BSD-licensed dataset.
Produces:
  data/raw/pokeapi/*.csv          (cached raw CSVs)
  data/raw/maps.json              english -> korean name maps + move -> type maps

Korean = local_language_id 3, English = 9.
The repo's move data has NO type field, so we also derive english/korean move types here.
"""
import csv
import io
import json
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CSV_BASE = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
FILES = [
    "pokemon_species_names.csv",
    "move_names.csv",
    "ability_names.csv",
    "item_names.csv",
    "nature_names.csv",
    "type_names.csv",
    "moves.csv",
    "types.csv",
    "type_efficacy.csv",
]
KO, EN = "3", "9"

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "pokeapi"


def get(url: str) -> str:
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "pkmn-champions-db/1.0"})
            with urlopen(req, timeout=40) as r:
                return r.read().decode("utf-8")
        except (URLError, HTTPError):
            if attempt == 2:
                raise
    return ""


def load_csv(name: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO((RAW / name).read_text(encoding="utf-8"))))


def name_map(rows: list[dict], id_col: str) -> dict[str, str]:
    """english display name -> korean display name, joined on id_col."""
    en = {r[id_col]: r["name"] for r in rows if r["local_language_id"] == EN}
    ko = {r[id_col]: r["name"] for r in rows if r["local_language_id"] == KO}
    return {en_name: ko[rid] for rid, en_name in en.items() if rid in ko}


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        (RAW / f).write_text(get(CSV_BASE + f), encoding="utf-8")
        print(f"  ok {f}")

    maps = {
        "species": name_map(load_csv("pokemon_species_names.csv"), "pokemon_species_id"),
        "move": name_map(load_csv("move_names.csv"), "move_id"),
        "ability": name_map(load_csv("ability_names.csv"), "ability_id"),
        "item": name_map(load_csv("item_names.csv"), "item_id"),
        "nature": name_map(load_csv("nature_names.csv"), "nature_id"),
        "type": name_map(load_csv("type_names.csv"), "type_id"),
    }

    # english move name -> {type_en, type_ko}
    types = load_csv("types.csv")
    type_id_to_ident = {t["id"]: t["identifier"].capitalize() for t in types}
    tnames = load_csv("type_names.csv")
    type_id_to_ko = {t["type_id"]: t["name"] for t in tnames if t["local_language_id"] == KO}
    type_id_to_en = {t["type_id"]: t["name"] for t in tnames if t["local_language_id"] == EN}
    mv_names_en = {r["move_id"]: r["name"] for r in load_csv("move_names.csv") if r["local_language_id"] == EN}
    move_type = {}
    for m in load_csv("moves.csv"):
        en_name = mv_names_en.get(m["id"])
        tid = m.get("type_id")
        if en_name and tid:
            move_type[en_name] = {
                "type_en": type_id_to_en.get(tid) or type_id_to_ident.get(tid),
                "type_ko": type_id_to_ko.get(tid),
            }
    maps["move_type"] = move_type

    # type chart: attacking_en -> {defending_en: multiplier} from type_efficacy.csv
    type_id_to_en_name = {t["id"]: (type_id_to_en.get(t["id"]) or t["identifier"].capitalize())
                          for t in types}
    type_chart: dict = {}
    for r in load_csv("type_efficacy.csv"):
        atk = type_id_to_en_name.get(r["damage_type_id"])
        dfd = type_id_to_en_name.get(r["target_type_id"])
        if atk and dfd:
            type_chart.setdefault(atk, {})[dfd] = int(r["damage_factor"]) / 100.0
    maps["type_chart"] = type_chart

    (ROOT / "data" / "raw" / "maps.json").write_text(
        json.dumps(maps, ensure_ascii=False, indent=1), encoding="utf-8")
    print("maps.json:", json.dumps({k: len(v) for k, v in maps.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
