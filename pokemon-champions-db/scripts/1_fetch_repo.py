#!/usr/bin/env python3
"""Step 1 — Download raw JSON from the otterlyclueless/pokemon-champions-data repo.

Source: https://github.com/otterlyclueless/pokemon-champions-data  (CC BY 4.0)
Saves every data file into data/raw/repo/<path>.
"""
import json
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

REPO = "otterlyclueless/pokemon-champions-data"
BRANCH = "main"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
TREE_API = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "raw" / "repo"


def fetch(url: str, *, as_json: bool = False, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "pkmn-champions-db/1.0"})
            with urlopen(req, timeout=30) as resp:
                data = resp.read()
            return json.loads(data) if as_json else data
        except (HTTPError, URLError) as e:  # noqa: PERF203
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tree = fetch(TREE_API, as_json=True)
    paths = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]
    json_paths = [p for p in paths if p.endswith(".json")]

    print(f"Found {len(json_paths)} JSON files in {REPO}@{BRANCH}")
    ok = 0
    for p in json_paths:
        dest = OUT / p
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw = fetch(RAW_BASE + p)
            dest.write_bytes(raw)
            ok += 1
            print(f"  ✓ {p}  ({len(raw):,} bytes)")
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {p}  -> {e}", file=sys.stderr)

    # Echo verification counts from meta/version.json if present
    meta = OUT / "meta" / "version.json"
    if meta.exists():
        v = json.loads(meta.read_text())
        print("\nmeta/version.json:")
        print(json.dumps(v, ensure_ascii=False, indent=2)[:1200])

    print(f"\nDownloaded {ok}/{len(json_paths)} files into {OUT}")
    return 0 if ok == len(json_paths) else 1


if __name__ == "__main__":
    raise SystemExit(main())
