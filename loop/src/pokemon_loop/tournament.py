"""Tournament bracket logic and leaderboard display."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from .runner import BattleResult, run_battle
from .teams import Team

if TYPE_CHECKING:
    from .elo import EloBoard
    from .genome import Genome


@dataclass
class TeamRecord:
    name: str
    wins: int = 0
    losses: int = 0
    battles: int = 0
    total_turns: int = 0

    def record(self, won: bool, turns: int) -> None:
        self.battles += 1
        self.total_turns += turns
        if won:
            self.wins += 1
        else:
            self.losses += 1


@dataclass
class Leaderboard:
    records: list[TeamRecord]
    fallback_mode: bool
    run_id: str


def run_tournament(
    teams: list[Team],
    demo_path: str,
    socket: str,
    rulebook: str,
    supported_flags: dict[str, bool],
    run_dir: Path,
    n_battles: int = 12,
    seed: int = 42,
) -> Leaderboard:
    """
    Run a 12-battle tournament.

    Bracket (7 elimination + 5 loser round-robin = 12):
      QF1: team[0] vs team[1]
      QF2: team[2] vs team[3]
      QF3: team[4] vs team[5]
      QF4: team[6] vs team[7]
      SF1: QF1-winner vs QF2-winner
      SF2: QF3-winner vs QF4-winner
      Final: SF1-winner vs SF2-winner
      Extra 5 battles among the 4 QF losers (round-robin subset).

    In fallback mode the binary ignores team paths so every battle uses
    the binary's hard-coded teams A and B; results are still tracked per
    logical team slot to show the loop running.
    """
    assert len(teams) == 8, "Tournament requires exactly 8 teams"

    records: dict[str, TeamRecord] = {t["name"]: TeamRecord(name=t["name"]) for t in teams}
    fallback_mode = not supported_flags.get("sidecar", False)

    team_json_dir = run_dir.parent / "teams"

    def _team_path(team: Team) -> str | None:
        if not supported_flags.get("team_ab"):
            return None
        p = team_json_dir / f"{team['name']}.json"
        return str(p) if p.exists() else None

    def _battle(
        idx: int,
        team_a_obj: Team,
        team_b_obj: Team,
        battle_seed: int,
    ) -> str:
        """Run one battle, update records, return winner team name."""
        result = run_battle(
            demo_path=demo_path,
            socket=socket,
            rulebook=rulebook,
            seed=battle_seed,
            team_a=_team_path(team_a_obj),
            team_b=_team_path(team_b_obj),
            supported_flags=supported_flags,
            run_dir=run_dir,
            battle_idx=idx,
        )

        name_a, name_b = team_a_obj["name"], team_b_obj["name"]

        # Map binary winner ("A" / "B") to team name. On a draw / timeout
        # neither team won — credit both with a loss to keep totals honest,
        # and advance team A arbitrarily so the bracket can proceed.
        if result.winner == "A":
            records[name_a].record(won=True, turns=result.turns)
            records[name_b].record(won=False, turns=result.turns)
            return name_a
        elif result.winner == "B":
            records[name_b].record(won=True, turns=result.turns)
            records[name_a].record(won=False, turns=result.turns)
            return name_b
        else:
            records[name_a].record(won=False, turns=result.turns)
            records[name_b].record(won=False, turns=result.turns)
            return name_a

    battle_idx = 0

    # QF round
    qf_winners: list[str] = []
    qf_losers: list[str] = []
    qf_pairs = [(0, 1), (2, 3), (4, 5), (6, 7)]
    for a_idx, b_idx in qf_pairs:
        winner = _battle(battle_idx, teams[a_idx], teams[b_idx], seed + battle_idx)
        loser = teams[b_idx]["name"] if winner == teams[a_idx]["name"] else teams[a_idx]["name"]
        qf_winners.append(winner)
        qf_losers.append(loser)
        battle_idx += 1

    # SF round
    sf_winner_teams = [next(t for t in teams if t["name"] == name) for name in qf_winners]
    sf_winners: list[str] = []
    sf_losers: list[str] = []
    sf_pairs = [(0, 1), (2, 3)]
    for a_idx, b_idx in sf_pairs:
        winner = _battle(battle_idx, sf_winner_teams[a_idx], sf_winner_teams[b_idx], seed + battle_idx)
        loser = sf_winner_teams[b_idx]["name"] if winner == sf_winner_teams[a_idx]["name"] else sf_winner_teams[a_idx]["name"]
        sf_winners.append(winner)
        sf_losers.append(loser)
        battle_idx += 1

    # Final
    final_teams = [next(t for t in teams if t["name"] == name) for name in sf_winners]
    _battle(battle_idx, final_teams[0], final_teams[1], seed + battle_idx)
    battle_idx += 1

    # Extra round-robin among QF losers (5 battles from a 4-team round-robin = 6 pairs, take first 5)
    loser_team_objs = [next(t for t in teams if t["name"] == name) for name in qf_losers]
    extra_pairs = [
        (0, 1), (0, 2), (0, 3), (1, 2), (1, 3),  # 5 of 6 possible pairs
    ]
    for a_idx, b_idx in extra_pairs:
        if battle_idx >= n_battles:
            break
        _battle(battle_idx, loser_team_objs[a_idx], loser_team_objs[b_idx], seed + battle_idx)
        battle_idx += 1

    return Leaderboard(
        records=sorted(records.values(), key=lambda r: (-r.wins, r.losses)),
        fallback_mode=fallback_mode,
        run_id=run_dir.name,
    )


def print_leaderboard(lb: Leaderboard) -> None:
    console = Console()

    if lb.fallback_mode:
        console.print(
            "\n[yellow]NOTE: Running in FALLBACK mode[/yellow] — "
            "battle_demo does not yet support [bold]--sidecar[/bold] / [bold]--seed[/bold] flags.\n"
            "All battles used the binary's hard-coded teams A and B with fixed RNG.\n"
            "Team names in this leaderboard reflect [italic]logical bracket slots[/italic], "
            "not distinct team compositions.\n"
            "Once the C++ executor adds --sidecar + --seed flags, re-run for real diversity.\n",
        )

    table = Table(title=f"Tournament Leaderboard  [dim](run {lb.run_id})[/dim]", show_lines=True)
    table.add_column("Rank", justify="right", style="bold cyan")
    table.add_column("Team", style="bold white")
    table.add_column("W", justify="right", style="green")
    table.add_column("L", justify="right", style="red")
    table.add_column("Battles", justify="right")
    table.add_column("Avg Turns", justify="right", style="dim")

    for rank, rec in enumerate(lb.records, 1):
        avg = f"{rec.total_turns / rec.battles:.1f}" if rec.battles else "—"
        table.add_row(
            str(rank),
            rec.name,
            str(rec.wins),
            str(rec.losses),
            str(rec.battles),
            avg,
        )

    console.print(table)


def run_tournament_genomes(
    genomes: "list[Genome]",
    demo_path: str,
    socket: str,
    rulebook: str,
    supported_flags: dict[str, bool],
    run_dir: Path,
    n_battles: int = 12,
    seed: int = 42,
    elo: "EloBoard | None" = None,
    k_elo: float = 32.0,
) -> list[BattleResult]:
    """
    Run a tournament over a list of Genome objects.

    Writes genome JSON files to run_dir/teams/, then runs an elimination +
    round-robin bracket.  Updates the supplied EloBoard in place.

    Returns the list of BattleResult objects produced.
    """
    # Delayed import to avoid circular dependency at module level
    from .genome import write_genome_json

    assert len(genomes) >= 2, "Need at least 2 genomes for a tournament"

    teams_dir = run_dir / "teams"
    teams_dir.mkdir(parents=True, exist_ok=True)

    # Write genome JSONs to disk so --team-a/--team-b can load them
    genome_paths: dict[str, str] = {}
    for g in genomes:
        p = teams_dir / f"{g.name}.json"
        write_genome_json(g, p)
        genome_paths[g.name] = str(p)

    records: dict[str, TeamRecord] = {g.name: TeamRecord(name=g.name) for g in genomes}
    results: list[BattleResult] = []
    battle_idx = 0

    def _battle(genome_a: "Genome", genome_b: "Genome", battle_seed: int) -> str:
        nonlocal battle_idx
        result = run_battle(
            demo_path=demo_path,
            socket=socket,
            rulebook=rulebook,
            seed=battle_seed,
            team_a=genome_paths.get(genome_a.name) if supported_flags.get("team_ab") else None,
            team_b=genome_paths.get(genome_b.name) if supported_flags.get("team_ab") else None,
            supported_flags=supported_flags,
            run_dir=run_dir,
            battle_idx=battle_idx,
        )
        battle_idx += 1
        results.append(result)

        # On a draw / timeout neither genome won: credit both a loss, apply a
        # 0.5/0.5 Elo update (not a decisive win for A), advance A arbitrarily.
        if result.winner == "A":
            records[genome_a.name].record(won=True, turns=result.turns)
            records[genome_b.name].record(won=False, turns=result.turns)
            if elo is not None:
                elo.update(genome_a.name, genome_b.name, k=k_elo)
            return genome_a.name
        elif result.winner == "B":
            records[genome_b.name].record(won=True, turns=result.turns)
            records[genome_a.name].record(won=False, turns=result.turns)
            if elo is not None:
                elo.update(genome_b.name, genome_a.name, k=k_elo)
            return genome_b.name
        else:
            records[genome_a.name].record(won=False, turns=result.turns)
            records[genome_b.name].record(won=False, turns=result.turns)
            if elo is not None:
                elo.update_draw(genome_a.name, genome_b.name, k=k_elo)
            return genome_a.name

    # Handle varying pop sizes — run round-robin when fewer than 8
    n = len(genomes)
    if n >= 8:
        # Standard 8-team bracket (uses first 8 entries)
        g = genomes[:8]
        qf_winners: list[str] = []
        qf_losers: list[str] = []
        for ai, bi in [(0, 1), (2, 3), (4, 5), (6, 7)]:
            winner = _battle(g[ai], g[bi], seed + battle_idx)
            loser = g[bi].name if winner == g[ai].name else g[ai].name
            qf_winners.append(winner)
            qf_losers.append(loser)

        sf_genomes = [next(x for x in g if x.name == name) for name in qf_winners]
        sf_winners: list[str] = []
        for ai, bi in [(0, 1), (2, 3)]:
            winner = _battle(sf_genomes[ai], sf_genomes[bi], seed + battle_idx)
            sf_winners.append(winner)

        final_genomes = [next(x for x in g if x.name == name) for name in sf_winners]
        _battle(final_genomes[0], final_genomes[1], seed + battle_idx)

        # Extra round-robin among QF losers
        loser_objs = [next(x for x in g if x.name == name) for name in qf_losers]
        for ai, bi in [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3)]:
            if battle_idx >= n_battles:
                break
            _battle(loser_objs[ai], loser_objs[bi], seed + battle_idx)
    else:
        # Round-robin for small populations
        import itertools
        pairs = list(itertools.combinations(range(n), 2))
        for pair_idx, (ai, bi) in enumerate(pairs):
            if battle_idx >= n_battles:
                break
            _battle(genomes[ai], genomes[bi], seed + battle_idx)

    return results
