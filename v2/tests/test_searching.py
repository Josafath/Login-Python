import random

from authlab.algorithms import Metrics, Trie, binary_search, lower_bound, prefix_range

NAMES = ["ana", "andres", "angel", "beto", "carla", "carlos", "dani", "eva"]


def test_lower_bound_matches_bisect_left():
    import bisect  # used only as a referee

    rng = random.Random(0)
    for _ in range(200):
        data = sorted(rng.randint(0, 30) for _ in range(rng.randint(0, 40)))
        target = rng.randint(-5, 35)
        assert lower_bound(data, target) == bisect.bisect_left(data, target)


def test_binary_search():
    assert binary_search(NAMES, "carla") == 4
    assert binary_search(NAMES, "zoe") == -1
    assert binary_search(NAMES, "a") == -1  # a prefix is not a match
    assert binary_search([], "ana") == -1


def test_binary_search_is_logarithmic():
    m = Metrics()
    binary_search(list(range(1_000_000)), 765_432, metrics=m)
    assert m.comparisons <= 21  # ceil(log2(1,000,000)) + 1


def test_prefix_range():
    assert [NAMES[i] for i in prefix_range(NAMES, "an")] == ["ana", "andres", "angel"]
    assert [NAMES[i] for i in prefix_range(NAMES, "carl")] == ["carla", "carlos"]
    assert list(prefix_range(NAMES, "x")) == []
    assert len(prefix_range(NAMES, "")) == len(NAMES)


def test_trie_prefix_search_is_alphabetical():
    trie = Trie(reversed(NAMES))
    assert trie.starts_with("an") == ["ana", "andres", "angel"]
    assert trie.starts_with("") == NAMES
    assert trie.starts_with("an", limit=2) == ["ana", "andres"]
    assert trie.starts_with("zz") == []


def test_trie_insert_contains_remove():
    trie = Trie(["ana", "anabel"])
    assert "ana" in trie and "an" not in trie
    assert not trie.insert("ana")  # duplicates are ignored
    assert trie.remove("ana")
    assert "ana" not in trie and "anabel" in trie
    assert trie.remove("anabel")
    assert len(trie) == 0 and trie.starts_with("") == []
    assert not trie.remove("nobody")
