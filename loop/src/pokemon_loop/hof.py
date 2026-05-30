"""Hall of Fame: track the best genomes across generations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .genome import Genome, Member


_HOF_CAPACITY = 2


class HallOfFame:
    """Keeps the top `capacity` genomes seen across all generations."""

    def __init__(self, capacity: int = _HOF_CAPACITY) -> None:
        self.capacity = capacity
        # Each entry: (genome, rating, gen_added)
        self._entries: list[tuple[Genome, float, int]] = []

    def consider(self, genome: Genome, rating: float, gen_added: int = 0) -> None:
        """Add this genome if it beats the worst current member (or HoF isn't full)."""
        if len(self._entries) < self.capacity:
            self._entries.append((genome, rating, gen_added))
            self._entries.sort(key=lambda e: -e[1])
            return

        worst_rating = self._entries[-1][1]
        if rating > worst_rating:
            self._entries[-1] = (genome, rating, gen_added)
            self._entries.sort(key=lambda e: -e[1])

    def members(self) -> list[tuple[Genome, float, int]]:
        """Return list of (genome, rating, gen_added) sorted best-first."""
        return list(self._entries)

    def genomes(self) -> list[Genome]:
        return [e[0] for e in self._entries]

    def persist(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data: list[dict[str, Any]] = []
        for genome, rating, gen_added in self._entries:
            data.append({
                "rating": rating,
                "gen_added": gen_added,
                "genome": genome.model_dump(),
            })
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path, capacity: int = _HOF_CAPACITY) -> "HallOfFame":
        hof = cls(capacity=capacity)
        if not path.exists():
            return hof
        entries = json.loads(path.read_text())
        for entry in entries:
            genome = Genome.model_validate(entry["genome"])
            hof._entries.append((genome, entry["rating"], entry["gen_added"]))
        return hof
