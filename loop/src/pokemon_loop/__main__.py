"""Entry point: python -m pokemon_loop"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from .runner import probe_demo_flags
from .sidecar_proc import SidecarProcess
from .teams import TEAMS, dump_teams
from .tournament import print_leaderboard, run_tournament


def _resolve_paths(repo_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    demo_path = repo_root / "build" / "battle_demo"
    sidecar_dir = repo_root / "sidecar"
    rulebook = repo_root / "rulebook" / "rulebook.md"
    loop_dir = repo_root / "loop"
    teams_dir = loop_dir / "teams"
    return demo_path, sidecar_dir, rulebook, loop_dir, teams_dir


def _validate_paths(demo_path: Path, sidecar_dir: Path) -> int:
    if not demo_path.exists():
        print(
            f"ERROR: battle_demo not found at {demo_path}\n"
            "Run `make build` first.",
            file=sys.stderr,
        )
        return 1
    if not sidecar_dir.exists():
        print(f"ERROR: sidecar directory not found at {sidecar_dir}", file=sys.stderr)
        return 1
    return 0


def cmd_tournament(args: argparse.Namespace) -> int:
    repo_root = Path(os.environ.get("POKEMON_REPO", "/Users/song-wonjun/20261RCOSE32200"))
    demo_path, sidecar_dir, rulebook, loop_dir, teams_dir = _resolve_paths(repo_root)

    rc = _validate_paths(demo_path, sidecar_dir)
    if rc:
        return rc

    dump_teams(teams_dir)

    print("Probing battle_demo capabilities...", flush=True)
    supported_flags = probe_demo_flags(str(demo_path))
    print(f"  --sidecar : {'YES' if supported_flags['sidecar'] else 'NO (fallback mode)'}")
    print(f"  --seed    : {'YES' if supported_flags['seed'] else 'NO'}")
    print(f"  --team-a/b: {'YES' if supported_flags['team_ab'] else 'NO'}")
    print()

    run_id = f"run_{int(time.time())}"
    run_dir = loop_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    socket_path = f"/tmp/pokemon_sidecar_{run_id}.sock"
    print(f"Starting sidecar (stub mode)... socket={socket_path}", flush=True)

    ctx = SidecarProcess(sidecar_dir=str(sidecar_dir), socket_path=socket_path)

    try:
        socket = ctx.__enter__()
        print("Sidecar ready.\n", flush=True)
        print(f"Running {args.n_battles}-battle tournament (seed={args.seed})...\n", flush=True)

        lb = run_tournament(
            teams=TEAMS,
            demo_path=str(demo_path),
            socket=socket,
            rulebook=str(rulebook),
            supported_flags=supported_flags,
            run_dir=run_dir,
            n_battles=args.n_battles,
            seed=args.seed,
        )

        print_leaderboard(lb)
        print(f"\nBattle logs saved to: {run_dir}", flush=True)

    finally:
        if not getattr(args, "keep_sidecar", False):
            ctx.__exit__(None, None, None)

    return 0


def cmd_evolve(args: argparse.Namespace) -> int:
    import time as _time

    repo_root = Path(os.environ.get("POKEMON_REPO", "/Users/song-wonjun/20261RCOSE32200"))
    demo_path, sidecar_dir, rulebook, loop_dir, _ = _resolve_paths(repo_root)

    rc = _validate_paths(demo_path, sidecar_dir)
    if rc:
        return rc

    from .palette import load_palette
    from .evolution import Evolution

    print("Loading palette...", flush=True)
    # load_palette() reads the DB JSON directly — no demo_path needed
    palette = load_palette()
    print(f"  species={len(palette.species)}, moves={len(palette.moves)}, "
          f"items={len(palette.items)}, natures={len(palette.natures)}", flush=True)

    run_id = f"evo_{int(_time.time())}"

    evo = Evolution(
        palette=palette,
        repo_root=repo_root,
        run_id=run_id,
        seed=args.seed,
    )

    print(f"\nStarting evolution: {args.generations} generations, "
          f"pop={args.pop}, battles/gen={args.battles_per_gen}\n", flush=True)

    report = evo.run(
        n_generations=args.generations,
        pop_size=args.pop,
        battles_per_gen=args.battles_per_gen,
    )

    report.render()

    run_dir = loop_dir / "runs" / run_id
    print(f"\nArtifacts saved to: {run_dir}", flush=True)

    return 0


def main() -> int:
    # Top-level parser — supports both old no-subcommand style and new subcommands.
    parser = argparse.ArgumentParser(
        description="Pokemon Champions MVP — tournament orchestrator + GA evolution"
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- tournament subcommand ---
    t_parser = subparsers.add_parser("tournament", help="Run a single tournament")
    t_parser.add_argument("--n-battles", type=int, default=12)
    t_parser.add_argument("--seed", type=int, default=42)
    t_parser.add_argument("--keep-sidecar", action="store_true")

    # --- evolve subcommand ---
    e_parser = subparsers.add_parser("evolve", help="Run multi-generation GA evolution")
    e_parser.add_argument("--generations", type=int, default=5)
    e_parser.add_argument("--pop", type=int, default=8)
    e_parser.add_argument("--battles-per-gen", type=int, default=12)
    e_parser.add_argument("--seed", type=int, default=42)

    # Back-compat: add the old flags at the top level too so that
    # `python -m pokemon_loop --n-battles=12` still works.
    parser.add_argument("--n-battles", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--keep-sidecar", action="store_true")

    args = parser.parse_args()

    if args.command == "evolve":
        return cmd_evolve(args)
    else:
        # Default to tournament (back-compat for no-subcommand invocation)
        return cmd_tournament(args)


if __name__ == "__main__":
    sys.exit(main())
