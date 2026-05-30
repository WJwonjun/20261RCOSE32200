# Pokemon Champions — LLM Sidecar

Minimal asyncio Unix-domain-socket sidecar that receives turn state from the C++ Battle Core and returns an LLM-chosen action via Anthropic Claude (Haiku 4.5).

## Install

```bash
cd sidecar
uv sync --extra dev
```

## Run the server

```bash
# Stub mode (no API key needed)
POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar

# Real mode
ANTHROPIC_API_KEY=sk-ant-... uv run python -m pokemon_sidecar
```

## Run tests

```bash
cd sidecar
POKEMON_SIDECAR_STUB=1 uv run pytest
```

## Manual smoke test

With the server already running in a separate terminal:

```bash
cd sidecar
uv run python scripts/mock_client.py
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | When unset, stub mode activates automatically |
| `POKEMON_SIDECAR_STUB` | unset | Set to `1` to force stub mode even if API key is present |
| `POKEMON_SIDECAR_SOCK` | `/tmp/pokemon_sidecar.sock` | Unix domain socket path |

## Protocol

JSONL over Unix domain socket. One request line in, one response line out.

**Request** = `TurnState` fields + `rulebook_path` + `team_spec` + `idempotency_key`.

**Response** = `LLMCallResult` JSON (see `schemas.py`).

## Architecture notes

- Semaphore of 3 concurrent LLM calls (MVP: latency over throughput).
- Two system prompt blocks with `cache_control: ephemeral`: rulebook + team spec. These are stable per battle session; opponent state and turn number change every turn so they stay uncached.
- Stub returns the first legal action with `reason: "stub"` — safe fallback for CI and offline dev.
