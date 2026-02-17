"""Simple on-disk cache for Modrinth API responses."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Self, cast

logger = logging.getLogger(__name__)


class ApiCache:
    """Tiny TTL cache backed by a JSON file."""

    def __init__(self, path: Path, ttl_seconds: int = 300) -> None:
        self._path = path
        self._ttl_seconds = ttl_seconds
        self._data: dict[str, dict[str, dict[str, object]]] = {
            "project": {},
            "versions": {},
        }
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if isinstance(data, dict):
            self._data["project"] = data.get("project", {}) or {}
            self._data["versions"] = data.get("versions", {}) or {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data))
        except OSError as e:
            logger.warning("Failed to save cache to %s: %s", self._path, e)
            return

    def _is_fresh(self, ts: float) -> bool:
        return (time.time() - ts) <= self._ttl_seconds

    def flush(self) -> None:
        """Write cache to disk if dirty."""
        if self._dirty:
            self._save()
            self._dirty = False

    def get_project(self, slug: str) -> dict | None:
        entry = self._data["project"].get(slug)
        if not isinstance(entry, dict):
            return None
        ts = entry.get("ts")
        data = entry.get("data")
        if (
            isinstance(ts, int | float)
            and isinstance(data, dict)
            and self._is_fresh(ts)
        ):
            return data
        return None

    def set_project(self, slug: str, data: dict) -> None:
        self._data["project"][slug] = {"ts": time.time(), "data": data}
        self._dirty = True

    def get_versions(self, slug: str) -> list[dict] | None:
        entry = self._data["versions"].get(slug)
        if not isinstance(entry, dict):
            return None
        ts = entry.get("ts")
        data = entry.get("data")
        if (
            isinstance(ts, int | float)
            and isinstance(data, list)
            and self._is_fresh(ts)
        ):
            return cast(list[dict], data)
        return None

    def set_versions(self, slug: str, data: list[dict]) -> None:
        self._data["versions"][slug] = {"ts": time.time(), "data": data}
        self._dirty = True

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - flush cache to disk."""
        self.flush()
