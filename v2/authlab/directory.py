"""The data behind the "Algorithms Lab" screen: search and sort users while
measuring the work each algorithm does. No UI code here.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .algorithms import ALGORITHMS, STABLE, Metrics, Trie, merge_sort, prefix_range
from .storage import User

SEARCH_MODES = ("Prefix · Trie", "Prefix · Binary search")

# Columns the table can be sorted by, with the key used for each one.
# Users who never logged in have last_login None; "" sorts them first.
COLUMNS: dict[str, Callable[[User], str]] = {
    "Username": lambda u: u.username,
    "Email": lambda u: u.email,
    "Member since": lambda u: u.created_at,
    "Last login": lambda u: u.last_login or "",
}


@dataclass(frozen=True)
class Report:
    """What an operation did, shown under the table in the Lab."""

    algorithm: str
    work: int  # how many comparisons it took
    millis: float
    results: int

    def __str__(self) -> str:
        return (f"{self.results} result(s) · {self.algorithm}: "
                f"{self.work:,} comparisons in {self.millis:.2f} ms")


def _timed(fn: Callable[[], list]) -> tuple[list, float]:
    """Run fn and return its result with the elapsed time in milliseconds."""
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000


class Directory:
    """A searchable, sortable snapshot of users (real ones plus optional demo ones)."""

    def __init__(self, users: list[User]) -> None:
        # Sorted by username: required by binary search.
        self.users = merge_sort(users, key=lambda u: u.username)
        self._by_name = {u.username: u for u in self.users}
        self.trie = Trie(self._by_name)

    def search(self, query: str, mode: str) -> tuple[list[User], Report]:
        query = query.strip().lower()
        metrics = Metrics()
        if mode == "Prefix · Trie":
            names, ms = _timed(lambda: self.trie.starts_with(query, metrics=metrics))
            found = [self._by_name[n] for n in names]
        elif mode == "Prefix · Binary search":
            found, ms = _timed(lambda: [self.users[i] for i in prefix_range(
                self.users, query, key=lambda u: u.username, metrics=metrics)])
        else:
            raise ValueError(f"unknown search mode: {mode}")
        return found, Report(mode, metrics.comparisons, ms, len(found))

    def sort(self, users: list[User], column: str, algorithm: str,
             reverse: bool = False) -> tuple[list[User], Report]:
        metrics = Metrics()
        fn = ALGORITHMS[algorithm]
        ordered, ms = _timed(lambda: fn(users, key=COLUMNS[column], reverse=reverse, metrics=metrics))
        return ordered, Report(algorithm, metrics.comparisons, ms, len(ordered))


# ----------------------------------------------------------- demo data

_SYLLABLES = ("ka", "lo", "ma", "ri", "to", "na", "sa", "el", "an", "jo", "ve", "lu", "da", "mi", "ro", "be")
_DOMAINS = ("gmail.com", "outlook.com", "live.com", "yahoo.com", "proton.me")


def demo_users(n: int, seed: int = 7) -> list[User]:
    """`n` fake users so the Lab has enough data to compare algorithms.

    They only live in memory and have no password, so nobody can log in as them.
    """
    rng = random.Random(seed)  # same seed -> same demo users every time
    users: dict[str, User] = {}
    while len(users) < n:
        name = "".join(rng.choice(_SYLLABLES) for _ in range(rng.randint(2, 4)))
        if rng.random() < 0.3:
            name += str(rng.randint(1, 99))
        day = f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}T{rng.randint(0, 23):02d}:00:00"
        users[name] = User(name, f"{name}@{rng.choice(_DOMAINS)}", "", day,
                           None if rng.random() < 0.2 else day.replace("2025", "2026"))
    return list(users.values())


@dataclass(frozen=True)
class BenchmarkRow:
    algorithm: str
    stable: bool
    comparisons: int
    millis: float
    correct: bool


def benchmark(n: int = 1500, seed: int = 1) -> list[BenchmarkRow]:
    """Sort the same n shuffled demo users with every algorithm."""
    users = demo_users(n, seed)
    random.Random(seed).shuffle(users)
    # sorted() is used ONLY here, as an independent referee to check our results.
    expected = sorted(u.username for u in users)
    rows = []
    for name, fn in ALGORITHMS.items():
        metrics = Metrics()
        result, ms = _timed(lambda: fn(users, key=lambda u: u.username, metrics=metrics))
        rows.append(BenchmarkRow(name, name in STABLE, metrics.comparisons, ms,
                                 [u.username for u in result] == expected))
    return rows
