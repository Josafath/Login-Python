import pytest

from authlab.algorithms import ALGORITHMS
from authlab.directory import COLUMNS, SEARCH_MODES, Directory, benchmark, demo_users


@pytest.fixture(scope="module")
def directory():
    return Directory(demo_users(400))


def test_demo_users_are_unique_and_repeatable():
    users = demo_users(300)
    assert len({u.username for u in users}) == 300
    assert [u.username for u in demo_users(300)] == [u.username for u in users]


def test_both_prefix_searches_agree(directory):
    for prefix in ["ka", "ma", "lo", "z", ""]:
        trie, _ = directory.search(prefix, "Prefix · Trie")
        binary, _ = directory.search(prefix, "Prefix · Binary search")
        assert [u.username for u in trie] == [u.username for u in binary]
        assert all(u.username.startswith(prefix) for u in trie)


def test_unknown_search_mode(directory):
    with pytest.raises(ValueError):
        directory.search("a", "Telepathy")


@pytest.mark.parametrize("algorithm", ALGORITHMS)
@pytest.mark.parametrize("column", COLUMNS)
def test_sort_every_column_with_every_algorithm(directory, algorithm, column):
    key = COLUMNS[column]
    result, report = directory.sort(directory.users, column, algorithm, reverse=True)
    assert [key(u) for u in result] == sorted((key(u) for u in directory.users), reverse=True)
    assert report.work > 0


def test_benchmark_checks_every_algorithm():
    rows = benchmark(300)
    assert [r.algorithm for r in rows] == list(ALGORITHMS)
    assert all(r.correct for r in rows)
    # Insertion sort is O(n²): far more comparisons than merge sort
    by_name = {r.algorithm: r for r in rows}
    assert by_name["Insertion sort"].comparisons > 5 * by_name["Merge sort"].comparisons


def test_search_modes_constant_is_complete():
    assert len(SEARCH_MODES) == 2
