#!/usr/bin/env python3
"""Step 5 — Build champions.db (SQLite) from the merged data/json/* files.

Re-runnable: drops and recreates everything. Edit data/json/* and re-run to
update the DB — no hand-written SQL inserts needed.
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = ROOT / "data" / "json"
DB = ROOT / "champions.db"

SCHEMA = """
DROP TABLE IF EXISTS pokemon;
DROP TABLE IF EXISTS pokemon_abilities;
DROP TABLE IF EXISTS pokemon_moves;
DROP TABLE IF EXISTS moves;
DROP TABLE IF EXISTS abilities;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS natures;
DROP TABLE IF EXISTS type_chart;
DROP TABLE IF EXISTS reference;
DROP VIEW IF EXISTS v_pokemon_movepool;
DROP VIEW IF EXISTS v_pokemon_abilities;

CREATE TABLE pokemon (
  id INTEGER PRIMARY KEY,
  dex INTEGER, name_ko TEXT, name_en TEXT UNIQUE NOT NULL, form TEXT,
  type1 TEXT, type2 TEXT,
  hp INTEGER, atk INTEGER, def INTEGER, spa INTEGER, spd INTEGER, spe INTEGER, total INTEGER,
  ability_hidden TEXT, champions_legal INTEGER
);
CREATE TABLE pokemon_abilities (
  pokemon_en TEXT NOT NULL, ability_en TEXT NOT NULL, slot INTEGER, is_hidden INTEGER,
  PRIMARY KEY (pokemon_en, ability_en)
);
CREATE TABLE moves (
  id INTEGER PRIMARY KEY,
  name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  type_ko TEXT, type_en TEXT, category TEXT,
  power INTEGER, accuracy INTEGER, pp INTEGER, priority INTEGER, target TEXT,
  effect_en TEXT, champions_legal INTEGER
);
CREATE TABLE pokemon_moves (
  pokemon_en TEXT NOT NULL, move_en TEXT NOT NULL,
  PRIMARY KEY (pokemon_en, move_en)
);
CREATE TABLE abilities (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  desc_en TEXT, champions_legal INTEGER
);
CREATE TABLE items (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  category TEXT, desc_en TEXT, champions_legal INTEGER
);
CREATE TABLE natures (
  id INTEGER PRIMARY KEY, name_ko TEXT, name_en TEXT UNIQUE NOT NULL,
  increased TEXT, decreased TEXT, champions_legal INTEGER
);
CREATE TABLE type_chart (
  attacking TEXT NOT NULL, defending TEXT NOT NULL, multiplier REAL,
  PRIMARY KEY (attacking, defending)
);
CREATE TABLE reference (key TEXT PRIMARY KEY, value_ko TEXT, value_en TEXT);

CREATE INDEX idx_pm_move ON pokemon_moves(move_en);
CREATE INDEX idx_moves_type ON moves(type_en);
CREATE INDEX idx_moves_legal ON moves(champions_legal);
CREATE INDEX idx_pa_ability ON pokemon_abilities(ability_en);

CREATE VIEW v_pokemon_movepool AS
  SELECT p.name_ko AS 포켓몬, p.name_en AS pokemon, m.name_ko AS 기술, m.name_en AS move,
         m.type_ko AS 타입, m.category, m.power, m.accuracy, m.pp
  FROM pokemon_moves pm
  JOIN pokemon p ON p.name_en = pm.pokemon_en
  JOIN moves   m ON m.name_en = pm.move_en;

CREATE VIEW v_pokemon_abilities AS
  SELECT p.name_ko AS 포켓몬, p.name_en AS pokemon, a.name_ko AS 특성, pa.ability_en AS ability,
         pa.is_hidden AS 숨겨진특성, a.desc_en
  FROM pokemon_abilities pa
  JOIN pokemon p ON p.name_en = pa.pokemon_en
  LEFT JOIN abilities a ON a.name_en = pa.ability_en;
"""


def load(name):
    return json.loads((J / name).read_text(encoding="utf-8"))


def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    pk = load("pokemon.json")
    cur.executemany(
        "INSERT INTO pokemon(dex,name_ko,name_en,form,type1,type2,hp,atk,def,spa,spd,spe,total,ability_hidden,champions_legal)"
        " VALUES(:dex,:name_ko,:name_en,:form,:type1,:type2,:hp,:atk,:def,:spa,:spd,:spe,:total,:ability_hidden,:cl)",
        [{**p, "cl": int(p["champions_legal"])} for p in pk],
    )
    pa_rows = []
    for p in pk:
        for slot, ab in enumerate(p["abilities"]):
            pa_rows.append((p["name_en"], ab, slot, int(ab == p["ability_hidden"])))
    cur.executemany("INSERT OR IGNORE INTO pokemon_abilities VALUES(?,?,?,?)", pa_rows)

    mv = load("moves.json")
    cur.executemany(
        "INSERT INTO moves(name_ko,name_en,type_ko,type_en,category,power,accuracy,pp,priority,target,effect_en,champions_legal)"
        " VALUES(:name_ko,:name_en,:type_ko,:type_en,:category,:power,:accuracy,:pp,:priority,:target,:effect_en,:cl)",
        [{**m, "cl": int(m["champions_legal"])} for m in mv],
    )

    ls = load("learnsets.json")
    cur.executemany("INSERT OR IGNORE INTO pokemon_moves VALUES(?,?)",
                    [(name, move) for name, moves in ls.items() for move in moves])

    ab = load("abilities.json")
    cur.executemany(
        "INSERT INTO abilities(name_ko,name_en,desc_en,champions_legal) VALUES(:name_ko,:name_en,:desc_en,:cl)",
        [{**a, "cl": int(a["champions_legal"])} for a in ab],
    )

    it = load("items.json")
    cur.executemany(
        "INSERT INTO items(name_ko,name_en,category,desc_en,champions_legal) VALUES(:name_ko,:name_en,:category,:desc_en,:cl)",
        [{**i, "cl": int(i["champions_legal"])} for i in it],
    )

    na = load("natures.json")
    cur.executemany(
        "INSERT INTO natures(name_ko,name_en,increased,decreased,champions_legal) VALUES(:name_ko,:name_en,:increased,:decreased,:cl)",
        [{**n, "cl": int(n["champions_legal"])} for n in na],
    )

    tc = load("type_chart.json")
    cur.executemany("INSERT INTO type_chart VALUES(?,?,?)",
                    [(atk, df, mult) for atk, row in tc.items() for df, mult in row.items()])

    ref = load("reference.json")
    cur.executemany("INSERT INTO reference VALUES(?,?,?)",
                    [(k, v["value_ko"], v["value_en"]) for k, v in ref.items()])

    con.commit()
    print("Built champions.db")
    for t in ["pokemon", "pokemon_abilities", "pokemon_moves", "moves", "abilities",
              "items", "natures", "type_chart", "reference"]:
        print(f"  {t}: {cur.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
