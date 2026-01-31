"""StatusBar widget for displaying Minecraft configuration."""

from typing import Any

from textual.widgets import Static

from mcpax.core.models import AppConfig


class StatusBar(Static):
    """StatusBar widget to display Minecraft version and loader information."""

    def __init__(self, config: AppConfig | None = None, **kwargs: Any) -> None:
        """Initialize the StatusBar.

        Args:
            config: Application configuration (optional)
            **kwargs: Additional arguments passed to Static
        """
        super().__init__(**kwargs)
        self._config = config

    def render(self) -> str:
        """Render the status bar content.

        Returns:
            Formatted string with Minecraft version and loader information,
            or a message if config is not loaded.
        """
        if self._config is None:
            return "Config not loaded"

        parts = [
            f"MC: {self._config.minecraft_version}",
            f"Loader: {self._config.mod_loader.value.capitalize()}",
        ]

        if self._config.shader_loader is not None:
            parts.append(f"Shader: {self._config.shader_loader.value.capitalize()}")

        return "  ".join(parts)

    def update_config(self, config: AppConfig | None) -> None:
        """Update the configuration and refresh display.

        Args:
            config: New application configuration
        """
        self._config = config
        self.refresh()
