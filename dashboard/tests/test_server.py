import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def runs_root(tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    return root


@pytest.fixture()
def client(runs_root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("POKEMON_RUNS_ROOT", str(runs_root))
    # Import after env is set so _runs_root() picks it up at call time (it reads env on each call)
    from pokemon_dashboard.server import app
    return TestClient(app)


def test_index_returns_html(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Pokemon" in r.text


def test_api_runs_empty(client: TestClient) -> None:
    r = client.get("/api/runs")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_runs_with_fake_run(client: TestClient, runs_root: Path) -> None:
    run_dir = runs_root / "evo_test_123"
    run_dir.mkdir()
    (run_dir / "gen_0").mkdir()

    r = client.get("/api/runs")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["run_id"] == "evo_test_123"
    assert data[0]["generations"] == 1


def test_api_run_summary(client: TestClient, runs_root: Path) -> None:
    run_dir = runs_root / "evo_summary"
    run_dir.mkdir()
    gen_dir = run_dir / "gen_0"
    gen_dir.mkdir()
    (gen_dir / "battle_0.jsonl").write_text(
        '{"event":"battle_start","team_a":"A","team_b":"B"}\n'
        '{"event":"battle_end","winner":"A"}\n',
        encoding="utf-8",
    )
    hof = [{"rating": 1050.0, "gen_added": 0, "genome": {"name": "team_0", "members": []}}]
    (run_dir / "hof.json").write_text(json.dumps(hof), encoding="utf-8")

    r = client.get("/api/runs/evo_summary/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["run_id"] == "evo_summary"
    assert data["total_battles"] == 1
    assert len(data["hof"]) == 1


def test_api_elo(client: TestClient, runs_root: Path) -> None:
    run_dir = runs_root / "evo_elo"
    run_dir.mkdir()
    gen_dir = run_dir / "gen_0"
    gen_dir.mkdir()
    (gen_dir / "elo.json").write_text('{"team_a": 1020.0, "team_b": 980.0}', encoding="utf-8")

    r = client.get("/api/runs/evo_elo/elo")
    assert r.status_code == 200
    data = r.json()
    assert "0" in data
    assert data["0"]["team_a"] == pytest.approx(1020.0)


def _write_battle(path: Path, events: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_api_run_battles_shape(client: TestClient, runs_root: Path) -> None:
    """GET /api/runs/{id}/battles returns a list with the right shape and ordering."""
    run_dir = runs_root / "evo_battles"
    run_dir.mkdir()

    gen0 = run_dir / "gen_0"
    gen0.mkdir()
    _write_battle(gen0 / "battle_0.jsonl", [
        {"event": "battle_start", "team_a": "Charizard lead", "team_b": "Blastoise lead"},
        {"event": "turn_end", "turn": 1, "hp_a": 200, "hp_b": 150, "action_source_a": "sidecar", "action_source_b": "sidecar"},
        {"event": "battle_end", "winner": "A"},
    ])
    _write_battle(gen0 / "battle_1.jsonl", [
        {"event": "battle_start", "team_a": "Pikachu lead", "team_b": "Snorlax lead"},
        {"event": "battle_end", "winner": "B"},
    ])

    gen1 = run_dir / "gen_1"
    gen1.mkdir()
    _write_battle(gen1 / "battle_0.jsonl", [
        {"event": "battle_start", "team_a": "Gengar lead", "team_b": "Machamp lead"},
        {"event": "battle_end", "winner": "A"},
    ])

    r = client.get("/api/runs/evo_battles/battles")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 3

    # Should be sorted: gen 0 battle 0, gen 0 battle 1, gen 1 battle 0
    assert data[0]["gen"] == 0 and data[0]["battle_id"] == 0
    assert data[1]["gen"] == 0 and data[1]["battle_id"] == 1
    assert data[2]["gen"] == 1 and data[2]["battle_id"] == 0

    # Check shape of one entry
    entry = data[0]
    assert entry["winner"] == "A"
    assert entry["turns"] == 1
    assert entry["team_a_name"] == "Charizard lead"
    assert entry["team_b_name"] == "Blastoise lead"
    assert "started_at" in entry


def test_api_run_battle_detail_events(client: TestClient, runs_root: Path) -> None:
    """GET /api/runs/{id}/battles/{gen}/{bid} returns full event list."""
    run_dir = runs_root / "evo_detail"
    run_dir.mkdir()
    gen0 = run_dir / "gen_0"
    gen0.mkdir()
    events = [
        {"event": "battle_start", "team_a": "Gyarados lead", "team_b": "Blastoise lead"},
        {"event": "turn_start", "turn": 1},
        {"event": "move", "pokemon": "Blastoise", "move": "Thunderbolt"},
        {"event": "damage", "target": "Gyarados", "damage": 121, "hp_remaining": 74},
        {"event": "turn_end", "turn": 1, "hp_a": 74, "hp_b": 154, "action_source_a": "sidecar", "action_source_b": "sidecar"},
        {"event": "battle_end", "winner": "A", "turns": 1},
    ]
    _write_battle(gen0 / "battle_0.jsonl", events)

    r = client.get("/api/runs/evo_detail/battles/0/0")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    result_events = data["events"]
    assert len(result_events) == len(events)
    assert result_events[0]["event"] == "battle_start"
    assert result_events[2]["event"] == "move"
    assert result_events[2]["move"] == "Thunderbolt"
    assert result_events[3]["event"] == "damage"
    assert result_events[3]["damage"] == 121
    assert result_events[4]["event"] == "turn_end"
    assert result_events[4]["hp_a"] == 74
    assert result_events[5]["event"] == "battle_end"


def test_api_run_battle_detail_missing(client: TestClient, runs_root: Path) -> None:
    """Non-existent battle returns empty event list, not 500."""
    run_dir = runs_root / "evo_missing"
    run_dir.mkdir()
    r = client.get("/api/runs/evo_missing/battles/0/99")
    assert r.status_code == 200
    assert r.json() == {"events": []}


def test_ws_snapshot_on_connect(runs_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POKEMON_RUNS_ROOT", str(runs_root))
    run_dir = runs_root / "evo_ws"
    run_dir.mkdir()
    gen_dir = run_dir / "gen_0"
    gen_dir.mkdir()
    hof = [{"rating": 1000.0, "gen_added": 0, "genome": {"name": "t0", "members": []}}]
    (run_dir / "hof.json").write_text(json.dumps(hof), encoding="utf-8")

    from pokemon_dashboard.server import app
    # Use raise_server_exceptions=False so the watchfiles stop_event teardown
    # (which may still be racing) does not propagate into the test assertion.
    with TestClient(app, raise_server_exceptions=False) as client:
        with client.websocket_connect("/ws/runs/evo_ws") as ws:
            raw = ws.receive_text()
            msg = json.loads(raw)
            assert msg["type"] == "snapshot"
            assert "runs_state" in msg
            assert msg["run_id"] == "evo_ws"
            # Close explicitly before context exit to let stop_event propagate cleanly.
