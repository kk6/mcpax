"""Shared test fixtures."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcpax.core.api import ModrinthClient
from mcpax.core.models import ProjectVersion, ReleaseChannel


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


def _make_version(
    version_number: str,
    game_versions: list[str] | None = None,
    loaders: list[str] | None = None,
    version_type: ReleaseChannel = ReleaseChannel.RELEASE,
    date_published: datetime | None = None,
) -> ProjectVersion:
    """Helper to create ProjectVersion for tests."""
    return ProjectVersion(
        id=f"id-{version_number}",
        project_id="test-project",
        version_number=version_number,
        version_type=version_type,
        game_versions=game_versions or ["1.21.4"],
        loaders=loaders or ["fabric"],
        files=[],
        dependencies=[],
        date_published=date_published or datetime.now(UTC),
    )
