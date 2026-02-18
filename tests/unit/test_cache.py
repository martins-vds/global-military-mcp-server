"""Unit tests for FileCache with TTL, eviction, and atomic writes."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cache.store import FileCache


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


@pytest.fixture
def cache(cache_dir: Path) -> FileCache:
    return FileCache(cache_dir=cache_dir, default_ttl=3600.0, max_entries=10)


class TestFileCacheBasic:
    """T012: Basic cache operations."""

    def test_get_missing_key_returns_none(self, cache: FileCache):
        assert cache.get("nonexistent") is None

    def test_set_and_get(self, cache: FileCache):
        cache.set("key1", {"name": "F-16", "category": "aircraft"})
        result = cache.get("key1")
        assert result is not None
        assert result["name"] == "F-16"

    def test_set_overwrites(self, cache: FileCache):
        cache.set("key1", {"version": 1})
        cache.set("key1", {"version": 2})
        result = cache.get("key1")
        assert result["version"] == 2

    def test_delete_existing(self, cache: FileCache):
        cache.set("key1", {"data": "value"})
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing(self, cache: FileCache):
        assert cache.delete("nonexistent") is False

    def test_clear_all(self, cache: FileCache):
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})
        cache.set("key3", {"c": 3})
        count = cache.clear()
        assert count == 3
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_clear_empty(self, cache: FileCache):
        assert cache.clear() == 0


class TestFileCacheTTL:
    """T012: TTL expiration tests."""

    def test_expired_entry_returns_none(self, cache: FileCache):
        cache.set("key1", {"data": "value"}, ttl=-1.0)
        # Entry is immediately expired (negative TTL)
        assert cache.get("key1") is None

    def test_custom_ttl(self, cache: FileCache):
        cache.set("key1", {"data": "value"}, ttl=10.0)
        assert cache.get("key1") is not None

    def test_lazy_eviction_on_get(self, cache_dir: Path):
        cache = FileCache(cache_dir=cache_dir, default_ttl=1.0)
        cache.set("key1", {"data": "value"})
        # Simulate time passing
        with patch("src.cache.store.time") as mock_time:
            mock_time.time.return_value = time.time() + 3600
            result = cache.get("key1")
        assert result is None


class TestFileCacheEviction:
    """T012: LRU eviction tests."""

    def test_eviction_when_full(self, cache_dir: Path):
        cache = FileCache(cache_dir=cache_dir, default_ttl=3600.0, max_entries=3)
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})
        cache.set("key3", {"c": 3})
        # Adding a 4th entry should evict the oldest
        cache.set("key4", {"d": 4})
        # At least key4 should exist
        assert cache.get("key4") is not None
        # Total json files should be <= max_entries
        json_files = list(cache_dir.glob("*.json"))
        assert len(json_files) <= 3


class TestFileCacheAtomicity:
    """T012: Atomic write tests."""

    def test_no_tmp_files_after_set(self, cache: FileCache, cache_dir: Path):
        cache.set("key1", {"data": "value"})
        tmp_files = list(cache_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_cache_file_is_valid_json(self, cache: FileCache, cache_dir: Path):
        cache.set("key1", {"data": "value"})
        json_files = list(cache_dir.glob("*.json"))
        assert len(json_files) == 1
        data = json.loads(json_files[0].read_text())
        assert "data" in data
        assert "expires_at" in data
        assert "written_at" in data


class TestFileCacheKeyHashing:
    """T012: SHA-256 key hashing tests."""

    def test_different_keys_different_files(self, cache: FileCache, cache_dir: Path):
        cache.set("key1", {"a": 1})
        cache.set("key2", {"b": 2})
        json_files = list(cache_dir.glob("*.json"))
        assert len(json_files) == 2

    def test_same_key_same_file(self, cache: FileCache, cache_dir: Path):
        cache.set("key1", {"a": 1})
        cache.set("key1", {"a": 2})
        json_files = list(cache_dir.glob("*.json"))
        assert len(json_files) == 1

    def test_corrupted_cache_file_returns_none(self, cache: FileCache, cache_dir: Path):
        cache.set("key1", {"a": 1})
        # Corrupt the file
        json_files = list(cache_dir.glob("*.json"))
        json_files[0].write_text("not valid json{{{")
        assert cache.get("key1") is None
