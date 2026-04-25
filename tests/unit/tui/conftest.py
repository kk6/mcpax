"""Shared fixtures for TUI tests."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mcpax.core.models import (
    AppConfig,
    InstallStatus,
    Loader,
    ProjectType,
    SearchHit,
    UpdateCheckResult,
)

# Data Factory Fixtures


@pytest.fixture
def app_config() -> AppConfig:
    """Create a standard AppConfig instance for testing.

    Returns:
        AppConfig: Standard test configuration with typical values.
    """
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=Loader.IRIS,
        minecraft_dir=Path("/tmp/.minecraft"),
    )


@pytest.fixture(scope="session")
def make_update_check_result():
    """Create UpdateCheckResult factory fixture.

    Returns:
        Callable: Factory function that creates UpdateCheckResult instances.
    """

    def _make_result(
        slug: str,
        project_type: ProjectType = ProjectType.MOD,
        status: InstallStatus = InstallStatus.INSTALLED,
        current_version: str | None = "1.0.0",
        latest_version: str | None = "1.0.0",
        error: str | None = None,
    ) -> UpdateCheckResult:
        """Create a test UpdateCheckResult instance.

        Args:
            slug: Project slug identifier
            project_type: Type of project (mod, shader, etc.)
            status: Installation status
            current_version: Current installed version
            latest_version: Latest available version
            error: Optional error message

        Returns:
            UpdateCheckResult: Test instance
        """
        return UpdateCheckResult(
            slug=slug,
            project_type=project_type,
            status=status,
            current_version=current_version,
            latest_version=latest_version,
            current_file=None,
            latest_file=None,
            error=error,
        )

    return _make_result


@pytest.fixture(scope="session")
def make_search_hit():
    """Create SearchHit factory fixture.

    Returns:
        Callable: Factory function that creates SearchHit instances.
    """

    def _make_hit(
        slug: str,
        title: str,
        project_type: ProjectType = ProjectType.MOD,
        downloads: int = 1000,
        description: str = "Test description",
    ) -> SearchHit:
        """Create a test SearchHit instance.

        Args:
            slug: Project slug identifier
            title: Project display title
            project_type: Type of project
            downloads: Number of downloads
            description: Project description

        Returns:
            SearchHit: Test instance
        """
        return SearchHit(
            slug=slug,
            title=title,
            description=description,
            project_type=project_type,
            downloads=downloads,
            icon_url=None,
        )

    return _make_hit


# Mock Fixtures


@pytest.fixture
def mock_project_services():
    """Create configured ProjectServices AsyncMock.

    Returns:
        AsyncMock: Mock with __aenter__, __aexit__, update_checker, and update_applier
                   configured for async context manager usage.
    """
    mock = AsyncMock()
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    mock.update_checker.check_updates = AsyncMock(return_value=[])
    mock.update_applier.apply_updates = AsyncMock()
    return mock


@pytest.fixture
def mock_load_projects():
    """Create patched load_projects function.

    Yields:
        MagicMock: Patched load_projects that returns empty list by default.
    """
    with patch("mcpax.tui.screens.main.load_projects") as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_modrinth_client():
    """Create configured ModrinthClient AsyncMock.

    Returns:
        AsyncMock: Mock with __aenter__, __aexit__, and search method configured
                   for async context manager usage.
    """
    mock = AsyncMock()
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    mock.search = AsyncMock()
    return mock


@pytest.fixture
def mock_downloader():
    """Create configured Downloader AsyncMock.

    Returns:
        AsyncMock: Mock with __aenter__ and __aexit__ configured
                   for async context manager usage.
    """
    mock = AsyncMock()
    mock.__aenter__.return_value = mock
    mock.__aexit__.return_value = None
    return mock


# Test App Fixtures for MainScreen


@pytest.fixture
def patched_main_screen_dependencies():
    """Patch dependencies for MainScreen tests.

    Yields:
        tuple: (mock_load_projects, mock_manager_class, mock_manager)
    """
    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load,
        patch("mcpax.tui.screens.main.ProjectServices") as mock_manager_class,
    ):
        mock_load.return_value = []
        mock_manager = AsyncMock()
        mock_manager.update_checker.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()
        yield mock_load, mock_manager_class, mock_manager


# Test App Fixtures for SettingsScreen


@pytest.fixture
def settings_config_path(tmp_path: Path) -> Path:
    """Create a temporary config.toml for SettingsScreen tests.

    Args:
        tmp_path: Pytest temporary directory

    Returns:
        Path: Path to temporary config file
    """
    config_path = tmp_path / "config.toml"
    config_path.write_text("""[minecraft]
version = "1.21.4"
mod_loader = "fabric"

[paths]
minecraft_dir = "/tmp/.minecraft"
""")
    return config_path
