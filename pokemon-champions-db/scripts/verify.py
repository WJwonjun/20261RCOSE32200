#!/usr/bin/env python3
"""Validation — sanity-check champions.db end to end. Prints a readable report."""
import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "champions.db"


def main() -> int:
    con = sqlite3.connect(DB)
    c = con.cursor()
    one = lambda q, *a: c.execute(q, a).fetchone()[0]
    rows = lambda q, *a: c.execute(q, a).fetchall()

    print("=== row counts ===")
    for t in ["pokemon", "moves", "abilities", "items", "natures",
              "type_chart", "pokemon_moves", "pokemon_abilities", "reference"]:
        print(f"  {t:18} {one(f'SELECT count(*) FROM {t}')}")

    print("\n=== coverage ===")
    print(f"  pokemon w/ KO name      {one('SELECT count(*) FROM pokemon WHERE name_ko IS NOT NULL')}/{one('SELECT count(*) FROM pokemon')}")
    print(f"  pokemon missing stats   {one('SELECT count(*) FROM pokemon WHERE total IS NULL')}")
    legal = one("SELECT count(*) FROM moves WHERE champions_legal=1")
    print(f"  legal moves             {legal}")
    print(f"   ├ with KO name         {one('SELECT count(*) FROM moves WHERE champions_legal=1 AND name_ko IS NOT NULL')}/{legal}")
    print(f"   └ with type            {one('SELECT count(*) FROM moves WHERE champions_legal=1 AND type_en IS NOT NULL')}/{legal}")
    print(f"  legal natures           {one('SELECT count(*) FROM natures WHERE champions_legal=1')}")

    print("\n=== sample: Venusaur movepool (top power) ===")
    for r in rows("SELECT 기술,타입,power,pp FROM v_pokemon_movepool WHERE pokemon='Venusaur' ORDER BY power DESC LIMIT 5"):
        print("  ", r)
    ven_q = "SELECT count(*) FROM pokemon_moves WHERE pokemon_en='Venusaur'"
    print("  movepool size:", one(ven_q))

    print("\n=== sample: Venusaur abilities ===")
    for r in rows("SELECT ability,특성,숨겨진특성 FROM v_pokemon_abilities WHERE pokemon='Venusaur'"):
        print("  ", r)

    print("\n=== sample: top-5 BST ===")
    for r in rows("SELECT name_ko,name_en,total FROM pokemon ORDER BY total DESC LIMIT 5"):
        print("  ", r)

    print("\n=== sample: Fire legal moves power>=100 ===")
    for r in rows("SELECT name_ko,name_en,power FROM moves WHERE type_en='Fire' AND champions_legal=1 AND power>=100 ORDER BY power DESC LIMIT 5"):
        print("  ", r)

    print("\n=== sample: item categories ===")
    for r in rows("SELECT category,count(*) FROM items GROUP BY category ORDER BY 2 DESC"):
        print("  ", r)

    print("\n=== sample: 3 legal natures ===")
    for r in rows("SELECT name_ko,name_en,increased,decreased FROM natures WHERE champions_legal=1 LIMIT 3"):
        print("  ", r)

    con.close()
    print("\nOK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
