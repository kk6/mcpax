"""Shared test fixtures."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mcpax.core.api import ModrinthClient
from mcpax.core.models import (
    Loader,
    ModrinthProject,
    ProjectType,
    ProjectVersion,
    ReleaseChannel,
    SearchResult,
)
from mcpax.core.version_resolver import VersionCriteria, VersionResolver


class FakeModrinthClient:
    """In-memory Modrinth API fake for business logic tests."""

    def __init__(self) -> None:
        self.projects: dict[str, ModrinthProject] = {}
        self.versions: dict[str, list[ProjectVersion]] = {}
        self.search_result = SearchResult(hits=[], total_hits=0, offset=0, limit=0)
        self.version_resolver = VersionResolver()

    async def get_project(self, slug: str) -> ModrinthProject:
        return self.projects[slug]

    async def get_versions(self, slug: str) -> list[ProjectVersion]:
        return self.versions.get(slug, [])

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        facets: str | None = None,
    ) -> SearchResult:
        return self.search_result

    def get_latest_compatible_version(
        self,
        versions: list[ProjectVersion],
        minecraft_version: str,
        loader: Loader,
        channel: ReleaseChannel = ReleaseChannel.RELEASE,
        project_type: ProjectType | None = None,
        shader_loader: Loader | None = None,
    ) -> ProjectVersion | None:
        return self.version_resolver.latest_compatible_version(
            versions,
            VersionCriteria(
                minecraft_version=minecraft_version,
                mod_loader=loader,
                channel=channel,
                project_type=project_type,
                shader_loader=shader_loader,
            ),
        )


@pytest.fixture(autouse=True)
def fixed_terminal_width(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix terminal width for consistent Rich output across different environments.

    This prevents CI/local environment differences in terminal width from causing
    test failures due to line wrapping in Rich console output.
    """
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("LINES", "50")


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


@pytest.fixture
def fake_modrinth_client() -> FakeModrinthClient:
    """Return an in-memory Modrinth API fake."""
    return FakeModrinthClient()


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
        date_published=date_published or datetime(2024, 1, 1, tzinfo=UTC),
    )
