"""Tests for TUI styles and CSS configuration."""

from pathlib import Path

import pytest

from mcpax.tui.app import McpaxApp


@pytest.mark.asyncio
async def test_app_has_css_path() -> None:
    """Test that McpaxApp has CSS_PATH attribute."""
    app = McpaxApp()
    async with app.run_test():
        assert hasattr(app, "CSS_PATH")
        assert app.CSS_PATH is not None


@pytest.mark.asyncio
async def test_css_path_points_to_app_tcss() -> None:
    """Test that CSS_PATH points to app.tcss in styles directory."""
    app = McpaxApp()
    async with app.run_test():
        css_path = app.CSS_PATH
        # CSS_PATH should be a Path object or string
        if isinstance(css_path, str):
            css_path = Path(css_path)

        assert css_path.name == "app.tcss"
        assert css_path.parent.name == "styles"


@pytest.mark.asyncio
async def test_css_file_exists() -> None:
    """Test that the CSS file exists at the specified path."""
    app = McpaxApp()
    async with app.run_test():
        css_path = app.CSS_PATH
        if isinstance(css_path, str):
            css_path = Path(css_path)

        assert css_path.exists(), f"CSS file not found at {css_path}"
        assert css_path.is_file(), f"CSS path is not a file: {css_path}"
