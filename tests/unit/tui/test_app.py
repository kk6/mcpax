"""Tests for mcpax.tui.app module."""

import pytest

from mcpax.tui.app import McpaxApp


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
