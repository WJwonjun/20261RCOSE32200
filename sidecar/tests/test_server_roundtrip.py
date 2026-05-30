from __future__ import annotations

import asyncio
import json
import os
import pathlib

import pytest

from pokemon_sidecar.schemas import LLMCallResult

TEST_SOCK = "/tmp/pokemon_sidecar_test.sock"

TURN_STATE_MSG = {
    "rulebook_hash": "deadbeef",
    "acting_team": {"pokemon": [{"name": "Bulbasaur", "hp": 120}]},
    "opponent_visible": {"pokemon": [{"name": "Squirtle", "hp": 90}]},
    "turn_no": 3,
    "side": "player2",
    "legal_actions": [{"action": "move", "target": 2}],
    "rulebook_path": "/dev/null",
    "team_spec": "Bulbasaur @ Leftovers",
    "idempotency_key": "roundtrip-001",
}


@pytest.fixture(autouse=True)
def force_stub_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEMON_SIDECAR_STUB", "1")
    monkeypatch.setenv("POKEMON_SIDECAR_SOCK", TEST_SOCK)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def cleanup_sock() -> None:
    pathlib.Path(TEST_SOCK).unlink(missing_ok=True)
    yield
    pathlib.Path(TEST_SOCK).unlink(missing_ok=True)


async def test_server_roundtrip() -> None:
    from pokemon_sidecar.server import run_server

    # Run server as a background task; cancel when done.
    server_task = asyncio.create_task(run_server())
    # Give server time to bind
    await asyncio.sleep(0.1)

    try:
        reader, writer = await asyncio.open_unix_connection(TEST_SOCK)
        writer.write((json.dumps(TURN_STATE_MSG) + "\n").encode())
        await writer.drain()

        line = await asyncio.wait_for(reader.readline(), timeout=5.0)
        data = json.loads(line.decode())

        # Validate against schema
        result = LLMCallResult(**data)
        assert result.action is not None
        assert result.action.action in ("move", "switch")
        assert isinstance(result.action.target, int)
        assert result.idempotency_key == "roundtrip-001"
        assert result.failure_reason is None

        writer.close()
        await writer.wait_closed()
    finally:
        server_task.cancel()
        try:
            await server_task
        except (asyncio.CancelledError, Exception):
            pass
