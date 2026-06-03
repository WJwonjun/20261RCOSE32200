# Pokemon Champions — LLM Sidecar

Minimal asyncio Unix-domain-socket sidecar that receives turn state from the C++ Battle Core and returns an LLM-chosen action. Works with Anthropic Claude or any OpenAI-compatible provider (Gemini / Groq / OpenAI / local Ollama), and falls back to a free offline heuristic stub when no key is set.

## Install

```bash
cd sidecar
uv sync --extra dev
```

## Run the server

```bash
# Stub mode — free, no API key (offline heuristic)
POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-... uv run python -m pokemon_sidecar

# Google Gemini (free tier key from aistudio.google.com)
GEMINI_API_KEY=... uv run python -m pokemon_sidecar

# Groq (free tier key from console.groq.com)
GROQ_API_KEY=... uv run python -m pokemon_sidecar

# Local Ollama (no key, fully offline real LLM)
OPENAI_API_KEY=ollama OPENAI_BASE_URL=http://localhost:11434/v1 \
  POKEMON_SIDECAR_MODEL=llama3.1 uv run python -m pokemon_sidecar
```

Provider precedence: `POKEMON_SIDECAR_STUB=1` (stub) > any OpenAI-compatible key
(`GEMINI_API_KEY` / `GROQ_API_KEY` / `OPENAI_API_KEY`) > `ANTHROPIC_API_KEY` >
stub. Override the model with `POKEMON_SIDECAR_MODEL` (default per provider) and
the endpoint with `OPENAI_BASE_URL`.

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
