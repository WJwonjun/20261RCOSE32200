# Battle Core

C++20 deterministic Pokemon single-battle simulator core for Pokemon Champions MVP.

## Requirements

- CMake 3.20+
- C++20 compiler (GCC 12+, Clang 14+, or Apple Clang 14+)
- Internet access on first build (FetchContent downloads nlohmann/json and Catch2)

## Build

```bash
cmake -B build -S core
cmake --build build
```

Or from within the `core/` directory:

```bash
cmake -B build
cmake --build build
```

## Run Demo

```bash
./build/battle_demo
```

Prints a JSON-lines turn log to stdout followed by the battle result. Each line is a self-contained JSON object describing one event (move, damage, status, switch, turn start/end, battle end).

Example output:
```
{"event":"battle_start","team_a":"Pikachu lead","team_b":"Gengar lead"}
{"event":"turn_start","turn":1}
{"event":"move","pokemon":"Gengar","move":"Thunderbolt"}
{"event":"damage","target":"Pikachu","damage":45,"hp_remaining":55}
...
{"event":"battle_end","winner":"A","team":"Pikachu side"}
```

## Run Tests

```bash
ctest --test-dir build
```

Or run individual test binaries directly for verbose output:

```bash
./build/test_determinism
./build/test_damage
```

## Architecture

```
core/
  include/battle/
    types.hpp       -- enums (Type, StatusCondition, MoveCategory), Stats, IVs, EVs, Nature
    rng.hpp         -- PCG64 deterministic RNG
    move.hpp        -- Move struct + 10 hard-coded sample moves
    pokemon.hpp     -- Pokemon struct + compute_stats()
    typechart.hpp   -- 18x18 constexpr effectiveness table
    team.hpp        -- Team (6-slot party + active_slot)
    action.hpp      -- Action = variant<MoveAction, SwitchAction, NoAction>
    state.hpp       -- BattleState: teams, RNG, log, legal_actions, apply_action
    damage.hpp      -- compute_damage() declaration
    ai_stub.hpp     -- choose_max_damage_action() declaration
    ipc.hpp         -- SidecarClient stub (IMPL DEFERRED)
  src/
    state.cpp       -- FSM: priority sort, speed tie, damage, status tick, force-switch
    damage.cpp      -- Gen9-ish damage formula
    ai_stub.cpp     -- max-damage heuristic AI (used as LLM sidecar fallback)
    main_demo.cpp   -- builds two 6-mon teams, runs battle, prints JSON-lines log
  tests/
    test_determinism.cpp  -- 100-run bit-identical log + winner check
    test_damage.cpp       -- formula spot checks
```

## Sidecar mode

`./build/battle_demo --sidecar` requires a running Python LLM sidecar on the Unix socket (default `/tmp/pokemon_sidecar.sock`).

Quickest way to test end-to-end with no real LLM calls:

```bash
(cd ../sidecar && POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar) &
./build/battle_demo --sidecar --rulebook=rulebook/rulebook.md
```

Additional flags:
- `--socket=PATH` — override socket path (also honoured via `POKEMON_SIDECAR_SOCK` env var)
- `--rulebook=PATH` — path passed to sidecar in each request (default `rulebook/rulebook.md`)
- `--seed=N` — RNG seed (default 42)

When the sidecar returns a `failure_reason`, the demo falls back to `choose_max_damage_action()` and appends a `{"event":"sidecar_failure",...}` log line. Without `--sidecar`, the demo runs the pure C++ heuristic unchanged.

## Team JSON loading

Pass `--team-a=PATH` and/or `--team-b=PATH` to load a GA-generated team instead of the hard-coded demo teams. Both flags are independent; omitting one uses the hard-coded side.

Schema (exactly 6 members required):

```json
{
  "name": "GenZero_team_3",
  "members": [
    {
      "species": "snorlax",
      "level": 50,
      "ivs": {"hp":31,"atk":31,"def":31,"spa":31,"spd":31,"spe":31},
      "evs": {"hp":4,"atk":252,"def":0,"spa":0,"spd":0,"spe":252},
      "nature": "adamant",
      "moves": ["body_slam","earthquake","crunch","rest"],
      "item": "leftovers"
    }
  ]
}
```

To discover all valid species, move, item, and nature IDs (so the GA never generates an invalid genome):

```bash
./build/battle_demo --print-palette
```

Prints JSON to stdout with keys `species`, `moves`, `items`, `natures`. The `id` field on each entry is the string to use in team JSON files.

On load failure the demo exits with code 2 and prints `# error: failed to load team A/B: <reason>` to stderr.

## Data source

The battle core loads Champions regulation data from JSON files at startup via `champions::load_data()`.

**Default path resolution** (first match wins):
1. `$POKEMON_CHAMPIONS_DB` environment variable (set to a directory containing the JSON files)
2. Upward search from `cwd` for `pokemon-champions-db/data/json/`

**Override example:**
```bash
POKEMON_CHAMPIONS_DB=/path/to/pokemon-champions-db/data/json ./build/battle_demo
```

**Files consumed:**
- `pokemon.json` — 258 Champions-legal species with base stats, types, abilities
- `moves.json` — ~493 legal moves (filtered: `champions_legal == true` AND `category in {Physical, Special, Status}` AND non-null type)
- `natures.json` — 21 Champions-legal natures with stat modifiers
- `items.json` — 583 Champions-legal items (only `leftovers` and `life_orb` have runtime effects)
- `type_chart.json` — 18×18 effectiveness multipliers (read-only; the constexpr table in `typechart.hpp` is used at runtime)
- `learnsets.json` — per-species legal move pools (used to enforce learnset legality in `team_loader`)

**ID normalization:** display names like `"Thunder Bolt"` → code IDs like `"thunder_bolt"` (lowercase, spaces/hyphens → underscores). Both `id` and `display_name` are stored on each entry.

**Learnset enforcement:** `load_team_json()` rejects any move not in the loaded species learnset, throwing `std::runtime_error("team_loader: move '<X>' not in <species>'s learnset")`.

If the data path cannot be found, `load_data()` throws `std::runtime_error` with a clear message and the demo exits with code 1.

## Excluded (M5+)

- Weather (`// NOT IMPLEMENTED: weather`)
- Terrain (`// NOT IMPLEMENTED: terrain`)
- Abilities (noop)
- Z-moves, Dynamax, Tera, Doubles
