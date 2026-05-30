# 포켓몬 챔피언스 배틀 정보 DB (Pokémon Champions battle DB)

포켓몬 챔피언스(Pokémon Champions, 레귤레이션 M-A 기준)의 배틀 레퍼런스 정보를
로컬에서 조회하기 위한 데이터베이스입니다. 한국어 우선(영문 병기).

수록 정보: 현재 사용 가능한 **포켓몬**, **기술**, **특성**, **도구**, **성격(스탯 얼라인먼트)**,
**종별 사용 가능 기술 목록(movepool)**, 타입 상성표, SP/VP 커스터마이즈 규칙.

## 구조

```
data/raw/      # 원본 다운로드 (재현용 캐시)
  repo/        #   otterlyclueless/pokemon-champions-data (기술/특성/도구/성격 상세)
  pokeapi/     #   PokeAPI CSV (한글 이름 + 기술 타입)
  serebii/     #   Serebii Champions 페이지 (사용 가능 로스터 + 종별 movepool)
data/json/     # 병합된 원천 데이터 (사람이 직접 수정 가능) — DB의 source of truth
scripts/       # 파이프라인 (번호순 실행)
champions.db   # 생성된 SQLite DB (조회용)
```

## 파이프라인

| 스크립트 | 역할 |
|---|---|
| `1_fetch_repo.py` | GitHub 챔피언스 데이터셋 JSON 다운로드 (포켓몬/기술/특성/도구/성격/종족값) |
| `2_fetch_pokeapi.py` | PokeAPI CSV → 영문→한글 이름맵 + 기술 타입맵 + 타입 상성표 |
| `3_scrape_serebii.py` | Serebii Champions 페이지 스크랩(캐시) → **종별 movepool 전용** |
| `4_merge.py` | 위 모두 병합 + 한글 병기 → `data/json/*` |
| `5_build_db.py` | `data/json/*` → `champions.db` |
| `verify.py` | 빌드 검증(행 수/커버리지/샘플 쿼리) |

포켓몬 본체(이름·도감번호·타입·특성·종족값·폼)는 GitHub 데이터셋의 `roster.json` +
`base-stats.json`(폼별로 깔끔함)에서 가져오고, **Serebii는 오직 종별 movepool**에만 사용합니다
(데이터셋의 learnsets가 종당 9개로 잘린 샘플이었기 때문). 타입 상성표는 PokeAPI에서 가져옵니다.

전체 재빌드 (원클릭):
```bash
bash build_all.sh
```
또는 단계별:
```bash
./.venv/bin/python scripts/1_fetch_repo.py
./.venv/bin/python scripts/2_fetch_pokeapi.py
./.venv/bin/python scripts/3_scrape_serebii.py   # 최초 1회만 느림(캐시됨)
./.venv/bin/python scripts/4_merge.py
./.venv/bin/python scripts/5_build_db.py
./.venv/bin/python scripts/verify.py
```

`data/json/*` 를 손으로 고친 뒤 `5_build_db.py` 만 다시 돌리면 DB가 갱신됩니다.
(긴 도구·기술 설명도 JSON에서 편집 — SQL INSERT 직접 작성 불필요.)
레귤레이션이 바뀌면 `3_scrape_serebii.py` 의 `html/` 캐시를 지우고 다시 실행하세요.

## 스키마 (champions.db)

- `pokemon` — 도감번호, 한/영명, 타입1/2, 종족값(hp/atk/def/spa/spd/spe/total), 숨겨진특성, 사용가능여부
- `pokemon_abilities` — 종-특성 (slot, 숨겨진특성 플래그)
- `pokemon_moves` — 종-기술 (종별 movepool)
- `moves` — 한/영명, 타입(한/영), 분류, 위력, 명중, PP, 우선도, 효과, 챔피언스 사용가능
- `abilities` / `items` / `natures` — 한/영명 + 상세
- `type_chart` — 공격타입 × 방어타입 → 배율
- `reference` — SP/VP 규칙, 배틀 포맷 등 상수
- 뷰: `v_pokemon_movepool`, `v_pokemon_abilities`

## 조회 예시

```sql
-- 이상해꽃이 배울 수 있는 기술
SELECT 기술, 타입, power, pp FROM v_pokemon_movepool WHERE pokemon='Venusaur';

-- 한글 이름으로 검색
SELECT * FROM pokemon WHERE name_ko LIKE '%리자몽%';

-- 불꽃 타입 중 챔피언스에서 쓸 수 있는 위력 100 이상 기술
SELECT name_ko, power, accuracy FROM moves
WHERE type_en='Fire' AND champions_legal=1 AND power>=100 ORDER BY power DESC;

-- 지진(Earthquake)을 배우는 포켓몬
SELECT 포켓몬 FROM v_pokemon_movepool WHERE move='Earthquake';
```

```bash
sqlite3 champions.db "SELECT name_ko, total FROM pokemon ORDER BY total DESC LIMIT 10"
```

## 데이터 출처 / 라이선스

- **otterlyclueless/pokemon-champions-data** — 기술/특성/도구/성격/타입표. CC BY 4.0.
- **Serebii.net** (Pokémon Champions 섹션) — 사용 가능 로스터, 종별 movepool, 종족값/타입/특성.
- **PokeAPI** (github.com/PokeAPI/pokeapi, BSD) — 한글 이름, 기술 타입.

데이터는 커뮤니티가 정리한 것으로 인게임과 다를 수 있으며, 레귤레이션 갱신 시 재수집이 필요합니다.

## 현재 빌드 결과 (검증됨)

- 포켓몬 **258** (Base/Mega/Regional), 한글명 258/258, 종족값 누락 0
- 종-기술 매핑 **15,788**건 (245/258 폼에 movepool — 일부 메가/리전폼은 Serebii 페이지명
  불일치로 누락, 베이스 movepool로 대체 시도)
- 기술 **901** (챔피언스 사용가능 496) · 특성 191 · 도구 583 · 성격 25(사용 21) · 타입표 18×18(324)

## 주의 / 한계

- 포켓몬은 데이터셋(2026-04-16 스냅샷)의 258종 기준이며 메가/리전폼을 **별도 행**으로 둡니다.
  (메가는 베이스 종의 movepool을 공유)
- IV 31·레벨 50 고정이라 개체별 변수로 저장하지 않습니다 (`reference` 참고).
- 성격은 25종을 모두 수록하되, 챔피언스 미사용 4종(Hardy/Docile/Bashful/Quirky)은
  `champions_legal=0` 으로 표시했습니다.
- 일부 신규/비(非)챔피언스 기술·도구는 PokeAPI에 한글명이 없어 비어 있을 수 있습니다
  (영문 fallback). 챔피언스 사용가능 기술 중 약 43개(주로 신규 기술)는 한글명·타입이 미상입니다.
