import json
import logging
import os
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RunInfo(BaseModel):
    run_id: str
    path: Path
    started_at: datetime
    generations: int
    has_hof: bool
    has_champion: bool

    model_config = {"arbitrary_types_allowed": True}


def list_runs(runs_root: Path) -> list[RunInfo]:
    if not runs_root.exists():
        return []

    runs = []
    for entry in runs_root.iterdir():
        if not entry.is_dir():
            continue
        try:
            mtime = entry.stat().st_mtime
            gens = sum(1 for d in entry.iterdir() if d.is_dir() and d.name.startswith("gen_"))
            runs.append(
                RunInfo(
                    run_id=entry.name,
                    path=entry,
                    started_at=datetime.fromtimestamp(mtime),
                    generations=gens,
                    has_hof=(entry / "hof.json").exists(),
                    has_champion=(entry / "champion.json").exists(),
                )
            )
        except OSError:
            continue

    runs.sort(key=lambda r: r.started_at, reverse=True)
    return runs[:50]


def parse_battle_log(path: Path) -> dict:
    turns = 0
    winner = None
    team_a_name = None
    team_b_name = None
    fallback_count = 0
    action_sources: dict[str, int] = {}

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        logger.warning("Cannot read %s: %s", path, e)
        return {
            "turns": 0,
            "winner": None,
            "team_a_name": None,
            "team_b_name": None,
            "fallback_count": 0,
            "action_sources": {},
        }

    for raw in lines:
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed line in %s: %r", path, raw[:120])
            continue

        event = obj.get("event")
        if event == "battle_start":
            team_a_name = obj.get("team_a")
            team_b_name = obj.get("team_b")
        elif event == "turn_end":
            turns = max(turns, obj.get("turn", 0))
            for key in ("action_source_a", "action_source_b"):
                src = obj.get(key)
                if src:
                    action_sources[src] = action_sources.get(src, 0) + 1
                    if src == "heuristic":
                        fallback_count += 1
        elif event == "battle_end":
            winner = obj.get("winner")

    return {
        "turns": turns,
        "winner": winner,
        "team_a_name": team_a_name,
        "team_b_name": team_b_name,
        "fallback_count": fallback_count,
        "action_sources": action_sources,
    }


def list_run_battles(run_dir: Path) -> list[dict]:
    """Return metadata for every battle log in run_dir, sorted by gen then battle_id."""
    battles = []
    if not run_dir.exists():
        return battles

    for gen_dir in run_dir.iterdir():
        if not gen_dir.is_dir() or not gen_dir.name.startswith("gen_"):
            continue
        try:
            gen_idx = int(gen_dir.name.split("_", 1)[1])
        except (ValueError, IndexError):
            continue

        for log_path in gen_dir.glob("battle_*.jsonl"):
            stem = log_path.stem  # battle_3
            try:
                battle_id = int(stem.split("_", 1)[1])
            except (ValueError, IndexError):
                continue

            try:
                mtime = log_path.stat().st_mtime
                started_at = datetime.fromtimestamp(mtime).isoformat()
            except OSError:
                started_at = None

            meta = parse_battle_log(log_path)
            battles.append({
                "gen": gen_idx,
                "battle_id": battle_id,
                "started_at": started_at,
                "turns": meta["turns"],
                "winner": meta["winner"],
                "team_a_name": meta["team_a_name"],
                "team_b_name": meta["team_b_name"],
            })

    battles.sort(key=lambda b: (b["gen"], b["battle_id"]))
    return battles


def load_elo(run_dir: Path) -> dict[int, dict[str, float]]:
    result: dict[int, dict[str, float]] = {}
    if not run_dir.exists():
        return result

    for gen_dir in sorted(run_dir.iterdir()):
        if not gen_dir.is_dir() or not gen_dir.name.startswith("gen_"):
            continue
        try:
            gen_idx = int(gen_dir.name.split("_", 1)[1])
        except (ValueError, IndexError):
            continue
        elo_file = gen_dir / "elo.json"
        if not elo_file.exists():
            continue
        try:
            data = json.loads(elo_file.read_text(encoding="utf-8"))
            result[gen_idx] = {str(k): float(v) for k, v in data.items()}
        except (OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("Cannot load %s: %s", elo_file, e)

    return result


def load_hof(run_dir: Path) -> list[dict]:
    hof_file = run_dir / "hof.json"
    if not hof_file.exists():
        return []
    try:
        data = json.loads(hof_file.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Cannot load hof.json in %s: %s", run_dir, e)
        return []
