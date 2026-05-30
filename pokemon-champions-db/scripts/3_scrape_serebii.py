#!/usr/bin/env python3
"""Step 3 — Scrape per-species movepools from Serebii's Champions Pokédex.

WHY: the source repo's learnset files are truncated to 9 moves/species (sample
data). Serebii is the authoritative upstream for full Champions movepools.

Source: https://www.serebii.net/pokemonchampions/pokemon.shtml  (index)
        https://www.serebii.net/pokedex-champions/<slug>/         (per species)
Produces:
  data/raw/serebii/html/<slug>.html     cached pages (reruns are free)
  data/raw/serebii/roster.json          [{name, slug}]
  data/raw/serebii/learnsets.json       {name: {slug, moves: [...]}}

Polite: ~1.3s delay, descriptive UA, cached. Movepool = unique move names linking
to /attackdex-champions/ on each page (validated to match the repo move DB).
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from bs4 import BeautifulSoup

BASE = "https://www.serebii.net"
INDEX = f"{BASE}/pokemonchampions/pokemon.shtml"
UA = "Mozilla/5.0 (compatible; pkmn-champions-db/1.0; personal reference)"
DELAY = 1.3

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "serebii"
HTML = OUT / "html"
ATK = re.compile(r"/attackdex-champions/")
PDX = re.compile(r"/pokedex-champions/")


def get(url: str) -> str:
    last = None
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA}), timeout=45) as r:
                return r.read().decode("utf-8", "replace")
        except (URLError, HTTPError) as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def get_index() -> dict[str, str]:
    soup = BeautifulSoup(get(INDEX), "lxml")
    pairs: dict[str, str] = {}
    for a in soup.find_all("a", href=PDX):
        txt = a.get_text(strip=True)
        href = a.get("href", "")
        if txt and "/pokedex-champions/" in href:
            pairs.setdefault(txt, href)
    return pairs


def movepool(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    seen, moves = set(), []
    for a in soup.find_all("a", href=ATK):
        n = a.get_text(strip=True)
        if n and n not in seen:
            seen.add(n)
            moves.append(n)
    return moves


def main() -> int:
    HTML.mkdir(parents=True, exist_ok=True)
    index = get_index()
    print(f"Index: {len(index)} available species")
    roster, learnsets, empty = [], {}, []
    for i, (name, href) in enumerate(sorted(index.items()), 1):
        slug = href.rstrip("/").split("/")[-1]
        cache = HTML / f"{slug}.html"
        if cache.exists() and cache.stat().st_size > 5000:
            html = cache.read_text(encoding="utf-8")
        else:
            html = get(BASE + href if href.startswith("/") else href)
            cache.write_text(html, encoding="utf-8")
            time.sleep(DELAY)
        moves = movepool(html)
        roster.append({"name": name, "slug": slug})
        learnsets[name] = {"slug": slug, "moves": moves}
        if not moves:
            empty.append(name)
        if i % 25 == 0:
            print(f"  {i}/{len(index)} ... {name}: {len(moves)} moves")

    (OUT / "roster.json").write_text(json.dumps(roster, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "learnsets.json").write_text(json.dumps(learnsets, ensure_ascii=False, indent=1), encoding="utf-8")
    sizes = [len(v["moves"]) for v in learnsets.values()]
    print(f"Done: {len(learnsets)} species, moves/species min={min(sizes)} max={max(sizes)}")
    if empty:
        print(f"WARNING {len(empty)} species had 0 moves: {empty[:10]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
