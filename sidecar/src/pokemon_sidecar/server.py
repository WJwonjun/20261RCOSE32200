from __future__ import annotations

import asyncio
import json
import os
import signal
import uuid
from typing import Any

from .client import LLMClient
from .schemas import LLMCallResult, TurnState

SOCK_PATH = os.environ.get("POKEMON_SIDECAR_SOCK", "/tmp/pokemon_sidecar.sock")
# Limit concurrent LLM inflight requests: MVP optimizes for latency over throughput.
_SEMAPHORE_LIMIT = 3

_client = LLMClient()
_semaphore: asyncio.Semaphore | None = None


async def _handle_request(data: dict[str, Any]) -> dict[str, Any]:
    turn_state = TurnState(**{k: v for k, v in data.items() if k in TurnState.model_fields})
    rulebook_path: str = data.get("rulebook_path", "/dev/null")
    team_spec: str = data.get("team_spec", "")
    idempotency_key: str = data.get("idempotency_key", str(uuid.uuid4()))

    result: LLMCallResult = await _client.choose_action(
        turn_state=turn_state,
        rulebook_path=rulebook_path,
        team_spec=team_spec,
        idempotency_key=idempotency_key,
    )
    return result.model_dump()


async def _handle_connection(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    sem: asyncio.Semaphore,
) -> None:
    try:
        async for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                response = {"error": f"json_decode: {exc}"}
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
                continue

            async with sem:
                result = await _handle_request(data)

            writer.write((json.dumps(result) + "\n").encode())
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def run_server() -> None:
    global _semaphore
    sem = asyncio.Semaphore(_SEMAPHORE_LIMIT)

    sock_path = os.environ.get("POKEMON_SIDECAR_SOCK", SOCK_PATH)

    import pathlib
    pathlib.Path(sock_path).unlink(missing_ok=True)

    server = await asyncio.start_unix_server(
        lambda r, w: _handle_connection(r, w, sem),
        path=sock_path,
    )

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown() -> None:
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _shutdown)
    loop.add_signal_handler(signal.SIGINT, _shutdown)

    async with server:
        await stop_event.wait()

    pathlib.Path(sock_path).unlink(missing_ok=True)
