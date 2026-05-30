import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

import anyio
from watchfiles import awatch

from .runs import list_run_battles, load_elo, load_hof

logger = logging.getLogger(__name__)


def _parse_run_id(run_dir: Path) -> str:
    return run_dir.name


def _gen_idx_from_path(path: Path, run_dir: Path) -> int | None:
    """Extract generation index from a path like run_dir/gen_N/..."""
    try:
        rel = path.relative_to(run_dir)
        parts = rel.parts
        if parts and parts[0].startswith("gen_"):
            return int(parts[0].split("_", 1)[1])
    except (ValueError, IndexError):
        pass
    return None


def _battle_id_from_path(path: Path) -> str | None:
    stem = path.stem  # battle_3
    if stem.startswith("battle_"):
        return stem.split("_", 1)[1]
    return None


async def watch_run(
    run_dir: Path,
    on_event: Callable[[dict], Awaitable[None]],
    stop_event: anyio.Event | None = None,
) -> None:
    """Watch run_dir and emit events to on_event.

    Accepts an optional stop_event; set it to request a clean shutdown.
    The caller may also cancel this coroutine — we catch CancelledError,
    set the stop_event to unblock watchfiles' internal thread, then re-raise.
    """
    run_id = _parse_run_id(run_dir)
    offsets: dict[Path, int] = {}

    # --- emit initial snapshot ---
    elo = load_elo(run_dir)
    hof = load_hof(run_dir)
    gens = (
        sum(1 for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("gen_"))
        if run_dir.exists()
        else 0
    )

    # Collect recent battle metadata for the snapshot so the frontend can populate
    # the battle picker immediately without a separate HTTP request.
    recent_battles: list[dict] = []
    most_recent_battle_path: Path | None = None
    if run_dir.exists():
        all_battle_logs = list(run_dir.rglob("battle_*.jsonl"))
        if all_battle_logs:
            # Find the single most-recently-modified battle log so we can seed its
            # offset to 0 (stream from the beginning).  All older logs stay at their
            # current file size so we don't flood the client with history on connect.
            most_recent_battle_path = max(
                all_battle_logs, key=lambda p: p.stat().st_mtime
            )

        # Build the recent_battles list from list_run_battles (already has metadata)
        all_meta = list_run_battles(run_dir)
        recent_battles = all_meta[-5:] if len(all_meta) > 5 else all_meta

    await on_event({
        "type": "snapshot",
        "run_id": run_id,
        "runs_state": {
            "generations": gens,
            "hof": hof,
            "elo": {str(k): v for k, v in elo.items()},
        },
        "recent_battles": recent_battles,
    })

    # Seed offsets so existing logs aren't replayed on startup — EXCEPT for the
    # most recent battle file.  Seeding it to 0 means its events stream out on
    # the very first awatch tick, letting a user who opens the dashboard after the
    # run finishes still see the last battle animate through the playback queue.
    if run_dir.exists():
        for jsonl in run_dir.rglob("battle_*.jsonl"):
            if jsonl == most_recent_battle_path:
                # Leave at 0 (default) so all events are replayed.
                offsets[jsonl] = 0
            else:
                try:
                    offsets[jsonl] = jsonl.stat().st_size
                except OSError:
                    offsets[jsonl] = 0

    if stop_event is None:
        stop_event = anyio.Event()

    async for changes in awatch(run_dir, stop_event=stop_event):
        for _change_type, path_str in changes:
            path = Path(path_str)

            if not path.exists():
                continue

            name = path.name

            if path.is_dir() and name.startswith("gen_"):
                try:
                    gen_n = int(name.split("_", 1)[1])
                    await on_event({"type": "gen_start", "run_id": run_id, "gen": gen_n})
                except (ValueError, IndexError):
                    pass
                continue

            if path.suffix == ".jsonl" and name.startswith("battle_"):
                gen = _gen_idx_from_path(path, run_dir)
                battle_id = _battle_id_from_path(path)
                await _emit_new_lines(path, offsets, on_event, run_id, gen, battle_id)

            elif name == "elo.json":
                gen = _gen_idx_from_path(path, run_dir)
                try:
                    ratings = json.loads(path.read_text(encoding="utf-8"))
                    await on_event({
                        "type": "elo_snapshot",
                        "run_id": run_id,
                        "gen": gen,
                        "ratings": ratings,
                    })
                except (OSError, json.JSONDecodeError) as e:
                    await on_event({"type": "error", "message": f"elo.json parse error: {e}"})

            elif name == "hof.json":
                try:
                    members = json.loads(path.read_text(encoding="utf-8"))
                    await on_event({"type": "hof_update", "run_id": run_id, "members": members})
                except (OSError, json.JSONDecodeError) as e:
                    await on_event({"type": "error", "message": f"hof.json parse error: {e}"})

            elif name == "champion.json":
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    await on_event({"type": "champion", "run_id": run_id, "payload": payload})
                except (OSError, json.JSONDecodeError) as e:
                    await on_event({"type": "error", "message": f"champion.json parse error: {e}"})


async def _emit_new_lines(
    path: Path,
    offsets: dict[Path, int],
    on_event: Callable[[dict], Awaitable[None]],
    run_id: str,
    gen: int | None,
    battle_id: str | None,
) -> None:
    current_offset = offsets.get(path, 0)
    try:
        size = path.stat().st_size
    except OSError:
        return

    if size <= current_offset:
        return

    try:
        with path.open("rb") as fh:
            fh.seek(current_offset)
            new_data = fh.read(size - current_offset)
    except OSError as e:
        logger.warning("Cannot read %s at offset %d: %s", path, current_offset, e)
        return

    offsets[path] = size

    for raw in new_data.decode("utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Malformed JSONL in %s: %r", path, raw[:120])
            continue
        await on_event({
            "type": "battle_event",
            "run_id": run_id,
            "gen": gen,
            "battle_id": battle_id,
            "payload": payload,
        })
