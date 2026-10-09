"""Tiny TTL cache for hot API paths (Task 3.1.4: 5s ticket list).

No deps, no threads: {key: (expires_at, value)} with lazy expiry on read.
Tests reset via get_cache().clear().
"""
from __future__ import annotations

import time


class TTLCache:
    def __init__(self, default_ttl_s: float = 5.0):
        self.default_ttl_s = default_ttl_s
        self._store: dict = {}

    def get(self, key, ttl_s: float | None = None):
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key, value, ttl_s: float | None = None):
        self._store[key] = (time.monotonic() + (ttl_s or self.default_ttl_s), value)

    def clear(self):
        self._store.clear()


_cache = TTLCache()


def get_cache() -> TTLCache:
    return _cache
