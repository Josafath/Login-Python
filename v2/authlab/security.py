"""Password hashing and password strength.

Unlike the search/sort algorithms, the cryptography is NOT written from
scratch on purpose. Home-made crypto is one of the classic security
mistakes; the right move is a well-reviewed standard (PBKDF2) from the
standard library.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import math
import secrets
from dataclasses import dataclass

ALGORITHM = "pbkdf2_sha256"
# OWASP's 2023 recommendation for PBKDF2-SHA256. Each hash takes ~0.2 s on
# purpose: unnoticeable at login, but it makes guessing billions of
# passwords from a stolen file impractical.
DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a self-describing hash: "pbkdf2_sha256$<iterations>$<salt>$<hash>".

    A random salt per user means two people with the same password get
    different hashes, and precomputed tables ("rainbow tables") are useless.
    Storing the iterations lets us raise them in the future without breaking
    old accounts.
    """
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    """True if `password` matches the stored hash. Never raises on bad input."""
    try:
        algorithm, iterations, salt, digest = encoded.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = base64.b64decode(digest)
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), base64.b64decode(salt), int(iterations)
        )
    except (ValueError, TypeError):
        return False  # corrupted or unknown hash format
    # compare_digest takes the same time whether the first or the last byte
    # differs, so response times leak nothing about the hash.
    return hmac.compare_digest(candidate, expected)


# The most common passwords in public breach lists. Real systems check against
# millions (e.g. the "Have I Been Pwned" list); a handful is enough here.
COMMON_PASSWORDS = frozenset("""
123456 123456789 12345678 password qwerty123 qwerty 1q2w3e4r 111111 123123 abc123
password1 iloveyou 1234567890 000000 qwertyuiop 654321 dragon monkey letmein
football baseball welcome admin admin123 sunshine princess passw0rd master
contraseña contrasena 12341234 superman
""".split())

LABELS = ("Very weak", "Weak", "Fair", "Strong", "Very strong")
MIN_SCORE = 2  # "Fair" or better is required to register


@dataclass(frozen=True)
class Strength:
    score: int  # 0 (very weak) .. 4 (very strong)
    entropy_bits: float  # rough estimate of how hard it is to guess
    problems: tuple[str, ...]  # human tips; empty when there is nothing to fix

    @property
    def label(self) -> str:
        return LABELS[self.score]

    @property
    def acceptable(self) -> bool:
        return self.score >= MIN_SCORE and not self.problems


def password_strength(password: str, username: str = "") -> Strength:
    """Estimate how hard a password is to guess.

    Entropy estimate: length x log2(size of the character pool). For example,
    8 lowercase letters = 8 x log2(26) ≈ 37.6 bits. The estimate is then
    lowered for patterns attackers try first.
    """
    pool = 0
    if any(c.islower() for c in password):
        pool += 26
    if any(c.isupper() for c in password):
        pool += 26
    if any(c.isdigit() for c in password):
        pool += 10
    if any(not c.isalnum() for c in password):
        pool += 33  # printable symbols
    bits = len(password) * math.log2(pool) if pool else 0.0

    problems = []
    if len(password) < 8:
        problems.append("Use at least 8 characters")
    if password.lower() in COMMON_PASSWORDS:
        problems.append("This is one of the most common passwords")
        bits = min(bits, 10)  # attackers try these first
    if username and len(username) >= 3 and username.lower() in password.lower():
        problems.append("Don't include your username")
        bits = min(bits, 25)
    if password and len(set(password)) <= len(password) // 3:
        problems.append("Too many repeated characters")
        bits /= 2

    # Bit thresholds similar to the ones used by password managers.
    score = sum(bits >= t for t in (28, 36, 60, 80))
    if len(password) < 8:
        score = min(score, 1)
    return Strength(score, round(bits, 1), tuple(problems))
