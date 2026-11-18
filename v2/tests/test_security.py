from authlab.security import hash_password, password_strength, verify_password

FAST = 1_000  # few iterations so tests stay fast; the app uses 600,000


def test_hash_and_verify():
    stored = hash_password("Correct-Horse-9", FAST)
    assert stored.startswith("pbkdf2_sha256$1000$")
    assert "Correct-Horse-9" not in stored
    assert verify_password("Correct-Horse-9", stored)
    assert not verify_password("correct-horse-9", stored)  # case-sensitive


def test_same_password_gets_different_salts():
    assert hash_password("Tr0ub4dor&3", FAST) != hash_password("Tr0ub4dor&3", FAST)


def test_corrupted_hashes_are_rejected_without_crashing():
    for bad in ["", "plain-text", "md5$1$a$b", "pbkdf2_sha256$x$y$z", "pbkdf2_sha256$10$%%%$%%%"]:
        assert not verify_password("anything", bad)


def test_strength_scores():
    assert password_strength("abc").score <= 1
    assert password_strength("password").score == 0
    assert password_strength("Tr4in-Station-Blue!").score == 4
    assert password_strength("Tr4in-Station-Blue!").acceptable


def test_strength_problems():
    assert "Use at least 8 characters" in password_strength("Ab1!").problems
    assert "This is one of the most common passwords" in password_strength("Password1").problems
    assert "Don't include your username" in password_strength("carla2026!X", "carla").problems
    assert "Too many repeated characters" in password_strength("aaaaaaaaaaaa").problems
