"""Evolution: multi-generation genetic algorithm driver."""

from __future__ import annotations

import random
import time
from pathlib import Path

from .elo import EloBoard
from .genome import Genome, crossover, mutate, random_genome, write_genome_json
from .hof import HallOfFame
from .palette import Palette, load_palette
from .report import EvolutionReport, GenerationStats
from .runner import probe_demo_flags
from .seed_pool import seed_pool, write_seed_jsons
from .sidecar_proc import SidecarProcess
from .tournament import run_tournament_genomes


class Evolution:
    def __init__(
        self,
        palette: Palette,
        repo_root: Path,
        run_id: str,
        seed: int = 42,
    ) -> None:
        self.palette = palette
        self.repo_root = repo_root
        self.run_id = run_id
        self.rng = random.Random(seed)
        self._base_seed = seed

        self.demo_path = repo_root / "build" / "battle_demo"
        self.sidecar_dir = repo_root / "sidecar"
        self.rulebook = repo_root / "rulebook" / "rulebook.md"
        self.loop_dir = repo_root / "loop"
        self.run_dir = self.loop_dir / "runs" / run_id

    def _gen_dir(self, gen: int) -> Path:
        return self.run_dir / f"gen_{gen}"

    def _initial_population(self, pop_size: int) -> list[Genome]:
        return [
            random_genome(self.palette, f"gen0_team_{i}", self.rng)
            for i in range(pop_size)
        ]

    def _build_next_generation(
        self,
        current_pop: list[Genome],
        elo: EloBoard,
        hof: HallOfFame,
        gen: int,
        pop_size: int,
    ) -> tuple[list[Genome], int]:
        """Build next-gen population. Returns (new_pop, mutations_applied)."""
        top_names = [name for name, _ in elo.top(pop_size)]
        # Sort current pop by Elo rank
        ranked = sorted(
            current_pop,
            key=lambda g: top_names.index(g.name) if g.name in top_names else pop_size,
        )

        mutations_applied = 0
        next_pop: list[Genome] = []

        # 1. HoF members (up to 2, no mutation)
        for hof_genome, _, _ in hof.members():
            renamed = Genome(
                name=f"hof_{hof_genome.name}_g{gen + 1}",
                members=hof_genome.members,
            )
            next_pop.append(renamed)
            if len(next_pop) >= 2:
                break

        # 2. Elite: top-1 unchanged, top-2 mutated
        if len(ranked) >= 1:
            elite = ranked[0]
            elite_copy = Genome(
                name=f"{elite.name}_elite_g{gen + 1}",
                members=elite.members,
            )
            next_pop.append(elite_copy)

        if len(ranked) >= 2:
            mutated = mutate(ranked[1], self.palette, self.rng)
            next_pop.append(Genome(
                name=f"mut_{ranked[1].name}_g{gen + 1}",
                members=mutated.members,
            ))
            mutations_applied += 1

        # 3. Two crossover children from top-4
        top4 = ranked[:min(4, len(ranked))]
        for child_idx in range(2):
            if len(top4) >= 2:
                parents = self.rng.sample(top4, 2)
                child = crossover(parents[0], parents[1], self.rng)
                child = mutate(child, self.palette, self.rng)
                mutations_applied += 1
                next_pop.append(Genome(
                    name=f"cross_{gen + 1}_{child_idx}",
                    members=child.members,
                ))

        # 4. Fresh random (variety) — fill remaining slots up to pop_size
        fresh_idx = 0
        while len(next_pop) < pop_size:
            fresh = random_genome(self.palette, f"gen{gen + 1}_fresh_{fresh_idx}", self.rng)
            next_pop.append(fresh)
            fresh_idx += 1

        return next_pop[:pop_size], mutations_applied

    def run(
        self,
        n_generations: int = 5,
        pop_size: int = 8,
        battles_per_gen: int = 12,
        k_elo: float = 32.0,
    ) -> EvolutionReport:
        self.run_dir.mkdir(parents=True, exist_ok=True)

        supported_flags = probe_demo_flags(str(self.demo_path))
        socket_path = f"/tmp/pokemon_sidecar_{self.run_id}.sock"

        seeds = seed_pool()
        # Palette was already loaded at Evolution construction time and passed in;
        # seed teams use hardcoded IDs that are already normalized.
        seed_dir = self.run_dir / "seeds"
        write_seed_jsons(seed_dir)

        hof = HallOfFame(capacity=2)
        elo = EloBoard()
        report = EvolutionReport(run_id=self.run_id)

        population = self._initial_population(pop_size)

        ctx = SidecarProcess(
            sidecar_dir=str(self.sidecar_dir),
            socket_path=socket_path,
        )
        socket = ctx.__enter__()

        try:
            for gen in range(n_generations):
                gen_dir = self._gen_dir(gen)
                teams_dir = gen_dir / "teams"
                teams_dir.mkdir(parents=True, exist_ok=True)

                # 1. Persist population genomes
                for genome in population:
                    write_genome_json(genome, teams_dir / f"{genome.name}.json")

                # 2. Run tournament, update Elo
                battle_results = run_tournament_genomes(
                    genomes=population,
                    demo_path=str(self.demo_path),
                    socket=socket,
                    rulebook=str(self.rulebook),
                    supported_flags=supported_flags,
                    run_dir=gen_dir,
                    n_battles=battles_per_gen,
                    seed=self._base_seed + gen * 100,
                    elo=elo,
                    k_elo=k_elo,
                )

                # 3. Evaluate champion vs seed pool (1 battle per seed)
                # Find best genome in the *current* population by their Elo rating
                pop_names = {g.name for g in population}
                top_in_pop = [(name, r) for name, r in elo.top(len(population) + 10)
                              if name in pop_names]
                vs_seed_wins = 0
                vs_seed_battles = 0

                if top_in_pop:
                    champion_name = top_in_pop[0][0]
                    champion_genome = next(
                        (g for g in population if g.name == champion_name), None
                    )
                    if champion_genome:
                        seed_eval_dir = gen_dir / "seed_evals"
                        seed_eval_dir.mkdir(parents=True, exist_ok=True)

                        champ_path = teams_dir / f"{champion_genome.name}.json"

                        for seed_idx, seed_genome in enumerate(seeds):
                            seed_path = seed_dir / f"{seed_genome.name}.json"
                            if not seed_path.exists():
                                write_genome_json(seed_genome, seed_path)

                            from .runner import run_battle
                            b_result = run_battle(
                                demo_path=str(self.demo_path),
                                socket=socket,
                                rulebook=str(self.rulebook),
                                seed=self._base_seed + gen * 100 + battles_per_gen + seed_idx,
                                team_a=str(champ_path) if supported_flags.get("team_ab") else None,
                                team_b=str(seed_path) if supported_flags.get("team_ab") else None,
                                supported_flags=supported_flags,
                                run_dir=seed_eval_dir,
                                battle_idx=seed_idx,
                            )
                            vs_seed_battles += 1
                            if b_result.winner == "A":
                                vs_seed_wins += 1

                # 4. Update Hall of Fame
                top2 = elo.top(2)
                for name, rating in top2:
                    genome = next((g for g in population if g.name == name), None)
                    if genome:
                        hof.consider(genome, rating, gen_added=gen)

                hof.persist(self.run_dir / "hof.json")

                # 5. Persist Elo
                elo.persist(gen_dir / "elo.json")

                # 6. Log generation stats (use current population's ratings only)
                all_ratings = [elo.get(g.name) for g in population]
                avg_elo = sum(all_ratings) / len(all_ratings) if all_ratings else 1000.0
                max_elo = max(all_ratings) if all_ratings else 1000.0
                champion_name = top_in_pop[0][0] if top_in_pop else (population[0].name if population else "?")

                next_pop, mutations_applied = self._build_next_generation(
                    population, elo, hof, gen, pop_size
                )

                report.generations.append(GenerationStats(
                    generation=gen,
                    avg_elo=avg_elo,
                    max_elo=max_elo,
                    champion_name=champion_name,
                    vs_seed_wins=vs_seed_wins,
                    vs_seed_battles=vs_seed_battles,
                    mutations_applied=mutations_applied,
                    hof_names=[e[0].name for e in hof.members()],
                ))

                population = next_pop

        finally:
            ctx.__exit__(None, None, None)

        # Final champion
        report.hof_entries = hof.members()
        if hof.members():
            report.champion_genome = hof.members()[0][0]
            write_genome_json(
                report.champion_genome,
                self.run_dir / "champion.json",
            )

        return report
