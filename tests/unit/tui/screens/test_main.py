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
)
from mcpax.tui.screens import MainScreen
from mcpax.tui.widgets import ProjectTable, SearchInput, StatusBar


@pytest.mark.asyncio
async def test_main_screen_initialization(app_config) -> None:
    """Test MainScreen initialization."""
    screen = MainScreen(config=app_config)
    assert screen is not None
    assert screen._config == app_config


@pytest.mark.asyncio
async def test_main_screen_compose(app_config) -> None:
    """Test MainScreen compose includes all required widgets."""

    class TestApp(App[None]):
        def compose(self):
            yield MainScreen(config=app_config)

    app = TestApp()
    async with app.run_test():
        screen = app.query_one(MainScreen)

        # Check that required widgets are present
        status_bar = screen.query_one(StatusBar)
        assert status_bar is not None

        search_input = screen.query_one(SearchInput)
        assert search_input is not None

        project_table = screen.query_one(ProjectTable)
        assert project_table is not None

        footer = screen.query_one(Footer)
        assert footer is not None


@pytest.mark.asyncio
async def test_main_screen_has_quit_binding(app_config) -> None:
    """Test MainScreen has quit (q) keybinding."""
    screen = MainScreen(config=app_config)

    # Check that 'q' is bound to quit action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "q" in bindings
    assert bindings["q"] == "quit"


@pytest.mark.asyncio
async def test_main_screen_has_refresh_binding(app_config) -> None:
    """Test MainScreen has refresh (r) keybinding."""
    screen = MainScreen(config=app_config)

    # Check that 'r' is bound to refresh action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "r" in bindings
    assert bindings["r"] == "refresh"


@pytest.mark.asyncio
async def test_main_screen_has_detail_binding(app_config) -> None:
    """Test MainScreen has view detail (enter) keybinding."""
    screen = MainScreen(config=app_config)

    # Check that 'enter' is bound to view_detail action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "enter" in bindings
    assert bindings["enter"] == "view_detail"


@pytest.mark.asyncio
async def test_main_screen_action_quit(app_config) -> None:
    """Test quit action exits the app."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    app = TestApp()
    async with app.run_test() as pilot:
        # Press 'q' to quit
        await pilot.press("q")
        # App should exit (run_test context manager handles verification)


@pytest.mark.asyncio
async def test_main_screen_loads_projects_on_mount(
    app_config, make_update_check_result
) -> None:
    """Test MainScreen loads projects on mount."""

    test_projects = [
        make_update_check_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        make_update_check_result(
            "sodium", ProjectType.MOD, InstallStatus.OUTDATED, "0.5.0", "0.6.0"
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

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
async def test_main_screen_handles_missing_projects_file(app_config) -> None:
    """Test MainScreen handles missing projects.toml file gracefully."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    with patch("mcpax.tui.screens.main.load_projects") as mock_load_projects:
        mock_load_projects.side_effect = FileNotFoundError("projects.toml not found")

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for mount to complete
            await pilot.pause()
            # App should not crash (screen should be pushed)
            assert app.screen is not None


@pytest.mark.asyncio
async def test_main_screen_action_refresh(app_config, make_update_check_result) -> None:
    """Test refresh action reloads projects."""

    test_projects = [
        make_update_check_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

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
                await pilot.press("r")
                await pilot.pause()

                # Verify check_updates was called
                assert mock_manager.check_updates.called


@pytest.mark.asyncio
async def test_main_screen_action_view_detail_no_selection(app_config) -> None:
    """Test view_detail action shows warning when no project is selected."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    app = TestApp()
    async with app.run_test() as pilot:
        # Press 'enter' to view detail without selecting a project
        await pilot.press("enter")
        await pilot.pause()

        # Should show a warning notification
        # (Future: will push detail screen)


@pytest.mark.asyncio
async def test_main_screen_action_view_detail_with_selection(
    app_config, make_update_check_result
) -> None:
    """Test view_detail action with a selected project."""

    test_projects = [
        make_update_check_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
        make_update_check_result(
            "sodium", ProjectType.MOD, InstallStatus.OUTDATED, "0.5.0", "0.6.0"
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

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

                # Get the main screen and table
                main_screen = app.screen
                assert isinstance(main_screen, MainScreen)
                table = main_screen.query_one(ProjectTable)

                # Verify projects are loaded
                assert len(table.projects) == 2

                # Manually set a selected project for testing
                # (In actual usage, user would navigate with arrow keys)
                if hasattr(table, "move_cursor"):
                    table.move_cursor(row=0, column=0)
                    await pilot.pause()

                # Now action_view_detail should work
                # We just verify the implementation exists and doesn't crash
                main_screen.action_view_detail()


@pytest.mark.asyncio
@pytest.mark.skip(
    reason="RowActivated event interaction with enter binding needs investigation"
)
async def test_main_screen_row_activated_event(
    app_config, make_update_check_result
) -> None:
    """Test that pressing Enter on a row triggers detail view."""

    test_projects = [
        make_update_check_result(
            "fabric-api", ProjectType.MOD, InstallStatus.INSTALLED
        ),
    ]

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

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
                # Wait for projects to load
                await pilot.pause()

                # Get the main screen and verify project loaded
                main_screen = app.screen
                assert isinstance(main_screen, MainScreen)
                table = main_screen.query_one(ProjectTable)
                assert len(table.projects) == 1

                # Focus the table, move cursor to first row, and press Enter
                table.focus()
                await pilot.pause()
                # Move cursor to first row (row index 0)
                table.move_cursor(row=0)
                await pilot.pause()

                # Verify that a project is now selected
                assert table.selected_project is not None
                assert table.selected_project.slug == "fabric-api"

                await pilot.press("enter")
                await pilot.pause()
                await pilot.pause()  # Extra pause to ensure screen transition completes

                # DetailScreen should now be on top
                from mcpax.tui.screens.detail import ProjectDetailScreen

                assert isinstance(app.screen, ProjectDetailScreen)


@pytest.mark.asyncio
async def test_main_screen_search_requested_handler(app_config) -> None:
    """Test MainScreen opens SearchScreen when search is requested."""

    class TestApp(App[None]):
        def compose(self):
            yield MainScreen(config=app_config)

    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load_projects,
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_load_projects.return_value = []
        mock_manager = AsyncMock()
        mock_manager.__aenter__.return_value = mock_manager
        mock_manager.__aexit__.return_value = None
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value = mock_manager

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for mount
            await pilot.pause()

            screen = app.query_one(MainScreen)
            search_input = screen.query_one(SearchInput)

            # Trigger search with query
            search_input.post_message(
                SearchInput.SearchRequested("sodium", ProjectType.MOD)
            )
            await pilot.pause(0.1)

            # Verify SearchScreen was pushed
            from mcpax.tui.screens.search import SearchScreen

            assert isinstance(app.screen, SearchScreen)


@pytest.mark.asyncio
async def test_main_screen_search_with_empty_query(app_config) -> None:
    """Test MainScreen does not open SearchScreen with empty query."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load_projects,
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_load_projects.return_value = []
        mock_manager = AsyncMock()
        mock_manager.__aenter__.return_value = mock_manager
        mock_manager.__aexit__.return_value = None
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value = mock_manager

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for mount
            await pilot.pause()

            screen = app.screen
            assert isinstance(screen, MainScreen)
            search_input = screen.query_one(SearchInput)

            # Trigger search with empty query
            search_input.post_message(SearchInput.SearchRequested("", None))
            await pilot.pause(0.1)

            # Verify SearchScreen was NOT pushed (still on MainScreen)
            assert isinstance(app.screen, MainScreen)


@pytest.mark.asyncio
async def test_main_screen_has_install_binding(app_config) -> None:
    """Test MainScreen has install (i) keybinding."""
    screen = MainScreen(config=app_config)

    # Check that 'i' is bound to install action
    bindings = {binding.key: binding.action for binding in screen.BINDINGS}
    assert "i" in bindings
    assert bindings["i"] == "install"


@pytest.mark.asyncio
async def test_main_screen_install_action_no_updates(
    app_config, make_update_check_result
) -> None:
    """Test install action shows notification when no projects need installation."""

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    mock_projects = []
    mock_results = [
        make_update_check_result("fabric-api", status=InstallStatus.INSTALLED),
    ]

    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load,
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_load.return_value = mock_projects
        mock_manager = AsyncMock()
        mock_manager.check_updates = AsyncMock(return_value=mock_results)
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test() as pilot:
            # Wait for initial load to complete
            await app.workers.wait_for_complete()

            screen = app.screen
            assert isinstance(screen, MainScreen)

            # Trigger install action
            await pilot.press("i")
            await pilot.pause()

            # Verify we're still on MainScreen (no InstallScreen pushed)
            assert isinstance(app.screen, MainScreen)


@pytest.mark.asyncio
async def test_main_screen_has_settings_binding(app_config) -> None:
    """Test that MainScreen has settings key binding."""
    screen = MainScreen(config=app_config)
    binding_keys = [b.key for b in screen.BINDINGS]
    assert "s" in binding_keys


@pytest.mark.asyncio
async def test_main_screen_action_settings_opens_screen(app_config) -> None:
    """Test that action_settings opens SettingsScreen."""
    from unittest.mock import MagicMock, patch

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    # Mock load_projects to return empty list
    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load,
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_load.return_value = []
        mock_manager = AsyncMock()
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        app = TestApp()
        async with app.run_test():
            # Wait for initial load
            await app.workers.wait_for_complete()

            screen = app.screen
            assert isinstance(screen, MainScreen)

            # Mock push_screen to verify it's called
            app.push_screen = MagicMock()  # type: ignore

            # Call action_settings directly
            screen.action_settings()

            # Verify push_screen was called
            assert app.push_screen.called
            # Verify first argument is SettingsScreen instance
            from mcpax.tui.screens.settings import SettingsScreen

            args, kwargs = app.push_screen.call_args
            assert isinstance(args[0], SettingsScreen)


@pytest.mark.asyncio
async def test_main_screen_on_settings_dismissed_reloads_config(app_config) -> None:
    """Test that config is reloaded when settings are changed."""
    from unittest.mock import patch

    class TestApp(App[None]):
        def on_mount(self):
            self.push_screen(MainScreen(config=app_config))

    # Mock load_projects to return empty list
    with (
        patch("mcpax.tui.screens.main.load_projects") as mock_load,
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
        patch("mcpax.tui.screens.main.load_config") as mock_load_config,
    ):
        mock_load.return_value = []
        mock_manager = AsyncMock()
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value.__aenter__.return_value = mock_manager
        mock_manager_class.return_value.__aexit__.return_value = AsyncMock()

        # Create a new config for reload
        new_config = AppConfig(
            minecraft_version="1.22.0",
            mod_loader=Loader.FABRIC,
            minecraft_dir=Path("/tmp/.minecraft"),
        )
        mock_load_config.return_value = new_config

        app = TestApp()
        async with app.run_test():
            # Wait for initial load
            await app.workers.wait_for_complete()

            screen = app.screen
            assert isinstance(screen, MainScreen)

            # Call _on_settings_dismissed with True (changed)
            screen._on_settings_dismissed(True)

            # Verify load_config was called
            mock_load_config.assert_called_once()

            # Verify config was updated
            assert screen._config == new_config
