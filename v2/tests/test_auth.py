import json

import pytest

from authlab.auth import (INVALID_LOGIN, LOCK_SECONDS, MAX_FAILED_ATTEMPTS, AccountLocked,
                          AuthService, LoginError, RegistrationError)
from authlab.storage import User, UserStore

GOOD = "Blue-Rocket-42!"


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def service(tmp_path, clock):
    return AuthService(UserStore(tmp_path / "users.json"), iterations=1_000, clock=clock)


def test_register_and_login(service):
    service.register("Carla", "Carla@Mail.com", GOOD)
    result = service.login("  CARLA ", GOOD)  # usernames are case-insensitive
    assert result.user.username == "carla"
    assert result.user.email == "carla@mail.com"
    assert result.previous_login is None
    assert service.login("carla", GOOD).previous_login is not None


def test_password_is_never_stored(service, tmp_path):
    service.register("carla", "c@mail.com", GOOD)
    assert GOOD not in (tmp_path / "users.json").read_text()


def test_registration_reports_every_problem(service):
    with pytest.raises(RegistrationError) as err:
        service.register("a", "not-an-email", "123", confirm="456")
    problems = err.value.problems
    assert len(problems) >= 4
    assert any("Username" in p for p in problems)
    assert any("email" in p for p in problems)
    assert "Passwords don't match" in problems


def test_duplicate_username_is_rejected(service):
    service.register("carla", "c@mail.com", GOOD)
    with pytest.raises(RegistrationError, match="already taken"):
        service.register("CARLA", "other@mail.com", GOOD)


def test_same_error_for_unknown_user_and_wrong_password(service):
    service.register("carla", "c@mail.com", GOOD)
    with pytest.raises(LoginError) as wrong_password:
        service.login("carla", "nope")
    with pytest.raises(LoginError) as unknown_user:
        service.login("nobody", "nope")
    assert str(wrong_password.value) == str(unknown_user.value) == INVALID_LOGIN


def test_lockout_after_failed_attempts(service, clock):
    service.register("carla", "c@mail.com", GOOD)
    for _ in range(MAX_FAILED_ATTEMPTS):
        with pytest.raises(LoginError):
            service.login("carla", "wrong")
    # Even the right password is refused while locked
    with pytest.raises(AccountLocked) as locked:
        service.login("carla", GOOD)
    assert 0 < locked.value.seconds_left <= LOCK_SECONDS
    clock.t += LOCK_SECONDS + 1
    assert service.login("carla", GOOD).user.username == "carla"


def test_unknown_usernames_lock_too(service):
    for _ in range(MAX_FAILED_ATTEMPTS):
        with pytest.raises(LoginError):
            service.login("ghost", "x")
    with pytest.raises(AccountLocked):
        service.login("ghost", "x")


def test_store_keeps_users_sorted_and_survives_reload(tmp_path):
    path = tmp_path / "users.json"
    service = AuthService(UserStore(path), iterations=1_000)
    for name in ["zoe", "beto", "ana", "maria"]:
        service.register(name, f"{name}@mail.com", GOOD)
    assert [u.username for u in UserStore(path).all()] == ["ana", "beto", "maria", "zoe"]
    assert UserStore(path).starting_with("m") == ["maria"]


def test_hand_edited_unsorted_file_is_sorted_on_load(tmp_path):
    path = tmp_path / "users.json"
    users = [User(n, f"{n}@x.com", "h", "2026-01-01T00:00:00").__dict__ for n in ["eva", "ana", "dani"]]
    path.write_text(json.dumps({"version": 1, "users": users}))
    store = UserStore(path)
    assert [u.username for u in store.all()] == ["ana", "dani", "eva"]
    assert store.get("dani") is not None


def test_corrupt_file_is_backed_up(tmp_path):
    path = tmp_path / "users.json"
    path.write_text("{ broken")
    assert len(UserStore(path)) == 0
    assert (tmp_path / "users.corrupt.json").read_text() == "{ broken"
