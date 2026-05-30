# Pokemon Champions Dashboard

Real-time web dashboard for the Pokemon Champions battle simulator and evolution loop. Watches `loop/runs/` for live battle logs and evolution artifacts, pushes events to the browser via WebSocket, and renders battle progress, Elo curves, and Hall of Fame.

## What it does

- **Live Battle panel**: shows team names, HP bars, status conditions, last action source (sidecar vs heuristic fallback), and an auto-scrolling raw event feed.
- **Elo Curves panel**: Chart.js line chart with one line per genome across generations, updated live as `elo.json` files change.
- **Hall of Fame panel**: table of best genomes with rating, generation added, and top-3 species.
- **Champion panel**: displays the current champion genome.
- **Metrics strip**: running totals for battles, turns, sidecar fallbacks, and generations.

Auto-discovers all runs under `POKEMON_RUNS_ROOT` and lets you pick one from a dropdown. On selection, opens a WebSocket that streams all events live and initialises with a snapshot of existing state.

## Run

```bash
make dashboard
```

Opens at `http://127.0.0.1:8765`. Kill with Ctrl-C.

## How to test live

```bash
# terminal 1 — run evolution
make evolve

# terminal 2 — start dashboard
make dashboard
```

Open `http://127.0.0.1:8765`, pick the latest run in the dropdown, and watch battles stream in real time.

## Architecture

```
loop/runs/{run_id}/
  gen_N/battle_M.jsonl   <- battle events (JSONL)
  gen_N/elo.json         <- Elo ratings after gen N
  hof.json               <- Hall of Fame
  champion.json          <- Current champion genome

watchfiles.awatch()      <- inotify/FSEvents file watcher
    |
    v
FastAPI WebSocket        <- /ws/runs/{run_id}
    |
    v
vanilla JS + Chart.js    <- static/index.html
```

File offsets are tracked per battle log so reconnects and re-watches never double-emit events. No database, no Redis — pure file-watching with asyncio.

## Env vars

| Variable | Default | Description |
|---|---|---|
| `POKEMON_RUNS_ROOT` | `<repo>/loop/runs` | Path to the runs directory |
| `POKEMON_DASHBOARD_HOST` | `127.0.0.1` | Bind host |
| `POKEMON_DASHBOARD_PORT` | `8765` | Bind port |

## Install & test

```bash
cd dashboard && uv sync --extra dev
cd dashboard && uv run pytest -v
```
