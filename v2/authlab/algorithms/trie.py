"""Trie (prefix tree) for fast "starts with ..." searches.

Each node is one character; a word is the path from the root to a node
marked as terminal. Words that share a beginning share nodes:

    root ─ a ─ n ─ a*        "ana"
               └ g ─ e ─ l*  "angel"
         └ b ─ e ─ t ─ o*    "beto"

Finding every word that starts with "an" means walking 2 nodes and then
collecting what hangs below. The cost depends on the length of the prefix
and the number of results, not on how many words are stored.
"""
from __future__ import annotations

from typing import Iterable, Iterator, Optional

from .metrics import Metrics
from .sorting import insertion_sort


class _Node:
    # __slots__ saves memory: a trie creates one object per character.
    __slots__ = ("children", "terminal")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.terminal = False  # True if a word ends exactly here


class Trie:
    def __init__(self, words: Iterable[str] = ()) -> None:
        self._root = _Node()
        self._size = 0
        for word in words:
            self.insert(word)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, word: str) -> bool:
        node = self._find(word)
        return node is not None and node.terminal

    def insert(self, word: str) -> bool:
        """Add a word. Returns False if it was already there."""
        node = self._root
        for ch in word:
            # Create the child node the first time this path is used.
            node = node.children.setdefault(ch, _Node())
        if node.terminal:
            return False
        node.terminal = True
        self._size += 1
        return True

    def remove(self, word: str) -> bool:
        """Delete a word and prune branches left empty. Returns False if absent."""
        # Remember the path so we can walk back up and clean it.
        path: list[tuple[_Node, str]] = []
        node = self._root
        for ch in word:
            child = node.children.get(ch)
            if child is None:
                return False
            path.append((node, ch))
            node = child
        if not node.terminal:
            return False
        node.terminal = False
        self._size -= 1
        # Walk back towards the root, deleting nodes that no longer lead to any word.
        for parent, ch in reversed(path):
            child = parent.children[ch]
            if child.terminal or child.children:
                break
            del parent.children[ch]
        return True

    def starts_with(self, prefix: str, limit: Optional[int] = None,
                    metrics: Optional[Metrics] = None) -> list[str]:
        """Words that start with `prefix`, in alphabetical order (up to `limit`)."""
        node = self._find(prefix)
        if node is None:
            return []
        results = []
        for word in self._walk(node, prefix, metrics):
            results.append(word)
            if limit is not None and len(results) >= limit:
                break
        return results

    def _find(self, prefix: str) -> Optional[_Node]:
        """Follow the characters of `prefix` from the root; None if the path breaks."""
        node = self._root
        for ch in prefix:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def _walk(self, node: _Node, prefix: str, metrics: Optional[Metrics]) -> Iterator[str]:
        """Depth-first walk that yields the words below `node` alphabetically.

        It uses an explicit stack instead of recursion, so very long words
        can't hit Python's recursion limit.
        """
        stack = [(node, prefix)]
        while stack:
            current, word = stack.pop()
            if current.terminal:
                yield word
            # A stack is last-in-first-out, so children are pushed in reverse
            # (z ... a) for "a" to come out first. A node has few children,
            # which is exactly where insertion sort shines.
            for ch in reversed(insertion_sort(current.children, metrics=metrics)):
                stack.append((current.children[ch], word + ch))
