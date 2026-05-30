"""EvolutionReport: per-generation stats + rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.table import Table

from .genome import Genome


@dataclass
class GenerationStats:
    generation: int
    avg_elo: float
    max_elo: float
    champion_name: str
    vs_seed_wins: int
    vs_seed_battles: int
    mutations_applied: int
    hof_names: list[str]

    @property
    def vs_seed_rating(self) -> str:
        if self.vs_seed_battles == 0:
            return "—"
        return f"{self.vs_seed_wins}/{self.vs_seed_battles}"


@dataclass
class EvolutionReport:
    run_id: str
    generations: list[GenerationStats] = field(default_factory=list)
    hof_entries: list[tuple[Genome, float, int]] = field(default_factory=list)
    champion_genome: Genome | None = None

    def render(self) -> None:
        console = Console()

        # Per-generation table
        gen_table = Table(
            title=f"Evolution Progress  [dim](run {self.run_id})[/dim]",
            show_lines=True,
        )
        gen_table.add_column("Gen", justify="right", style="bold cyan")
        gen_table.add_column("Avg Elo", justify="right")
        gen_table.add_column("Max Elo", justify="right", style="bold green")
        gen_table.add_column("Champion", style="bold white")
        gen_table.add_column("vs Seeds", justify="right", style="yellow")
        gen_table.add_column("Mutations", justify="right", style="dim")
        gen_table.add_column("HoF", style="dim")

        for gs in self.generations:
            gen_table.add_row(
                str(gs.generation),
                f"{gs.avg_elo:.1f}",
                f"{gs.max_elo:.1f}",
                gs.champion_name,
                gs.vs_seed_rating,
                str(gs.mutations_applied),
                ", ".join(gs.hof_names) or "—",
            )

        console.print(gen_table)

        # Hall of Fame table
        if self.hof_entries:
            hof_table = Table(title="Hall of Fame", show_lines=True)
            hof_table.add_column("Rank", justify="right", style="bold yellow")
            hof_table.add_column("Genome", style="bold white")
            hof_table.add_column("Rating", justify="right", style="bold green")
            hof_table.add_column("Gen Added", justify="right", style="dim")
            hof_table.add_column("Species", style="dim")

            for rank, (genome, rating, gen_added) in enumerate(self.hof_entries, 1):
                species_list = ", ".join(m.species for m in genome.members)
                hof_table.add_row(
                    str(rank),
                    genome.name,
                    f"{rating:.1f}",
                    str(gen_added),
                    species_list,
                )

            console.print(hof_table)

        # Champion summary
        if self.champion_genome:
            console.print(f"\n[bold green]Champion:[/bold green] {self.champion_genome.name}")
            console.print("  Members:")
            for m in self.champion_genome.members:
                console.print(
                    f"    [cyan]{m.species}[/cyan]  "
                    f"nature={m.nature}  "
                    f"item={m.item}  "
                    f"moves={m.moves}"
                )
