"""A tiny counter shared by every algorithm, so the app can show how much work it did."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metrics:
    """How many key comparisons an algorithm made.

    Comparisons are the classic way to measure sorting/searching cost, because
    they don't depend on how fast the computer is.
    """

    comparisons: int = 0

    def tick(self) -> None:
        self.comparisons += 1
