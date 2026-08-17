"""Кеш за оценките на моделите.

Оценяването на регресиите отнема стотици милисекунди, а входните редове се
обновяват веднъж дневно. Кешираме за кратко, за да не плаща всяка заявка
цената на повторна оценка.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

TTL_SECONDS = 900

_lock = threading.Lock()
_entries: dict[str, tuple[float, Any]] = {}


def get_or_compute(key: str, producer: Callable[[], Any]) -> Any:
    now = time.monotonic()
    with _lock:
        cached = _entries.get(key)
        if cached is not None and now - cached[0] < TTL_SECONDS:
            return cached[1]

    value = producer()

    with _lock:
        _entries[key] = (time.monotonic(), value)
    return value


def invalidate() -> None:
    with _lock:
        _entries.clear()
