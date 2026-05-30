import json
import time
from pathlib import Path

import pytest

from pokemon_dashboard.runs import list_runs, load_elo, parse_battle_log


def write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")


SAMPLE_BATTLE = [
    {"event": "battle_start", "team_a": "Jolteon lead", "team_b": "Snorlax lead"},
    {"event": "turn_start", "turn": 1},
    {"event": "move", "pokemon": "Jolteon", "move": "Thunderbolt"},
    {"event": "damage", "target": "Snorlax", "damage": 30, "hp_remaining": 231},
    {"action_source_a": "sidecar", "action_source_b": "heuristic", "event": "turn_end", "hp_a": 159, "hp_b": 231, "turn": 1},
    {"event": "turn_start", "turn": 2},
    {"event": "move", "pokemon": "Snorlax", "move": "Body Slam"},
    {"event": "damage", "target": "Jolteon", "damage": 55, "hp_remaining": 104},
    {"action_source_a": "sidecar", "action_source_b": "sidecar", "event": "turn_end", "hp_a": 104, "hp_b": 231, "turn": 2},
    {"event": "turn_start", "turn": 3},
    {"event": "move", "pokemon": "Jolteon", "move": "Thunderbolt"},
    {"event": "damage", "target": "Snorlax", "damage": 35, "hp_remaining": 196},
    {"action_source_a": "sidecar", "action_source_b": "sidecar", "event": "turn_end", "hp_a": 104, "hp_b": 196, "turn": 3},
    {"event": "battle_end", "winner": "A", "team": "Jolteon side"},
]


def test_parse_battle_log_basic(tmp_path: Path) -> None:
    log = tmp_path / "battle_0.jsonl"
    write_jsonl(log, SAMPLE_BATTLE)

    result = parse_battle_log(log)

    assert result["turns"] == 3
    assert result["winner"] == "A"
    assert result["team_a_name"] == "Jolteon lead"
    assert result["team_b_name"] == "Snorlax lead"
    # one heuristic action (turn 1 side B)
    assert result["fallback_count"] == 1
    assert result["action_sources"]["sidecar"] == 5  # 5 sidecar actions across 3 turns (2+2+1? let's count)
    assert result["action_sources"]["heuristic"] == 1


def test_parse_battle_log_skips_malformed(tmp_path: Path) -> None:
    log = tmp_path / "battle_bad.jsonl"
    lines = [
        '{"event":"battle_start","team_a":"A","team_b":"B"}',
        "NOT_JSON {{{{",
        '# a comment line',
        '{"action_source_a":"sidecar","action_source_b":"sidecar","event":"turn_end","turn":1}',
        '{"event":"battle_end","winner":"B"}',
    ]
    log.write_text("\n".join(lines), encoding="utf-8")
    result = parse_battle_log(log)
    assert result["winner"] == "B"
    assert result["turns"] == 1  # malformed line skipped


def test_list_runs_sorted_by_mtime(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()

    older = runs_root / "run_old"
    newer = runs_root / "run_new"
    older.mkdir()
    time.sleep(0.02)  # ensure different mtime
    newer.mkdir()

    result = list_runs(runs_root)
    assert len(result) == 2
    assert result[0].run_id == "run_new"
    assert result[1].run_id == "run_old"


def test_list_runs_empty(tmp_path: Path) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    assert list_runs(runs_root) == []


def test_list_runs_nonexistent(tmp_path: Path) -> None:
    assert list_runs(tmp_path / "no_such_dir") == []


def test_load_elo_multi_gen(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_x"
    run_dir.mkdir()

    for i in range(3):
        gen_dir = run_dir / f"gen_{i}"
        gen_dir.mkdir()
        elo = {f"team_{j}": 1000.0 + i * 10 + j for j in range(4)}
        (gen_dir / "elo.json").write_text(json.dumps(elo), encoding="utf-8")

    result = load_elo(run_dir)
    assert set(result.keys()) == {0, 1, 2}
    assert result[0]["team_0"] == pytest.approx(1000.0)
    assert result[2]["team_3"] == pytest.approx(1023.0)


def test_load_elo_missing_gens(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_y"
    run_dir.mkdir()
    gen_dir = run_dir / "gen_5"
    gen_dir.mkdir()
    (gen_dir / "elo.json").write_text('{"team_a": 1100.0}', encoding="utf-8")
    result = load_elo(run_dir)
    assert 5 in result
    assert result[5]["team_a"] == pytest.approx(1100.0)
