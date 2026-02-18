"""TTL-based file cache with atomic POSIX writes and LRU eviction."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class FileCache:
    """Local file-based cache with SHA-256 key hashing and configurable TTL.

    - Atomic writes via POSIX rename (write to .tmp → rename to target).
    - Lazy TTL eviction on get().
    - LRU eviction on set() when max_entries is exceeded.
    """

    def __init__(
        self,
        cache_dir: Path,
        default_ttl: float = 86400.0,
        max_entries: int = 500,
    ) -> None:
        self._dir = cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._default_ttl = default_ttl
        self._max_entries = max_entries

    def _key_path(self, key: str) -> Path:
        hashed = hashlib.sha256(key.encode()).hexdigest()
        return self._dir / f"{hashed}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        """Return cached data or None if missing/expired (lazy eviction)."""
        path = self._key_path(key)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            path.unlink(missing_ok=True)
            return None
        if raw.get("expires_at", 0) < time.time():
            path.unlink(missing_ok=True)
            return None
        return raw["data"]

    def set(self, key: str, value: dict[str, Any], ttl: float | None = None) -> None:
        """Write data to cache with atomic POSIX rename.

        If the cache exceeds max_entries, the oldest entries by write
        timestamp are evicted.
        """
        self._evict_if_full()
        path = self._key_path(key)
        tmp = path.with_suffix(".tmp")
        payload = {
            "data": value,
            "expires_at": time.time() + (ttl or self._default_ttl),
            "written_at": time.time(),
        }
        tmp.write_text(json.dumps(payload))
        tmp.rename(path)

    def delete(self, key: str) -> bool:
        """Delete a single cache entry. Returns True if it existed."""
        path = self._key_path(key)
        if path.exists():
            path.unlink(missing_ok=True)
            return True
        return False

    def clear(self) -> int:
        """Delete all cache entries. Returns count of deleted files."""
        count = 0
        for path in self._dir.glob("*.json"):
            path.unlink(missing_ok=True)
            count += 1
        return count

    def _evict_if_full(self) -> None:
        """Evict oldest entries if cache exceeds max_entries."""
        entries = sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        excess = len(entries) - self._max_entries + 1  # +1 to make room
        if excess > 0:
            for path in entries[:excess]:
                path.unlink(missing_ok=True)
