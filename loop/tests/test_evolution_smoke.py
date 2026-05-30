"""Smoke test for Evolution.run() — skips if battle_demo is missing."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(os.environ.get("POKEMON_REPO", "/Users/song-wonjun/20261RCOSE32200"))
DEMO_PATH = REPO_ROOT / "build" / "battle_demo"


@pytest.fixture(scope="module", autouse=False)
def require_demo():
    if not DEMO_PATH.exists():
        pytest.skip(f"battle_demo not found at {DEMO_PATH} — run `make build` first")


def test_evolution_smoke(require_demo, tmp_path):
    """Run 2 generations with pop=4, 4 battles/gen — fast enough for CI."""
    from pokemon_loop.palette import load_palette
    from pokemon_loop.evolution import Evolution

    palette = load_palette()  # reads DB JSON directly, no demo_path needed

    run_id = f"smoke_{int(time.time())}"
    # Override loop_dir to use tmp_path so we don't litter the repo
    evo = Evolution(
        palette=palette,
        repo_root=REPO_ROOT,
        run_id=run_id,
        seed=7,
    )
    # Patch loop_dir and run_dir to use tmp_path
    loop_dir = tmp_path / "loop"
    evo.loop_dir = loop_dir
    evo.run_dir = loop_dir / "runs" / run_id

    report = evo.run(
        n_generations=2,
        pop_size=4,
        battles_per_gen=4,
    )

    # --- Assertions ---
    assert len(report.generations) == 2, "Expected 2 generations of stats"

    # HoF has at most 2 members
    assert len(report.hof_entries) <= 2

    # Champion genome JSON exists on disk
    champion_path = evo.run_dir / "champion.json"
    assert champion_path.exists(), f"champion.json not found at {champion_path}"

    # Per-generation elo.json files exist
    for gen in range(2):
        elo_path = evo.run_dir / f"gen_{gen}" / "elo.json"
        assert elo_path.exists(), f"elo.json missing for gen {gen}: {elo_path}"

    # HoF persisted
    hof_path = evo.run_dir / "hof.json"
    assert hof_path.exists(), f"hof.json missing at {hof_path}"

    # All battle log files exist (at least 1 per gen)
    for gen in range(2):
        gen_dir = evo.run_dir / f"gen_{gen}"
        logs = list(gen_dir.glob("battle_*.jsonl"))
        assert len(logs) >= 1, f"No battle logs found in gen_{gen}"

    # Stats sanity
    for gs in report.generations:
        assert gs.avg_elo > 0
        assert gs.max_elo >= gs.avg_elo
