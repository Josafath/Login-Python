"""User storage: a JSON file on disk plus a sorted list and a trie in memory.

The list is always kept sorted by username (an invariant), which is what
allows every lookup to use binary search instead of scanning all users.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .algorithms import Metrics, Trie, binary_search, lower_bound, merge_sort

SCHEMA_VERSION = 1


@dataclass
class User:
    username: str  # always lowercase, unique
    email: str
    password_hash: str  # never the password itself (see security.py)
    created_at: str  # ISO date-time, e.g. "2026-11-17T15:30:00"
    last_login: Optional[str] = None


def _username(user: User) -> str:
    """Sort/search key: every algorithm compares users by username."""
    return user.username


def default_path() -> Path:
    """Where the users file lives, following each OS's conventions."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "authlab" / "users.json"


class UserStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else default_path()
        # Sort what we load with our own merge sort: the file could have been
        # edited by hand, and binary search only works on sorted data.
        self._users: list[User] = merge_sort(self._load(), key=_username)
        self._trie = Trie(u.username for u in self._users)

    def __len__(self) -> int:
        return len(self._users)

    def all(self) -> list[User]:
        """Every user, sorted by username (a copy, so callers can't break the order)."""
        return list(self._users)

    def get(self, username: str, metrics: Optional[Metrics] = None) -> Optional[User]:
        """Find a user by exact username with binary search: O(log n)."""
        i = binary_search(self._users, username, key=_username, metrics=metrics)
        return self._users[i] if i >= 0 else None

    def exists(self, username: str, metrics: Optional[Metrics] = None) -> bool:
        return self.get(username, metrics) is not None

    def starting_with(self, prefix: str, limit: int = 10) -> list[str]:
        """Usernames that start with `prefix`, via the trie."""
        return self._trie.starts_with(prefix, limit)

    def add(self, user: User) -> None:
        """Insert a new user at its sorted position and save."""
        # lower_bound gives both answers at once: whether the name is taken,
        # and where it must go to keep the list sorted.
        i = lower_bound(self._users, user.username, key=_username)
        if i < len(self._users) and self._users[i].username == user.username:
            raise ValueError(f"username '{user.username}' already exists")
        self._users.insert(i, user)
        self._trie.insert(user.username)
        self.save()

    def update(self, user: User) -> None:
        """Save changes to an existing user (e.g. a new last_login)."""
        i = binary_search(self._users, user.username, key=_username)
        if i < 0:
            raise KeyError(user.username)
        self._users[i] = user
        self.save()

    def _load(self) -> list[User]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") == SCHEMA_VERSION:
                return [User(**record) for record in data["users"]]
        except FileNotFoundError:
            return []  # first run: no users yet
        except (ValueError, KeyError, TypeError, AttributeError):
            pass  # invalid JSON or unexpected structure: handled below
        # Keep the unreadable file aside instead of silently overwriting it.
        self.path.replace(self.path.with_suffix(".corrupt.json"))
        return []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": SCHEMA_VERSION, "users": [asdict(u) for u in self._users]}
        # Write to a temporary file and then rename it over the real one.
        # A rename is atomic, so a crash can never leave a half-written file.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(self.path)
