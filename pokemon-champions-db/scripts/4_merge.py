#!/usr/bin/env python3
"""Step 4 — Merge all raw sources into clean, Korean-annotated source-of-truth JSON.

Pokémon identity / stats / types / abilities / dex / form come from the repo
(roster.json + base-stats.json — clean, per-form). Serebii supplies ONLY the
per-species movepool (the repo's learnsets were truncated sample data). Korean
names, move types, and the type chart come from PokeAPI.

Outputs (data/json/): pokemon, moves, abilities, items, natures, learnsets,
  type_chart, reference, merge_report (.json each).
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "json"

NATURE_NOT_LEGAL = {"Hardy", "Docile", "Bashful", "Quirky"}
FORM_PREFIX = (("mega ", "메가 "), ("primal ", "원시 "),
               ("alolan ", "알로라 "), ("galarian ", "가라르 "),
               ("hisuian ", "히스이 "), ("paldean ", "팔데아 "))

REFERENCE = {
    "level": {"value_en": "All Pokémon fixed at Level 50", "value_ko": "모든 포켓몬 레벨 50 고정"},
    "ivs": {"value_en": "All IVs fixed at 31", "value_ko": "모든 개체값(IV) 31 고정"},
    "sp_total": {"value_en": "66 Stat Points total", "value_ko": "스탯 포인트(SP) 총 66"},
    "sp_per_stat_max": {"value_en": "Max 32 SP per stat", "value_ko": "스탯당 최대 32 SP"},
    "sp_ratio": {"value_en": "1 SP = +1 actual stat at Lv50", "value_ko": "1 SP = 실수치 +1 (Lv50)"},
    "vp_move": {"value_en": "250 VP per move change", "value_ko": "기술 변경 250 VP (개당)"},
    "vp_ability": {"value_en": "500 VP per ability change (incl. Hidden)", "value_ko": "특성 변경 500 VP (숨겨진 특성 포함)"},
    "vp_nature": {"value_en": "500 VP per nature (Stat Alignment) change", "value_ko": "성격(스탯 얼라인먼트) 변경 500 VP"},
    "vp_sp": {"value_en": "5 VP per Stat Point", "value_ko": "스탯 포인트당 5 VP"},
    "format_single": {"value_en": "Single Battle: bring 6, select 3", "value_ko": "싱글 배틀: 6마리 중 3마리 선출"},
    "format_double": {"value_en": "Double Battle: bring 6, select 4", "value_ko": "더블 배틀: 6마리 중 4마리 선출"},
    "gimmick": {"value_en": "Mega Evolution active; Terastallization planned", "value_ko": "메가진화 활성, 테라스탈 예정"},
    "regulation": {"value_en": "Regulation M-A (as of data snapshot)", "value_ko": "레귤레이션 M-A 기준"},
}


def load_repo(path: str):
    d = json.loads((RAW / "repo" / path).read_text(encoding="utf-8"))
    return d["data"] if isinstance(d, dict) and "data" in d else d


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s)).lower().strip()
    s = s.replace("♀", "f").replace("♂", "m")
    return re.sub(r"[.'’:\-\s_]+", "", s)


def ko_lookup(mp: dict, name: str):
    nm = {norm(k): v for k, v in mp.items()}
    return mp.get(name) or nm.get(norm(name))


def ko_pokemon(species_map: dict, name: str):
    """Korean name for a species; for forms, translate base + Korean prefix."""
    direct = ko_lookup(species_map, name)
    if direct:
        return direct
    low = name.lower()
    for en_pre, ko_pre in FORM_PREFIX:
        if low.startswith(en_pre):
            base = name[len(en_pre):]
            base = re.sub(r"\s+[XY]$", "", base)  # Mega Charizard X/Y
            suffix = name[len(en_pre):][len(base):].strip()
            base_ko = ko_lookup(species_map, base)
            if base_ko:
                return f"{ko_pre}{base_ko}" + (f" {suffix}" if suffix else "")
    return None


def item_category(name: str) -> str:
    n = name.lower()
    if n.endswith("berry"):
        return "Berry"
    if n.endswith(" z") or "ium z" in n:
        return "Z-Crystal"
    if n.endswith("ite") and name[:1].isupper():
        return "Mega Stone"
    if n.endswith("plate"):
        return "Plate"
    if n.endswith("memory"):
        return "Memory"
    if "gem" in n:
        return "Gem"
    return "Other"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    maps = json.loads((RAW / "maps.json").read_text(encoding="utf-8"))
    report = {"unmatched": {}}

    # ---- Serebii movepools (the only thing we take from Serebii) ----
    sb_learn = json.loads((RAW / "serebii" / "learnsets.json").read_text())
    sb_move = {}  # normalized name -> [moves]
    for k, v in sb_learn.items():
        if norm(k) in (norm("pokedex-champions"),) or "database" in k.lower() or "dex" == k.lower():
            continue
        moves = [m["name"] if isinstance(m, dict) else m for m in v["moves"]]
        sb_move[norm(k)] = moves

    # ---- POKEMON (repo roster + base-stats; clean per-form) ----
    roster = load_repo("pokemon/roster.json")
    stats = {(norm(s["name"])): s for s in load_repo("pokemon/base-stats.json")}
    pokemon, learnsets = [], {}
    miss_pk_ko, miss_movepool = [], []
    for r in roster:
        name = r["name"]
        nk = norm(name)
        st = stats.get(nk, {})
        ab = r.get("abilities", {}) or {}
        ability_list = [ab[k] for k in ("0", "1", "H") if ab.get(k)]
        # de-dup while preserving order
        seen = set()
        ability_list = [a for a in ability_list if not (a in seen or seen.add(a))]
        hidden = ab.get("H")
        ko = ko_pokemon(maps["species"], name)
        if not ko:
            miss_pk_ko.append(name)
        types = r.get("types", [])
        mp = sb_move.get(nk)
        if mp is None and name.lower().startswith("mega charizard"):
            mp = sb_move.get(norm("Mega Charizard"))      # Serebii lists one Mega Charizard page
        if mp is None and name.lower().startswith(("mega ", "primal ")):
            base = re.sub(r"\s+[XY]$", "", name.split(" ", 1)[1])
            mp = sb_move.get(norm(base))                   # mega shares base movepool
        if mp is None:
            mp = []
            miss_movepool.append(name)
        learnsets[name] = mp
        pokemon.append({
            "dex": r.get("dexNumber"), "name_en": name, "name_ko": ko,
            "form": r.get("form"),
            "type1": types[0] if types else None,
            "type2": types[1] if len(types) > 1 else None,
            "hp": st.get("hp"), "atk": st.get("atk"), "def": st.get("def"),
            "spa": st.get("spa"), "spd": st.get("spd"), "spe": st.get("spe"),
            "total": st.get("total"),
            "abilities": ability_list, "ability_hidden": hidden,
            "champions_legal": bool(r.get("championsVerified", True)),
        })
    pokemon.sort(key=lambda x: (x["dex"] or 9999, 0 if x["form"] == "Base" else 1, x["name_en"]))
    report["unmatched"]["pokemon_ko"] = miss_pk_ko
    report["unmatched"]["movepool_missing"] = miss_movepool
    movepool_moves = {m for ms in learnsets.values() for m in ms}

    # ---- MOVES ----
    repo_moves = {m["name"]: m for m in load_repo("moves/moves.json")}
    moves, miss_mv_ko, miss_mv_type = [], [], []
    for name in sorted(set(repo_moves) | movepool_moves):
        rm = repo_moves.get(name, {})
        eff = rm.get("effects") or {}
        ko = ko_lookup(maps["move"], name)
        mt = maps["move_type"].get(name) or {}
        if not ko:
            miss_mv_ko.append(name)
        if not mt.get("type_en"):
            miss_mv_type.append(name)
        moves.append({
            "name_en": name, "name_ko": ko,
            "type_en": mt.get("type_en"), "type_ko": mt.get("type_ko"),
            "category": rm.get("category"), "power": rm.get("power"),
            "accuracy": rm.get("accuracy"), "pp": rm.get("pp"),
            "priority": rm.get("priority"), "target": rm.get("target"),
            "effect_en": rm.get("description") or eff.get("description"),
            "champions_legal": bool(rm.get("inChampions")) or (name in movepool_moves),
        })
    report["unmatched"]["move_ko"] = miss_mv_ko
    report["unmatched"]["move_type"] = miss_mv_type

    # ---- ABILITIES ----
    repo_ab = {a["name"]: a for a in load_repo("abilities/abilities.json")}
    used_ab = {a for p in pokemon for a in p["abilities"]}
    abilities, miss_ab = [], []
    for name in sorted(set(repo_ab) | used_ab):
        ra = repo_ab.get(name, {})
        ko = ko_lookup(maps["ability"], name)
        if not ko:
            miss_ab.append(name)
        abilities.append({
            "name_en": name, "name_ko": ko,
            "desc_en": ra.get("description") or ra.get("effect"),
            "champions_legal": bool(ra.get("inChampions", True)),
        })
    report["unmatched"]["ability_ko"] = miss_ab

    # ---- ITEMS ----
    items, miss_it = [], []
    for it in load_repo("items/items.json"):
        name = it["name"]
        ko = ko_lookup(maps["item"], name)
        if not ko:
            miss_it.append(name)
        items.append({
            "name_en": name, "name_ko": ko, "category": item_category(name),
            "desc_en": it.get("description") or it.get("effect"),
            "champions_legal": bool(it.get("inChampions", True)),
        })
    items.sort(key=lambda x: x["name_en"])
    report["unmatched"]["item_ko"] = miss_it

    # ---- NATURES ----
    natures = []
    for n in load_repo("natures/natures.json"):
        name = n["name"]
        natures.append({
            "name_en": name, "name_ko": ko_lookup(maps["nature"], name),
            "increased": n.get("increasedStat") or n.get("increased") or n.get("plus"),
            "decreased": n.get("decreasedStat") or n.get("decreased") or n.get("minus"),
            "champions_legal": name not in NATURE_NOT_LEGAL,
        })
    natures.sort(key=lambda x: x["name_en"])

    # ---- TYPE CHART (PokeAPI efficacy) ----
    type_chart = maps.get("type_chart", {})

    def dump(obj, fn):
        (OUT / fn).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")

    dump(pokemon, "pokemon.json")
    dump(moves, "moves.json")
    dump(abilities, "abilities.json")
    dump(items, "items.json")
    dump(natures, "natures.json")
    dump(learnsets, "learnsets.json")
    dump(type_chart, "type_chart.json")
    dump(REFERENCE, "reference.json")
    dump(report, "merge_report.json")

    print(f"pokemon={len(pokemon)} (ko_missing={len(miss_pk_ko)} movepool_missing={len(miss_movepool)})")
    print(f"  with_stats={sum(1 for p in pokemon if p['total'])} legal={sum(p['champions_legal'] for p in pokemon)}")
    print(f"moves={len(moves)} legal={sum(m['champions_legal'] for m in moves)} "
          f"(ko_missing={len(miss_mv_ko)} type_missing={len(miss_mv_type)})")
    print(f"abilities={len(abilities)} (ko_missing={len(miss_ab)})")
    print(f"items={len(items)} (ko_missing={len(miss_it)})")
    print(f"natures={len(natures)} legal={sum(n['champions_legal'] for n in natures)}")
    print(f"learnsets={len(learnsets)} type_chart_attackers={len(type_chart)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
