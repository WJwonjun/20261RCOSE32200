#!/usr/bin/env python3
"""Step 6 — Filter champions.db down to the currently-available set:
  - 등장 포켓몬: Pokémon whose Korean name appears in the namu.wiki M-A list
    (+ their Mega/Regional forms, since a mega appears iff its base appears).
  - 도구 (held items): items present on Serebii's Champions items page.
  - 메가스톤: mega stones belonging to a kept Mega form.

Everything else (moves, abilities, natures, type_chart, reference) is kept as
battle reference. pokemon_moves / pokemon_abilities are pruned to kept Pokémon.

Usage:
  python scripts/6_filter_available.py          # DRY RUN (report only)
  python scripts/6_filter_available.py --apply  # actually delete
"""
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from urllib.request import urlopen, Request

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "champions.db"
NAMU_SRC = Path("/Users/song-wonjun/.claude/projects/-Users-song-wonjun/"
                "8306fe9b-6f6e-4041-9748-0c6a0cf9f396/tool-results/"
                "toolu_01Tbrq5UEiYKsvUXbaGiL58M.txt")
SEREBII_ITEMS = "https://www.serebii.net/pokemonchampions/items.shtml"
UA = "Mozilla/5.0 (compatible; pkmn-champions-db/1.0; personal reference)"
CACHE = ROOT / "data" / "raw" / "serebii" / "items.html"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).lower().strip()
    return re.sub(r"[\s.\-’':()]+", "", s)


def namu_blob() -> str:
    soup = BeautifulSoup(NAMU_SRC.read_text(encoding="utf-8"), "lxml")
    parts = [soup.get_text(" ", strip=True)]
    for t in soup.find_all(True):
        for a in ("alt", "title", "href"):
            if t.get(a):
                parts.append(str(t.get(a)))
    return norm(" ".join(parts))


def serebii_items() -> set[str]:
    if CACHE.exists() and CACHE.stat().st_size > 3000:
        html = CACHE.read_text(encoding="utf-8")
    else:
        html = urlopen(Request(SEREBII_ITEMS, headers={"User-Agent": UA}), timeout=45).read().decode("utf-8", "replace")
        CACHE.write_text(html, encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    names = set()
    for a in soup.find_all("a", href=re.compile(r"/itemdex/")):
        t = a.get_text(strip=True)
        if t:
            names.add(norm(t))
    return names


def main() -> int:
    apply = "--apply" in sys.argv
    blob = namu_blob()
    con = sqlite3.connect(DB)
    c = con.cursor()

    # namu explicitly lists every base species AND every Mega by Korean name, so a
    # direct name_ko match is exactly right. Regional forms (Alolan/Hisuian/Galarian/
    # Paldean) are NOT in the M-A list and are correctly dropped by direct match.
    pk = c.execute("SELECT name_en, name_ko, form, dex FROM pokemon").fetchall()
    keep_pk = {en for en, ko, f, d in pk if ko and norm(ko) in blob}
    drop_pk = [en for en, ko, f, d in pk if en not in keep_pk]

    # items: held items from Serebii + mega stones of kept megas
    sere = serebii_items()
    items = c.execute("SELECT name_en, name_ko, category FROM items").fetchall()
    kept_mega_dex = {d for en, ko, f, d in pk if f == "Mega" and en in keep_pk}
    # a mega stone is kept if any kept mega exists; match stone<->mega loosely by name stem
    kept_mega_ko = [ko for en, ko, f, d in pk if f == "Mega" and en in keep_pk and ko]
    keep_items = set()
    for en, ko, cat in items:
        if norm(en) in sere or (ko and norm(ko) in sere):
            keep_items.add(en)
        elif cat == "Mega Stone":
            # keep mega stone if its target mega is kept (match by base name stem)
            stem = norm(re.sub(r"(ite|나이트|나이트엑스|나이트와이)\s*[xy]?$", "", en.lower()))
            if any(stem and stem in norm(mk) for mk in kept_mega_ko) or norm(en) in sere:
                keep_items.add(en)
    drop_items = [en for en, ko, cat in items if en not in keep_items]
    mega_kept = [en for en, ko, cat in items if cat == "Mega Stone" and en in keep_items]

    print(f"namu blob_len={len(blob)}  serebii_items={len(sere)}")
    print(f"POKEMON: total={len(pk)} keep={len(keep_pk)} drop={len(drop_pk)}")
    print(f"  keep by form: base={sum(1 for e,k,f,d in pk if e in keep_pk and f=='Base')} "
          f"mega={sum(1 for e,k,f,d in pk if e in keep_pk and f=='Mega')} "
          f"regional={sum(1 for e,k,f,d in pk if e in keep_pk and f=='Regional')}")
    print(f"  drop sample: {drop_pk[:15]}")
    print(f"ITEMS: total={len(items)} keep={len(keep_items)} drop={len(drop_items)} (mega_stones_kept={len(mega_kept)})")
    print(f"  keep sample: {sorted(keep_items)[:20]}")
    print(f"  mega stones kept sample: {sorted(mega_kept)[:12]}")

    if not apply:
        print("\nDRY RUN — no changes. Re-run with --apply to delete.")
        con.close()
        return 0

    qpk = ",".join("?" * len(keep_pk))
    qit = ",".join("?" * len(keep_items))
    kp, ki = list(keep_pk), list(keep_items)
    c.execute(f"DELETE FROM pokemon WHERE name_en NOT IN ({qpk})", kp)
    c.execute(f"DELETE FROM pokemon_moves WHERE pokemon_en NOT IN ({qpk})", kp)
    c.execute(f"DELETE FROM pokemon_abilities WHERE pokemon_en NOT IN ({qpk})", kp)
    c.execute(f"DELETE FROM items WHERE name_en NOT IN ({qit})", ki)
    con.commit()
    print("\nAPPLIED. Final counts:")
    for t in ["pokemon", "items", "pokemon_moves", "pokemon_abilities", "moves", "abilities", "natures", "type_chart"]:
        print(f"  {t}: {c.execute(f'SELECT count(*) FROM {t}').fetchone()[0]}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
