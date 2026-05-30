#!/usr/bin/env python3
"""
Standalone smoke-test client.

Usage:
    POKEMON_SIDECAR_STUB=1 uv run python -m pokemon_sidecar &
    uv run python scripts/mock_client.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

SOCK_PATH = os.environ.get("POKEMON_SIDECAR_SOCK", "/tmp/pokemon_sidecar.sock")

SAMPLE_REQUEST = {
    "rulebook_hash": "cafebabe",
    "acting_team": {
        "pokemon": [
            {"name": "Gengar", "hp": 95, "moves": ["Shadow Ball", "Sludge Bomb", "Focus Blast", "Dazzling Gleam"]},
        ]
    },
    "opponent_visible": {
        "pokemon": [{"name": "Alakazam", "hp": 65}]
    },
    "turn_no": 7,
    "side": "player1",
    "legal_actions": [
        {"action": "move", "target": 0},
        {"action": "move", "target": 1},
        {"action": "move", "target": 2},
        {"action": "switch", "target": 0},
    ],
    "rulebook_path": "/dev/null",
    "team_spec": "Gengar @ Choice Specs",
    "idempotency_key": "mock-client-smoke-01",
}


async def main() -> None:
    try:
        reader, writer = await asyncio.open_unix_connection(SOCK_PATH)
    except FileNotFoundError:
        print(f"ERROR: Socket not found at {SOCK_PATH}. Is the sidecar running?", file=sys.stderr)
        sys.exit(1)

    writer.write((json.dumps(SAMPLE_REQUEST) + "\n").encode())
    await writer.drain()

    line = await asyncio.wait_for(reader.readline(), timeout=15.0)
    response = json.loads(line.decode())

    print("Response from sidecar:")
    print(json.dumps(response, indent=2))

    writer.close()
    await writer.wait_closed()

    action = response.get("action")
    if action is None:
        print(f"\nWARN: No action returned. failure_reason={response.get('failure_reason')}", file=sys.stderr)
        sys.exit(1)
    print(f"\nOK: action={action['action']} target={action['target']} reason={action.get('reason')}")


if __name__ == "__main__":
    asyncio.run(main())
