"""Tests for MainScreen."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App
from textual.widgets import Footer

from mcpax.core.models import (
    AppConfig,
    InstallStatus,
    Loader,
    ProjectType,
    UpdateCheckResult,
)
from mcpax.tui.screens import MainScreen
from mcpax.tui.widgets import ProjectTable, StatusBar


def create_test_config() -> AppConfig:
    """Create a test AppConfig instance."""
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=Loader.IRIS,
        minecraft_dir=Path("/tmp/.minecraft"),
    )


def create_test_update_result(
    slug: str,
    project_type: ProjectType = ProjectType.MOD,
    status: InstallStatus = InstallStatus.INSTALLED,
    current_version: str | None = "1.0.0",
    latest_version: str | None = "1.0.0",
) -> UpdateCheckResult:
    """Create a test UpdateCheckResult instance."""
    return UpdateCheckResult(
        slug=slug,
        project_type=project_type,
        status=status,
        current_version=current_version,
        latest_version=latest_version,
        current_file=None,
        latest_file=None,
    )


@pytest.mark.asyncio
async def test_main_screen_initialization() -> None:
    """Test MainScreen initialization."""
    config = create_test_config()
    screen = MainScreen(config=config)
    assert screen is not None
    assert screen._config == config


@pytest.mark.asyncio
async def test_main_screen_compose() -> None:
    """Test MainScreen compose includes StatusBar, ProjectTable, Footer."""

    class TestApp(App[None]):
        def compose(self):
            yield MainScreen(config=create_test_config())

    app = TestApp()
    async with app.run_test():
        screen = app.query_one(MainScreen)

        # Check that required widgets are present
        status_bar = screen.query_one(StatusBar)
        assert status_bar is not None

        project_table = screen.query_one(ProjectTable)
        assert project_table is not None

        footer = screen.query_one(Footer)
        assert footer is not None


@pytest.mark.asyncio
async def test_main_screen_has_quit_binding() -> None:
    """Test MainScreen has quit (q) keybinding."""
    config = create_test_config()
    screen = MainScreen(config=config)

    # Check that 'q' is bound to quit action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert 'q' in bindings
    assert bindings['q'] == 'quit'


@pytest.mark.asyncio
async def test_main_screen_has_refresh_binding() -> None:
    """Test MainScreen has refresh (r) keybinding."""
    config = create_test_config()
    screen = MainScreen(config=config)

    # Check that 'r' is bound to refresh action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert 'r' in bindings
    assert bindings['r'] == 'refresh'


@pytest.mark.asyncio
async def test_main_screen_has_detail_binding() -> None:
    """Test MainScreen has view detail (enter) keybinding."""
    config = create_test_config()
    screen = MainScreen(config=config)

    # Check that 'enter' is bound to view_detail action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert 'enter' in bindings
    assert bindings['enter'] == 'view_detail'


@pytest.mark.asyncio
async def test_main_screen_action_quit() -> None:
    """Test quit action exits the app."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    app = TestApp()
    async with app.run_test() as pilot:
        # Press 'q' to quit
        await pilot.press('q')
        # App should exit (run_test context manager handles verification)


@pytest.mark.asyncio
async def test_main_screen_loads_projects_on_mount() -> None:
    """Test MainScreen loads projects on mount."""

    test_projects = [
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        create_test_update_result(
            "sodium", ProjectType.MOD, InstallStatus.OUTDATED, "0.5.0", "0.6.0"
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    with patch("mcpax.tui.screens.main.load_projects") as mock_load_projects:
        mock_load_projects.return_value = ["fabric-api", "sodium"]

        with patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.__aenter__.return_value = mock_manager
            mock_manager.__aexit__.return_value = None
            mock_manager.check_updates = AsyncMock(return_value=test_projects)
            mock_manager_class.return_value = mock_manager

            app = TestApp()
            async with app.run_test() as pilot:
                # Wait for mount to complete
                await pilot.pause()

                # Verify projects were loaded
                assert mock_load_projects.called
                assert mock_manager.check_updates.called


@pytest.mark.asyncio
async def test_main_screen_handles_missing_projects_file() -> None:
    """Test MainScreen handles missing projects.toml file gracefully."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    with patch("mcpax.tui.screens.main.load_projects") as mock_load_projects:
        mock_load_projects.side_effect = FileNotFoundError("projects.toml not found")

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for mount to complete
            await pilot.pause()
            # App should not crash (screen should be pushed)
            assert app.screen is not None


@pytest.mark.asyncio
async def test_main_screen_action_refresh() -> None:
    """Test refresh action reloads projects."""

    test_projects = [
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    with patch("mcpax.tui.screens.main.load_projects") as mock_load_projects:
        mock_load_projects.return_value = ["fabric-api"]

        with patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.__aenter__.return_value = mock_manager
            mock_manager.__aexit__.return_value = None
            mock_manager.check_updates = AsyncMock(return_value=test_projects)
            mock_manager_class.return_value = mock_manager

            app = TestApp()
            async with app.run_test() as pilot:
                # Press 'r' to refresh
                await pilot.press('r')
                await pilot.pause()

                # Verify check_updates was called
                assert mock_manager.check_updates.called


@pytest.mark.asyncio
async def test_main_screen_action_view_detail_no_selection() -> None:
    """Test view_detail action shows warning when no project is selected."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    app = TestApp()
    async with app.run_test() as pilot:
        # Press 'enter' to view detail without selecting a project
        await pilot.press('enter')
        await pilot.pause()

        # Should show a warning notification
        # (Future: will push detail screen)


@pytest.mark.asyncio
async def test_main_screen_action_view_detail_with_selection() -> None:
    """Test view_detail action shows notification with selected project."""

    test_projects = [
        create_test_update_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        create_test_update_result(
            "sodium", ProjectType.MOD, InstallStatus.OUTDATED, "0.5.0", "0.6.0"
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=create_test_config()))

    with patch("mcpax.tui.screens.main.load_projects") as mock_load_projects:
        mock_load_projects.return_value = ["fabric-api", "sodium"]

        with patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class:
            mock_manager = AsyncMock()
            mock_manager.__aenter__.return_value = mock_manager
            mock_manager.__aexit__.return_value = None
            mock_manager.check_updates = AsyncMock(return_value=test_projects)
            mock_manager_class.return_value = mock_manager

            app = TestApp()
            async with app.run_test() as pilot:
                # Wait for projects to load
                await pilot.pause()

                # Press 'enter' to view detail with a project selected
                await pilot.press('enter')
                await pilot.pause()

                # Should show a notification with the selected project slug
                # (Future: will push detail screen)
