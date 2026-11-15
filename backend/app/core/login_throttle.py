"""Bremse gegen das Durchprobieren von Passwörtern (NFR-SEC-006, Befund Sicherheitsprüfung).

Fehlversuche werden je Benutzername gezählt. Ab dem fünften Fehlversuch muss vor dem nächsten
Versuch gewartet werden: 30 s, danach jeweils doppelt so lange, höchstens 15 Minuten.
Eine erfolgreiche Anmeldung setzt den Zähler zurück; nach 15 Minuten ohne Fehlversuch
verfällt er. Der Zustand liegt im Arbeitsspeicher – das Backend läuft als ein Prozess
(Dockerfile: ein uvicorn-Worker); ein Neustart setzt ihn zurück.
"""

import threading
import time
from dataclasses import dataclass

FREE_ATTEMPTS = 5
BASE_DELAY = 30.0
MAX_DELAY = 15 * 60.0
FORGET_AFTER = 15 * 60.0


@dataclass
class _State:
    failures: int
    last_failure: float


class LoginThrottle:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._lock = threading.Lock()
        self._states: dict[str, _State] = {}

    def wait_seconds(self, username: str) -> float:
        """Wie lange vor dem nächsten Versuch noch gewartet werden muss (0 = sofort)."""
        with self._lock:
            state = self._current(username.lower())
            if state is None or state.failures < FREE_ATTEMPTS:
                return 0.0
            delay = min(BASE_DELAY * 2 ** (state.failures - FREE_ATTEMPTS), MAX_DELAY)
            return max(0.0, state.last_failure + delay - self._clock())

    def failure(self, username: str) -> None:
        with self._lock:
            key = username.lower()
            state = self._current(key)
            self._states[key] = _State((state.failures if state else 0) + 1, self._clock())

    def success(self, username: str) -> None:
        with self._lock:
            self._states.pop(username.lower(), None)

    def _current(self, key: str) -> _State | None:
        state = self._states.get(key)
        if state and self._clock() - state.last_failure > FORGET_AFTER + MAX_DELAY:
            del self._states[key]
            return None
        return state


login_throttle = LoginThrottle()
