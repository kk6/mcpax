"""TUI interface for mcpax."""

from mcpax.tui.app import McpaxApp

__all__ = ["McpaxApp", "run_tui"]


def run_tui() -> None:
    """Run the TUI application."""
    app = McpaxApp()
    app.run()
