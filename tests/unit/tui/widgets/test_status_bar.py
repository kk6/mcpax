"""Tests for StatusBar widget."""

from pathlib import Path

import pytest
from textual.app import App, ComposeResult

from mcpax.core.models import AppConfig, Loader
from mcpax.tui.widgets import StatusBar


def create_test_config() -> AppConfig:
    """Create a test AppConfig instance."""
    return AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=Loader.IRIS,
        minecraft_dir=Path("/tmp/.minecraft"),
    )


@pytest.mark.asyncio
async def test_status_bar_with_config() -> None:
    """Test StatusBar initialization with config."""
    config = create_test_config()
    status_bar = StatusBar(config=config)

    # Status bar should be instantiated
    assert status_bar is not None


@pytest.mark.asyncio
async def test_status_bar_without_config() -> None:
    """Test StatusBar initialization without config."""
    status_bar = StatusBar(config=None)

    # Status bar should be instantiated
    assert status_bar is not None


@pytest.mark.asyncio
async def test_status_bar_render_with_config() -> None:
    """Test StatusBar renders correct text with config."""
    config = create_test_config()
    status_bar = StatusBar(config=config)

    # Render should return formatted config info
    rendered = status_bar.render()
    assert "MC: 1.21.4" in rendered
    assert "Loader: Fabric" in rendered


@pytest.mark.asyncio
async def test_status_bar_render_without_config() -> None:
    """Test StatusBar renders message when config is None."""
    status_bar = StatusBar(config=None)

    # Render should return message indicating config not loaded
    rendered = status_bar.render()
    assert "Config not loaded" in rendered


@pytest.mark.asyncio
async def test_status_bar_update_config() -> None:
    """Test StatusBar can update config after initialization."""
    status_bar = StatusBar(config=None)

    # Initially should show no config message
    rendered = status_bar.render()
    assert "Config not loaded" in rendered

    # Update with config
    config = create_test_config()
    status_bar.update_config(config)

    # After update, should show config info
    rendered = status_bar.render()
    assert "MC: 1.21.4" in rendered
    assert "Loader: Fabric" in rendered


@pytest.mark.asyncio
async def test_status_bar_in_app() -> None:
    """Test StatusBar integration in a minimal app."""

    class TestApp(App[None]):
        """Minimal app for testing StatusBar."""

        def compose(self) -> ComposeResult:
            config = create_test_config()
            yield StatusBar(config=config)

    app = TestApp()
    async with app.run_test():
        # Check that StatusBar is rendered
        status_bar = app.query_one(StatusBar)
        assert status_bar is not None

        # Check rendered content
        rendered = status_bar.render()
        assert "MC: 1.21.4" in rendered
        assert "Loader: Fabric" in rendered


@pytest.mark.asyncio
async def test_status_bar_with_shader_loader() -> None:
    """Test StatusBar displays shader loader when available."""
    config = create_test_config()
    status_bar = StatusBar(config=config)

    rendered = status_bar.render()
    # Should show both mod loader and shader loader
    assert "Loader: Fabric" in rendered
    # Shader loader should be shown separately or indicated
    assert "Iris" in rendered or "iris" in rendered.lower()


@pytest.mark.asyncio
async def test_status_bar_without_shader_loader() -> None:
    """Test StatusBar when shader_loader is None."""
    config = AppConfig(
        minecraft_version="1.21.4",
        mod_loader=Loader.FABRIC,
        shader_loader=None,
        minecraft_dir=Path("/tmp/.minecraft"),
    )
    status_bar = StatusBar(config=config)

    rendered = status_bar.render()
    assert "MC: 1.21.4" in rendered
    assert "Loader: Fabric" in rendered
    # Should not mention shader loader
    assert "Iris" not in rendered
