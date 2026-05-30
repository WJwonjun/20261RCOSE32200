import asyncio
import json
import os
from pathlib import Path

import anyio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .palette import clear_palette_cache, load_palette
from .runs import list_run_battles, list_runs, load_elo, load_hof, parse_battle_log
from .watcher import watch_run

_REPO_ROOT = Path(__file__).parent.parent.parent.parent  # dashboard/../.. = repo root
_DEFAULT_RUNS_ROOT = _REPO_ROOT / "loop" / "runs"
_STATIC_DIR = Path(__file__).parent.parent.parent / "static"

app = FastAPI(title="Pokemon Dashboard")

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


def _runs_root() -> Path:
    env = os.environ.get("POKEMON_RUNS_ROOT")
    return Path(env) if env else _DEFAULT_RUNS_ROOT


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    return FileResponse(str(_STATIC_DIR / "index.html"))


@app.get("/api/runs")
async def api_runs() -> list[dict]:
    runs = list_runs(_runs_root())
    return [
        {
            "run_id": r.run_id,
            "started_at": r.started_at.isoformat(),
            "generations": r.generations,
            "has_hof": r.has_hof,
            "has_champion": r.has_champion,
        }
        for r in runs
    ]


@app.get("/api/runs/{run_id}/summary")
async def api_run_summary(run_id: str) -> dict:
    run_dir = _runs_root() / run_id
    gens = sum(1 for d in run_dir.iterdir() if d.is_dir() and d.name.startswith("gen_")) if run_dir.exists() else 0
    total_battles = 0
    if run_dir.exists():
        total_battles = sum(1 for _ in run_dir.rglob("battle_*.jsonl"))
    hof = load_hof(run_dir)

    champion = None
    champ_file = run_dir / "champion.json"
    if champ_file.exists():
        try:
            champion = json.loads(champ_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "run_id": run_id,
        "generations": gens,
        "total_battles": total_battles,
        "hof": hof,
        "champion": champion,
    }


@app.get("/api/runs/{run_id}/battles")
async def api_run_battles(run_id: str) -> list[dict]:
    """Return all battles for a run as a sortable list."""
    run_dir = _runs_root() / run_id
    return list_run_battles(run_dir)


@app.get("/api/runs/{run_id}/battles/{gen}/{battle_id}")
async def api_run_battle_detail(run_id: str, gen: int, battle_id: int) -> dict:
    """Return the full ordered event list for one battle (for replay)."""
    run_dir = _runs_root() / run_id
    log_path = run_dir / f"gen_{gen}" / f"battle_{battle_id}.jsonl"
    events: list[dict] = []
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []
        for raw in lines:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    return {"events": events}


@app.get("/api/palette")
async def api_palette() -> JSONResponse:
    """Return normalized species palette loaded from pokemon-champions-db JSON.

    The result is cached in memory after the first request (load_palette() is
    idempotent and thread-safe for single-process async use).  Returns 503 if
    the source JSON file is missing so the caller can surface a clear error.
    """
    try:
        data = load_palette()
    except FileNotFoundError as exc:
        return JSONResponse(
            status_code=503,
            content={"error": str(exc)},
        )
    return JSONResponse(content=data)


@app.get("/api/runs/{run_id}/elo")
async def api_run_elo(run_id: str) -> dict:
    run_dir = _runs_root() / run_id
    elo = load_elo(run_dir)
    return {str(k): v for k, v in elo.items()}


@app.websocket("/ws/runs/{run_id}")
async def ws_run(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    run_dir = _runs_root() / run_id

    async def send_event(event: dict) -> None:
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            pass

    # Use a stop_event so we can ask the watcher to exit cleanly on disconnect,
    # avoiding the watchfiles UnboundLocalError that occurs on task cancellation.
    stop_event = anyio.Event()
    watcher_task = asyncio.get_event_loop().create_task(
        watch_run(run_dir, send_event, stop_event=stop_event)
    )

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        # Give the watcher up to 2s to exit via stop_event before cancelling.
        try:
            await asyncio.wait_for(asyncio.shield(watcher_task), timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            watcher_task.cancel()
            try:
                await watcher_task
            except (asyncio.CancelledError, Exception):
                pass
