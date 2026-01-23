"""Tests for mcpax.tui.app module."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mcpax.core.config import ConfigValidationError
from mcpax.core.models import AppConfig, Loader
from mcpax.tui.app import McpaxApp
from mcpax.tui.screens import MainScreen
from mcpax.tui.widgets import StatusBar


@pytest.mark.asyncio
async def test_app_launches() -> None:
    """Test that the app can be instantiated and has correct title."""
    app = McpaxApp()
    async with app.run_test():
        assert app.title == "mcpax"


@pytest.mark.asyncio
async def test_app_quit_binding() -> None:
    """Test that pressing q exits the app."""
    app = McpaxApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        # In Textual's run_test(), calling exit exits the context manager
        # Reaching this point indicates the test has passed


@pytest.mark.asyncio
async def test_app_has_status_bar() -> None:
    """Test that the app includes StatusBar widget."""
    test_config = AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=None,
        minecraft_dir=Path("/tmp/.minecraft"),
    )

    with (
        patch("mcpax.tui.app.load_config", return_value=test_config),
        patch("mcpax.tui.screens.main.load_projects", return_value=[]),
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_manager = AsyncMock()
        mock_manager.__aenter__.return_value = mock_manager
        mock_manager.__aexit__.return_value = None
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value = mock_manager

        app = McpaxApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # MainScreen should be active
            main_screen = app.screen
            assert isinstance(main_screen, MainScreen)

            # Check that StatusBar is in MainScreen
            status_bar = main_screen.query_one(StatusBar)
            assert status_bar is not None


@pytest.mark.asyncio
async def test_app_loads_config_successfully() -> None:
    """Test that the app loads config successfully when available."""
    test_config = AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=None,
        minecraft_dir=Path("/tmp/.minecraft"),
    )

    with (
        patch("mcpax.tui.app.load_config", return_value=test_config),
        patch("mcpax.tui.screens.main.load_projects", return_value=[]),
        patch("mcpax.tui.screens.main.ProjectManager") as mock_manager_class,
    ):
        mock_manager = AsyncMock()
        mock_manager.__aenter__.return_value = mock_manager
        mock_manager.__aexit__.return_value = None
        mock_manager.check_updates = AsyncMock(return_value=[])
        mock_manager_class.return_value = mock_manager

        app = McpaxApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            # Check that config was loaded
            assert app._config is not None
            assert app._config.minecraft_version == "1.21.4"

            # Check that StatusBar shows config
            main_screen = app.screen
            status_bar = main_screen.query_one(StatusBar)
            rendered = status_bar.render()
            assert "MC: 1.21.4" in rendered
            assert "Loader: Fabric" in rendered


@pytest.mark.asyncio
async def test_app_handles_missing_config() -> None:
    """Test that the app handles missing config gracefully."""
    with patch("mcpax.tui.app.load_config", side_effect=FileNotFoundError()):
        app = McpaxApp()
        # Config should be None
        assert app._config is None
        # App will exit on mount due to missing config


@pytest.mark.asyncio
async def test_app_handles_invalid_config() -> None:
    """Test that the app handles invalid config gracefully."""
    with patch(
        "mcpax.tui.app.load_config",
        side_effect=ConfigValidationError("Invalid config"),
    ):
        app = McpaxApp()
        # Config should be None
        assert app._config is None
        # App will exit on mount due to invalid config
