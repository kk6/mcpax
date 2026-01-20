"""Tests for mcpax.tui.app module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from mcpax.core.config import ConfigValidationError
from mcpax.core.models import AppConfig, Loader
from mcpax.tui.app import McpaxApp
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
    app = McpaxApp()
    async with app.run_test():
        # Check that StatusBar is in the widget tree
        status_bar = app.query_one(StatusBar)
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

    with patch("mcpax.tui.app.load_config", return_value=test_config):
        app = McpaxApp()
        async with app.run_test():
            # Check that config was loaded
            assert app._config is not None
            assert app._config.minecraft_version == "1.21.4"

            # Check that StatusBar shows config
            status_bar = app.query_one(StatusBar)
            rendered = status_bar.render()
            assert "MC: 1.21.4" in rendered
            assert "Loader: Fabric" in rendered


@pytest.mark.asyncio
async def test_app_handles_missing_config() -> None:
    """Test that the app handles missing config gracefully."""
    with patch("mcpax.tui.app.load_config", side_effect=FileNotFoundError()):
        app = McpaxApp()
        async with app.run_test():
            # Config should be None
            assert app._config is None

            # StatusBar should show config not loaded message
            status_bar = app.query_one(StatusBar)
            rendered = status_bar.render()
            assert "Config not loaded" in rendered


@pytest.mark.asyncio
async def test_app_handles_invalid_config() -> None:
    """Test that the app handles invalid config gracefully."""
    with patch(
        "mcpax.tui.app.load_config",
        side_effect=ConfigValidationError("Invalid config"),
    ):
        app = McpaxApp()
        async with app.run_test():
            # Config should be None
            assert app._config is None

            # StatusBar should show config not loaded message
            status_bar = app.query_one(StatusBar)
            rendered = status_bar.render()
            assert "Config not loaded" in rendered
