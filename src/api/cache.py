"""In-memory TTL cache for scored results + background refresh."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class TTLCache:
    """Simple in-memory TTL cache keyed by tuple."""

    def __init__(self, ttl_seconds: float = 300.0) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple, tuple[float, Any]] = {}

    def get(self, key: tuple) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: tuple, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)

    def invalidate_all(self) -> None:
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
