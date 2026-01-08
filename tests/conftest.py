"""Shared test fixtures."""

from pathlib import Path

import pytest


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
