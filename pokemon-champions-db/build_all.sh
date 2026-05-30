#!/usr/bin/env bash
# 포켓몬 챔피언스 DB 전체 빌드. 프로젝트 루트에서 실행하세요.
#   bash build_all.sh
set -euo pipefail
cd "$(dirname "$0")"
PY=./.venv/bin/python

echo "[1/6] GitHub 챔피언스 데이터셋 다운로드"
$PY scripts/1_fetch_repo.py
echo "[2/6] PokeAPI 한글 이름/타입 맵"
$PY scripts/2_fetch_pokeapi.py
echo "[3/5] Serebii 종별 movepool 스크랩 (최초 1회만 느림, 캐시됨)"
$PY scripts/3_scrape_serebii.py
echo "[4/5] 병합 + 한글 병기 -> data/json/"
$PY scripts/4_merge.py
echo "[5/5] SQLite 빌드 -> champions.db"
$PY scripts/5_build_db.py
echo "[검증]"
$PY scripts/verify.py

echo
echo "완료. 예시 조회:"
echo "  sqlite3 champions.db \"SELECT 기술,타입,power FROM v_pokemon_movepool WHERE pokemon='Venusaur' LIMIT 5\""
