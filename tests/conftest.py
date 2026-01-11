"""Shared test fixtures."""

from pathlib import Path

import pytest

from mcpax.core.api import ModrinthClient


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config(fixtures_dir: Path) -> Path:
    """Return the path to the sample config.toml."""
    return fixtures_dir / "config.toml"


@pytest.fixture
def sample_projects(fixtures_dir: Path) -> Path:
    """Return the path to the sample projects.toml."""
    return fixtures_dir / "projects.toml"


@pytest.fixture
def fast_api_client() -> ModrinthClient:
    """Return a ModrinthClient with zero backoff for fast testing.

    This fixture creates a ModrinthClient with backoff_factor=0 to avoid
    waiting during retry operations in tests, significantly speeding up
    tests that simulate API errors.
    """
    return ModrinthClient(backoff_factor=0)
