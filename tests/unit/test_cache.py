"""Tests for cache.py."""

import json
import time
from pathlib import Path

from mcpax.core.cache import ApiCache


class TestApiCacheDirtyFlag:
    """Tests for dirty flag behavior."""

    def test_set_project_marks_dirty(self, tmp_path: Path) -> None:
        """set_project should mark cache as dirty without writing to disk."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)

        # Act
        cache.set_project("sodium", {"title": "Sodium"})

        # Assert - file should not exist yet (no immediate write)
        assert not cache_file.exists()

    def test_set_versions_marks_dirty(self, tmp_path: Path) -> None:
        """set_versions should mark cache as dirty without writing to disk."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)

        # Act
        cache.set_versions("sodium", [{"id": "v1"}])

        # Assert - file should not exist yet (no immediate write)
        assert not cache_file.exists()

    def test_flush_writes_when_dirty(self, tmp_path: Path) -> None:
        """flush should write to disk when cache is dirty."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)
        cache.set_project("sodium", {"title": "Sodium"})

        # Act
        cache.flush()

        # Assert
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert "sodium" in data["project"]
        assert data["project"]["sodium"]["data"]["title"] == "Sodium"

    def test_flush_does_nothing_when_not_dirty(self, tmp_path: Path) -> None:
        """flush should not write to disk when cache is not dirty."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)

        # Act
        cache.flush()

        # Assert - file should not be created
        assert not cache_file.exists()

    def test_multiple_operations_single_flush(self, tmp_path: Path) -> None:
        """Multiple set operations should only write once on flush."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)

        # Act - multiple operations
        cache.set_project("sodium", {"title": "Sodium"})
        cache.set_project("lithium", {"title": "Lithium"})
        cache.set_versions("sodium", [{"id": "v1"}])
        cache.flush()

        # Assert - all data should be present after single flush
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert "sodium" in data["project"]
        assert "lithium" in data["project"]
        assert "sodium" in data["versions"]


class TestApiCacheContextManager:
    """Tests for context manager behavior."""

    def test_context_manager_flushes_on_exit(self, tmp_path: Path) -> None:
        """Context manager should flush on exit."""
        # Arrange
        cache_file = tmp_path / "cache.json"

        # Act
        with ApiCache(cache_file) as cache:
            cache.set_project("sodium", {"title": "Sodium"})

        # Assert - data should be written after context exit
        assert cache_file.exists()
        data = json.loads(cache_file.read_text())
        assert "sodium" in data["project"]

    def test_context_manager_flushes_even_with_no_changes(self, tmp_path: Path) -> None:
        """Context manager should work even with no changes."""
        # Arrange
        cache_file = tmp_path / "cache.json"

        # Act & Assert - should not raise
        with ApiCache(cache_file):
            pass

        # File should not exist if nothing was set
        assert not cache_file.exists()

    def test_multiple_operations_in_context(self, tmp_path: Path) -> None:
        """Context manager should handle multiple operations."""
        # Arrange
        cache_file = tmp_path / "cache.json"

        # Act
        with ApiCache(cache_file) as cache:
            cache.set_project("sodium", {"title": "Sodium"})
            cache.set_versions("sodium", [{"id": "v1"}])
            cache.set_project("lithium", {"title": "Lithium"})

        # Assert
        data = json.loads(cache_file.read_text())
        assert len(data["project"]) == 2
        assert len(data["versions"]) == 1


class TestApiCacheSaveError:
    """Tests for error handling in _save."""

    def test_save_logs_oserror_warning(
        self, tmp_path: Path, caplog, monkeypatch
    ) -> None:
        """_save should log warning on OSError instead of silently failing."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)
        cache.set_project("sodium", {"title": "Sodium"})

        # Mock Path.write_text to raise OSError
        def mock_write_text(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        # Act
        with caplog.at_level("WARNING"):
            cache.flush()

        # Assert - should log warning
        assert any(
            "Failed to save cache" in record.message for record in caplog.records
        )


class TestApiCacheBasicFunctionality:
    """Tests for basic cache operations (existing behavior)."""

    def test_get_project_returns_none_for_missing_slug(self, tmp_path: Path) -> None:
        """get_project returns None for non-existent slug."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)

        # Act
        result = cache.get_project("nonexistent")

        # Assert
        assert result is None

    def test_set_and_get_project(self, tmp_path: Path) -> None:
        """set_project followed by get_project returns the data."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file)
        project_data = {"title": "Sodium", "id": "AANobbMI"}

        # Act
        cache.set_project("sodium", project_data)
        cache.flush()
        result = cache.get_project("sodium")

        # Assert
        assert result == project_data

    def test_cache_respects_ttl(self, tmp_path: Path) -> None:
        """Cache entries should expire after TTL."""
        # Arrange
        cache_file = tmp_path / "cache.json"
        cache = ApiCache(cache_file, ttl_seconds=1)  # 1 second TTL
        cache.set_project("sodium", {"title": "Sodium"})
        cache.flush()

        # Act - wait for TTL to expire
        time.sleep(1.1)
        result = cache.get_project("sodium")

        # Assert - should return None after expiration
        assert result is None
