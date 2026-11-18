"""Sign-up and log-in rules. No UI code here, so all of it is testable."""
from __future__ import annotations

import math
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from .security import DEFAULT_ITERATIONS, hash_password, password_strength, verify_password
from .storage import User, UserStore

USERNAME_RE = re.compile(r"^[a-z0-9_.]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MAX_FAILED_ATTEMPTS = 5  # wrong passwords in a row before locking
LOCK_SECONDS = 30

# Same message for "no such user" and "wrong password". Saying which one
# failed would let anybody find out which usernames exist.
INVALID_LOGIN = "Invalid username or password"


class AuthError(Exception):
    """Base class for every expected sign-up/log-in failure."""


class RegistrationError(AuthError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems  # every problem at once, not just the first


class LoginError(AuthError):
    pass


class AccountLocked(LoginError):
    def __init__(self, seconds_left: int) -> None:
        super().__init__(f"Too many failed attempts. Try again in {seconds_left} s")
        self.seconds_left = seconds_left


@dataclass(frozen=True)
class LoginResult:
    user: User
    previous_login: Optional[str]  # shown as "Last login: ..." on the home screen


def normalize_username(username: str) -> str:
    """Usernames are case-insensitive: "Ana", "ANA" and " ana " are the same account."""
    return username.strip().lower()


class AuthService:
    def __init__(
        self,
        store: UserStore,
        iterations: int = DEFAULT_ITERATIONS,
        clock: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.store = store
        self.iterations = iterations
        # Injected so tests can fake the passing of time instead of sleeping.
        self._clock = clock
        self._now = now
        # username -> (failed attempts in a row, locked until <clock time>)
        self._failures: dict[str, tuple[int, float]] = {}
        self._dummy_hash: Optional[str] = None

    # ------------------------------------------------------------- sign up

    def validate(self, username: str, email: str, password: str, confirm: str) -> list[str]:
        """Every problem with a sign-up form, in reading order (empty if valid)."""
        problems = []
        name = normalize_username(username)
        if not USERNAME_RE.match(name):
            problems.append("Username: 3-20 characters, only letters, numbers, '_' and '.'")
        elif self.store.exists(name):
            problems.append("That username is already taken")
        if not EMAIL_RE.match(email.strip()):
            problems.append("Enter a valid email address")
        strength = password_strength(password, name)
        problems.extend(strength.problems)
        # No specific tip, but still too guessable (e.g. "84736251": 8 digits ≈ 27 bits).
        if not strength.problems and not strength.acceptable:
            problems.append("Password is too weak: mix upper/lowercase, numbers and symbols")
        if password != confirm:
            problems.append("Passwords don't match")
        return problems

    def register(self, username: str, email: str, password: str, confirm: Optional[str] = None) -> User:
        problems = self.validate(username, email, password, password if confirm is None else confirm)
        if problems:
            raise RegistrationError(problems)
        user = User(
            username=normalize_username(username),
            email=email.strip().lower(),
            # The password is case-sensitive and stored only as a hash.
            password_hash=hash_password(password, self.iterations),
            created_at=self._now().isoformat(timespec="seconds"),
        )
        self.store.add(user)
        return user

    # -------------------------------------------------------------- log in

    def login(self, username: str, password: str) -> LoginResult:
        name = normalize_username(username)
        self._check_lock(name)
        user = self.store.get(name)
        if user is None:
            # Hash anyway, so "unknown user" takes as long as "wrong password".
            # Otherwise the response time would reveal which usernames exist.
            verify_password(password, self._get_dummy_hash())
            ok = False
        else:
            ok = verify_password(password, user.password_hash)
        if not ok:
            self._record_failure(name)
            raise LoginError(INVALID_LOGIN)

        self._failures.pop(name, None)  # success resets the counter
        previous = user.last_login
        user.last_login = self._now().isoformat(timespec="seconds")
        self.store.update(user)
        return LoginResult(user, previous)

    def _check_lock(self, name: str) -> None:
        _, locked_until = self._failures.get(name, (0, 0.0))
        remaining = locked_until - self._clock()
        if remaining > 0:
            raise AccountLocked(math.ceil(remaining))  # round up: never say "0 s"

    def _record_failure(self, name: str) -> None:
        # Unknown usernames are counted and locked too; otherwise locking
        # would be another way to tell which usernames exist.
        count, _ = self._failures.get(name, (0, 0.0))
        count += 1
        if count >= MAX_FAILED_ATTEMPTS:
            self._failures[name] = (0, self._clock() + LOCK_SECONDS)
        else:
            self._failures[name] = (count, 0.0)

    def _get_dummy_hash(self) -> str:
        # Created on first use only, so starting the app stays instant.
        if self._dummy_hash is None:
            self._dummy_hash = hash_password(secrets.token_hex(16), self.iterations)
        return self._dummy_hash
