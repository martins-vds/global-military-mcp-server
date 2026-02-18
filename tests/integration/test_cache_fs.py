"""Integration tests for FileCache filesystem operations."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cache.store import FileCache


class TestCacheFilesystemIntegration:
    """T016: Integration tests for FileCache with real filesystem."""

    @pytest.fixture
    def cache_dir(self, tmp_path: Path) -> Path:
        return tmp_path / "integration_cache"

    @pytest.fixture
    def cache(self, cache_dir: Path) -> FileCache:
        return FileCache(cache_dir=cache_dir, default_ttl=3600.0, max_entries=50)

    def test_directory_created_on_init(self, cache_dir: Path):
        assert not cache_dir.exists()
        FileCache(cache_dir=cache_dir)
        assert cache_dir.exists()
        assert cache_dir.is_dir()

    def test_atomic_write_no_partial_files(self, cache: FileCache, cache_dir: Path):
        """Verify that set() produces no .tmp files (atomic rename)."""
        for i in range(10):
            cache.set(f"key_{i}", {"index": i})
        tmp_files = list(cache_dir.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_files_are_valid_json(self, cache: FileCache, cache_dir: Path):
        """Every cache file should be valid JSON with expected structure."""
        cache.set("test", {"equipment": "F-16", "country": "usa"})
        for path in cache_dir.glob("*.json"):
            data = json.loads(path.read_text())
            assert "data" in data
            assert "expires_at" in data
            assert "written_at" in data
            assert isinstance(data["data"], dict)

    def test_ttl_expiry_with_time_mock(self, cache_dir: Path):
        """Verify TTL expiry with mocked time."""
        cache = FileCache(cache_dir=cache_dir, default_ttl=60.0)
        real_now = time.time()

        cache.set("key1", {"value": "test"})
        assert cache.get("key1") is not None

        # Advance time past TTL
        with patch("src.cache.store.time") as mock_time:
            mock_time.time.return_value = real_now + 120  # 2 minutes later
            result = cache.get("key1")
        assert result is None

    def test_clear_removes_all_files(self, cache: FileCache, cache_dir: Path):
        """Verify clear() removes all .json files."""
        for i in range(5):
            cache.set(f"key_{i}", {"i": i})
        assert len(list(cache_dir.glob("*.json"))) == 5
        cache.clear()
        assert len(list(cache_dir.glob("*.json"))) == 0

    def test_max_entries_eviction(self, cache_dir: Path):
        """Verify LRU eviction when exceeding max_entries."""
        cache = FileCache(cache_dir=cache_dir, default_ttl=3600.0, max_entries=5)
        for i in range(10):
            cache.set(f"key_{i}", {"i": i})
            # Small sleep to ensure different mtime
            time.sleep(0.01)

        json_files = list(cache_dir.glob("*.json"))
        assert len(json_files) <= 5

    def test_concurrent_safe_sequential(self, cache: FileCache):
        """Sequential set/get operations maintain consistency."""
        for i in range(20):
            cache.set(f"key_{i}", {"value": i})
        for i in range(20):
            result = cache.get(f"key_{i}")
            assert result is not None
            assert result["value"] == i

    def test_delete_removes_file(self, cache: FileCache, cache_dir: Path):
        """Delete actually removes the file from disk."""
        cache.set("to_delete", {"data": "gone"})
        assert len(list(cache_dir.glob("*.json"))) == 1
        cache.delete("to_delete")
        assert len(list(cache_dir.glob("*.json"))) == 0

    def test_large_payload(self, cache: FileCache):
        """Cache handles moderately large payloads."""
        large_data = {
            "items": [
                {"name": f"Equipment_{i}", "slug": f"equipment-{i}", "index": i}
                for i in range(100)
            ]
        }
        cache.set("large", large_data)
        result = cache.get("large")
        assert result is not None
        assert len(result["items"]) == 100
