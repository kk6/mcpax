"""Main TUI application for mcpax."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header


class McpaxApp(App[None]):
    """Minecraft MOD/Shader/Resource Pack manager TUI."""

    TITLE = "mcpax"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield Footer()

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
