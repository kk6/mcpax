"""Main TUI application for mcpax."""

from pathlib import Path

from textual.app import App

from mcpax.core.config import ConfigValidationError, load_config
from mcpax.core.models import AppConfig
from mcpax.tui.screens import MainScreen


class McpaxApp(App[None]):
    """Minecraft MOD/Shader/Resource Pack manager TUI."""

    CSS_PATH = Path(__file__).parent / "styles" / "app.tcss"
    TITLE = "mcpax"

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

    def on_mount(self) -> None:
        """Push MainScreen when app is mounted."""
        if self._config is not None:
            self.push_screen(MainScreen(config=self._config))
        else:
            self.exit(message="Error: Configuration not found or invalid")
