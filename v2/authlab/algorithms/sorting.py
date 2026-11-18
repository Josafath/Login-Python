"""Sorting algorithms written from scratch (no `sorted()` or `list.sort()`).

Every function has the same shape:

    algorithm(items, key=None, reverse=False, metrics=None) -> new sorted list

* key      - function that extracts what to compare (like `sorted(key=...)`).
* reverse  - largest first.
* metrics  - optional Metrics object that counts the comparisons made.

| Algorithm        | Best       | Average    | Worst      | Extra memory | Stable |
|------------------|------------|------------|------------|--------------|--------|
| insertion_sort   | O(n)       | O(n²)      | O(n²)      | O(1)         | yes    |
| merge_sort       | O(n)*      | O(n log n) | O(n log n) | O(n)         | yes    |
| quick_sort       | O(n log n) | O(n log n) | O(n²)**    | O(log n)     | no     |
| heap_sort        | O(n log n) | O(n log n) | O(n log n) | O(1)         | no     |

 *  merge_sort skips merging halves that are already in order.
 ** practically impossible thanks to the random pivot.

"Stable" means items with equal keys keep their original order. That matters
when you sort a table by one column and then by another.
"""
from __future__ import annotations

import random
from typing import Any, Callable, Iterable, Optional

from .metrics import Metrics

# Below this size, insertion sort beats the "smart" algorithms because it has
# almost no overhead. Real libraries (Timsort, introsort) use the same trick.
INSERTION_CUTOFF = 16

# Internally every algorithm works on (key, item) pairs, so the key function
# runs once per item instead of once per comparison.
Pair = tuple[Any, Any]
Less = Callable[[Any, Any], bool]


def _prepare(items: Iterable, key: Optional[Callable], reverse: bool,
             metrics: Optional[Metrics]) -> tuple[list[Pair], Less]:
    """Build the (key, item) list and the comparison function shared by all algorithms."""
    pairs = [(key(x) if key else x, x) for x in items]

    def less(a: Any, b: Any) -> bool:
        # The only place where keys are compared, so counting here counts everything.
        if metrics is not None:
            metrics.tick()
        # For descending order just flip the comparison. Equal keys still
        # compare as "not less", so stable algorithms stay stable.
        return b < a if reverse else a < b

    return pairs, less


def _strip(pairs: list[Pair]) -> list:
    """Drop the keys again and return just the items."""
    return [item for _, item in pairs]


# ---------------------------------------------------------------- insertion

def _insertion(a: list[Pair], lo: int, hi: int, less: Less) -> None:
    """Sort a[lo:hi] in place: grow a sorted prefix one item at a time."""
    for i in range(lo + 1, hi):
        current = a[i]
        j = i - 1
        # Shift bigger items one slot to the right until current's spot is found.
        # Strict `less` means equal items are never jumped over (stable).
        while j >= lo and less(current[0], a[j][0]):
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = current


def insertion_sort(items: Iterable, key: Optional[Callable] = None, reverse: bool = False,
                   metrics: Optional[Metrics] = None) -> list:
    """O(n²), but very fast on tiny or almost-sorted lists."""
    pairs, less = _prepare(items, key, reverse, metrics)
    _insertion(pairs, 0, len(pairs), less)
    return _strip(pairs)


# -------------------------------------------------------------------- merge

def _merge_sort(a: list[Pair], buf: list[Pair], lo: int, hi: int, less: Less) -> None:
    """Sort a[lo:hi] using buf as scratch space (divide and conquer)."""
    # Small pieces: insertion sort is faster than splitting further (hybrid).
    if hi - lo <= INSERTION_CUTOFF:
        _insertion(a, lo, hi, less)
        return
    mid = (lo + hi) // 2
    _merge_sort(a, buf, lo, mid, less)
    _merge_sort(a, buf, mid, hi, less)
    # If the last item of the left half is not bigger than the first of the
    # right half, both halves are already in order: nothing to merge.
    # This makes already-sorted input O(n).
    if not less(a[mid][0], a[mid - 1][0]):
        return
    # Merge: copy both halves aside, then repeatedly take the smaller front item.
    buf[lo:hi] = a[lo:hi]
    i, j = lo, mid
    for k in range(lo, hi):
        if i >= mid:  # left half used up
            a[k] = buf[j]
            j += 1
        elif j >= hi:  # right half used up
            a[k] = buf[i]
            i += 1
        elif less(buf[j][0], buf[i][0]):  # strictly smaller: take from the right
            a[k] = buf[j]
            j += 1
        else:  # ties take from the left, which keeps the sort stable
            a[k] = buf[i]
            i += 1


def merge_sort(items: Iterable, key: Optional[Callable] = None, reverse: bool = False,
               metrics: Optional[Metrics] = None) -> list:
    """Stable O(n log n). The default algorithm of the app."""
    pairs, less = _prepare(items, key, reverse, metrics)
    # One scratch buffer allocated once and reused by every merge.
    _merge_sort(pairs, pairs[:], 0, len(pairs), less)
    return _strip(pairs)


# -------------------------------------------------------------------- quick

def _quick_sort(a: list[Pair], lo: int, hi: int, less: Less, rng: random.Random) -> None:
    """Sort a[lo:hi] with randomized 3-way quicksort."""
    while hi - lo > INSERTION_CUTOFF:
        # A random pivot makes the O(n²) worst case (e.g. already sorted
        # input with a "first item" pivot) astronomically unlikely.
        pivot = a[rng.randrange(lo, hi)][0]
        # 3-way partition (Dijkstra's "Dutch national flag"):
        #   a[lo:lt]   < pivot
        #   a[lt:i]   == pivot
        #   a[i:gt+1]    not looked at yet
        #   a[gt+1:hi] > pivot
        # Grouping the equal keys in the middle keeps lists with many duplicates fast.
        lt, i, gt = lo, lo, hi - 1
        while i <= gt:
            k = a[i][0]
            if less(k, pivot):
                a[lt], a[i] = a[i], a[lt]
                lt += 1
                i += 1
            elif less(pivot, k):
                a[i], a[gt] = a[gt], a[i]
                gt -= 1
            else:
                i += 1
        # Recurse into the smaller side and loop over the bigger one. This keeps
        # the recursion depth at O(log n) even on unlucky pivots.
        if lt - lo < hi - (gt + 1):
            _quick_sort(a, lo, lt, less, rng)
            lo = gt + 1
        else:
            _quick_sort(a, gt + 1, hi, less, rng)
            hi = lt
    _insertion(a, lo, hi, less)


def quick_sort(items: Iterable, key: Optional[Callable] = None, reverse: bool = False,
               metrics: Optional[Metrics] = None, rng: Optional[random.Random] = None) -> list:
    """Usually the fastest in practice, but not stable."""
    pairs, less = _prepare(items, key, reverse, metrics)
    _quick_sort(pairs, 0, len(pairs), less, rng or random.Random())
    return _strip(pairs)


# --------------------------------------------------------------------- heap

def _sift_down(a: list[Pair], root: int, end: int, less: Less) -> None:
    """Move a[root] down until both children are smaller (max-heap in a[:end])."""
    while (child := 2 * root + 1) < end:
        # Pick the bigger of the two children.
        if child + 1 < end and less(a[child][0], a[child + 1][0]):
            child += 1
        if not less(a[root][0], a[child][0]):
            return  # heap property holds
        a[root], a[child] = a[child], a[root]
        root = child


def heap_sort(items: Iterable, key: Optional[Callable] = None, reverse: bool = False,
              metrics: Optional[Metrics] = None) -> list:
    """Guaranteed O(n log n) with no extra memory, but not stable."""
    pairs, less = _prepare(items, key, reverse, metrics)
    n = len(pairs)
    # 1) Heapify: turn the list into a max-heap, where every parent is >= its
    #    children (children of i live at 2i+1 and 2i+2). Bottom-up is O(n).
    for start in range(n // 2 - 1, -1, -1):
        _sift_down(pairs, start, n, less)
    # 2) The biggest item is at the root: swap it to the end, shrink the
    #    heap by one and repair it. Repeat until the heap is empty.
    for end in range(n - 1, 0, -1):
        pairs[0], pairs[end] = pairs[end], pairs[0]
        _sift_down(pairs, 0, end, less)
    return _strip(pairs)


# Name -> function. Used by the "Algorithms Lab" menu and the benchmark.
ALGORITHMS: dict[str, Callable[..., list]] = {
    "Merge sort": merge_sort,
    "Quick sort": quick_sort,
    "Heap sort": heap_sort,
    "Insertion sort": insertion_sort,
}
STABLE = {"Merge sort", "Insertion sort"}
