"""Bremse gegen das Durchprobieren von Passwörtern (Sicherheitsprüfung Phase 6b)."""

from app.core.login_throttle import LoginThrottle
from tests.conftest import PASSWORD


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_first_five_failures_are_free_then_delay_doubles():
    clock = Clock()
    t = LoginThrottle(clock)
    for _ in range(5):
        assert t.wait_seconds("admin") == 0
        t.failure("admin")
    assert t.wait_seconds("ADMIN") == 30  # Groß-/Kleinschreibung egal
    clock.now += 30
    assert t.wait_seconds("admin") == 0
    t.failure("admin")
    assert t.wait_seconds("admin") == 60
    for _ in range(20):
        t.failure("admin")
    assert t.wait_seconds("admin") == 15 * 60  # Obergrenze


def test_success_resets_and_counter_expires():
    clock = Clock()
    t = LoginThrottle(clock)
    for _ in range(6):
        t.failure("admin")
    t.success("admin")
    assert t.wait_seconds("admin") == 0
    for _ in range(6):
        t.failure("mitglied")
    clock.now += 31 * 60
    assert t.wait_seconds("mitglied") == 0
    t.failure("mitglied")
    assert t.wait_seconds("mitglied") == 0  # Zähler war verfallen, neu bei 1


def test_login_is_throttled_after_repeated_failures(anon, admin):
    for _ in range(5):
        r = anon.post("/api/v1/auth/login", json={"username": "admin", "password": "falsch-123"})
        assert r.status_code == 401
    r = anon.post("/api/v1/auth/login", json={"username": "admin", "password": PASSWORD})
    assert r.status_code == 429, r.text
    body = r.json()["error"]
    assert body["code"] == "too_many_attempts" and body["details"]["retry_after"] == 30
    # Andere Benutzernamen sind nicht betroffen
    r = anon.post("/api/v1/auth/login", json={"username": "jemand", "password": "x-12345678"})
    assert r.status_code == 401
