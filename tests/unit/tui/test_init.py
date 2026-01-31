"""Tests for mcpax.tui.__init__ module."""

from unittest.mock import MagicMock, patch

from mcpax.tui import run_tui


def test_run_tui() -> None:
    """Test that run_tui creates and runs the app."""
    with patch("mcpax.tui.McpaxApp") as mock_app_class:
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app

        run_tui()

        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()
