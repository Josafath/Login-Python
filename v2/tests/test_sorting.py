import random

import pytest

from authlab.algorithms import ALGORITHMS, STABLE, Metrics, merge_sort

ALL = list(ALGORITHMS.items())


def random_lists():
    rng = random.Random(0)
    yield []
    yield [1]
    yield list(range(50))  # already sorted
    yield list(range(50, 0, -1))  # reversed
    yield [3] * 40  # all equal
    for _ in range(40):
        n = rng.randint(0, 120)
        yield [rng.randint(-20, 20) for _ in range(n)]  # many duplicates


@pytest.mark.parametrize("name, sort", ALL)
def test_matches_python_sorted(name, sort):
    for data in random_lists():
        original = data[:]
        assert sort(data) == sorted(original), name
        assert data == original  # input list is not modified


@pytest.mark.parametrize("name, sort", ALL)
def test_reverse_and_key(name, sort):
    words = ["pear", "Fig", "apple", "kiwi", "Banana"]
    assert sort(words, key=str.lower) == sorted(words, key=str.lower)
    assert sort(words, key=len, reverse=True)[0] == "Banana"


@pytest.mark.parametrize("name", sorted(STABLE))
def test_stable_algorithms_keep_order_of_equal_keys(name):
    rng = random.Random(1)
    # (key, original position): after sorting by key, positions must stay increasing
    items = [(rng.randint(0, 5), i) for i in range(300)]
    for reverse in (False, True):
        result = ALGORITHMS[name](items, key=lambda x: x[0], reverse=reverse)
        assert result == sorted(items, key=lambda x: x[0], reverse=reverse)


def test_merge_sort_is_linear_on_sorted_input():
    m = Metrics()
    merge_sort(list(range(1024)), metrics=m)
    assert m.comparisons < 2 * 1024


@pytest.mark.parametrize("name, sort", ALL)
def test_comparisons_are_counted(name, sort):
    m = Metrics()
    sort([5, 3, 1, 4, 2], metrics=m)
    assert m.comparisons > 0
