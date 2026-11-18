"""Binary search on sorted sequences, written from scratch (no `bisect`).

All functions take an optional `key` (what each item is sorted by) and an
optional Metrics object to count comparisons. Each step halves the part of
the list that is left, so a list of 1,000,000 users needs ~20 comparisons.
"""
from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .metrics import Metrics

# Highest possible Unicode character. "abc" + MAX_CHAR is bigger than every
# string that starts with "abc", which turns a prefix into a range.
MAX_CHAR = "\U0010ffff"


def lower_bound(seq: Sequence, target: Any, key: Optional[Callable] = None,
                metrics: Optional[Metrics] = None) -> int:
    """First index whose key is >= target (len(seq) if there is none).

    It is also the position where `target` should be inserted to keep the
    sequence sorted, which is how new users are added.
    """
    lo, hi = 0, len(seq)  # the answer is always inside [lo, hi]
    while lo < hi:
        mid = (lo + hi) // 2
        if metrics is not None:
            metrics.tick()
        value = key(seq[mid]) if key else seq[mid]
        if value < target:
            lo = mid + 1  # the answer is to the right of mid
        else:
            hi = mid  # mid could be the answer; keep it in the range
    return lo


def binary_search(seq: Sequence, target: Any, key: Optional[Callable] = None,
                  metrics: Optional[Metrics] = None) -> int:
    """Index of an item whose key equals target, or -1. O(log n)."""
    i = lower_bound(seq, target, key, metrics)
    if i < len(seq) and (key(seq[i]) if key else seq[i]) == target:
        return i
    return -1


def prefix_range(seq: Sequence, prefix: str, key: Optional[Callable] = None,
                 metrics: Optional[Metrics] = None) -> range:
    """Indexes of every item whose key starts with `prefix`. O(log n).

    In a sorted list all the matches sit next to each other, so two binary
    searches find where the block starts and where it ends.
    """
    start = lower_bound(seq, prefix, key, metrics)
    end = lower_bound(seq, prefix + MAX_CHAR, key, metrics)
    return range(start, end)
