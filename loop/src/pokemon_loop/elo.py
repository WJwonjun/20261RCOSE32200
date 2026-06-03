"""EloBoard: track and persist team ratings."""

from __future__ import annotations

import json
from pathlib import Path


class EloBoard:
    """Dict of team-name → rating with standard Elo update logic."""

    def __init__(self) -> None:
        self._ratings: dict[str, float] = {}

    def get(self, name: str) -> float:
        return self._ratings.get(name, 1000.0)

    def update(
        self,
        winner_name: str,
        loser_name: str,
        k: float = 32.0,
        weight: float = 1.0,
    ) -> None:
        """Standard Elo update with optional weighting."""
        ra = self.get(winner_name)
        rb = self.get(loser_name)
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        eb = 1.0 / (1.0 + 10 ** ((ra - rb) / 400.0))
        self._ratings[winner_name] = ra + k * weight * (1.0 - ea)
        self._ratings[loser_name] = rb + k * weight * (0.0 - eb)

    def update_draw(
        self,
        name_a: str,
        name_b: str,
        k: float = 32.0,
        weight: float = 1.0,
    ) -> None:
        """Elo update for a drawn game: both sides score 0.5.

        Symmetric — equal-rated teams stay put; an upset (lower-rated team
        draws a higher-rated one) shifts ratings toward each other.
        """
        ra = self.get(name_a)
        rb = self.get(name_b)
        ea = 1.0 / (1.0 + 10 ** ((rb - ra) / 400.0))
        eb = 1.0 / (1.0 + 10 ** ((ra - rb) / 400.0))
        self._ratings[name_a] = ra + k * weight * (0.5 - ea)
        self._ratings[name_b] = rb + k * weight * (0.5 - eb)

    def top(self, n: int) -> list[tuple[str, float]]:
        """Return the top-n teams sorted by rating descending."""
        return sorted(self._ratings.items(), key=lambda x: -x[1])[:n]

    def all_ratings(self) -> dict[str, float]:
        return dict(self._ratings)

    def persist(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self._ratings, indent=2))

    @classmethod
    def load(cls, path: Path) -> "EloBoard":
        board = cls()
        if path.exists():
            board._ratings = json.loads(path.read_text())
        return board
