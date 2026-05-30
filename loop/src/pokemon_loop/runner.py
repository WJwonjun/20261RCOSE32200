"""Run a single battle via the C++ battle_demo binary."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BattleResult:
    winner: str          # "A", "B", or "draw_or_timeout"
    turns: int
    fallback_mode: bool  # True if running without --sidecar / --seed flags
    stdout_path: str     # path to saved JSONL log


def _probe_flag(demo_path: str, flag: str) -> bool:
    """
    Return True if the demo binary accepts the given flag without complaining.

    Strategy: launch the binary with the flag, give it 0.5 s, then kill it.
    If stderr contains 'unknown' or 'unrecognized' the flag is not supported.
    If the binary ran happily (or is blocking waiting for a socket) the flag
    is supported.
    """
    proc = subprocess.Popen(
        [demo_path, flag],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _, stderr_bytes = proc.communicate(timeout=0.5)
        stderr_lower = stderr_bytes.decode(errors="replace").lower()
        return "unknown" not in stderr_lower and "unrecognized" not in stderr_lower
    except subprocess.TimeoutExpired:
        # Binary is happily running (blocking on socket / battle loop) — flag accepted
        proc.kill()
        proc.wait()
        return True


def probe_demo_flags(demo_path: str) -> dict[str, bool]:
    """Check which optional flags the demo binary supports."""
    return {
        "sidecar": _probe_flag(demo_path, "--sidecar"),
        "seed":    _probe_flag(demo_path, "--seed=0"),
        "team_ab": _probe_flag(demo_path, "--team-a=nonexistent.json"),
    }


def run_battle(
    demo_path: str,
    socket: str,
    rulebook: str,
    seed: int,
    team_a: str | None,
    team_b: str | None,
    supported_flags: dict[str, bool],
    run_dir: Path,
    battle_idx: int,
) -> BattleResult:
    """
    Run one battle and return a BattleResult.

    Falls back gracefully when --sidecar / --seed / --team-a are not yet
    supported by the compiled binary (the C++ executor adds these flags
    concurrently; this orchestrator runs with whatever is present).
    """
    cmd = [demo_path]

    if supported_flags.get("sidecar"):
        cmd += [f"--socket={socket}", "--sidecar"]

    if supported_flags.get("seed"):
        cmd.append(f"--seed={seed}")

    if supported_flags.get("team_ab") and team_a and team_b:
        cmd += [f"--team-a={team_a}", f"--team-b={team_b}"]

    fallback_mode = not supported_flags.get("sidecar", False)

    result = subprocess.run(
        cmd,
        capture_output=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
    )

    stdout_text = result.stdout

    # Save log
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"battle_{battle_idx}.jsonl"
    log_path.write_text(stdout_text)

    # Parse output: find last line with event=battle_end
    winner = "draw_or_timeout"
    turns = 0

    for line in stdout_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("event") == "turn_end":
            turns = obj.get("turn", turns)
        elif obj.get("event") == "battle_end":
            winner = obj.get("winner", "draw_or_timeout")
            turns = obj.get("turns", turns)  # draw case uses turns field

    return BattleResult(
        winner=winner,
        turns=turns,
        fallback_mode=fallback_mode,
        stdout_path=str(log_path),
    )
