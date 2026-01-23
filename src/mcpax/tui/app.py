"""Main TUI application for mcpax."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from mcpax.core.config import ConfigValidationError, load_config
from mcpax.core.models import AppConfig
from mcpax.tui.widgets import StatusBar


class McpaxApp(App[None]):
    """Minecraft MOD/Shader/Resource Pack manager TUI."""

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "mcpax"
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        """Initialize the TUI application."""
        super().__init__()
        self._config: AppConfig | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from default path."""
        try:
            self._config = load_config()
        except (FileNotFoundError, ConfigValidationError):
            # Config will be None if not found or invalid
            self._config = None

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        yield Header()
        yield StatusBar(config=self._config)
        yield Footer()

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
