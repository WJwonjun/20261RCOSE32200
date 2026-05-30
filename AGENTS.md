# Agent Ownership Map

Multi-agent concurrent development. Each agent owns a directory; changes cross-component go through this file.

| Directory | Owner | Status | Contact |
|-----------|-------|--------|---------|
| `core/` | Core Executor | Building C++20 battle engine | - |
| `sidecar/` | Sidecar Executor | Building Python async LLM gateway | - |
| `rulebook/` | Rulebook Executor | Building Markdown rulebook + schemas | - |
| `db/` | DB Executor | Building SQLite schema + data layer | **DO NOT TOUCH** |
| `loop/` | (TBD) | Orchestrator and evolution loop (M3+) | (not yet active) |
| Root-level scaffolding | Scaffold Executor | Root CMakeLists, README, .gitignore, .editorconfig, Makefile | - |

## Current Contracts

### C++ ↔ Python IPC
- **Protocol**: Unix socket (JSONL over raw bytes).
- **Socket path**: `$POKEMON_SIDECAR_SOCK` (default `/tmp/pokemon_sidecar.sock`).
- **Request schema**: `sidecar/src/pokemon_sidecar/schemas.py::TurnState`.
- **Response schema**: `sidecar/src/pokemon_sidecar/schemas.py::LLMCallResult`.
- **Owned by**: Core Executor (client side), Sidecar Executor (server side).
- **Status**: Defined in both `core/` and `sidecar/` codebases; schema must stay in sync.

### Rulebook ↔ Sidecar
- **Entry point**: `rulebook/rulebook.md`.
- **Integration**: Sidecar's `LLMClient` accepts `rulebook_path` parameter; reads file at runtime and includes in Claude prompt with prompt caching.
- **Sub-files**: May be inlined by a future `rulebook/build.sh` step; for now, sidecar treats rulebook.md as a single file.
- **Owned by**: Rulebook Executor (content), Sidecar Executor (loading + caching).
- **Status**: Sidecar stub mode uses hard-coded example rulebook; real integration happens when rulebook.md is finalized.

### Core ↔ DB
At startup the core calls `champions::load_data()` which reads `pokemon-champions-db/data/json/{pokemon,moves,items,natures,type_chart,learnsets}.json`. The path is configurable via `$POKEMON_CHAMPIONS_DB` (must point to the directory containing the JSON files); if unset, the loader searches upward from `cwd` for `pokemon-champions-db/data/json/`. Filtering rules: `champions_legal == true`; moves additionally require `category in {Physical, Special, Status}` and non-null `type_en`. ID normalization: display names are lowercased with spaces and hyphens replaced by underscores to form code IDs (e.g. `"Thunder Bolt"` → `"thunder_bolt"`); both `id` and `display_name` are stored on each palette entry. The DB project is read-only from the core's perspective — never modify JSON files from within `core/`.
- **Owned by**: DB Executor (JSON export schema + data), Core Executor (loading + in-memory palette).
- **Status**: Implemented in `core/src/champions_data.cpp`. Loads 258 species / 493 moves / 583 items / 21 natures at startup.

## Development Workflow

1. **Parallel builds**: Each executor commits to their directory. Root-level files (CMakeLists.txt, Makefile, README, .gitignore, .editorconfig) are shared; coordinate via this file.
2. **Cross-component testing**: After all three component executors finish, the Scaffold Executor (or a final test agent) runs `make build && make test` from root to verify integration.
3. **Schema disputes**: If IPC or DB schema conflicts arise, document as ADR entries below.

## Architecture Decision Records (ADRs)

*(None yet. Add here when cross-component decisions need documentation.)*
