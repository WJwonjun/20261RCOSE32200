# Pokemon Champions Battle Simulator + LLM Evolutionary Trainer

A deterministic C++ battle simulator that drives self-play between LLM-controlled teams. An evolutionary loop discovers strong team compositions over generations using Claude Haiku 4.5 with prompt caching, powered by a high-performance single-threaded battle engine and async Python sidecar.

## Components

- **`core/`** — C++20 deterministic battle engine (the source of truth for game rules). See `core/README.md`.
- **`sidecar/`** — Python asyncio LLM gateway (Claude Haiku 4.5, prompt caching). See `sidecar/README.md`.
- **`rulebook/`** — Markdown rulebook the LLM agent reads to make decisions. Entry: `rulebook/rulebook.md`.
- **`db/`** — SQLite schema and master data (managed by separate agent — do not modify in PRs touching core/sidecar/rulebook).
- **`loop/`** — (TBD) Orchestrator and evolution loop. Not yet implemented.

## Quickstart

**Build core:**
```bash
cmake -B build -S core && cmake --build build
```

**Run mock battle:**
```bash
./build/battle_demo
```

**Install sidecar:**
```bash
cd sidecar && uv sync
```

**Run sidecar in stub mode (no API key needed):**
```bash
POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar
```

**Smoke test sidecar:**
```bash
uv run python scripts/mock_client.py
```

## Architecture

C++ Battle Core owns deterministic state. Per turn, it emits state JSON over Unix socket to the Python sidecar. Sidecar calls Claude with cached rulebook. Core advances state based on returned action JSON. On LLM failure, core falls back to max-damage heuristic. Replay is deterministic: (RNG seed, ordered LLM response log).

## MVP Status

Population 8, Haiku only, tournament 12 battles/generation, ~$1 per generation cost. M1: C++ core determinism. M2: Single LLM turn. M3: Full loop. M4: Evolution + dashboard.

## Constraints / Non-Goals (MVP)

No weather, terrain, abilities, Z-moves, Dynamax, Terastallize, doubles. Single-machine, single-process per component. Performance over throughput.

## Plan Reference

See `.omc/plans/pokemon-champions-sim.md` for the full development strategy.