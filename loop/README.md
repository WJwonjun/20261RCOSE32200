# Pokemon Champions — MVP Tournament Orchestrator

Ties together the C++ Battle Core and Python LLM Sidecar into a runnable
end-to-end loop: 8 teams, 12 battles, leaderboard.

## What it does

1. Starts the sidecar in **stub mode** (no API key, no cost).
2. Runs 12 battles through the C++ `battle_demo` binary.
3. Aggregates wins/losses per team and prints a `rich` leaderboard.

The stub sidecar responds with the first legal action instantly — this is a
first-class operating mode documented in `sidecar/README.md`, not a workaround.
Swap to a real LLM by unsetting `POKEMON_SIDECAR_STUB` and setting your key.

## Quickstart

```bash
# From repo root — builds core, installs loop deps, runs tournament
make tournament
```

## Manual run

```bash
cd loop
uv sync --extra dev
POKEMON_REPO=/path/to/repo uv run python -m pokemon_loop --n-battles=12
```

## Data source

The GA palette (species, moves, items, natures) is loaded directly from the
Pokemon Champions DB JSON files. By default the DB is resolved relative to the
repo root:

```
<repo-root>/pokemon-champions-db/data/json/
```

Override with an env var:

```bash
export POKEMON_CHAMPIONS_DB=/path/to/pokemon-champions-db/data/json
```

The palette includes:
- **258 species** (filtered `champions_legal == true`)
- **~495 moves** (filtered `champions_legal == true` AND category in Physical/Special/Status)
- **583 items** (filtered `champions_legal == true`)
- **21 natures** (filtered `champions_legal == true`)

Each species carries its legal learnset from `learnsets.json`, so GA mutations
(swap_move) are always restricted to moves that species can actually learn. The
cache is stored at `loop/.cache/palette.json` and is invalidated automatically
when any source JSON is newer than the cache.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `POKEMON_REPO` | `/Users/song-wonjun/20261RCOSE32200` | Repo root (overrides hardcoded path) |
| `POKEMON_SIDECAR_STUB` | set to `1` automatically by orchestrator | Force stub mode |
| `POKEMON_SIDECAR_SOCK` | `/tmp/pokemon_sidecar_<run_id>.sock` | Socket path (set automatically) |
| `ANTHROPIC_API_KEY` | unset | Set to use real LLM (see below) |

## Swapping stub for real LLM

```bash
unset POKEMON_SIDECAR_STUB
export ANTHROPIC_API_KEY=sk-ant-...
cd loop && uv run python -m pokemon_loop
```

The orchestrator passes `POKEMON_SIDECAR_STUB=1` in the sidecar's environment.
To override, edit `sidecar_proc.py` to remove that env var and ensure your key
is in the environment before running.

## Limitations

- **Hard-coded teams in binary**: `battle_demo` currently ignores `--team-a` /
  `--team-b` flags (the C++ executor is adding these in parallel). Until those
  flags land, every battle uses the binary's built-in Team A vs Team B with
  fixed RNG. The leaderboard shows logical bracket slots, not distinct archetypes.
  Re-run after the flags are merged for real team diversity.

- **No `--seed` flag**: RNG seeding is also pending in the C++ binary. All
  battles produce the same outcome until `--seed` is supported.

- **Sequential battles**: battles run one at a time (one sidecar, easy to
  reason about). Parallelism is out of scope for this MVP.

## Running tests

```bash
cd loop
uv sync --extra dev
POKEMON_REPO=/path/to/repo uv run pytest -v
```

The smoke test skips automatically if `build/battle_demo` doesn't exist.

## Evolution mode

The GA evolution layer runs a multi-generation tournament that mutates team
genomes, tracks Elo ratings, maintains a Hall of Fame, and evaluates the
champion against 3 fixed seed teams each generation.

### Quickstart

```bash
# From repo root — builds core, installs loop deps, runs 5-generation GA
make evolve
```

### Manual run

```bash
cd loop
POKEMON_REPO=/path/to/repo uv run python -m pokemon_loop evolve \
    --generations=5 --pop=8 --battles-per-gen=12 --seed=42
```

### What the output looks like

```
Evolution Progress  (run evo_1234567890)
┌─────┬──────────┬──────────┬──────────────────┬──────────┬───────────┬──────────────────┐
│ Gen │  Avg Elo │  Max Elo │ Champion         │ vs Seeds │ Mutations │ HoF              │
├─────┼──────────┼──────────┼──────────────────┼──────────┼───────────┼──────────────────┤
│   0 │  1008.3  │  1045.6  │ gen0_team_3      │     1/3  │         4 │ gen0_team_3      │
│   1 │  1012.1  │  1061.2  │ mut_gen0_team_3  │     2/3  │         3 │ mut_gen0_team_3  │
│ ... │    ...   │    ...   │ ...              │      ... │       ... │ ...              │
└─────┴──────────┴──────────┴──────────────────┴──────────┴───────────┴──────────────────┘

Hall of Fame
┌──────┬────────────────────────┬────────┬───────────┬──────────────────────────────────────┐
│ Rank │ Genome                 │ Rating │ Gen Added │ Species                              │
├──────┼────────────────────────┼────────┼───────────┼──────────────────────────────────────┤
│    1 │ mut_gen0_team_3_g4     │ 1078.4 │         3 │ charizard, lucario, ...              │
│    2 │ cross_4_1              │ 1061.2 │         4 │ garchomp, togekiss, ...              │
└──────┴────────────────────────┴────────┴───────────┴──────────────────────────────────────┘
```

### Artifacts

After `make evolve`, the following files are created under `loop/runs/{run_id}/`:

| File | Description |
|---|---|
| `gen_{n}/elo.json` | Elo ratings snapshot after generation n |
| `gen_{n}/teams/{name}.json` | All genome JSONs for that generation |
| `gen_{n}/seed_evals/battle_*.jsonl` | Champion vs seed battle logs |
| `hof.json` | Hall of Fame (top 2 genomes across all generations) |
| `champion.json` | Best genome's JSON in C++ team_loader format |

### Stub mode (default — no API key needed)

By default, the sidecar runs in stub mode (`POKEMON_SIDECAR_STUB=1`) — it
responds with the first legal action without calling any LLM. This keeps
`make evolve` free and fast (~75 battles ≈ <5 min).

### Switching to real LLM

```bash
unset POKEMON_SIDECAR_STUB
export ANTHROPIC_API_KEY=sk-ant-...
make evolve
```

### C++ dependency note

`--team-a`/`--team-b` JSON loading and `--print-palette` are implemented by
the C++ executor in parallel. Until those flags land in `battle_demo`:

- All genome JSON files are still written to disk correctly.
- The binary ignores `--team-a`/`--team-b` and uses its hard-coded teams.
- Elo/HoF/GA logic still runs — team diversity is simulated via bracket
  randomness until the C++ side lands.

Re-run `make evolve` after the C++ flags are merged for real genome-driven battles.
